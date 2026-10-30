# S&OP Cycle Pre-Read (10-13-2026)
*Compared with the last cycle (09-15-2026). Numbers and rules are computed by code; the explanations are drafted by Claude and checked.*

## Executive summary

Cycle reviewed 17 materials as of 10-13-2026. Safety stock raised by $204,081. Supplier risk elevated three tiers to mitigate typhoon alert in Taiwan (Pacific Components Ltd), customs delay in Mexico (Bajio Wire & Cable SA), and earthquake alert in Japan (Kansai Sensors KK). Five spike orders require immediate action for ITM-001, ITM-008, ITM-014, ITM-035, and ITM-037. Penang Semiconductor Sdn downgraded one tier.

### Decisions for leadership

1. Order 5,600 units ITM-001 from Pacific Components Ltd immediately due to Taiwan typhoon risk
2. Order 2,800 units ITM-008 from Formosa Circuits Co by 11-02-2026 for unforecasted spike
3. ITM-014 order for 300 units from Nordic Precision AB is late; ask supplier about expediting
4. Order 4,500 units ITM-035 from Rhein Magnetics GmbH by 11-16-2026 for persistent spike
5. Order 3,500 units ITM-037 from Kansai Sensors KK immediately due to Japan earthquake alert

## Supplier risk changes since the last cycle

| Supplier | Moved | Days in new tier | Reason (Risk Detection Agent) |
|---|---|---|---|
| Pacific Components Ltd (SUP-001) | LOW to HIGH | 12 | active HIGH alert ALT-001 (TYPHOON) in Taiwan |
| Bajio Wire & Cable SA (SUP-007) | LOW to MEDIUM | 7 | active MEDIUM alert ALT-003 (CUSTOMS) in Mexico |
| Kansai Sensors KK (SUP-009) | MEDIUM to HIGH | 8 | active HIGH alert ALT-005 (EARTHQUAKE) in Japan |
| Penang Semiconductor Sdn (SUP-010) | MEDIUM to LOW | 12 | no risk triggers |

Pacific Components Ltd, Bajio Wire & Cable SA, and Kansai Sensors KK raised to mitigate active regional risks. Penang Semiconductor Sdn downgraded to low tier with stable operations. Monitor ITM-031 supplier (Bajio Wire & Cable SA) through 11-05-2026 and hold ITM-044 decisions until 10-31-2026.

## Spike POs

| Material | Why | Status | Order qty (whole lots) | Calculated need | Lot size | Order by | Timing | Typical re-order | Ask supplier? |
|---|---|---|---|---|---|---|---|---|---|
| ITM-001 PCB 4-LAYER V1 | Supplier High | Spike PO | 5,600 | 5,500 | 200 | 10-13-2026 | Order Now | 2,000 | Yes: lead time / partials |
| ITM-008 CARTON 12X10X8 V8 | Spike Order Unforecasted | Spike PO | 2,800 | 2,700 | 400 | 11-02-2026 | Order By | 1,600 | Yes: lead time / partials |
| ITM-014 SENSOR TEMP V14 | Spike Order Forecasted | Spike PO | 300 | 186 | 300 | 10-07-2026 | Order Late | 600 | No |
| ITM-035 CRYSTAL 16MHZ V35 | Spike Order Forecasted | Spike PO | 4,500 | 4,440 | 300 | 11-16-2026 | Order By | 2,100 | Yes: lead time / partials |
| ITM-037 FASTENER M3X8 V37 | Supplier High | Spike PO | 3,500 | 3,200 | 500 | 10-13-2026 | Order Now | 2,000 | Yes: lead time / partials |
| ITM-046 RESISTOR 10K V46 | Spike Order Unforecasted | Covered By Stock | 0 | 0 | 500 | - | - | 1,500 | No |
| ITM-053 CONNECTOR 24PIN V53 | Spike Order Unforecasted | Covered By Stock | 0 | 0 | 500 | - | - | 1,500 | No |

## Safety stock recommendations

