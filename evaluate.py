"""
Grades the whole S&OP agent against the hand-written answer key. No AI, no cost. Run: python evaluate.py

Part A: the rules engine (policy.py) vs answer_key_*.csv   (runs evaluate_policy.py)
Part B: the agent's WRITING in sop_results.json vs the same key. These checks are written separately from the agent's own
        checks: they read the key, not the engine, and look for what a buyer or planner would need to see.
Only the materials that were actually drafted are graded. Run agent.py with MAX_MATERIALS = 17 to grade all of them.
"""
import json
import runpy

import pandas as pd

import sop_checks as ck

print("=== Part A: rules engine vs answer key ===")
runpy.run_path("evaluate_policy.py")

print("\n=== Part B: the agent's writing vs answer key ===")
try:
    data = json.load(open("sop_results.json", encoding="utf-8"))
except FileNotFoundError:
    raise SystemExit("sop_results.json not found. Run agent.py first.")
key = pd.read_csv("answer_key_policy.csv", keep_default_na=False).set_index("material_id")
mats = pd.read_csv("materials.csv").set_index("material_id")
pk = pd.read_csv("answer_key_purchases.csv", keep_default_na=False)
tk = pd.read_csv("answer_key_tiers.csv", keep_default_na=False)
briefs = {b["key"]: b for b in data["briefs"]}
import agent                                    # tool outputs, to recheck grounding independently

tally = {}


def score(name, ok, detail=""):
    t = tally.setdefault(name, [0, 0, []])
    t[1] += 1
    t[0] += bool(ok)
    if not ok:
        t[2].append(detail)


for mid, b in briefs.items():
    k, s = key.loc[mid], b["submission"]
    s = {x: ck.to_iso(y) for x, y in s.items()}            # people read MM-dd-yyyy; the key is year-first
    ss, sp, dn, cu, fc, wc = (s[x].lower().replace(",", "") for x in ("safety_stock_recommendation", "spike_po_message", "decision_note", "custom_item_note", "forecast_note", "what_changed"))
    cur = int(mats.loc[mid, "current_safety_stock"])
    tgt = int(k.ss_target)
    up = any(w in ss for w in ck.UP)
    down = any(w in ss for w in ck.DOWN)
    # safety stock: target quoted and direction right
    direction = (up and not down) if (k.ss_change == "CHANGE" and tgt > cur) else (down and not up) if k.ss_change == "CHANGE" else not (up or down)
    score("Safety stock target quoted and direction correct", str(tgt) in ss and direction or (tgt == 0 and direction), f"{mid}")
    if k.reorder_point != "":
        score("Reorder point / policy dates quoted", str(k.reorder_point) in ss, f"{mid} reorder point")
    if k.step_date:
        score("Reorder point / policy dates quoted", k.step_date in ss, f"{mid} step date")
    if k.monitor == "Y":
        score("Monitor flag raised", "monitor" in ss, mid)
    if k.variance_regime == "ONE_TIME":
        score("One-time spike left alone and explained", ("one-time" in ss + wc or "one time" in ss + wc) and not up, mid)
    # spike PO message
    if k.spike_po_status == "SPIKE_PO":
        good = str(k.spike_po_qty) in sp and (k.spike_po_timing != "ORDER_BY" or k.spike_po_order_by in sp) and \
            (k.spike_po_timing != "ORDER_LATE" or ("late" in sp and k.spike_po_order_by in sp)) and (k.spike_po_timing != "ORDER_NOW" or any(w in sp for w in ("now", "today", "immediately")))
        score("Spike PO quantity and order-by date correct", good, mid)
        score("Supplier check (lead time / partials) only when required", ("lead time" in sp and "partial" in sp) == (k.spike_po_supplier_check == "Y"), mid)
    elif k.spike_po_status == "COVERED_BY_STOCK":
        score("Covered spike orders get no Spike PO", "cover" in sp and "order by" not in sp, mid)
    else:
        score("No Spike PO message when none is triggered", sp.strip() == "", mid)
    # decisions
    score("Executive decision raised only when needed (names the bucket)", (k.decision_needed == "Y" and k.first_shortage_bucket.lower() in dn) or (k.decision_needed == "N" and dn.strip() == "") if k.first_shortage_bucket or k.decision_needed == "N" else bool(dn.strip()), mid)
    # tier change described
    if k.tier_now != k.tier_prior:
        score("Supplier tier change described (from and to)", k.tier_prior.lower() in wc and k.tier_now.lower() in wc, mid)
    # custom items
    lines = pk[pk.material_id == mid]
    for _, p in lines.iterrows():
        if p.decision in ("BUY", "BUY_LATE"):
            score("Custom-item buys and do-not-buys correct", p.release_date in cu, f"{mid} buy {p.release_date}")
            if p.below_lot == "Y":
                score("Below-lot custom buys say: smaller quantity or rework", any(w in cu for w in ("smaller quantit", "smaller amount", "smaller order", "fewer units", "below one lot", "below the lot", "less than", "minimum lot", "below the minimum", "under one lot")) and "rework" in cu, f"{mid} {p.release_date}")
        elif p.decision == "DO_NOT_BUY":
            score("Custom-item buys and do-not-buys correct", p.need_week in cu, f"{mid} do not buy {p.need_week}")
        else:
            score("Custom-item buys and do-not-buys correct", "future planned buy" in cu, f"{mid} not-yet line {p.need_week}: must read 'future planned buy'")
    # forecast flags
    for flag, word in (("bias_flag", "bias"), ("fva_flag", "override"), ("error_flag", "error")):
        if k[flag]:
            score("Forecast accuracy flags covered", word in fc, f"{mid} {flag}")
    # grounding, rechecked here from the tool outputs
    seen = " ".join(json.dumps(x, default=str) for x in (agent.get_material_facts(mid), agent.get_supplier_risk(mid), agent.get_orders(mid)))
    allt = " ".join(s.values())
    ok = all(x in ck.nums(seen) or x in ck.ALLOWED_NUMBERS for x in ck.nums(allt)) and all(x in seen for x in ck.DATE_RE.findall(allt)) and all(x in seen for x in ck.ID_RE.findall(allt))
    score("Every number, date and ID comes from the data", ok, mid)
    score("Neutral tone, within word limits, all sections present", b["checks"]["tone_ok"] and b["checks"]["length_ok"] and b["checks"]["fields_ok"], mid)

