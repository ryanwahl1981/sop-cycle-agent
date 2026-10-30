"""
Checks on Claude's writing for the S&OP agent (code, no AI).
 - what each material brief MUST say (built from the rules engine's results)
 - grounding: every number, date and ID in the writing must appear in what the model was shown
 - length limits, tone, and the safety-stock wording must match the engine's decision
"""
import json
import re

BRIEF_FIELDS = ["headline", "what_changed", "safety_stock_recommendation", "spike_po_message", "custom_item_note",
                "forecast_note", "decision_note"]
LIMITS = {"headline": 30, "what_changed": 45, "safety_stock_recommendation": 45, "spike_po_message": 70,
          "custom_item_note": 90, "forecast_note": 35, "decision_note": 45,
          "executive_summary": 90, "decision": 35, "supplier_watch": 60}
MAX_DECISIONS = 5
BANNED = ["catastrophic", "disastrous", "unacceptable", "negligent", "fraudulent", "panic", "disaster"]
# causes and claims the data does not support (alerts are typhoon / customs / earthquake; nothing is "geopolitical")
UNSUPPORTED = ["even with the spike po", "even after the spike po", "despite the spike po", "orders placed", "spike pos placed", "have been placed", "promot", "geopolitical", "political", "reintegrat", "critical shortage", "crisis"]
CODE_RE = re.compile(r"\b[A-Z]{2,}(?:_[A-Z0-9]+)+\b")          # raw system labels such as SUPPLIER_HIGH must be written in plain words
CHECK_KEYS = ["fields_ok", "length_ok", "safety_stock_ok", "variance_ok", "tier_ok", "spike_ok", "decision_ok", "custom_ok",
              "forecast_ok", "numbers_ok", "dates_ok", "ids_ok", "tone_ok"]
CHECK_LABELS = {"fields_ok": "All sections present", "length_ok": "Concise (slide-ready)", "safety_stock_ok": "Safety stock matches the rules",
                "variance_ok": "Spike pattern described", "tier_ok": "Supplier tier change described", "spike_ok": "Spike PO message correct",
                "decision_ok": "Decision flagged correctly", "custom_ok": "Custom-item buys correct", "forecast_ok": "Forecast flags covered",
                "numbers_ok": "Numbers come from the data", "dates_ok": "Dates come from the data", "ids_ok": "IDs come from the data",
                "tone_ok": "Neutral wording"}
NUM_RE = re.compile(r"(?<![\w-])\d+(?:,\d{3})*(?:\.\d+)?")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
US_RE = re.compile(r"\b(\d{2})-(\d{2})-(\d{4})\b")


def to_us(text):
    """2026-10-13 -> 10-13-2026 (the format people read)."""
    return ISO_RE.sub(r"\2-\3-\1", str(text))


def to_iso(text):
    """10-13-2026 -> 2026-10-13 (the format the engine and the checks use inside)."""
    return US_RE.sub(r"\3-\1-\2", str(text))


def iso_in(sub):
    return sorted(set(ISO_RE.findall(" ".join(str(v) for v in (sub.values() if isinstance(sub, dict) else [])))))


ID_RE = re.compile(r"\b(?:ITM|SUP|PO|SO)-\d+\b")
ALLOWED_NUMBERS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 28, 30, 50, 70, 100}      # rule constants quoted in the key (20%, 70%, 30 days...)
UP = ["increase", "raise", "raised", "increased", "grow"]
DOWN = ["reduc", "lower safety", "lower the", "decreas", "cut ", "drop", "stop holding"]
SAME = ["no change", "hold", "keep", "unchanged", "maintain", "stay", "remain", "leave"]


def json_text(sub):
    return json.dumps(sub, default=str)


def sub_text(sub, key):
    return str(sub.get(key, "")).lower()


def words(text):
    return len(re.findall(r"\S+", text or ""))


def nums(text):
    t = DATE_RE.sub(" ", ID_RE.sub(" ", str(text)))
    return {round(float(x.replace(",", "")), 2) for x in NUM_RE.findall(t)}


def has(text, *tokens):
    t = (text or "").lower().replace(",", "")
    return all(str(k).lower() in t for k in tokens)


def any_of(text, options):
    t = (text or "").lower()
    return any(o in t for o in options)


