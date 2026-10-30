"""
S&OP Cycle Agent: safety stock policy, supplier risk changes, Spike POs and gaps for one S&OP cycle.

What it does:
  1. policy.py (code, no AI) decides every number: material class, safety stock target, change or no change,
     supplier tier changes and the 30-day rules, spike patterns, Spike PO quantity and order-by date,
     supplier-check flag, projected gaps, forecast accuracy, custom-item buy decisions.
  2. For each material, Claude investigates with TOOLS (get_material_facts, get_supplier_risk, get_orders)
     and writes a short brief (submit_brief): what changed, the safety stock recommendation, the buyer message
     for a Spike PO, custom-item buys, forecast notes and any decision needed.
  3. sop_checks.py (code) checks the writing. A failed brief is sent back ONCE with exact fixes; if it still
     fails it is saved and marked NEEDS HUMAN REVIEW.
  4. Claude then writes the cycle executive summary from a code-built fact sheet (also checked).
  5. Output: sop_pre_read.md (the pre-read) and sop_results.json.

The agent NEVER changes data, places an order or contacts a supplier. It only drafts.
Run order:   python policy.py (optional: see the decisions)  then  python agent.py
"""
import json
from datetime import timedelta

import anthropic
import pandas as pd

import policy
import sop_checks as ck

# ------------------------------------------------------------------
# SETTINGS (edit these)
# ------------------------------------------------------------------
MODEL = "claude-haiku-4-5-20251001"   # smallest, cheapest Claude model
MAX_MATERIALS = 3                     # materials to draft. Raise to 17 after a test run.
ONLY_MATERIALS = []                   # or pick yourself, e.g. ["ITM-001", "ITM-008"]
WRITE_SUMMARY = True                  # also write the cycle executive summary
MAX_TURNS = 8
PRICE_IN = 1.00                       # $ per million input tokens (rough estimate, check current pricing)
PRICE_OUT = 5.00                      # $ per million output tokens (rough estimate, check current pricing)

SYSTEM_PROMPT = """You are a supply planning analyst assistant drafting a short S&OP brief for ONE material.
Do this:
1. Call get_material_facts, get_supplier_risk and get_orders for the material.
2. Call submit_brief exactly once.

Rules:
- Use only facts from the tool results. Never invent numbers, dates, causes or IDs.
- Every decision (safety stock target, change or no change, Spike PO quantity, order-by date, supplier check, buy or
  do-not-buy) is made by the system. Quote it exactly. Never recalculate or round differently.
- Quote numbers exactly as given (write 5000 or 5,000). For dollar amounts use the *_text version exactly. Do NOT calculate new numbers (no sums, differences or percentages).
- get_material_facts returns must_cover: a list of things the brief must say. Cover every one, in your own words.
- Fields (each short, plain language, written so a planner or buyer can act on it):
    headline: the one-sentence recommendation.
    what_changed: supplier tier change, spike pattern or demand change, with dates. If nothing changed, say so briefly.
    safety_stock_recommendation: target vs current, change or no change, the rule in plain words, reorder point and key dates if given.
    spike_po_message: the message to the buyer about a Spike PO (quantity, order-by date or order now or late, and the
      supplier-check wording when required). Empty string if the facts show no Spike PO trigger.
    custom_item_note: only for custom (intermittent) items: which lines to buy and the release dates, which not to buy and why. Else empty.
    forecast_note: only if accuracy flags are present (bias, override value, high error). Else empty.
    decision_note: only if an executive decision is needed: the gap, the first bucket, what leadership must decide. Else empty.
- Neutral, factual wording. Do not use dramatic words. Respect the word limits.
- The Spike PO quantity is already rounded up to whole supplier lots. Quote that quantity exactly; do not quote the calculated need.
- Write system labels (such as SUPPLIER_HIGH) in plain words. Mention only causes named in the facts; never write 'geopolitical'.
- A NOT_YET custom line is a 'future planned buy' (never a do-not-buy): use those words, say it is too early to release and will be reviewed in a later cycle.
- Custom buys are released on their release dates; say 'immediately' only for a BUY_LATE line.
- 'current' safety stock is NOT on-hand stock. Never call the current safety stock 'on-hand' or 'current stock'.
- Use 'raised' or 'moved to' for a supplier tier increase, never 'promoted'. Say 'immediately' only for an order-now Spike PO.
- Only tell the buyer to ask about extended lead time or partial deliveries when the facts say supplier_check_required is true.
- The projected gaps are calculated BEFORE any Spike PO; never say 'even with the Spike PO'. Say what the gap is and that the Spike PO would help close it.
- A reorder point exists only if the facts give one. Do not mention a reorder point otherwise.
- If the Spike PO timing is ORDER_BY, say 'order by <date>', not immediately or now. The order-by date has not passed unless the facts say ORDER_LATE.
- Write dates as MM-dd-yyyy exactly as the tool results show them.
- A custom buy with below_lot = Y is smaller than one supplier lot: tell the buyer to ask the supplier about a smaller quantity, or consider reworking similar on-hand material into the custom item.
- A Spike PO is a purchase order for extra supply. If stock already covers a spike order, say so and recommend no Spike PO.
- If the supplier check is required, tell the buyer to contact the supplier to find out whether lead time will be
  extended or whether partial deliveries will be planned to build and ship the higher quantity.
"""

