"""
Rules engine for the S&OP agent (no AI). Code decides every number; see KEY.md for the rules in words.
Run:  python policy.py     (prints the policy table and writes policy_results.csv, purchase_results.csv, tier_changes.csv)
"""
import math
from datetime import date, datetime, timedelta
from fractions import Fraction as F
from statistics import median

import pandas as pd

# ---------------- settings (change these to fit a different business) ----------------
AS_OF = date(2026, 10, 13)
PRIOR_AS_OF = date(2026, 9, 15)                  # previous S&OP cycle
CURRENT_WEEK = date(2026, 10, 12)
PERIOD_WEEKS = 4                                 # one "period" = 4 weeks
N_PERIODS = 12
RUN_RATE_PERIODS = 3                             # run rate = mean weekly demand over the last 3 periods (12 weeks)
RECENT_PERIODS = 6                               # window for the spike regime
SPIKE_MEDIUM = F(1, 5)                           # above +20% = medium spike
SPIKE_HIGH = F(1, 2)                             # +50% or more = high spike
PERSISTENT_COUNT = 3                             # persistent = spike in at least 3 of the last 6 periods
CONTINUOUS_MIN_WEEKS = 20                        # continuous = demand in at least 20 of the last 26 weeks
TAIL_CUTOFF = F(4, 5)                            # top group = first 80% of annual order volume
TIER_HOLD_DAYS = 30                              # a tier change must hold 30 days before the stable-demand policy moves
LONG_LEAD_DAYS = 28                              # over 28 days = long lead time
MID_LEAD_DAYS = 14                               # 14 to 28 days = mid lead time
TAIL_DAYS = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}   # tail safety stock, days of expected demand
TAIL_ROP_DAYS = 3
CHANGE_TOLERANCE = F(1, 10)                      # recommend a change only if target differs from current by more than 10%
CONFIDENCE_MIN = 70                              # custom items: forecast confidence needed to buy
BUY_WINDOW_DAYS = 28                             # look-ahead for order release dates
BUCKETS = 6
DECISION_SHORT_PCT = F(1, 20)                    # shortage over 5% of 6-month demand needs a decision
SPIKE_ORDER_PCT = F(1, 5)                        # a spike order is a single order at least 20% above the weekly run rate (forecasted or not)
FC_WEEKS = 26
BIAS_LIMIT = F(1, 10)
ERROR_LIMIT = F(2, 5)

M = pd.read_csv("materials.csv", keep_default_na=False).set_index("material_id")
H = pd.read_csv("demand_history.csv", keep_default_na=False)
FC = pd.read_csv("demand_forecast.csv", keep_default_na=False)
PO = pd.read_csv("open_pos.csv", keep_default_na=False)
SO = pd.read_csv("customer_spike_orders.csv", keep_default_na=False)
TH = pd.read_csv("tier_history.csv")
TH["effective_date"] = pd.to_datetime(TH["effective_date"]).dt.date


def d(s):
    return datetime.strptime(str(s), "%Y-%m-%d").date()


def tier_record(sup, on):
    """(tier, since_date, previous_tier) for the supplier on a date."""
    rows = TH[(TH.supplier_id == sup) & (TH.effective_date <= on)].sort_values("effective_date")
    cur = rows.iloc[-1]
    prev = rows.iloc[-2]["tier"] if len(rows) > 1 else cur["tier"]
    return cur["tier"], cur["effective_date"], prev


