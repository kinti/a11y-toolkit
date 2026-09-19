# The free online analyzer (webapp/)

The machine half, free forever: drop these two files on any host with Python
3.9+ — no dependencies.

```bash
python3 analizador.py --port 8080          # http://your-host:8080
```

## What it serves

- `/` — the analyzer UI (URL in, full report out: score, findings grouped by
  severity with remediation, honest badge, the N-criteria-need-a-human block,
  evidence-pack download)
- `/analizar?url=…&lang=en|es` — full static audit as JSON
- `/pack?url=…` — countersignature-ready evidence pack (hash-verified)
- `/badge?score=N` — honest SVG badge

## Public-service hardening (already built in)

- http/https only; **private/loopback/reserved IPs blocked** (SSRF guard —
  the local CLI intentionally allows internal staging; a public service must
  not become someone's internal-network probe)
- per-IP rate limit (default 6/min, `--rate`)
- 3 MB fetch cap inherited from the engine; honest limits note on every report

## Deploying behind a reverse proxy (nginx)

```nginx
location /analizador/ {
    proxy_pass http://127.0.0.1:8080/;
    proxy_set_header X-Forwarded-For $remote_addr;   # rate limiting keys on this
}
```

Behind a proxy the client IP comes from the socket — if you front this with
another layer, adapt `_rate_ok` to read `X-Forwarded-For` safely (trusted
proxy only).

## The free/paid line

Free = everything the machine can measure (this app, forever, MIT).
Paid = the human half: guided WCAG-EM evaluation, signed conformance,
continuous monitoring with SLA, fixes with liability. Every free report
ends at exactly that boundary — the evidence pack IS the sales pitch,
printed by the product itself.
