# S&OP Cycle Agent: Data Key and Rules

All data is synthetic. Review date **2026-10-13**; previous S&OP cycle **2026-09-15**. Materials use the same IDs and suppliers as the Risk Detection Agent (ITM-xxx, SUP-xxx); supplier tiers come from its output (HIGH / MEDIUM / LOW) plus a tier history file.

## Definitions
| Term | Definition |
|---|---|
| Period | 4 consecutive weeks. P1 is the newest. The agent looks at the last 12 periods. |
| Baseline | Median of the 12 period totals (not distorted by spikes). |
| Spike variance | (period total minus baseline) divided by baseline. |
| Run rate | Mean weekly demand over the last 12 weeks (3 periods). If the spike pattern is ONE_TIME, the spike period is left out of the run rate. |
| Usage during lead time | Run rate x lead time in weeks. |
| Continuous | Demand in at least 20 of the last 26 weeks. Otherwise INTERMITTENT (custom). |
| Top / tail | Continuous materials ranked by trailing 52-week order volume (units). The top group is everything up to and including the item that crosses 80% of total volume. The rest is the tail. |
| Critical | A flag in the material master (customer or line-down impact). |

## Spike pattern (last 6 periods)
| Pattern | Rule |
|---|---|
| NONE | No period above +20% |
| ONE_TIME | 1 or 2 periods above +20% |
| PERSISTENT | 3 or more of the last 6 periods above +20% |

Variance class for a PERSISTENT pattern comes from the peak: **+50% or more = HIGH**, **above +20% and under +50% = MEDIUM**. Exactly +20% is not above 20%.
A ONE_TIME spike does not change safety stock. The report notes it and shows what the target would be if it became persistent.

## Safety stock (applied in this order)
| Material type | Safety stock |
|---|---|
| **Intermittent / custom** | **0.** Buy only for a firm customer order, or a forecast of **70% confidence or higher** (exactly 70% qualifies), released at the order point (need date minus lead time). Release dates within the next 28 days are shown. No spike orders. |
| **Continuous, tail** (not critical) | **1 to 3 days** of expected demand: LOW supplier 1 day, MEDIUM 2, HIGH 3. Lead time over 28 days: 3 days, with reorder point = usage during lead time + 3 days. |
| **Continuous, tail, critical** | Exempt from the cap. Uses the top-volume rules below. |
| **Continuous, top volume** | The highest of the applicable rules below. |

### Top-volume rules
| Condition | Safety stock |
|---|---|
| Supplier tier HIGH, or persistent variance of 50% or more | **2.5 x** usage during lead time |
| Persistent variance above 20% and under 50%, lead time over 28 days | **2.0 x** usage during lead time |
| Persistent medium variance, lead time 14 to 28 days | **1.5 x** usage during lead time |
| Persistent medium variance, lead time under 14 days | **1.0 x** weekly run rate |
| Stable demand, LOW supplier | **1 week** of run rate |
| Stable demand, MEDIUM supplier for 30 days or more | **2 weeks** of run rate |
| Stable demand, supplier just moved LOW to MEDIUM (under 30 days) | 1 week, with a **monitor** flag; becomes 2 weeks on day 30 |
| Stable demand, supplier moved MEDIUM to LOW (under 30 days) | Stays 2 weeks until day 30, then 1 week |
| Supplier moved HIGH to MEDIUM or LOW (under 30 days) | Stays at the HIGH policy until day 30 |

Upgrades to HIGH take effect immediately. Safety stock is rounded up to a whole unit.

## Changes, backlog, spike orders and Spike POs
- **Recommend a change** only when the new target differs from the current system value by more than 10% (or the current value is 0).
- **Backlog** = customer demand in current open orders that have no material allocated (unfilled) **plus** customer demand that is past due and unfilled.
- **Spike order** = a single customer order at least **20% above the weekly run rate** (exactly 20% counts). It can be **forecasted** (already in the consensus forecast) or **unforecasted** (it suddenly appears).
- **Spike PO** quantity = spike order + forecast demand over the lead time + safety stock target - on hand - open POs due within the lead time. Backlog (open unallocated + past due) is taken out of on hand.
  A **forecasted** spike order that falls inside the forecast window is already in the forecast, so it is not added a second time. An unforecasted order, or a forecasted one that falls after the window, is added as its own term.
  If the result is zero or less, stock already covers it and no Spike PO is recommended.