def supplier_policy(sup):
    """Which safety-stock basis the supplier tier gives for STABLE demand, with the 30-day timing rules."""
    tier, since, prev = tier_record(sup, AS_OF)
    days = (AS_OF - since).days
    info = dict(tier_now=tier, tier_prior=tier_record(sup, PRIOR_AS_OF)[0], since=since, days_in_tier=days,
                monitor="N", step_date="")
    step = since + timedelta(days=TIER_HOLD_DAYS)
    if tier == "HIGH":
        info.update(level="HIGH", weeks=None, label="HIGH_TIER")
    elif days < TIER_HOLD_DAYS and prev == "HIGH":
        info.update(level="HIGH", weeks=None, label="HIGH_TIER", step_date=str(step))     # downgrade from HIGH: hold 30 days
    elif tier == "MEDIUM" and days >= TIER_HOLD_DAYS:
        info.update(level="MEDIUM", weeks=2, label="STABLE_2WK")
    elif tier == "MEDIUM":
        info.update(level="MEDIUM", weeks=1, label="STABLE_1WK_MONITOR", monitor="Y", step_date=str(step))
    elif tier == "LOW" and days < TIER_HOLD_DAYS and prev == "MEDIUM":
        info.update(level="LOW", weeks=2, label="HOLD_2WK", step_date=str(step))
    else:
        info.update(level="LOW", weeks=1, label="STABLE_1WK")
    return info


def weekly(mid, shift=0):
    """Weekly actuals (list, oldest to newest), dropping the newest `shift` weeks."""
    a = H[H.material_id == mid].sort_values("week_start")["actual"].astype(int).tolist()
    return a[:len(a) - shift] if shift else a


def periods(acts):
    """Last N_PERIODS 4-week totals, oldest -> newest."""
    t = [sum(acts[len(acts) - PERIOD_WEEKS * (k + 1): len(acts) - PERIOD_WEEKS * k]) for k in range(N_PERIODS)]
    return t[::-1]


def variance(acts):
    """Spike regime from period totals: variance of each period against the median baseline."""
    tot = periods(acts)
    base = F(median(tot)).limit_denominator(1000)
    var = [(F(t) - base) / base for t in tot]
    recent = var[-RECENT_PERIODS:]
    n = sum(1 for v in recent if v > SPIKE_MEDIUM)
    regime = "NONE" if n == 0 else ("PERSISTENT" if n >= PERSISTENT_COUNT else "ONE_TIME")
    peak = max(recent)
    vclass = "LOW"
    if regime == "PERSISTENT":
        vclass = "HIGH" if peak >= SPIKE_HIGH else "MEDIUM"
    return dict(regime=regime, vclass=vclass, peak_pct=float(peak * 100), periods=tot, var=var, base=base)


def run_rate(acts, regime, var):
    """Mean weekly demand over the last 12 weeks; for a ONE_TIME spike the spike period is left out."""
    keep = [k for k in range(RUN_RATE_PERIODS) if not (regime == "ONE_TIME" and var[-1 - k] > SPIKE_MEDIUM)]
    keep = keep or list(range(RUN_RATE_PERIODS))
    tot = periods(acts)
    return F(sum(tot[-1 - k] for k in keep), PERIOD_WEEKS * len(keep))


def ceil(x):
    return int(math.ceil(F(x)))


def classify_all():
    """CONTINUOUS (TOP/TAIL) or INTERMITTENT, using the 80% annual-volume cut among continuous items."""
    vol, kind = {}, {}
    for mid in M.index:
        a = weekly(mid)
        kind[mid] = "CONTINUOUS" if sum(1 for x in a[-26:] if x > 0) >= CONTINUOUS_MIN_WEEKS else "INTERMITTENT"
        vol[mid] = sum(a[-52:])
    cont = sorted([m for m in M.index if kind[m] == "CONTINUOUS"], key=lambda m: (-vol[m], m))
    total, cum, cls = sum(vol[m] for m in cont), 0, {}
    for m in cont:
        cls[m] = "TOP" if cum < TAIL_CUTOFF * total else "TAIL"
        cum += vol[m]
    for m in M.index:
        cls.setdefault(m, "INTERMITTENT")
    return cls, vol


