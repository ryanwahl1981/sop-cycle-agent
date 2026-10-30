"""
Offline test: runs the whole agent loop with a STAND-IN for Claude (no API key, no cost).

The stand-in reads the tool results the real model would see and writes a brief from them. It lets us check that the
tools, the checks, the retry and the file output work before spending any money.

  mode "good"     writes correct briefs first time
  mode "sloppy"   first attempt has deliberate mistakes (invented number, invented ID and date, a dramatic word, wrong
                  safety stock wording, missing order-by date); the second attempt is correct
  mode "stubborn" repeats the mistakes after the retry, so the brief must be flagged for human review

Run:  python test_offline.py
"""
import json
import os
import tempfile
from types import SimpleNamespace as NS

import agent
import sop_checks as ck


def block_tool(i, name, **inp):
    return NS(type="tool_use", id=f"t{i}", name=name, input=inp)


class FakeClient:
    def __init__(self, mode):
        self.mode = mode
        self.messages = self
        self.sub_count = {}

    def create(self, model, max_tokens, system, tools, messages):
        first = messages[0]["content"]
        key = "CYCLE" if "S&OP cycle" in first else first.split()[-1].rstrip(".")
        turns = sum(1 for m in messages if m["role"] == "assistant")
        usage = NS(input_tokens=1000, output_tokens=500)
        if turns == 0:
            names = ["get_cycle_facts"] if key == "CYCLE" else ["get_material_facts", "get_supplier_risk", "get_orders"]
            blocks = [block_tool(i, n, **({} if key == "CYCLE" else {"material_id": key})) for i, n in enumerate(names)]
            return NS(content=blocks, stop_reason="tool_use", usage=usage)
        seen = {}
        for m in messages:
            if m["role"] == "user" and isinstance(m["content"], list):
                for r in m["content"]:
                    seen[r["tool_use_id"]] = json.loads(r["content"])
        n = self.sub_count.get(key, 0)
        self.sub_count[key] = n + 1
        broken = self.mode == "stubborn" or (self.mode == "sloppy" and n == 0)
        if key == "CYCLE":
            facts = next(v for v in seen.values() if isinstance(v, dict) and "must_name_materials" in v)
            return NS(content=[block_tool(20 + n, "submit_summary", **compose_summary(facts, broken))], stop_reason="tool_use", usage=usage)
        pick = lambda k: next(v for v in seen.values() if isinstance(v, dict) and k in v)
        return NS(content=[block_tool(10 + n, "submit_brief", **compose(key, pick("must_cover"), pick("tier_now"), pick("open_purchase_orders"), broken))],
                  stop_reason="tool_use", usage=usage)


def compose(mid, f, risk, orders, broken):
    ss, sp, g, dp, fa = f["safety_stock"], f["spike_po"], f["gaps"], f["demand_pattern"], f["forecast_accuracy"]
    cur, tgt = ss["current"], ss["target"]
    what = ""
    if risk["tier_changed_since_last_cycle"]:
        what = f"The supplier moved from {risk['tier_at_last_cycle']} to {risk['tier_now']} ({risk['days_in_current_tier']} days ago). "
    if dp["spike_pattern"] == "PERSISTENT":
        what += "Demand spikes are persistent."
    if dp["spike_pattern"] == "ONE_TIME":
        what += "A one-time demand spike."
    if ss["decision"] == "CHANGE":
        text = f"{'Increase' if tgt > cur else 'Reduce'} safety stock from {cur} to {tgt}."
        if tgt == 0:
            text += " A custom item carries zero safety stock."
    else:
        text = f"No change: hold safety stock at {tgt}." if tgt else "No change: a custom item carries zero safety stock."
    if ss["reorder_point"] != "":
        text += f" Reorder point {ss['reorder_point']}."
    if ss["step_date"]:
        text += f" Policy changes on {ss['step_date']}."
    if ss["monitor"] == "Y":
        text += " Monitor the supplier tier."
    if dp["spike_pattern"] == "ONE_TIME":
        text += f" One-time spike: if it becomes persistent the target would be {dp['target_if_it_becomes_persistent']}."
    msg = ""
    if sp["status"] == "SPIKE_PO":
        msg = f"Place a Spike PO for {sp['quantity']} units"
        msg += {"ORDER_BY": f" by {sp['order_by']}.", "ORDER_NOW": " now.", "ORDER_LATE": f". The order-by date {sp['order_by']} has passed, so it is late; ask about expediting."}[sp["timing"]]
        if sp["supplier_check_required"]:
            msg += " Contact the supplier to find out whether lead time will be extended or partial deliveries planned."
    elif sp["status"] == "COVERED_BY_STOCK":
        msg = "Stock already covers the spike order, so no Spike PO is needed."
    custom = ""
    if isinstance(orders["custom_item_lines"], list):
        for b in orders["custom_item_lines"]:
            if b["decision"] in ("BUY", "BUY_LATE"):
                custom += f"Buy {b['qty']} released {b['release_date']}. "
                if b["below_lot"] == "Y":
                    custom += "Below one lot: ask the supplier about a smaller quantity, or consider rework of similar on-hand material. "
            elif b["decision"] == "DO_NOT_BUY":
                custom += f"Do not buy the {b['need_week']} line ({b['confidence_pct']}% confidence). "
            elif b["decision"] == "NOT_YET":
                custom += f"The {b['need_week']} line is a future planned buy; review in a later cycle. "
    fc = "".join({"BIAS_HIGH": f"Consensus bias is {fa['bias_pct']}%. ", "BIAS_LOW": f"Consensus bias is {fa['bias_pct']}%. ",
                  "OVERRIDE_HURTS": "The sales override reduced accuracy. ", "OVERRIDE_ADDS_VALUE": "The sales override improved accuracy. ",
                  "HIGH_ERROR": "Forecast error is high. "}.get(x, "") for x in fa["flags"])
    dec = f"Decision needed: shortage starts in {g['first_shortage_bucket'] or g['first_bucket_below_safety_stock']}." if g["decision_needed"] else ""
    sub = {"headline": f"{mid}: {ss['decision'].replace('_', ' ').lower()} on safety stock.", "what_changed": what.strip(), "safety_stock_recommendation": text,
           "spike_po_message": msg, "custom_item_note": custom.strip(), "forecast_note": fc.strip(), "decision_note": dec}
    if broken:
        sub["headline"] += " This is a disaster."
        sub["what_changed"] += " Demand rose 17 points on 2026-12-25 per PO-9999."
        sub["safety_stock_recommendation"] = "Raise safety stock substantially."
        if sub["spike_po_message"]:
            sub["spike_po_message"] = f"Place a Spike PO for {sp['quantity']} units soon."
        del sub["decision_note"]
    return sub