| Material | Type | Rule | Current | Target | Decision | $ change | Reorder point |
|---|---|---|---|---|---|---|---|
| ITM-001 PCB 4-LAYER V1 | continuous, top volume | High Tier | 400 | 5,000 | Change | $57,500 | - |
| ITM-005 CRYSTAL 16MHZ V5 | continuous, top volume | High Tier | 300 | 3,750 | Change | $27,600 | - |
| ITM-003 CONNECTOR 24PIN V3 | custom / intermittent | Zero Stock | 0 | 0 | No Change | $0 | - |
| ITM-008 CARTON 12X10X8 V8 | continuous, top volume | High Tier | 4,000 | 4,000 | No Change | $0 | - |
| ITM-009 MAGNETIC COIL V9 | continuous, low-volume tail | High Tier | 1,500 | 1,500 | No Change | $0 | - |
| ITM-014 SENSOR TEMP V14 | continuous, low-volume tail | Tail Days | 86 | 86 | No Change | $0 | - |
| ITM-018 CARTON 12X10X8 V18 | continuous, low-volume tail | Tail Rop | 108 | 108 | No Change | $0 | 1608 |
| ITM-021 PCB 4-LAYER V21 | continuous, low-volume tail | Tail Days | 43 | 43 | No Change | $0 | - |
| ITM-022 CAPACITOR 100NF V22 | continuous, top volume | Stable 2Wk | 600 | 1,200 | Change | $660 | - |
| ITM-031 PCB 4-LAYER V31 | continuous, top volume | Stable 1Wk Monitor | 567 | 567 | No Change | $0 | - |
| ITM-035 CRYSTAL 16MHZ V35 | continuous, top volume | Medium Variance | 800 | 2,840 | Change | $11,424 | - |
| ITM-037 FASTENER M3X8 V37 | continuous, top volume | High Tier | 800 | 5,000 | Change | $92,400 | - |
| ITM-044 SENSOR TEMP V44 | continuous, top volume | Hold 2Wk | 800 | 800 | No Change | $0 | - |
| ITM-046 RESISTOR 10K V46 | continuous, top volume | Stable 1Wk | 600 | 600 | No Change | $0 | - |
| ITM-053 CONNECTOR 24PIN V53 | continuous, top volume | High Variance | 350 | 3,282 | Change | $21,697 | - |
| ITM-051 PCB 4-LAYER V51 | custom / intermittent | Zero Stock | 120 | 0 | Change | -$7,200 | - |
| ITM-026 RESISTOR 10K V26 | continuous, low-volume tail | Tail Rop | 73 | 73 | No Change | $0 | 802 |

## Projected gaps

| Material | First below safety stock | First shortage | Largest shortage (units) | Decision needed |
|---|---|---|---|---|
| ITM-001 PCB 4-LAYER V1 | B1 | B1 | 8,100 | YES |
| ITM-005 CRYSTAL 16MHZ V5 | - | - | 0 | - |
| ITM-003 CONNECTOR 24PIN V3 | - | - | 0 | - |
| ITM-008 CARTON 12X10X8 V8 | B2 | B3 | 5,500 | YES |
| ITM-009 MAGNETIC COIL V9 | - | - | 0 | - |
| ITM-014 SENSOR TEMP V14 | B1 | B1 | 4,300 | YES |
| ITM-018 CARTON 12X10X8 V18 | - | - | 0 | - |
| ITM-021 PCB 4-LAYER V21 | - | - | 0 | - |
| ITM-022 CAPACITOR 100NF V22 | B4 | - | 0 | - |
| ITM-031 PCB 4-LAYER V31 | - | - | 0 | - |
| ITM-035 CRYSTAL 16MHZ V35 | B2 | B3 | 7,600 | YES |
| ITM-037 FASTENER M3X8 V37 | B1 | B4 | 3,800 | YES |
| ITM-044 SENSOR TEMP V44 | - | - | 0 | - |
| ITM-046 RESISTOR 10K V46 | - | - | 0 | - |
| ITM-053 CONNECTOR 24PIN V53 | - | - | 0 | - |
| ITM-051 PCB 4-LAYER V51 | - | - | 0 | - |
| ITM-026 RESISTOR 10K V26 | - | - | 0 | - |