def safety_stock(mid, cls, sp, vr, rr):
    """Returns (target units, rule label, reorder point or None)."""
    lt = int(M.loc[mid, "lead_time_days"])
    crit = M.loc[mid, "criticality"] == "CRITICAL"
    lt_use = rr * F(lt, 7)
    if cls == "INTERMITTENT":
        return 0, "ZERO_STOCK", None
    if cls == "TAIL" and not crit:                       # tail: 1 to 3 days only (critical items are exempt)
        if lt > LONG_LEAD_DAYS:
            ss = rr * TAIL_ROP_DAYS / 7
            return ceil(ss), "TAIL_ROP", ceil(lt_use + ss)
        eff = "HIGH" if sp["level"] == "HIGH" else sp["tier_now"]
        return ceil(rr * TAIL_DAYS[eff] / 7), "TAIL_DAYS", None
    cands = []
    if sp["level"] == "HIGH":
        cands.append((F(5, 2) * lt_use, "HIGH_TIER"))
    if vr["regime"] == "PERSISTENT" and vr["vclass"] == "HIGH":
        cands.append((F(5, 2) * lt_use, "HIGH_VARIANCE"))
    if vr["regime"] == "PERSISTENT" and vr["vclass"] == "MEDIUM":
        mult = F(2) if lt > LONG_LEAD_DAYS else (F(3, 2) if lt >= MID_LEAD_DAYS else F(1))
        cands.append((mult * (lt_use if lt >= MID_LEAD_DAYS else rr), "MEDIUM_VARIANCE"))
    if sp["weeks"]:
        cands.append((sp["weeks"] * rr, sp["label"]))
    best = max(cands, key=lambda c: c[0])                # first listed wins a tie (supplier tier before variance)
    top = [c for c in cands if c[0] == best[0]][0]
    return ceil(best[0]), top[1], None


def forecast_over_lead_time(mid, lt):
    f = FC[FC.material_id == mid].sort_values("week_start")["consensus_forecast"].astype(float).tolist()
    return sum(f[k] * min(7, lt - 7 * k) / 7 for k in range(math.ceil(lt / 7)) if lt - 7 * k > 0)


def backlog(mid):
    """Past-due unfilled customer demand + open customer orders with no material allocated."""
    return int(M.loc[mid, "past_due_unfilled"]) + int(M.loc[mid, "open_unallocated"])


def forecast_between(mid, start, end):
    """Consensus forecast between two dates (each weekly forecast is spread evenly over its 7 days)."""
    tot = 0.0
    for _, r in FC[FC.material_id == mid].iterrows():
        w = d(r.week_start)
        days = (min(end, w + timedelta(days=7)) - max(start, w)).days
        if days > 0:
            tot += float(r.consensus_forecast) * days / 7
    return tot


def pos_between(mid, start, end):
    """Open PO quantity due on or after `start` and before `end`."""
    po = PO[PO.material_id == mid]
    return int(po[po.due_date.map(d).between(start, end - timedelta(days=1))]["qty"].astype(int).sum()) if len(po) else 0


def typical_order(mid, rr):
    """Typical re-order quantity: run-rate demand over the lead time, rounded up to a whole supplier lot (pallet)."""
    lot = int(M.loc[mid, "supplier_lot_size"])
    need = rr * F(int(M.loc[mid, "lead_time_days"]), 7)
    return int(math.ceil(need / lot)) * lot if lot else ceil(need)