SUMMARY_PROMPT = """You are drafting the executive summary for this month's S&OP cycle.
Call get_cycle_facts, then call submit_summary exactly once. Use only facts from get_cycle_facts; quote numbers, dates and IDs exactly (use the *_text dollar version);
do not calculate new numbers. Name every material in must_name_materials and every supplier in must_name_suppliers.
Rules: a Spike PO quantity is already in whole supplier lots; quote it exactly. A decision about a material may name only that material's own supplier
(see material_supplier). If timing is ORDER_LATE the order-by date has already passed: say the order is late and to ask the supplier about expediting; do not call it a shortage.
Do not use system labels such as SUPPLIER_HIGH; write plain words. Do not invent causes: say only what the facts name (for example typhoon, customs, earthquake alerts), never 'geopolitical'.
Do not add advice that is not in the facts. The agent only recommends: never say orders were 'placed'. Use upgrades and downgrades counts exactly; do not recount tier changes. Say 'immediately' only for orders due now; use 'raised', never 'promoted'. Write dates as MM-dd-yyyy exactly as shown.
executive_summary: at most 90 words. top_decisions: at most 5 items, each at most 35 words, each naming the material or supplier and the action.
supplier_watch: at most 60 words on supplier tier changes and what to monitor. Neutral wording."""

RULE_TEXT = {
    "HIGH_TIER": "Supplier tier is HIGH: safety stock = 2.5 x usage during lead time.",
    "HIGH_VARIANCE": "Persistent demand spikes of 50% or more: safety stock = 2.5 x usage during lead time.",
    "MEDIUM_VARIANCE": "Persistent demand spikes above 20% and under 50%: safety stock = 2.0 x (lead time over 28 days), 1.5 x (14 to 28 days) usage during lead time, or 1.0 x weekly run rate (under 14 days).",
    "STABLE_1WK": "Stable demand, LOW supplier tier: 1 week of run rate.",
    "STABLE_2WK": "Stable demand, supplier tier MEDIUM for 30 days or more: 2 weeks of run rate.",
    "STABLE_1WK_MONITOR": "Stable demand, supplier tier recently moved from LOW to MEDIUM: 1 week of run rate while monitoring; becomes 2 weeks on the step date if the tier is still MEDIUM.",
    "HOLD_2WK": "Stable demand, supplier tier recently moved from MEDIUM to LOW: 2 weeks held until the step date, then 1 week.",
    "TAIL_DAYS": "Low-volume (tail) item: safety stock is capped at 1 to 3 days of expected demand.",
    "TAIL_ROP": "Low-volume (tail) item with a long lead time: 3 days of safety stock and a reorder point = usage during lead time + 3 days.",
    "ZERO_STOCK": "Custom or intermittent item: zero safety stock; buy only for a firm customer order or a forecast of 70% confidence or higher.",
}
CLASS_TEXT = {"TOP": "continuous, top volume", "TAIL": "continuous, low-volume tail", "INTERMITTENT": "custom / intermittent"}