- **Order-by date** = the spike order's need date minus the material's lead time. The buyer message must say when to place the Spike PO so the material arrives in time:
  | Order-by date | Message |
  |---|---|
  | In the future | ORDER_BY: place the Spike PO by that date. Stock is projected forward to that date, and POs due before it count as on hand. |
  | Today | ORDER_NOW |
  | Already past | ORDER_LATE: order now and say how many days late; the lead time cannot be met, so ask the supplier about expediting. |
- **Typical re-order quantity** = the run-rate demand over the replenishment lead time, rounded **up** to a whole supplier lot (pallet). Example: lead time 2 weeks, run rate 200 a week, lot size 200 gives 400 per order. The lot size is a column in `materials.csv` (`supplier_lot_size`). Safety stock is held level and is not part of the typical order.
- **Spike PO is ordered in whole supplier lots.** The calculated need is rounded **up** to the next multiple of the supplier lot size (minimum one lot). The report shows the calculated need, the lot size and the order quantity. The supplier check (120% of the typical re-order quantity) uses the order quantity. Examples: ITM-001 5,500 needed, lot 200 -> 5,600; ITM-037 3,200, lot 500 -> 3,500; ITM-008 2,700, lot 400 -> 2,800; ITM-035 4,440, lot 300 -> 4,500; ITM-014 186, lot 300 -> 300.
- **Custom (intermittent) buys below one supplier lot** (ITM-003, ITM-051: lot 100): the buy stays at the forecast quantity and the report tells the buyer to ask the supplier about a smaller quantity, or to consider reworking similar on-hand material into the custom item. A buy at or above one lot is rounded up to whole lots.
- **A custom line that is not yet inside the 28-day release window is a 'future planned buy'**, never a do-not-buy. It is reviewed in a later cycle.
- **Dates in the report are written MM-dd-yyyy** (for example 10-13-2026). The engine and the answer key keep year-first dates internally; the report and Claude's writing convert.
- **Supplier check:** if the Spike PO is **at least 20% above the typical re-order quantity**, the buyer message must say to contact the supplier and find out whether the **lead time will be extended** or whether **partial deliveries** will be planned to build and ship the higher quantity.
- **A Spike PO is recommended for a continuous material in two situations:**
  1. A spike order exists (forecasted or unforecasted).
  2. A **critical** material's supplier moved to HIGH since the last cycle, with no spike order (the spike order term is 0).
  Custom (intermittent) materials never get a Spike PO; they follow the firm-order and 70% confidence rule. Tail items whose supplier was already HIGH get none unless a spike order exists.
- **Tier changes** between the last cycle and this one are reported for every supplier.

## Gap review and forecast accuracy
- **Projection:** 6 four-week buckets (B1 to B6) from 2026-10-12. Ending stock = start (on hand - backlog) + receipts - consensus forecast - any spike orders due in that bucket.
- **Below safety stock** = ending stock under the target. **Shortage** = ending stock under zero.
- **Needs an executive decision** when the shortage exceeds 5% of 6-month demand, or a HIGH-policy material falls below its safety stock.
- **Forecast accuracy** (last 26 weeks, continuous materials): WAPE; bias (flag above +/-10%); forecast value add = statistical WAPE minus consensus WAPE (a negative value means the sales override hurt); high error = WAPE above 40%.

## Planted cases (see `answer_key_policy.csv`)
Spike POs for a supplier moving to HIGH (ITM-001, ITM-037); for an unforecasted spike order with an order-by date (ITM-008); for a forecasted spike order inside the lead time, not double counted and already late (ITM-014); for a forecasted spike order far in the future with an order-by date (ITM-035). A spike order covered by stock (ITM-046, and ITM-053 at exactly 20% above run rate); an order below the 20% line (ITM-021). No Spike PO for a critical item with no tier move (ITM-009), a non-critical item with no spike order (ITM-005) or a custom item (ITM-003). Decoys: exactly +20% (ITM-031), exactly +50% (ITM-053), one-time spike (ITM-046), lead time exactly 28 and 30 days (ITM-035, ITM-026), confidence 69% vs 70% (ITM-051), high error with no bias (ITM-044), below safety stock but not HIGH policy (ITM-022).

## Files
`materials.csv`, `demand_history.csv` (78 weeks), `demand_forecast.csv` (26 weeks plus custom-item lines), `open_pos.csv`, `customer_spike_orders.csv`, `tier_history.csv`, `suppliers.csv`, `supplier_tiers.csv`; `answer_key_policy.csv`, `answer_key_purchases.csv`, `answer_key_tiers.csv`; rules engine `policy.py`; grader `evaluate_policy.py`; generator `make_sop_data.py`, `plan.py`, `plan_state.py`, `make_key.py`.