def spike_po(mid, sp, cls, ss, rr):
    """Spike PO = spike order + forecast demand over the lead time + safety stock target - on hand - open POs due inside the lead time
    (backlog is taken out of on hand). Order-by date = need date - lead time; if that is today or past, order now.
    Triggered by (a) a spike order (a single order >= 20% above the weekly run rate, forecasted or not) or
    (b) a critical material whose supplier just moved to HIGH (no spike order, order now)."""
    if cls == "INTERMITTENT":
        return None
    lt = int(M.loc[mid, "lead_time_days"])
    big = SO[(SO.material_id == mid) & (SO.qty.astype(int) >= rr * (1 + SPIKE_ORDER_PCT))]
    supplier_high = M.loc[mid, "criticality"] == "CRITICAL" and sp["tier_now"] == "HIGH" and sp["tier_prior"] != "HIGH"
    if not len(big) and not supplier_high:
        return None
    order_by = min([d(x) - timedelta(days=lt) for x in big.need_date] + ([AS_OF] if supplier_high else []))
    late = order_by <= AS_OF
    start = CURRENT_WEEK if late else order_by
    end = start + timedelta(days=lt)
    bl = backlog(mid)
    if late:
        on_hand_at = int(M.loc[mid, "on_hand"]) - bl
        pos_in = int(PO[PO.material_id == mid].pipe(lambda p: p[p.due_date.map(d) <= AS_OF + timedelta(days=lt)])["qty"].astype(int).sum())
    else:      # stock projected forward to the order-by date
        on_hand_at = round(int(M.loc[mid, "on_hand"]) - bl - forecast_between(mid, CURRENT_WEEK, order_by) + pos_between(mid, AS_OF, order_by), 2)
        pos_in = pos_between(mid, order_by, end)
    # unforecasted orders are always added; a forecasted order is added only if it falls after the forecast window (else it is already in it)
    spike_term = sum(int(r.qty) for _, r in big.iterrows() if r.unforecasted == "Y" or d(r.need_date) >= end)
    parts = dict(spike_order=spike_term, backlog=bl, lead_time_demand=round(forecast_between(mid, start, end), 2),
                 safety_stock_target=ss, on_hand_at_order_by=on_hand_at, open_pos_in_lead_time=pos_in)
    raw = F(spike_term + parts["lead_time_demand"] + ss - on_hand_at - pos_in).limit_denominator(100)
    uf = any(r.unforecasted == "Y" for _, r in big.iterrows())
    fo = any(r.unforecasted == "N" for _, r in big.iterrows())
    reason = "+".join(x for x, on in (("SPIKE_ORDER_UNFORECASTED", uf), ("SPIKE_ORDER_FORECASTED", fo), ("SUPPLIER_HIGH", supplier_high)) if on)
    need_qty = max(0, ceil(raw))
    lot = int(M.loc[mid, "supplier_lot_size"])
    qty = (int(math.ceil(F(need_qty, lot))) * lot if lot else need_qty)     # whole supplier lots, rounded up (a positive need is at least one lot)
    days_to = (order_by - AS_OF).days
    timing = "" if raw <= 0 else ("ORDER_LATE" if days_to < 0 else ("ORDER_NOW" if days_to == 0 else "ORDER_BY"))
    typical = typical_order(mid, rr)
    return dict(qty=qty, need_qty=need_qty, lot_size=lot, status="SPIKE_PO" if raw > 0 else "COVERED_BY_STOCK", reason=reason, order_by=str(order_by) if raw > 0 else "",
                days_to_order_by=days_to if raw > 0 else "", timing=timing,
                supplier_check="Y" if raw > 0 and qty >= (1 + SPIKE_ORDER_PCT) * typical else "N", typical_order_qty=typical, **parts)


def projection(mid, ss, rule):
    f = FC[FC.material_id == mid].sort_values("week_start")["consensus_forecast"].astype(float).tolist()
    po = PO[PO.material_id == mid]
    inv = int(M.loc[mid, "on_hand"]) - backlog(mid)
    so = SO[(SO.material_id == mid) & (SO.unforecasted == "Y")]      # forecasted orders are already in the consensus forecast
    ends, demand_total = [], 0
    for b in range(BUCKETS):
        start, stop = CURRENT_WEEK + timedelta(days=28 * b), CURRENT_WEEK + timedelta(days=28 * (b + 1))
        rec = int(po[po.due_date.map(d).between(start, stop - timedelta(days=1)) | (False)]["qty"].astype(int).sum()) if len(po) else 0
        if b == 0 and len(po):                                       # anything due before the first bucket counts in B1
            rec += int(po[po.due_date.map(d) < start]["qty"].astype(int).sum())
        dem = sum(f[4 * b: 4 * b + 4]) + (int(so[so.need_date.map(d).between(start, stop - timedelta(days=1))]["qty"].astype(int).sum()) if len(so) else 0)
        demand_total += dem
        inv = inv + rec - dem
        ends.append(round(inv))
    below = next((f"B{i + 1}" for i, e in enumerate(ends) if e < ss), "")
    short = next((f"B{i + 1}" for i, e in enumerate(ends) if e < 0), "")
    deficit = max(0, -min(ends))
    high = rule in ("HIGH_TIER", "HIGH_VARIANCE")
    need = bool(deficit > DECISION_SHORT_PCT * demand_total or (high and below))
    return dict(ends=ends, first_below=below, first_shortage=short, shortage_units=deficit, decision="Y" if need else "N")