## Custom (intermittent) items: buy decisions

| Custom item | Need week | Qty | Supplier lot | Confidence | Firm order | Release date | Decision |
|---|---|---|---|---|---|---|---|
| ITM-003 | 11-23-2026 | 40 | 100 | 100% | Y | 10-19-2026 | Buy (below one lot: ask supplier for a smaller quantity or rework similar on-hand material) |
| ITM-003 | 12-07-2026 | 25 | 100 | 80% | N | 11-02-2026 | Buy (below one lot: ask supplier for a smaller quantity or rework similar on-hand material) |
| ITM-003 | 12-14-2026 | 30 | 100 | 70% | N | 11-09-2026 | Buy (below one lot: ask supplier for a smaller quantity or rework similar on-hand material) |
| ITM-003 | 01-04-2027 | 18 | 100 | 90% | N | 11-30-2026 | Future Planned Buy |
| ITM-051 | 11-02-2026 | 15 | 100 | 100% | Y | 10-12-2026 | Buy Late (below one lot: ask supplier for a smaller quantity or rework similar on-hand material) |
| ITM-051 | 11-16-2026 | 20 | 100 | 69% | N | 10-26-2026 | Do Not Buy |
| ITM-051 | 11-23-2026 | 10 | 100 | 70% | N | 11-02-2026 | Buy (below one lot: ask supplier for a smaller quantity or rework similar on-hand material) |
| ITM-051 | 11-30-2026 | 12 | 100 | 40% | N | 11-09-2026 | Do Not Buy |
| ITM-051 | 12-14-2026 | 9 | 100 | 85% | N | 11-23-2026 | Future Planned Buy |

## Material briefs

### ITM-001 PCB 4-LAYER V1 (Pacific Components Ltd, tier HIGH)
**Raise safety stock to 5000 units and place a Spike PO for 5600 units immediately to cover supply gap starting in B1.**

- **What changed:** Supplier moved from LOW to HIGH tier on 10-13-2026 (12 days in current tier) due to active typhoon alert in Taiwan affecting Pacific Components Ltd.
- **Safety stock:** Increase safety stock from current 400 units to target 5000 units. The rule for HIGH-tier suppliers is 2.5 times usage during lead time. This raises inventory investment by $57,500. Change decision is CHANGE.
- **Spike PO message to buyer:** Place a Spike PO for 5600 units (whole supplier lots, rounded up) immediately. Before releasing, contact the supplier to confirm whether lead time will be extended or whether partial deliveries will be planned to build and ship this higher quantity. The Spike PO will help close the gap; without it, shortage starts in B1 (10-12-2026 to 11-08-2026) with ending stock at -100 units.
- **Decision needed:** A decision is needed on the projected shortage. The first bucket below safety stock is B1 (10-12-2026 to 11-08-2026). The largest shortage reaches 8100 units in B6. Leadership must decide whether the Spike PO is sufficient or additional mitigation is required.

### ITM-005 CRYSTAL 16MHZ V5 (Pacific Components Ltd, tier HIGH)
**Raise safety stock target from 300 to 3750 units due to supplier tier increase to HIGH.**

- **What changed:** Supplier Pacific Components Ltd moved from LOW to HIGH tier on 10-12-2026 (12 days in current tier) due to active HIGH alert ALT-001 (TYPHOON) in Taiwan.
- **Safety stock:** Target safety stock is 3750 units; current safety stock is 300 units. This should be increased. The rule is: supplier tier is HIGH, so safety stock equals 2.5 times usage during lead time (35 days at 300 units per week).
- **Forecast:** Forecast has high positive bias (25%) and a negative value-add score (−20 points). The forecast has overrides that are hurting accuracy. Review bias and consider adjusting the override assumptions.

### ITM-003 CONNECTOR 24PIN V3 (Pacific Components Ltd, tier HIGH)
**Buy 40, 25, and 30 units on schedule for three firm or high-confidence forecasted orders; supplier moved to HIGH risk due to Taiwan typhoon alert.**