def n(x):
    """A number as it would be written (no commas, no trailing .0)."""
    f = float(x)
    return str(int(f)) if f == int(f) else str(f)


def normalize(sub):
    """Make a submission safe to check: strings only, missing fields reported."""
    out, missing = {}, []
    for k in BRIEF_FIELDS:
        v = sub.get(k) if isinstance(sub, dict) else None
        if v is None:
            missing.append(k)
            v = ""
        out[k] = v if isinstance(v, str) else str(v)
    return out, missing


def required_texts(row, buys):
    """What the brief must contain, from the engine's facts. Returns a list of (check_key, field, test, problem text)."""
    r, req = row, []
    ss_text = lambda s: s["safety_stock_recommendation"]
    tgt, cur = int(r["ss_target"]), int(r["ss_current"])
    # safety stock wording must match the engine's decision
    if r["ss_change"] == "CHANGE":
        words_ = UP if tgt > cur else DOWN
        req.append(("safety_stock_ok", lambda s: has(ss_text(s), n(tgt)) and any_of(ss_text(s), words_) and (cur == 0 or has(ss_text(s), n(cur))),
                    f"state the safety stock target {tgt} and the current value {cur}, and say it should be {'increased' if tgt > cur else 'reduced'}"))
    else:
        req.append(("safety_stock_ok", lambda s: any_of(ss_text(s), SAME) and (tgt == 0 or has(ss_text(s), n(tgt))),
                    f"say the safety stock stays as it is (target {tgt}); do not recommend a change"))
    if r["material_class"] == "INTERMITTENT":
        req.append(("safety_stock_ok", lambda s: any_of(ss_text(s), ["zero", "no safety stock", "no stock", " 0"]) , "say a custom item carries zero safety stock"))
    if r["reorder_point"] != "":
        req.append(("safety_stock_ok", lambda s: has(ss_text(s), n(r["reorder_point"])), f"state the reorder point {r['reorder_point']}"))
    if r["step_date"]:
        req.append(("safety_stock_ok", lambda s: has(ss_text(s), r["step_date"]), f"include the date {r['step_date']} when the policy changes"))
    if r["monitor"] == "Y":
        req.append(("safety_stock_ok", lambda s: has(ss_text(s), "monitor"), "say to monitor the supplier tier until the date"))
    # variance pattern
    if r["variance_regime"] == "ONE_TIME":
        req.append(("variance_ok", lambda s: any_of(s["what_changed"] + s["safety_stock_recommendation"], ["one-time", "one time"]), "call the spike one-time"))
        req.append(("variance_ok", lambda s: has(ss_text(s) + " " + s["spike_po_message"] + " " + s["what_changed"], n(r["if_persistent_target"])), f"say what the target would be if it becomes persistent ({r['if_persistent_target']})"))
    if r["variance_regime"] == "PERSISTENT":
        req.append(("variance_ok", lambda s: has(s["what_changed"] + s["safety_stock_recommendation"], "persistent"), "call the spike pattern persistent"))
    # supplier tier change
    if r["tier_now"] != r["tier_prior"]:
        req.append(("tier_ok", lambda s: has(s["what_changed"], r["tier_prior"].lower()) and has(s["what_changed"], r["tier_now"].lower()),
                    f"say the supplier moved from {r['tier_prior']} to {r['tier_now']}"))
    # spike PO
    st = r["spike_po_status"]
    if st == "SPIKE_PO":
        q, tm = n(r["spike_po_qty"]), r["spike_po_timing"]
        req.append(("spike_ok", lambda s: has(s["spike_po_message"], q), f"state the Spike PO quantity {q}"))
        if tm == "ORDER_BY":
            req.append(("spike_ok", lambda s: has(s["spike_po_message"], r["spike_po_order_by"]), f"state the order-by date {r['spike_po_order_by']}"))
        elif tm == "ORDER_NOW":
            req.append(("spike_ok", lambda s: any_of(s["spike_po_message"], ["now", "today", "immediately"]), "say to order now"))
        elif tm == "ORDER_LATE":
            req.append(("spike_ok", lambda s: any_of(s["spike_po_message"], ["late"]) and has(s["spike_po_message"], r["spike_po_order_by"]),
                        f"say the order is late (order-by date {r['spike_po_order_by']} has passed) and ask the supplier about expediting"))
        if r["spike_po_supplier_check"] == "Y":
            req.append(("spike_ok", lambda s: has(s["spike_po_message"], "lead time", "partial"), "tell the buyer to ask the supplier whether lead time will be extended or partial deliveries planned"))
        else:
            req.append(("spike_ok", lambda s: not any_of(s["spike_po_message"], ["partial", "lead time will be extended", "lead time be extended"]),
                        "the supplier check is NOT required for this Spike PO (it is not 20% above the typical re-order quantity): do not tell the buyer to ask about extended lead time or partial deliveries"))
    elif st == "COVERED_BY_STOCK":
        req.append(("spike_ok", lambda s: any_of(s["spike_po_message"], ["cover"]) and not any_of(s["spike_po_message"], ["order by"]), "say stock already covers the spike order, so no Spike PO"))
    else:
        req.append(("spike_ok", lambda s: s["spike_po_message"].strip() == "", "leave spike_po_message empty (no spike order or supplier trigger)"))
    # decision
    if r["decision_needed"] == "Y":
        b = r["first_shortage_bucket"] or r["first_below_ss_bucket"]
        req.append(("decision_ok", lambda s: has(s["decision_note"], b), f"explain the decision needed and name bucket {b}"))
    else:
        req.append(("decision_ok", lambda s: s["decision_note"].strip() == "", "leave decision_note empty (no executive decision needed)"))
    # custom items
    if r["material_class"] == "INTERMITTENT":
        for b in buys:
            if b["material_id"] != r["material_id"]:
                continue
            if b["decision"] in ("BUY", "BUY_LATE"):
                req.append(("custom_ok", lambda s, b=b: has(s["custom_item_note"], b["release_date"]), f"mention the release date {b['release_date']} to buy {b['qty']} units"))
                if b["below_lot"] == "Y":
                    req.append(("custom_ok", lambda s, b=b: any_of(s["custom_item_note"], ["smaller quantit", "smaller amount", "smaller order", "fewer units", "below the lot", "below one lot", "less than", "minimum lot", "below the minimum", "under one lot"]) and has(s["custom_item_note"], "rework"),
                                f"the {b['qty']}-unit buy is below one supplier lot ({b['lot_size']}): say, using the words 'smaller quantity' and 'rework': ask the supplier about a smaller quantity, or consider rework of similar on-hand material into the custom item"))
            elif b["decision"] == "NOT_YET":
                req.append(("custom_ok", lambda s: has(s["custom_item_note"], "future planned buy"), "describe the not-yet line as a 'future planned buy' (too early to release; review in a later cycle)"))
            elif b["decision"] == "DO_NOT_BUY":
                req.append(("custom_ok", lambda s, b=b: has(s["custom_item_note"], b["need_week"]), f"say do not buy the {b['need_week']} line (confidence {b['confidence_pct']}%)"))
    else:
        req.append(("custom_ok", lambda s: s["custom_item_note"].strip() == "", "leave custom_item_note empty (not a custom item)"))
    # forecast flags
    for flag, word in (("bias_flag", "bias"), ("fva_flag", "override"), ("error_flag", "error")):
        if r.get(flag):
            req.append(("forecast_ok", lambda s, w=word: has(s["forecast_note"], w), f"mention the {flag.replace('_flag', '')} flag ({r[flag]}) in forecast_note"))
    return req