def accuracy(mid):
    h = H[H.material_id == mid].sort_values("week_start").tail(FC_WEEKS)
    a = h["actual"].astype(int)
    s, c = h["statistical_forecast"].astype(int), h["consensus_forecast"].astype(int)
    tot = int(a.sum())
    w_s, w_c = F(int((s - a).abs().sum()), tot), F(int((c - a).abs().sum()), tot)
    bias = F(int(c.sum()) - tot, tot)
    fva = w_s - w_c
    return dict(wape_pct=float(w_c * 100), bias_pct=float(bias * 100), fva_pts=float(fva * 100),
                bias_flag="BIAS_HIGH" if bias > BIAS_LIMIT else ("BIAS_LOW" if bias < -BIAS_LIMIT else ""),
                error_flag="HIGH_ERROR" if w_c > ERROR_LIMIT else "",
                fva_flag="OVERRIDE_HURTS" if fva < 0 else ("OVERRIDE_ADDS_VALUE" if fva > 0 else ""))


def purchases(mid):
    lt = int(M.loc[mid, "lead_time_days"])
    out = []
    for _, r in FC[(FC.material_id == mid)].iterrows():
        wk = d(r.week_start)
        release = wk - timedelta(days=lt)
        firm = r.firm_order == "Y"
        conf = int(r.confidence_pct)
        if release > AS_OF + timedelta(days=BUY_WINDOW_DAYS):
            dec = "NOT_YET"
        elif firm or conf >= CONFIDENCE_MIN:
            dec = "BUY_LATE" if release < AS_OF else "BUY"
        else:
            dec = "DO_NOT_BUY"
        q = int(r.consensus_forecast)
        lot = int(M.loc[mid, "supplier_lot_size"])
        below = "Y" if q < lot else "N"       # below one supplier lot: ask for a smaller quantity or rework on-hand material
        out.append(dict(material_id=mid, need_week=str(wk), qty=q, lot_size=lot, below_lot=below,
                        order_qty=q if below == "Y" else int(math.ceil(F(q, lot))) * lot,
                        confidence_pct=conf, firm_order=r.firm_order, release_date=str(release), decision=dec))
    return out