- **What changed:** Supplier Pacific Components Ltd moved from LOW to HIGH risk tier 12 days ago due to active typhoon alert ALT-001 in Taiwan.
- **Safety stock:** Safety stock target remains at 0. Custom or intermittent items carry zero safety stock; this material is bought only for firm customer orders or forecasts of 70% confidence or higher.
- **Custom item:** Release 40 units on 10-19-2026 (firm order), 25 units on 11-02-2026 (80% confidence), and 30 units on 11-09-2026 (70% confidence). All three quantities are below the 100-unit supplier lot. Ask the supplier about a smaller quantity for each, or consider rework of similar on-hand material. The fourth line (18 units, due 01-04-2027) is a future planned buy; review in a later cycle.

### ITM-008 CARTON 12X10X8 V8 (Formosa Circuits Co, tier HIGH)
**A Spike PO of 2,800 units is required to prevent stockouts beginning in bucket B3.**

- **What changed:** No change in supplier tier; Formosa Circuits Co remains at HIGH risk tier for 285 days due to an active typhoon alert in Taiwan. An unforecasted spike order for 3,000 units with a need date of 11-30-2026 has created a supply gap.
- **Safety stock:** Safety stock target remains at 4,000 units with no change recommended. The target is set by the rule for a HIGH-tier supplier: 2.5 times usage during the 28-day lead time.
- **Spike PO message to buyer:** Order 2,800 units by 11-02-2026. Contact the supplier to confirm whether lead time will be extended or whether partial deliveries will be planned to accommodate this higher quantity. The open PO for 1,600 units due 11-02-2026 remains in place.
- **Forecast:** Forecast accuracy is strong at 5% WAPE with no bias. The system override adds value and should be retained.
- **Decision needed:** Without the Spike PO, stock drops below safety stock (target 4,000) in bucket B2 and reaches -700 units in bucket B3 (12-07-2026 to 01-03-2027), with largest shortage of -5,500 units. Approve Spike PO to prevent stockouts.

### ITM-009 MAGNETIC COIL V9 (Formosa Circuits Co, tier HIGH)
**Magnetic coil V9 has stable demand with no spike; safety stock remains at target of 1500 units and no Spike PO is needed.**

- **What changed:** Supplier Formosa Circuits Co remains in HIGH risk tier due to active typhoon alert in Taiwan for 285 days. No change to demand pattern, which shows no spikes. No new purchase orders.
- **Safety stock:** Safety stock target remains at 1500 units and requires no change. Current safety stock of 1500 units meets the rule of 2.5 times weekly usage (150 units per week) during the 28-day lead time.

### ITM-014 SENSOR TEMP V14 (Nordic Precision AB, tier HIGH)
**Order 300 units immediately to cover forecasted spike, though the order-by date has passed; contact supplier about expediting and confirm feasibility of the higher volume.**

- **What changed:** Supplier Nordic Precision AB remains in the HIGH risk tier (285 days); on-time delivery has declined from 94% to 82% over six months. No change to safety stock or demand pattern.
- **Safety stock:** Safety stock target remains 86 units (1 to 3 days of expected demand for this low-volume tail item). No change recommended.
- **Spike PO message to buyer:** Place a Spike PO for 300 units to cover a forecasted spike order (SO-7003, 1000 units needed 10-28-2026). The order-by date of 10-07-2026 has passed; order is late. Contact the supplier about expediting delivery. Current on-hand stock is 1500 units.
- **Decision needed:** Projected shortages begin in bucket B1 (10-12-2026 to 11-08-2026) and reach 4300 units by bucket B6. Leadership must decide whether to accept the shortage, expedite the Spike PO, or adjust customer commitments for the spike order.

### ITM-018 CARTON 12X10X8 V18 (Gulf Metals FZE, tier HIGH)
**Safety stock remains appropriate at 108 units; monitor supplier financial health.**

- **What changed:** Supplier remains in HIGH tier (financial health score 38 is below 45) for 285 days. No change since last cycle.
- **Safety stock:** Safety stock target stays at 108 units. The rule is 3 days of safety stock for a low-volume tail item with long lead time. Reorder point is 1608 units (usage during lead time plus 3 days).