n_run, n_total = len(briefs), len(key)
print(f"Briefs written: {n_run} / {n_total}" + ("" if n_run == n_total else "  (partial run: only these are graded)"))
for name, (ok, tot, misses) in tally.items():
    print(f"{name}: {ok} / {tot}" + (f"   misses: {', '.join(misses)}" if misses else ""))
revised = sum(1 for b in briefs.values() if b["revised"])
flagged = [m for m, b in briefs.items() if not all(b["checks"].values())]
print(f"Briefs that needed one revision after a failed check: {revised} / {n_run}")
print(f"Briefs still flagged for human review: {len(flagged)}" + (f" ({', '.join(flagged)})" if flagged else ""))

sm = data.get("summary")
if sm:
    s = sm["submission"]
    s = json.loads(ck.to_iso(json.dumps(s)))
    allt = " ".join([s["executive_summary"], s["supplier_watch"]] + [x if isinstance(x, str) else str(x) for x in s["top_decisions"]])
    need_m = [m for m in key.index if key.loc[m, "spike_po_status"] == "SPIKE_PO" or key.loc[m, "decision_needed"] == "Y"]
    need_s = list(tk.supplier_id)
    sup_names = pd.read_csv("suppliers.csv").set_index("supplier_id")["name"].to_dict()
    print(f"Executive summary names every Spike PO / decision material and every tier-changed supplier: {all(m in allt for m in need_m) and all(x in allt or sup_names[x] in allt for x in need_s)}")
    print(f"Executive summary passed its checks: {sm['checks']['summary_ok']}" + (" (after one revision)" if sm["revised"] else ""))
else:
    print("No executive summary in the results (WRITE_SUMMARY was off or it failed).")