rows, buys, tier_changes = policy.build_all()
R = {r["material_id"]: r for r in rows}
SUP = pd.read_csv("suppliers.csv").set_index("supplier_id")["name"].to_dict()
REASON = pd.read_csv("supplier_tiers.csv").set_index("supplier_id")["reasons"].to_dict()
DESC = policy.M["description"].to_dict()


def clean(x):
    return {k: v for k, v in x.items() if not k.startswith("_")}


# ------------------------------------------------------------------
# TOOLS: ordinary Python functions that Claude is allowed to call
# ------------------------------------------------------------------
def bucket_dates(i):
    a = policy.CURRENT_WEEK + timedelta(days=28 * i)
    return str(a), str(a + timedelta(days=27))


def get_material_facts(mid):
    if mid not in R:
        return {"error": f"{mid} not found"}
    r = R[mid]
    out = {"material": {"material_id": mid, "description": DESC[mid], "supplier_id": r["supplier_id"], "supplier_name": SUP[r["supplier_id"]],
                        "criticality": r["criticality"], "class": CLASS_TEXT[r["material_class"]], "lead_time_days": r["lead_time_days"],
                        "supplier_lot_size": int(policy.M.loc[mid, "supplier_lot_size"]), "typical_reorder_quantity": r["typical_order_qty"]},
           "safety_stock": {"rule": RULE_TEXT[r["rule"]], "run_rate_per_week": r["run_rate"], "current": r["ss_current"], "target": r["ss_target"],
                            "decision": r["ss_change"], "dollar_change": r["ss_delta_value"], "dollar_change_text": usd(r["ss_delta_value"]), "reorder_point": r["reorder_point"],
                            "monitor": r["monitor"], "step_date": r["step_date"]},
           "demand_pattern": {"spike_pattern": r["variance_regime"], "peak_spike_pct": r["peak_spike_pct"], "target_if_it_becomes_persistent": r.get("if_persistent_target", "")},
           "forecast_accuracy": {"wape_pct": r.get("wape_pct", ""), "bias_pct": r.get("bias_pct", ""), "forecast_value_add_points": r.get("fva_pts", ""),
                                 "flags": [f for f in (r["bias_flag"], r["error_flag"], r["fva_flag"]) if f]},
           "spike_po": {"status": r["spike_po_status"] or "none", "quantity": r["spike_po_qty"], "quantity_note": "whole supplier lots, rounded up; quote this quantity, not the calculated need",
                        "calculated_need_before_lot_rounding": r["spike_po_need"], "reason": r["spike_po_reason"],
                        "order_by": r["spike_po_order_by"], "timing": r["spike_po_timing"], "days_to_order_by": (r["_spike_parts"] or {}).get("days_to_order_by", ""),
                        "supplier_check_required": r["spike_po_supplier_check"] == "Y", "how_it_was_built": {k: v for k, v in (r["_spike_parts"] or {}).items() if k in
                        ("spike_order", "backlog", "lead_time_demand", "safety_stock_target", "on_hand_at_order_by", "open_pos_in_lead_time")}},
           "gaps": {"decision_needed": r["decision_needed"] == "Y", "first_bucket_below_safety_stock": r["first_below_ss_bucket"],
                    "first_shortage_bucket": r["first_shortage_bucket"], "largest_shortage_units": r["shortage_units"],
                    "ending_stock_by_bucket": [{"bucket": f"B{i + 1}", "from": bucket_dates(i)[0], "to": bucket_dates(i)[1], "ending_stock": e}
                                               for i, e in enumerate(r.get("projected_end", []))]},
           "must_cover": [t[2] for t in ck.required_texts(r, buys)]}
    return out