### ITM-021 PCB 4-LAYER V21 (Midwest Fastener Co, tier MEDIUM)
**Safety stock remains at 43 units; ITM-021 is adequately positioned with no changes required this cycle.**

- **What changed:** Supplier Midwest Fastener Co remains at MEDIUM tier (41 days in current tier); no tier change since last cycle. Reason: PO PO-0020 for a related item is 22 days late. No spike pattern detected for ITM-021.
- **Safety stock:** Safety stock target stays at 43 units (current: 43). The rule for this low-volume tail item caps safety stock at 1 to 3 days of expected demand (run rate 150 units per week). No change recommended.
- **Forecast:** Forecast accuracy is strong (WAPE 5.3%, bias 0.0%); no accuracy flags present.

### ITM-022 CAPACITOR 100NF V22 (Midwest Fastener Co, tier MEDIUM)
**Raise safety stock target for ITM-022 from 600 to 1200 units to protect against supplier delays.**

- **What changed:** Supplier Midwest Fastener Co remains in MEDIUM tier (41 days in current tier). No change in supplier status or demand pattern since last cycle.
- **Safety stock:** Target should increase to 1200 units (currently 600). The rule for stable demand with a MEDIUM-tier supplier is 2 weeks of run rate, which is 1200 units. This $660 increase will help buffer against the supplier's documented delivery delays. Current on-hand stock is 2000 units.

### ITM-031 PCB 4-LAYER V31 (Bajio Wire & Cable SA, tier MEDIUM)
**Maintain safety stock at 567 units; monitor supplier tier through 11-05-2026.**

- **What changed:** Supplier moved from LOW to MEDIUM tier due to active customs alert ALT-003 in Mexico.
- **Safety stock:** Safety stock target remains 567 units; no change. Rule: 1 week of run rate while monitoring supplier tier. On 11-05-2026, if tier stays MEDIUM, target steps to 2 weeks. Monitor until that date.

### ITM-035 CRYSTAL 16MHZ V35 (Rhein Magnetics GmbH, tier MEDIUM)
**Increase safety stock to 2,840 units and place Spike PO of 4,500 units by 11-16-2026 to address persistent spike pattern and projected shortages.**

- **What changed:** Spike pattern is persistent, with peak spikes at 40%. Supplier Rhein Magnetics GmbH remains at medium risk tier (financial health and on-time delivery below targets for 285 days).
- **Safety stock:** Target safety stock should increase from current 800 units to 2,840 units. The rule for persistent demand spikes between 20% and 50% requires 1.5 times the usage during the 28-day lead time. This is a $11,424 increase in inventory value.
- **Spike PO message to buyer:** Place a Spike PO for 4,500 units (whole supplier lots, rounded up) by order-by date 11-16-2026. Contact Rhein Magnetics GmbH to confirm whether the lead time will be extended or partial deliveries will be planned to support this higher quantity. Without this order, the first shortage occurs in bucket B3 (starting 12-07-2026), with a maximum shortage of 7,600 units in bucket B6 (ending 03-28-2027).
- **Decision needed:** Leadership approval needed: Current on-hand stock covers the spike order but not projected shortages. First gap below safety stock is bucket B2. Without the Spike PO, bucket B3 will have a shortage. Approve the $11,424 safety stock increase and Spike PO commitment.

### ITM-037 FASTENER M3X8 V37 (Kansai Sensors KK, tier HIGH)
**Raise safety stock to 5000 units and place a 3500-unit Spike PO immediately due to supplier moved to HIGH risk tier.**

- **What changed:** Supplier Kansai Sensors KK moved from MEDIUM to HIGH risk tier (8 days in current tier) due to active HIGH alert for earthquake in Japan.
- **Safety stock:** Increase safety stock target from current 800 to 5000 units. The rule for HIGH tier suppliers is 2.5 times usage during lead time (35 days at 400 units per week). This must change immediately to protect against extended lead time or supply disruption.
- **Spike PO message to buyer:** Order 3500 units now. This is rounded up to whole supplier lots (500 units per lot). Contact the supplier to ask whether the higher quantity will trigger an extended lead time or whether partial deliveries will be planned to build and ship the order.
- **Decision needed:** Without the Spike PO, gaps begin in B4 with the largest shortage of 3800 units in B6. Leadership must decide whether to place the Spike PO to close projected gaps or accept shortage risk.

