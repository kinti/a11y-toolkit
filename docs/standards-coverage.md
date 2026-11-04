# Standards coverage — which command serves which market's law

Most national accessibility laws converge on **WCAG 2.2 A/AA** (the
engine's core audit) plus a regional or national layer on top. This map
says which law each market enforces and which toolkit command serves it.
Verified 2026-11-02 against official sources where available; laws
change — verify with counsel before a contract or award.

## Family 1 — EN 301 549 (EU + EEA + derivatives)

Served by: `a11ytoolkit audit --url … --standard en301549 --target …`
and `a11ytoolkit scope --standard en301549` (clause per finding,
applicability scope, families 5–13 declared, tender annex via
`--solicitation`).

| Market | Law | Notes |
|---|---|---|
| EU-27 (public sector) | Web Accessibility Directive (EU 2016/2102) | since 2018 |
| EU (private e-commerce, banking, transport…) | European Accessibility Act (2019/882) | services since 2025-06; remaining by 2030-06 |
| Sweden | DOS-lagen | transposition considered stricter (higher fines, stronger inspection) |
| Norway | Discrimination and Accessibility Act (universell utforming) | |
| Denmark / Finland | national transpositions | Finland leans on consumer law for enforcement |
| Estonia / Latvia / Lithuania | WAD + EAA transpositions | |
| Canada (federal ICT) | Standard on Web Accessibility / ICT requirements | the government's own wizard cites EN 301 549 V4.1.1 |
| Spain (this product's home market) | RD 1112/2018 + Ley 11/2023 | |

## Family 2 — WCAG-direct (much of Latin America, US practice)

Served by: the default audit (`a11ytoolkit audit --url …`) — the laws in
this family require WCAG 2.x A/AA directly.

| Market | Law | Notes |
|---|---|---|
| Brazil | LBI — Lei 13.146/2015 | requires WCAG 2.2 AA; federal sites additionally follow **e-MAG 3.1**, the official government model (own numbered recommendations, es/pt docs, HTML/PDF only — not machine-readable: candidate for a curated mapping, see below) |
| Argentina | Ley 26.653 | WCAG 2.0-based, update discussed |
| Chile / Peru / Colombia / Uruguay / Mexico | sectoral laws and decrees | WCAG AA |
| United States (ADA practice) | DOJ guidance cites WCAG 2.1 AA | federal ICT itself: Section 508 (moved to the private pro layer) |

## Family 3 — National standards and procedures

| Standard | Market | Toolkit status |
|---|---|---|
| Section 508 (Revised, 2017) | US federal ICT | served by the private pro layer (GSA tree) — WCAG 2.x itself is covered by the public engine |
| RGAA 4.1 | France (mandatory for public sector) | **served**: `audit/scope --standard rgaa` — ingested from the government's official open-data JSON (106 criteria, full mechanical bridge to WCAG) |
| JIS X 8341-3:2016 | Japan (de facto public procurement) | documented, not served — the JIS text is ISO-style paid; agencies publish voluntary WCAG 2.1/2.2 addendum checklists (the default audit covers those) |
| KWCAG 2.1/2.2 | Korea (mandatory + government certification) | documented, not served — mapping ingest possible from the Korean document |
| GB/T 37668-2019 | China (public and services) | documented, not served |
| GOST R 52872-2019 | Russia (public sector) | existing standard, not served — business decision, not technical |

## Adding a standard

The proven pattern (see `scripts/rgaa_ingest.py` and
`a11y_toolkit/a11yrgaa.py`): a machine-readable source → an ingest script
that verifies and flattens → a thin data module with the bridge to WCAG
SC → `--standard <name>` on audit and scope. A standard without open
data needs a curated mapping instead — heavier, still doable.

## Honesty note

Covering a standard's CHECKLIST is not conformance: automation sees part
of any standard, a person reviews the rest, and the signature is human.
See the README's coverage claims and the evidence pack's empty signature
block.