def get_supplier_risk(mid):
    r = R.get(mid)
    if not r:
        return {"error": f"{mid} not found"}
    s = r["supplier_id"]
    return {"supplier_id": s, "supplier_name": SUP[s], "tier_now": r["tier_now"], "tier_at_last_cycle": r["tier_prior"], "days_in_current_tier": r["days_in_tier"],
            "tier_changed_since_last_cycle": r["tier_now"] != r["tier_prior"], "reasons": REASON.get(s, "")}


def get_orders(mid):
    po = policy.PO[policy.PO.material_id == mid].to_dict("records")
    so = policy.SO[policy.SO.material_id == mid].to_dict("records")
    lines = [b for b in buys if b["material_id"] == mid]
    return {"open_purchase_orders": po or "none", "spike_orders": so or "none",
            "spike_order_note": "unforecasted = Y means the order was not in the forecast",
            "custom_item_lines": lines or "none", "backlog_units": policy.backlog(mid), "on_hand": int(policy.M.loc[mid, "on_hand"])}


def cycle_facts():
    ch = [r for r in rows if r["ss_change"] == "CHANGE"]
    sp = [r for r in rows if r["spike_po_status"] == "SPIKE_PO"]
    dec = [r for r in rows if r["decision_needed"] == "Y"]
    return {"as_of": str(policy.AS_OF), "last_cycle": str(policy.PRIOR_AS_OF), "materials_reviewed": len(rows),
            "safety_stock_changes": len(ch), "safety_stock_total_dollar_change": round(sum(r["ss_delta_value"] for r in ch), 2),
            "safety_stock_total_dollar_change_text": usd(sum(r["ss_delta_value"] for r in ch)),
            "upgrades": sum(1 for t in tier_changes if t["direction"] == "UPGRADE"), "downgrades": sum(1 for t in tier_changes if t["direction"] == "DOWNGRADE"),
            "supplier_tier_changes": [{**t, "name": SUP[t["supplier_id"]], "reasons": REASON.get(t["supplier_id"], "")} for t in tier_changes],
            "material_supplier": {r["material_id"]: {"supplier_id": r["supplier_id"], "name": SUP[r["supplier_id"]]} for r in rows},
            "spike_pos": [{"material_id": r["material_id"], "supplier": SUP[r["supplier_id"]], "quantity": r["spike_po_qty"], "reason": r["spike_po_reason"], "order_by": r["spike_po_order_by"],
                           "timing": r["spike_po_timing"], "supplier_check_required": r["spike_po_supplier_check"] == "Y"} for r in sp],
            "decisions_needed": [{"material_id": r["material_id"], "first_shortage_bucket": r["first_shortage_bucket"],
                                  "first_below_safety_stock_bucket": r["first_below_ss_bucket"], "largest_shortage_units": r["shortage_units"]} for r in dec],
            "monitor_or_hold": [{"material_id": r["material_id"], "rule": r["rule"], "step_date": r["step_date"]} for r in rows if r["step_date"]],
            "one_time_spikes": [r["material_id"] for r in rows if r["variance_regime"] == "ONE_TIME"],
            "persistent_spikes": [r["material_id"] for r in rows if r["variance_regime"] == "PERSISTENT"],
            "custom_item_lines": buys,
            "must_name_materials": sorted({r["material_id"] for r in sp} | {r["material_id"] for r in dec}),
            "must_name_suppliers": sorted(t["supplier_id"] for t in tier_changes)}


def run_tool(name, args, key, state):
    if name == "get_material_facts":
        out = get_material_facts(args["material_id"])
    elif name == "get_supplier_risk":
        out = get_supplier_risk(args["material_id"])
    elif name == "get_orders":
        out = get_orders(args["material_id"])
    elif name == "get_cycle_facts":
        out = cycle_facts()
    elif name in ("submit_brief", "submit_summary"):
        return submit(name, args, key, state)
    else:
        out = {"error": f"unknown tool {name}"}
    state["seen"] += json.dumps(out, default=str) + " "
    return out