### ITM-044 SENSOR TEMP V44 (Penang Semiconductor Sdn, tier LOW)
**Safety stock remains at 800 units; supplier moved to LOW tier with no risk triggers.**

- **What changed:** Supplier Penang Semiconductor Sdn moved from MEDIUM to LOW tier on 10-12-2026 (12 days in current tier) with no risk triggers. No spike pattern detected. Demand remains stable.
- **Safety stock:** Target remains 800 units; current safety stock is 800. No change. Policy rule: stable demand with supplier recently moved to LOW, holding 2 weeks of stock until 10-31-2026, then stepping down to 1 week.
- **Forecast:** Forecast accuracy shows high error (WAPE 50%). Bias is neutral. Monitor forecast quality in coming cycles.

### ITM-046 RESISTOR 10K V46 (Great Lakes Packaging, tier LOW)
**Safety stock remains at 600 units; stock already covers the one-time spike order of 3,000 units, so no additional purchase order is needed.**

- **What changed:** No change. Supplier Great Lakes Packaging remains in LOW tier with no risk triggers. Demand pattern is one-time spike.
- **Safety stock:** Safety stock stays at target of 600 units. The rule for this stable-demand, LOW-tier material is 1 week of run rate (600 units per week). No change is recommended.
- **Spike PO message to buyer:** The unforecasted spike order of 3,000 units (need date 12-14-2026) is already covered by on-hand stock of 24,000 units. No Spike PO is required. If this spike becomes persistent demand, the safety stock target would be raised to 3,800 units.

### ITM-053 CONNECTOR 24PIN V53 (Alpine Connectors AG, tier LOW)
**Increase safety stock from 350 to 3282 units to manage persistent demand spikes of 50% or more.**

- **What changed:** Demand pattern is persistent spike. Supplier Alpine Connectors AG remains at low risk tier (285 days in current tier, no risk triggers).
- **Safety stock:** Safety stock target should be increased from current 350 to 3282 units. Rule: persistent demand spikes of 50% or more require safety stock equal to 2.5 times usage during lead time (21 days at 437.5 units per week). This increases inventory value by $21,697.
- **Spike PO message to buyer:** No Spike PO required. An unforecasted spike order for 525 units due 11-25-2026 is already covered by current on-hand stock of 14000 units.

### ITM-051 PCB 4-LAYER V51 (Alpine Connectors AG, tier LOW)
**Reduce safety stock from 120 to 0 for this custom item; buy only confirmed orders and high-confidence forecast lines.**

- **What changed:** No supplier or demand pattern change. Supplier Alpine Connectors AG remains in the low risk tier (285 days).
- **Safety stock:** Safety stock target is 0; current safety stock is 120. Reduce by -$7,200. Custom or intermittent items carry zero safety stock and are bought only for firm customer orders or forecasts of 70% confidence or higher.
- **Custom item:** Release 15 units on 10-12-2026 (firm order, below lot size 100—ask supplier about smaller quantity or rework). Do not buy 11-16-2026 line (69% confidence). Release 10 units on 11-02-2026 (70% confidence, below lot size 100—ask supplier about smaller quantity or rework). Do not buy 11-30-2026 line (40% confidence). Buy 9 units on 11-23-2026 is a future planned buy; too early to release, review in next cycle.

### ITM-026 RESISTOR 10K V26 (Saigon Assembly JSC, tier LOW)
**Keep safety stock at 73 units; no Spike PO needed. Supplier remains stable and low-risk.**

- **What changed:** No change. Supplier remains at LOW risk tier with no risk triggers. Demand pattern shows no spike activity.
- **Safety stock:** Safety stock target remains at 73 units, matching current level—no change. Low-volume tail item with a 30-day lead time requires 3 days of safety stock plus usage during lead time, totaling a reorder point of 802 units.