def decision_line(facts, m):
    sp = next((q for q in facts["spike_pos"] if q["material_id"] == m), None)
    who = facts["material_supplier"][m]["name"]
    if not sp:
        return f"{m}: review the projected gap with {who}."
    when = " The order is late; ask {0} about expediting.".format(who) if sp["timing"] == "ORDER_LATE" else ""
    return f"{m}: place a Spike PO for {sp['quantity']} units with {who}.{when}"


def compose_summary(facts, broken):
    names = facts["must_name_materials"]
    sup = facts["must_name_suppliers"]
    sub = {"executive_summary": f"{facts['materials_reviewed']} materials reviewed; {facts['safety_stock_changes']} need a safety stock change.",
           "top_decisions": [decision_line(facts, m) for m in names[:5]],
           "supplier_watch": " ".join(f"{s} tier changed." for s in sup)}
    if broken:
        sub["executive_summary"] += " Costs will rise 41 percent."
        sub["supplier_watch"] = ""
        sub["executive_summary"] += " Geopolitical risk is rising."
        wrong = next(v["name"] for k, v in facts["material_supplier"].items() if k != facts["must_name_materials"][0])
        sub["top_decisions"][0] = sub["top_decisions"][0].replace(facts["material_supplier"][facts["must_name_materials"][0]]["name"], wrong) + " Trigger: SUPPLIER_HIGH."
    return sub


def run(mode, ids):
    print(f"\n=== mode: {mode} ===")
    client, usage, tally = FakeClient(mode), {"in": 0, "out": 0}, {"pass": 0, "revised": 0, "flagged": 0}
    results = []
    for mid in ids:
        r = agent.review_material(client, mid, usage)
        failed = [k for k in ck.CHECK_KEYS if not r["checks"][k]]
        tally["pass"] += not failed
        tally["revised"] += r["revised"]
        tally["flagged"] += bool(failed)
        results.append(r)
        if failed:
            print(f"  {mid} flagged: {failed}  {r['problems']}")
    s = agent.review_cycle(client, usage)
    agent.write_pre_read(results, s)             # writes into a temporary folder, not your project folder
    text = open("sop_pre_read.md", encoding="utf-8").read()
    print(f"  {len(ids)} materials: {tally['pass']} pass, {tally['revised']} revised after a failed check, {tally['flagged']} flagged for human review")
    print(f"  summary: {'pass' if s['checks']['summary_ok'] else 'flagged'}{' (revised)' if s['revised'] else ''}; pre-read {len(text.split()):,} words")
    return tally, s, text


if __name__ == "__main__":
    os.chdir(tempfile.mkdtemp())      # data was already loaded; outputs of this test go to a throwaway folder
    ids = list(agent.R)
    t, s, text = run("good", ids)
    assert t["pass"] == len(ids) and t["revised"] == 0 and s["checks"]["summary_ok"] and not s["revised"], (t, s)
    assert "NEEDS HUMAN REVIEW" not in text and "Spike POs" in text
    t, s, text = run("sloppy", ids)
    assert t["revised"] > 0 and t["flagged"] == 0 and s["checks"]["summary_ok"] and s["revised"], (t, s)
    t, s, text = run("stubborn", ids)
    assert t["flagged"] > 0 and not s["checks"]["summary_ok"] and "NEEDS HUMAN REVIEW" in text, (t, s)
    print("\nAll offline tests behaved as expected.")