def submit(name, args, key, state):
    """Check the writing. A failure is sent back ONCE with exact fixes; a second failure is saved and flagged."""
    if name == "submit_brief":
        checks, problems = ck.check_brief(R[key], buys, args, state["seen"])
        failed = [k for k in ck.CHECK_KEYS if not checks[k]]
        fixes = ck.fix_instructions(problems)
    else:
        ok, fixes = ck.check_summary(cycle_facts(), args, state["seen"])
        failed = [] if ok else ["summary"]
        checks, problems = {"summary_ok": ok}, {"summary": fixes}
    if failed and state["attempts"] == 0:
        state["attempts"] = 1
        state["first_failed"] = failed
        return {"status": "REJECTED - not saved. Fix these problems and call the submit tool again with the complete submission.", "fix_these": [ck.to_us(x) for x in fixes]}
    sub = ck.normalize(args)[0] if name == "submit_brief" else args
    state["result"] = {"key": key, "submission": sub, "checks": checks, "problems": {k: v for k, v in problems.items() if v},
                       "revised": state["attempts"] > 0, "first_failed": state.get("first_failed", [])}
    return {"status": "saved"}


def schema(field):
    return {"type": "object", "properties": {field: {"type": "string"}}, "required": [field]}


TOOLS = [
    {"name": "get_material_facts", "input_schema": schema("material_id"),
     "description": "Everything the system decided for the material: class, safety stock rule, target vs current, spike pattern, Spike PO, projected gaps, forecast accuracy, and a must_cover list."},
    {"name": "get_supplier_risk", "input_schema": schema("material_id"),
     "description": "The supplier's risk tier now and at the last cycle, days in the tier and the reasons, from the Risk Detection Agent."},
    {"name": "get_orders", "input_schema": schema("material_id"),
     "description": "Open purchase orders, spike orders, custom-item forecast lines with buy decisions, backlog and on-hand."},
    {"name": "submit_brief", "description": "Submit the brief for this material. Call exactly once.",
     "input_schema": {"type": "object", "properties": {f: {"type": "string"} for f in ck.BRIEF_FIELDS}, "required": ck.BRIEF_FIELDS}},
]
SUMMARY_TOOLS = [
    {"name": "get_cycle_facts", "description": "Cycle-level facts built by the system.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "submit_summary", "description": "Submit the executive summary. Call exactly once.",
     "input_schema": {"type": "object", "properties": {"executive_summary": {"type": "string"}, "top_decisions": {"type": "array", "items": {"type": "string"}},
                                                       "supplier_watch": {"type": "string"}}, "required": ["executive_summary", "top_decisions", "supplier_watch"]}},
]


# ------------------------------------------------------------------
# THE AGENT LOOP
# ------------------------------------------------------------------
def converse(client, system, tools, first_message, key, usage):
    messages = [{"role": "user", "content": first_message}]
    state = {"seen": "", "attempts": 0, "result": None}
    for _ in range(MAX_TURNS):
        reply = client.messages.create(model=MODEL, max_tokens=4000, system=system, tools=tools, messages=messages)
        usage["in"] += reply.usage.input_tokens
        usage["out"] += reply.usage.output_tokens
        messages.append({"role": "assistant", "content": reply.content})
        if reply.stop_reason != "tool_use":
            break
        results = []
        for block in reply.content:
            if block.type == "tool_use":
                out = run_tool(block.name, block.input, key, state)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": ck.to_us(json.dumps(out, default=str))})
        messages.append({"role": "user", "content": results})
        if state["result"]:
            break
    if not state["result"]:
        print(f"  WARNING: nothing was submitted for {key}")
    return state["result"]


def review_material(client, mid, usage):
    return converse(client, SYSTEM_PROMPT, TOOLS, f"Draft the brief for {mid}.", mid, usage)


def review_cycle(client, usage):
    return converse(client, SUMMARY_PROMPT, SUMMARY_TOOLS, "Write the executive summary for this S&OP cycle.", "CYCLE", usage)