def check_brief(row, buys, sub, seen):
    iso_found = iso_in(sub)
    sub = {k: to_iso(v) for k, v in sub.items()} if isinstance(sub, dict) else sub
    s, missing = normalize(sub)
    checks = {k: True for k in CHECK_KEYS}
    problems = {k: [] for k in CHECK_KEYS}

    def fail(k, msg):
        checks[k] = False
        problems[k].append(msg)

    if missing:
        fail("fields_ok", f"missing fields: {', '.join(missing)}")
    for f in BRIEF_FIELDS:
        if words(s[f]) > LIMITS[f]:
            fail("length_ok", f"{f} is {words(s[f])} words; the limit is {LIMITS[f]}")
    for k, test, msg in required_texts(row, buys):
        if not test(s):
            fail(k, msg)
    alltext = " ".join(s.values())
    shown_n, shown_text = nums(seen), seen
    bad = sorted(x for x in nums(alltext) if x not in shown_n and x not in ALLOWED_NUMBERS)
    if bad:
        fail("numbers_ok", f"these numbers are not in the data: {', '.join(n(x) for x in bad)}. Quote numbers exactly as given; do not calculate new ones")
    badd = sorted(x for x in set(DATE_RE.findall(alltext)) if x not in shown_text)
    if badd:
        fail("dates_ok", f"these dates are not in the data: {', '.join(badd)}")
    badi = sorted(x for x in set(ID_RE.findall(alltext)) if x not in shown_text)
    if badi:
        fail("ids_ok", f"these IDs are not in the data: {', '.join(badi)}")
    hit = [w for w in BANNED if w in alltext.lower()]
    if hit:
        fail("tone_ok", f"use neutral wording; remove: {', '.join(hit)}")
    if iso_found:
        fail("dates_ok", "write dates as MM-dd-yyyy (for example 10-13-2026), not year first")
    uns = [w for w in UNSUPPORTED if w in alltext.lower()]
    if uns:
        fail("tone_ok", f"remove claims the data does not support: {', '.join(uns)}. Use only the causes named in the facts")
    codes = sorted(set(CODE_RE.findall(alltext)))
    if codes:
        fail("tone_ok", f"write system labels in plain words instead of: {', '.join(codes)}")
    for m_ in re.finditer(r"(?:on[- ]hand|current stock|current inventory)[^.;]{0,35}?(\d[\d,]*)", s["safety_stock_recommendation"] + ". " + s["what_changed"] + ". " + s["spike_po_message"], re.I):
        v_ = int(m_.group(1).replace(",", ""))
        if v_ == int(row["ss_current"]) and v_ != int(row["on_hand"]):
            fail("safety_stock_ok", f"{v_} is the CURRENT SAFETY STOCK, not on-hand stock (on-hand is {row['on_hand']}). Do not call it on-hand or current stock")
    allb = (s["headline"] + " " + s["spike_po_message"]).lower()
    if row["spike_po_status"] == "SPIKE_PO" and row["spike_po_timing"] == "ORDER_BY" and any(w in allb for w in ("immediately", "right away", "order now", "urgent")):
        fail("spike_ok", f"the order is not due yet: order BY {row['spike_po_order_by']}; do not say immediately or now")
    if row["spike_po_status"] == "SPIKE_PO" and row["spike_po_timing"] in ("ORDER_NOW", "ORDER_BY") and any(w in allb for w in ("already passed", "has passed", "past due", "overdue", "already past")):
        fail("spike_ok", "the order-by date has not passed: it is " + ("today" if row["spike_po_timing"] == "ORDER_NOW" else "in the future"))
    if row["reorder_point"] == "" and re.search(r"reorder point|reorder at|re-order point", " ".join(s.values()).lower()):
        fail("safety_stock_ok", "no reorder point applies to this material: do not mention one")
    mine = [b for b in buys if b["material_id"] == row["material_id"]]
    if mine and not any(b["decision"] == "BUY_LATE" for b in mine) and any(w in (s["headline"] + " " + s["custom_item_note"]).lower() for w in ("immediately", "right now", "today")):
        fail("custom_ok", "do not say 'immediately' for custom buys: each is released on its own release date, none are late")
    if any(b["decision"] == "NOT_YET" for b in mine) and not any(b["decision"] == "DO_NOT_BUY" for b in mine) and \
            any(p in s["custom_item_note"].lower() for p in ("do not buy", "don't buy", "not buy")):
        fail("custom_ok", "a NOT_YET line is not a do-not-buy: say it is too early to release and will be reviewed in a later cycle")
    return checks, problems


