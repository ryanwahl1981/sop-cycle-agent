"""Part A: grades the rules engine (policy.py) against the hand-written answer key. No AI, no cost. Run: python evaluate_policy.py"""
import pandas as pd

import policy

rows, buys, tiers = policy.build_all()
got = {r["material_id"]: r for r in rows}
key = pd.read_csv("answer_key_policy.csv", keep_default_na=False)

FIELDS = [("material_class", "material_class"), ("rule", "rule"), ("tier_now", "tier_now"), ("tier_prior", "tier_prior"),
          ("variance_regime", "variance_regime"), ("variance_class", "variance_class"), ("ss_target", "ss_target"),
          ("reorder_point", "reorder_point"), ("ss_change", "ss_change"), ("monitor", "monitor"), ("step_date", "step_date"),
          ("spike_po_qty", "spike_po_qty"), ("spike_po_need", "spike_po_need"), ("spike_po_status", "spike_po_status"), ("spike_po_reason", "spike_po_reason"), ("spike_po_order_by", "spike_po_order_by"), ("spike_po_timing", "spike_po_timing"), ("spike_po_supplier_check", "spike_po_supplier_check"), ("first_below_ss_bucket", "first_below_ss_bucket"),
          ("first_shortage_bucket", "first_shortage_bucket"), ("decision_needed", "decision_needed"),
          ("bias_flag", "bias_flag"), ("error_flag", "error_flag"), ("fva_flag", "fva_flag"), ("typical_order_qty", "typical_order_qty")]


def same(a, b):
    return str(a).strip() == str(b).strip()


total = ok = 0
misses = []
for _, k in key.iterrows():
    g = got[k.material_id]
    for kf, gf in FIELDS:
        total += 1
        if same(k[kf], g.get(gf, "")):
            ok += 1
        else:
            misses.append(f"  {k.material_id} {kf}: key {k[kf]!r}, engine {g.get(gf, '')!r}")
    if str(k.run_rate) != "":                                    # run rate: key is rounded to a whole unit
        total += 1
        if abs(float(g["run_rate"]) - float(k.run_rate)) <= 1:
            ok += 1
        else:
            misses.append(f"  {k.material_id} run_rate: key {k.run_rate}, engine {g['run_rate']}")
print(f"Policy values vs answer key: {ok} / {total}")

pk = pd.read_csv("answer_key_purchases.csv", keep_default_na=False)
pg = pd.DataFrame(buys)
pt = pok = 0
for _, k in pk.iterrows():
    m = pg[(pg.material_id == k.material_id) & (pg.need_week == k.need_week)]
    pt += 1
    if len(m) == 1 and m.iloc[0].decision == k.decision and m.iloc[0].release_date == k.release_date and m.iloc[0].below_lot == k.below_lot:
        pok += 1
    else:
        misses.append(f"  purchase {k.material_id} {k.need_week}: key {k.decision} {k.release_date}, engine {m.to_dict('records')}")
print(f"Custom-item buy decisions (incl. the 69% / 70% boundary): {pok} / {pt}")

tk = pd.read_csv("answer_key_tiers.csv", keep_default_na=False)
tg = pd.DataFrame(tiers)
tt = len(tk)
tok = sum(1 for _, k in tk.iterrows() if len(tg[(tg.supplier_id == k.supplier_id) & (tg.tier_prior == k.tier_prior) & (tg.tier_now == k.tier_now) & (tg.direction == k.direction)]) == 1)
tok -= 0 if len(tg) == len(tk) else 1000      # extra or missing tier changes fail the check
print(f"Supplier tier changes (no extras, none missed): {max(tok, 0)} / {tt}")

if misses:
    print("\nMisses:")
    print("\n".join(misses))
else:
    print("\nEvery value matches the answer key.")
