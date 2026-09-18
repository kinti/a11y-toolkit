# Countersignatory sandbox protocol (run before 2026-10-21)

Public, honest account of what the endpoint does — from someone who audits
for a living. Douglas has asked for this explicitly and will tag our key as
supply-side so it never lands in his demand metrics.

## Step 0 — key and prefix (Jesús, manual, once)

```bash
# create the key (free, instant, unapproved; uses your email)
curl -s -X POST https://countersignatory.com/v1/keys
# then EMAIL DOUGLAS THE PREFIX ONLY (first 8 chars) — never the full key
```

## Step 1 — public surfaces (no key needed)

```bash
curl -s https://countersignatory.com/v1/index | python3 -m json.tool
curl -s https://countersignatory.com/llms.txt
```

Record: markets listed, states (check.general said "open" at seed; our
wcag-conformance market said market_not_open), indicative prices and their
published provenance.

## Step 2 — price a WCAG-EM tier-3 task (keyed)

Per llms.txt: `POST /v1/quotes` takes `task_type` ∈ {judgment, verification,
approval, physical, signature}, `tier`, `sla_seconds`, optional `max_price`.
The tier ladder from the index: Check / Consensus / Countersign / Seal.
A tier-3 WCAG-EM conformance review maps naturally to `countersign`.

```bash
KEY=…
curl -s -X POST https://countersignatory.com/v1/quotes \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"task_type":"signature","tier":"countersign","sla_seconds":86400,
       "meta":{"scope":"WCAG-EM tier-3 conformance review, one page sample",
               "evidence_format":"a11y-evidence-pack/1"}}'
```

Record the exact response (quote id, price, expiry, any market_not_open
behavior — expected while the market is listed as opening).

## Step 3 — try to break it (the part he asked for)

```bash
# missing required fields → expect well-formed validation errors
curl -s -X POST …/v1/quotes -H "Authorization: Bearer $KEY" -d '{}'
# negative max_price / price
… -d '{"task_type":"signature","tier":"countersign","sla_seconds":60,"max_price":-1}'
# absurd sla
… -d '{"task_type":"signature","tier":"countersign","sla_seconds":999999999}'
# unknown tier / task_type
… -d '{"task_type":"notarize","tier":"countersign","sla_seconds":60}'
# register_interest without a valid quote_id
curl -s -X POST …/v1/interest -H "Authorization: Bearer $KEY" -d '{"market_id":"wcag-conformance"}'
# unicode/oversized meta
… -d '{"task_type":"signature","tier":"countersign","sla_seconds":60,"meta":{"x":"🦾"*1000}}'
```

## Step 4 — the write-up (publish either way, before Oct 21)

Skeleton, honest-results style:

1. **What it is** — the market thesis in one paragraph, in his words.
2. **What ran** — steps above, dates, exact responses (redact the key).
3. **What worked** — validation quality, provenance of seeded prices,
   measurement hygiene (the supply-side key tagging deserves public credit).
4. **What broke / is missing** — factual list, no drama.
5. **Verdict for accessibility buyers/sellers** — what would have to be true
   for an a11y_evidence pack to route through it (market open, DPA, PI
   filter built — his own published list).
6. **Disclosure** — supply-side relationship in discussion; key excluded
   from his metrics at his initiative.

Publish on jquin.net (EN), link from the repo's docs/ and from the
Countersignatory thread. Tag him — he asked for the critique in public.