def build_all():
    cls, vol = classify_all()
    rows, buys = [], []
    for mid in M.index:
        sup = M.loc[mid, "supplier_id"]
        sp = supplier_policy(sup)
        base = dict(material_id=mid, supplier_id=sup, material_class=cls[mid], criticality=M.loc[mid, "criticality"],
                    lead_time_days=int(M.loc[mid, "lead_time_days"]), tier_now=sp["tier_now"], tier_prior=sp["tier_prior"],
                    days_in_tier=sp["days_in_tier"])
        if cls[mid] == "INTERMITTENT":
            vr, rr = dict(regime="N/A", vclass="N/A", peak_pct=0.0, var=[], periods=[]), F(0)
        else:
            acts = weekly(mid)
            vr = variance(acts)
            rr = run_rate(acts, vr["regime"], vr["var"])
        ss, rule, rop = safety_stock(mid, cls[mid], sp, vr, rr)
        cur = int(M.loc[mid, "current_safety_stock"])
        change = ("CHANGE" if ss > 0 else "NO_CHANGE") if cur == 0 else ("CHANGE" if F(abs(ss - cur), cur) > CHANGE_TOLERANCE else "NO_CHANGE")
        sp_order = spike_po(mid, sp, cls[mid], ss, rr)
        row = dict(base, annual_volume=vol[mid], variance_regime=vr["regime"], variance_class=vr["vclass"],
                   peak_spike_pct=round(vr["peak_pct"], 1), run_rate=round(float(rr), 2), rule=rule, ss_target=ss,
                   reorder_point=rop if rop is not None else "", ss_current=cur, on_hand=int(M.loc[mid, "on_hand"]), ss_change=change,
                   ss_delta_value=round((ss - cur) * float(M.loc[mid, "unit_cost"]), 2), monitor=sp["monitor"],
                   step_date=sp["step_date"], spike_po_qty=sp_order["qty"] if sp_order else "", spike_po_need=sp_order["need_qty"] if sp_order else "",
                   spike_po_status=sp_order["status"] if sp_order else "", spike_po_reason=sp_order["reason"] if sp_order else "",
                   spike_po_order_by=sp_order["order_by"] if sp_order else "", spike_po_timing=sp_order["timing"] if sp_order else "",
                   spike_po_supplier_check=sp_order["supplier_check"] if sp_order else "")
        if vr["regime"] == "ONE_TIME":                                # what it would be if the spike turns out to be persistent
            rr_all = F(sum(periods(weekly(mid))[-RUN_RATE_PERIODS:]), PERIOD_WEEKS * RUN_RATE_PERIODS)
            row["if_persistent_target"] = ceil(F(5, 2) * rr_all * F(row["lead_time_days"], 7))
        if cls[mid] == "INTERMITTENT":
            row.update(first_below_ss_bucket="", first_shortage_bucket="", decision_needed="N", shortage_units=0,
                       bias_flag="", error_flag="", fva_flag="")
            buys += purchases(mid)
        else:
            pr = projection(mid, ss, rule)
            ac = accuracy(mid)
            row.update(first_below_ss_bucket=pr["first_below"], first_shortage_bucket=pr["first_shortage"],
                       decision_needed=pr["decision"], shortage_units=pr["shortage_units"], wape_pct=round(ac["wape_pct"], 1),
                       bias_pct=round(ac["bias_pct"], 1), fva_pts=round(ac["fva_pts"], 1), bias_flag=ac["bias_flag"],
                       error_flag=ac["error_flag"], fva_flag=ac["fva_flag"], projected_end=pr["ends"])
        row["typical_order_qty"] = typical_order(mid, rr) if cls[mid] != "INTERMITTENT" else ""
        row["_spike_parts"] = sp_order
        rows.append(row)
    tiers = []
    for sup in sorted(set(M.supplier_id)):
        now, prior = tier_record(sup, AS_OF)[0], tier_record(sup, PRIOR_AS_OF)[0]
        if now != prior:
            order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
            tiers.append(dict(supplier_id=sup, tier_prior=prior, tier_now=now,
                              direction="UPGRADE" if order[now] > order[prior] else "DOWNGRADE"))
    return rows, buys, tiers


def main():
    rows, buys, tiers = build_all()
    df = pd.DataFrame(rows).drop(columns=["_spike_parts"])
    df.to_csv("policy_results.csv", index=False)
    pd.DataFrame(buys).to_csv("purchase_results.csv", index=False)
    pd.DataFrame(tiers).to_csv("tier_changes.csv", index=False)
    show = ["material_id", "material_class", "rule", "tier_now", "variance_regime", "run_rate", "ss_target", "ss_current", "ss_change", "spike_po_qty", "spike_po_status"]
    print(df[show].to_string(index=False))
    print(f"\n{len(buys)} custom-item purchase lines, {len(tiers)} supplier tier changes since {PRIOR_AS_OF}")


if __name__ == "__main__":
    main()
