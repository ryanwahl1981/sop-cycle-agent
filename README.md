# S&OP Cycle Agent: Safety Stock Policy, Supplier Risk and Spike POs

An AI agent that prepares the monthly S&OP / IBP supply review. It applies a written safety stock policy to every material, links the policy to **supplier risk tiers** from the [Supply Chain Risk Detection Agent](https://github.com/ryanwahl1981/supply-chain-risk-agent), recommends **Spike POs** with order-by dates, flags projected supply gaps that need an executive decision, and drafts a pre-read for the planning and buying teams.

**The design rule:** code decides every number; the AI investigates and writes; code checks the writing.

- **Code decides** (`policy.py`): material class, safety stock target, change or no change, supplier tier changes and the 30-day timing rules, demand spike patterns, Spike PO quantity and order-by date, supplier-check flag, projected gaps, forecast accuracy, and custom-item buy decisions.
- **Claude writes** (`agent.py`): a short brief per material, the message to the buyer, and a cycle executive summary.
- **Code checks the writing** (`sop_checks.py`): the brief must say what the rules decided, and every number, date and ID must come from the data. A brief that fails is sent back once with exact fixes; if it still fails it is flagged for human review.

Part of an AI-agent portfolio with the [Master Data Quality Agent](https://github.com/ryanwahl1981/master-data-quality-agent), the [Supply Chain Risk Detection Agent](https://github.com/ryanwahl1981/supply-chain-risk-agent) and the [Supplier QBR Agent](https://github.com/ryanwahl1981/supplier-qbr-agent). All data is **synthetic**. Materials and suppliers use the same IDs as the Risk Detection Agent.

## The policy in short (full rules in [`KEY.md`](KEY.md))

| Material type | Safety stock |
|---|---|
| Custom / intermittent | **Zero.** Buy only for a firm customer order, or a forecast of 70% confidence or higher, released at the order point |
| Continuous, low-volume tail | **1 to 3 days** of demand; long lead times get a reorder point of lead-time usage + 3 days |
| Continuous, top volume, HIGH-risk supplier or persistent spikes of 50%+ | **2.5 x** usage during lead time |
| Persistent medium spikes (20% to 50%) | **2.0 x / 1.5 x** usage during lead time, or **1.0 x** weekly run rate, by lead time |
| Stable demand | **1 week** (LOW supplier); **2 weeks** once a supplier has been MEDIUM for 30 days, with a monitor flag in the first 30 days |

A **spike order** is a single order at least 20% above weekly run rate, forecasted or not. The **Spike PO** quantity (rounded up to whole supplier lots) is the spike order + forecast over lead time + safety stock target - on hand - open POs due inside the lead time. The **order-by date** is the need date minus the lead time. If the Spike PO is 20% or more above the typical re-order quantity, the buyer is told to ask the supplier about extended lead time or partial deliveries.

## What it produces

`sop_pre_read.md` (dates written MM-dd-yyyy): executive summary and decisions for leadership; supplier risk changes; Spike POs with buyer messages; safety stock recommendations with dollar impact; projected gaps by 4-week bucket; custom-item buy decisions; and a brief per material.

## Measured results

**Rules engine (no AI), against the hand-written answer key:** 440 / 440 policy values, 9 / 9 custom-item buy decisions, 4 / 4 supplier tier changes.

**The agent's writing, final full run (all 17 materials, `claude-haiku-4-5`, about $0.20 per run), graded by `evaluate.py`:**

| What was graded | Result |
|---|---|
| Safety stock target quoted and direction correct | 17 / 17 |
| Spike PO quantity and order-by date correct | 5 / 5 |
| Supplier check (lead time / partials) only when required | 5 / 5 |
| Executive decision raised only when needed | 17 / 17 |
| Supplier tier change described (from and to) | 6 / 6 |
| Every number, date and ID comes from the data | 17 / 17 |
| Neutral tone, word limits, all sections present | 17 / 17 |
| No Spike PO message when none is triggered | 10 / 10 |
| Forecast accuracy flags covered | 4 / 4 |
| Custom-item buys and do-not-buys correct | 9 / 9 |
| Below-lot custom buys say "smaller quantity or rework" | 5 / 5 |
| Reorder point / policy dates, monitor flag, one-time spike, covered spike orders | 4/4, 1/1, 1/1, 2/2 |
| Briefs that needed one revision after a failed check | 11 / 17 |
| Briefs still flagged for human review after the retry | 0 / 17 |
| Executive summary names every Spike PO / decision material and every changed supplier | yes |

The earlier runs were weaker (3 briefs flagged in the first). Between runs I read the output by hand, found mistakes the checks missed, and added a check for each. `sample_output/sop_pre_read.md` is the real output of this run.

**Full marks do not mean the writing is perfect.** Reading this run by hand still found: the executive summary says supplier risk was "elevated three tiers" (it was three suppliers), and calls all five Spike POs "immediate" when two are due later; some briefs give the wrong date for when a supplier's tier changed (the date quoted exists in the data but belongs to another event); ITM-021's brief attributes another item's late purchase order to it; and one decision paragraph (ITM-035) is muddled. The checks verify facts, structure and the rules' decisions, not meaning. **A planner must read every brief.**

Offline test (a stand-in for Claude that makes deliberate mistakes): the checks catch every mistake and the retry fixes it.

The key tests the boundaries on purpose: spike variance of exactly +20% and +50%, lead times of exactly 28 and 30 days, forecast confidence of 69% versus 70%, a spike order of exactly 20% above run rate, a large order that stock already covers, a one-time spike that must not change safety stock, and a critical material that must not get a Spike PO because its supplier was already HIGH.

## How to run it (Windows)

1. Install Python and put these files in one folder, for example `C:\Users\<you>\sop_agent`.
2. Open Command Prompt in that folder and run: `pip install -r requirements.txt`
3. Set your Anthropic API key once: `setx ANTHROPIC_API_KEY "your-key-here"` (then close and reopen Command Prompt). **Never put the key in a file.**
4. See the decisions (no AI, free): `python policy.py`
5. Check the rules engine against the key (free): `python evaluate_policy.py`
6. Test the agent loop (free): `python test_offline.py`
7. Draft the pre-read: `python agent.py` (it drafts 3 materials first; set `MAX_MATERIALS = 17` at the top of `agent.py` for all)
8. Grade the result: `python evaluate.py`

## Limitations (please read)

- **Synthetic data, one cycle, 17 materials.** Real data is messier, and a real run would need exports from your planning system.
- **The checks verify facts, not meaning.** They confirm numbers, dates, IDs, structure and that the writing matches the rules' decisions, but they cannot judge whether a sentence makes sense. A planner must review every brief.
- **Assumptions I made that you may want to change** (all are settings in `policy.py`): run rate is the 12-week average (a one-time spike period is left out), "continuous" means demand in 20 of the last 26 weeks, the top group is the first 80% of annual order volume, a spike pattern is persistent when 3 of the last 6 four-week periods exceed +20%, and a spike order is 20% above weekly run rate.
- **Supplier tiers are a snapshot from the Risk Detection Agent**, and the tier history file is synthetic.
- **A small, cheap model is used.** Wording and the number of retries vary from run to run.
- The agent only drafts. It never places an order, changes a planning parameter or contacts a supplier.

## Files

| File | What it is |
|---|---|
| `policy.py` | Rules engine: classification, safety stock, tier timing, spike patterns, Spike POs, gaps, accuracy, custom-item buys |
| `sop_checks.py` | The "must say" list and the wording checks |
| `agent.py` | The Claude agent: tools, retry, pre-read output |
| `evaluate.py`, `evaluate_policy.py` | Grade the engine and the writing against the hand-written answer key |
| `test_offline.py` | Free test of the full loop with a stand-in for Claude |
| `KEY.md` | Every rule and definition |
| `materials.csv`, `demand_history.csv`, `demand_forecast.csv`, `open_pos.csv`, `customer_spike_orders.csv`, `tier_history.csv` | Synthetic input data |
| `suppliers.csv`, `supplier_tiers.csv` | Supplier names and the Risk Detection Agent's tiers |
| `answer_key_policy.csv`, `answer_key_purchases.csv`, `answer_key_tiers.csv` | Hand-written expected results |
| `sample_output/sop_pre_read.md` | A real output of the agent on the synthetic data |

## About

Built by **Ryan Wahl**, supply chain, procurement and data governance professional. [LinkedIn](https://www.linkedin.com/in/ryanmwahl)