# ------------------------------------------------------------------
# OUTPUT: tables are built by code; the explanations are Claude's
# ------------------------------------------------------------------
def usd(x):
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def tier_table():
    if not tier_changes:
        return ["No supplier tier changes since the last cycle.", ""]
    L = ["| Supplier | Moved | Days in new tier | Reason (Risk Detection Agent) |", "|---|---|---|---|"]
    for t in tier_changes:
        days = next(r["days_in_tier"] for r in rows if r["supplier_id"] == t["supplier_id"])
        L.append(f"| {SUP[t['supplier_id']]} ({t['supplier_id']}) | {t['tier_prior']} to {t['tier_now']} | {days} | {REASON.get(t['supplier_id'], '')} |")
    return L + [""]


def spike_table(done):
    sp = [r for r in rows if r["spike_po_status"]]
    if not sp:
        return ["No Spike PO triggers this cycle.", ""]
    L = ["| Material | Why | Status | Order qty (whole lots) | Calculated need | Lot size | Order by | Timing | Typical re-order | Ask supplier? |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sp:
        L.append(f"| {r['material_id']} {DESC[r['material_id']]} | {r['spike_po_reason'].replace('_', ' ').title()} | {r['spike_po_status'].replace('_', ' ').title()} | "
                 f"{r['spike_po_qty']:,} | {r['spike_po_need']:,} | {int(policy.M.loc[r['material_id'], 'supplier_lot_size']):,} | {r['spike_po_order_by'] or '-'} | {r['spike_po_timing'].replace('_', ' ').title() or '-'} | {r['typical_order_qty']:,} | "
                 f"{'Yes: lead time / partials' if r['spike_po_supplier_check'] == 'Y' else 'No'} |")
    return L + [""]


def safety_table(selected):
    L = ["| Material | Type | Rule | Current | Target | Decision | $ change | Reorder point |", "|---|---|---|---|---|---|---|---|"]
    for r in selected:
        L.append(f"| {r['material_id']} {DESC[r['material_id']]} | {CLASS_TEXT[r['material_class']]} | {r['rule'].replace('_', ' ').title()} | {r['ss_current']:,} | "
                 f"{r['ss_target']:,} | {r['ss_change'].replace('_', ' ').title()} | {usd(r['ss_delta_value'])} | {r['reorder_point'] if r['reorder_point'] != '' else '-'} |")
    return L + [""]


def gap_table(selected):
    L = ["| Material | First below safety stock | First shortage | Largest shortage (units) | Decision needed |", "|---|---|---|---|---|"]
    for r in selected:
        L.append(f"| {r['material_id']} {DESC[r['material_id']]} | {r['first_below_ss_bucket'] or '-'} | {r['first_shortage_bucket'] or '-'} | {r['shortage_units']:,} | {'YES' if r['decision_needed'] == 'Y' else '-'} |")
    return L + [""]


BUY_LABEL = {"NOT_YET": "Future Planned Buy"}


def buy_table():
    if not buys:
        return []
    L = ["| Custom item | Need week | Qty | Supplier lot | Confidence | Firm order | Release date | Decision |", "|---|---|---|---|---|---|---|---|"]
    for b in buys:
        L.append(f"| {b['material_id']} | {b['need_week']} | {b['qty']} | {b['lot_size']} | {b['confidence_pct']}% | {b['firm_order']} | {b['release_date']} | {BUY_LABEL.get(b['decision'], b['decision'].replace('_', ' ').title())}{' (below one lot: ask supplier for a smaller quantity or rework similar on-hand material)' if b['below_lot'] == 'Y' and b['decision'] in ('BUY', 'BUY_LATE') else ''} |")
    return L + [""]


def write_pre_read(results, summary):
    sel = [R[x["key"]] for x in results]
    review = "" if not summary or summary["checks"]["summary_ok"] else "  \n**NEEDS HUMAN REVIEW:** the summary failed an automated check."
    L = [f"# S&OP Cycle Pre-Read ({policy.AS_OF})", f"*Compared with the last cycle ({policy.PRIOR_AS_OF}). Numbers and rules are computed by code; the explanations are drafted by Claude and checked.*{review}", ""]
    if summary:
        s = summary["submission"]
        L += ["## Executive summary", "", s["executive_summary"], "", "### Decisions for leadership", ""]
        L += [f"{i + 1}. {d if isinstance(d, str) else d.get('decision', d)}" for i, d in enumerate(s["top_decisions"])] + [""]
        L += ["## Supplier risk changes since the last cycle", ""] + tier_table() + [s["supplier_watch"], ""]
    L += ["## Spike POs", ""] + spike_table(results) + ["## Safety stock recommendations", ""] + safety_table(sel)
    L += ["## Projected gaps", ""] + gap_table(sel)
    if any(R[x["key"]]["material_class"] == "INTERMITTENT" for x in results):
        L += ["## Custom (intermittent) items: buy decisions", ""] + buy_table()
    L += ["## Material briefs", ""]
    for x in results:
        r, s = R[x["key"]], x["submission"]
        bad = [ck.CHECK_LABELS[k] for k in ck.CHECK_KEYS if not x["checks"][k]]
        L += [f"### {r['material_id']} {DESC[r['material_id']]} ({SUP[r['supplier_id']]}, tier {r['tier_now']})", f"**{s['headline']}**" + (f"  \n**NEEDS HUMAN REVIEW:** {', '.join(bad)}" if bad else ""), ""]
        for label, f in (("What changed", "what_changed"), ("Safety stock", "safety_stock_recommendation"), ("Spike PO message to buyer", "spike_po_message"),
                         ("Custom item", "custom_item_note"), ("Forecast", "forecast_note"), ("Decision needed", "decision_note")):
            if s[f].strip():
                L.append(f"- **{label}:** {s[f]}")
        L.append("")
    open("sop_pre_read.md", "w", encoding="utf-8").write(ck.to_us("\n".join(L).replace("Spike Po", "Spike PO")))


def main():
    client = anthropic.Anthropic()          # reads your key from ANTHROPIC_API_KEY
    ids = ONLY_MATERIALS if ONLY_MATERIALS else list(R)[:MAX_MATERIALS]
    results, usage, summary = [], {"in": 0, "out": 0}, None
    print(f"Drafting briefs for {len(ids)} materials with {MODEL}...\n")
    for mid in ids:
        print(f"Reviewing {mid} {DESC[mid]}...")
        try:
            x = review_material(client, mid, usage)
        except anthropic.APIError as error:
            print(f"  API problem: {error}\n  Stopping early and saving what we have.")
            break
        except Exception as error:                      # one bad brief must not stop the others
            print(f"  PROBLEM with {mid}: {type(error).__name__}: {error}. Skipping it and carrying on.")
            continue
        if x:
            results.append(x)
            json.dump({"briefs": results, "summary": summary}, open("sop_results.json", "w", encoding="utf-8"), indent=1, default=str)
            write_pre_read(results, summary)
            failed = [ck.CHECK_LABELS[k] for k in ck.CHECK_KEYS if not x["checks"][k]]
            print("  done" + (f"  <-- CHECK WORDING ({', '.join(failed)})" if failed else "") +
                  (("  (revised: " + ", ".join(ck.CHECK_LABELS[k] for k in x["first_failed"]) + ")") if x["revised"] else ""))
    if WRITE_SUMMARY and results:
        print("\nWriting the cycle executive summary...")
        try:
            summary = review_cycle(client, usage)
            json.dump({"briefs": results, "summary": summary}, open("sop_results.json", "w", encoding="utf-8"), indent=1, default=str)
            write_pre_read(results, summary)
            if summary and summary["revised"]:
                print("  (revised after a failed check)")
        except Exception as error:
            print(f"  PROBLEM with the summary: {type(error).__name__}: {error}")
    if results:
        revised = sum(1 for r in results if r["revised"])
        print(f"\nSaved sop_pre_read.md and sop_results.json ({len(results)} briefs, {revised} needed one revision after a failed check)")
    cost = usage["in"] / 1e6 * PRICE_IN + usage["out"] / 1e6 * PRICE_OUT
    print(f"Tokens used: {usage['in']:,} in, {usage['out']:,} out (rough cost: ${cost:.3f})")


if __name__ == "__main__":
    main()