def fix_instructions(problems):
    return [f"[{CHECK_LABELS[k]}] {m}" for k, ms in problems.items() for m in ms]


# ---------------- cycle summary ----------------
def check_summary(facts, sub, seen):
    """The cycle-level executive summary: concise, grounded, and it must name every spike PO material, decision and tier change."""
    problems = []
    if not isinstance(sub, dict):
        return False, ["submission was not an object"]
    if ISO_RE.search(json_text(sub)):
        problems.append("write dates as MM-dd-yyyy (for example 10-13-2026), not year first")
    sub = json.loads(to_iso(json_text(sub)))
    es, sw = str(sub.get("executive_summary", "")), str(sub.get("supplier_watch", ""))
    dec = sub.get("top_decisions", [])
    dec = [x if isinstance(x, str) else str(x.get("decision", x)) if isinstance(x, dict) else str(x) for x in dec] if isinstance(dec, list) else []
    if not es or not dec:
        problems.append("executive_summary and top_decisions are required")
    if words(es) > LIMITS["executive_summary"]:
        problems.append(f"executive_summary is {words(es)} words; limit {LIMITS['executive_summary']}")
    if words(sw) > LIMITS["supplier_watch"]:
        problems.append(f"supplier_watch is {words(sw)} words; limit {LIMITS['supplier_watch']}")
    if len(dec) > MAX_DECISIONS:
        problems.append(f"at most {MAX_DECISIONS} top_decisions")
    for i, x in enumerate(dec):
        if words(x) > LIMITS["decision"]:
            problems.append(f"top_decisions item {i + 1} is {words(x)} words; limit {LIMITS['decision']}")
    allt = " ".join([es, sw] + dec)
    for mid in facts["must_name_materials"]:
        if mid not in allt:
            problems.append(f"name {mid} (it needs a decision or a Spike PO)")
    sname = {t["supplier_id"]: t["name"] for t in facts["supplier_tier_changes"]}
    for sup in facts["must_name_suppliers"]:
        if sup not in allt and sname.get(sup, sup) not in allt:
            problems.append(f"name {sname.get(sup, sup)} ({sup}; its risk tier changed)")
    bad = sorted(x for x in nums(allt) if x not in nums(seen) and x not in ALLOWED_NUMBERS)
    if bad:
        problems.append(f"these numbers are not in the data: {', '.join(n(x) for x in bad)}")
    badd = sorted(x for x in set(DATE_RE.findall(allt)) if x not in seen)
    badi = sorted(x for x in set(ID_RE.findall(allt)) if x not in seen)
    if badd:
        problems.append(f"these dates are not in the data: {', '.join(badd)}")
    if badi:
        problems.append(f"these IDs are not in the data: {', '.join(badi)}")
    hit = [w for w in BANNED if w in allt.lower()]
    if hit:
        problems.append(f"use neutral wording; remove: {', '.join(hit)}")
    uns = [w for w in UNSUPPORTED if w in allt.lower()]
    if uns:
        problems.append(f"remove claims the data does not support: {', '.join(uns)}. Use only the alert types in the facts")
    codes = sorted(set(CODE_RE.findall(allt)))
    if codes:
        problems.append(f"write system labels in plain words instead of: {', '.join(codes)}")
    NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
    for verb, key in (("upgraded|raised|moved up|elevated", "upgrades"), ("downgraded|lowered|moved down", "downgrades")):
        for m_ in re.finditer(r"\b(one|two|three|four|five|six|\d+) suppliers? (?:were |was |have been )?(?:" + verb + ")", allt.lower()):
            c_ = NUM.get(m_.group(1), int(m_.group(1)) if m_.group(1).isdigit() else -1)
            if c_ != facts[key]:
                problems.append(f"{facts['upgrades']} supplier(s) moved up and {facts['downgrades']} moved down; do not recount (say '{len(facts['supplier_tier_changes'])} supplier tier changes')")
    # each decision item must use the right supplier and the lot-rounded quantity, and say when an order is already late
    owner = facts.get("material_supplier", {})
    names = {v["name"] for v in owner.values()}
    for x in dec:
        for mid in set(ID_RE.findall(x)):
            if mid in owner:
                wrong = [nm for nm in names if nm in x and nm != owner[mid]["name"]]
                if wrong:
                    problems.append(f"{mid} is supplied by {owner[mid]['name']}, not {', '.join(wrong)}")
                sp = next((q for q in facts["spike_pos"] if q["material_id"] == mid), None)
                if sp and n(sp["quantity"]) not in x.replace(",", ""):
                    problems.append(f"{mid}: state the Spike PO quantity {n(sp['quantity'])} (whole supplier lots)")
                if sp and sp["timing"] == "ORDER_BY" and any(w in x.lower() for w in ("immediate", "urgent", "right now")):
                    problems.append(f"{mid}: the order is not due now (order by {sp['order_by']}); do not call it immediate or urgent")
                if sp and sp["timing"] == "ORDER_LATE" and "late" not in x.lower():
                    problems.append(f"{mid}: say the order is already late (order-by date {sp['order_by']} has passed)")
    return not problems, problems
