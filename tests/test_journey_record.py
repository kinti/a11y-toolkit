#!/usr/bin/env python3
"""a11y-journey/1: the sealed journey record.

Contract: the walk and the judgment in one sha-sealed envelope; the seal is
tamper-evident (sha over the canonical payload) AND re-derivable (the
scoring is deterministic, so the stored steps must reproduce the stored
verdict). Same input → same record. MCP: seal=true returns the record,
verify_record judges a record instead of steps."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a11y_toolkit.a11yjourney import (seal_record, record_verify,  # noqa: E402
                                     JOURNEY_FORMAT, verdict)
from a11y_toolkit import server  # noqa: E402

results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(('ok  ' if cond else 'FAIL') + ' ' + name)


TASK = {'goal': 'sign up', 'kind': 'sign-up'}
STEPS = [
    {'action': 'click', 'target': 'Sign up', 'perceived': 'button announced',
     'friction': {'pattern': 'journey_focus_lost'}},
    {'action': 'fill', 'target': 'Email', 'perceived': 'no label announced',
     'friction': {'pattern': 'journey_hidden_in_tree'}},
    {'action': 'click', 'target': 'Create account', 'perceived': 'submitted'},
]
OUTCOME = {'completed': True, 'gave_up': False, 'workaround_used': False,
           'notes': ''}
URL = 'https://example.dev/signup'

# ── the record: everything in one envelope ──────────────────────────────────
r = seal_record(TASK, STEPS, OUTCOME, url=URL)
check('format a11y-journey/1', r['format'] == JOURNEY_FORMAT)
check('engine version stamped', bool(r['engine_version']))
check('walk stored as walked', r['steps'] == STEPS)
check('verdict embedded', r['verdict']['verdict'] in ('pass', 'partial', 'fail',
                                                      'blocked'))
plain = verdict(TASK, STEPS, OUTCOME, url=URL)
check('embedded verdict equals the plain verdict',
      r['verdict']['score'] == plain['score']
      and r['verdict']['findings'] == plain['findings'])
check('sha present and 64-hex', len(r['sha256']) == 64
      and all(c in '0123456789abcdef' for c in r['sha256']))

# ── determinism: same input → same record ───────────────────────────────────
r_again = seal_record(TASK, STEPS, OUTCOME, url=URL)
check('same input → same sha', r_again['sha256'] == r['sha256'])

# ── verify: intact record verifies ──────────────────────────────────────────
v = record_verify(r)
check('intact → verified', v['status'] == 'verified'
      and v['verdict'] == r['verdict']['verdict'])

# ── tampering: sha layer ────────────────────────────────────────────────────
r_t = json.loads(json.dumps(r))
r_t['verdict']['score'] = 99
v_t = record_verify(r_t)
check('edited verdict → tampered (sha)', v_t['status'] == 'tampered'
      and v_t['sha_intact'] is False)

# ── tampering: re-derivation layer (even with a forged sha) ─────────────────
r_f = json.loads(json.dumps(r))
r_f['steps'] = json.loads(json.dumps(STEPS))
r_f['steps'][0].pop('friction')
import hashlib  # noqa: E402
body = {k: v for k, v in r_f.items() if k != 'sha256'}
r_f['sha256'] = hashlib.sha256(json.dumps(
    body, sort_keys=True, ensure_ascii=False,
    default=str).encode('utf-8')).hexdigest()
v_f = record_verify(r_f)
check('forged sha + edited steps → tampered (re-derivation)',
      v_f['status'] == 'tampered' and v_f.get('verdict_reproducible') is False)

# ── invalid: not a record ────────────────────────────────────────────────────
check('not a record → invalid', record_verify({'format': 'x'})['status'] == 'invalid')
check('missing sha → invalid', record_verify(
    {'format': JOURNEY_FORMAT})['status'] == 'invalid')

# ── error path: bad friction log → error, no record ─────────────────────────
check('invalid friction → error dict', 'error' in seal_record(
    TASK, [{'friction': {'pattern': 'no_such_pattern'}}], OUTCOME, url=URL))

# ── optional trace rides along ───────────────────────────────────────────────
r_tr = seal_record(TASK, STEPS, OUTCOME, url=URL, trace={'steps': [], 'url': URL})
check('optional trace stored', r_tr['trace'] == {'steps': [], 'url': URL})

# ── bilingual: note and verify in both languages ────────────────────────────
r_es = seal_record(TASK, STEPS, OUTCOME, url=URL, lang='es')
check('es note travels', 'Evidencia de usabilidad' in r_es['score_note'])
v_es = record_verify({'format': 'x'}, lang='es')
check('es invalid note resolves', 'a11y-journey/1' in v_es['note'])

# ── MCP: seal=true → record; verify_record → verification ───────────────────
resp = server.invoke('a11y_journey_verdict', {'task': TASK, 'steps': STEPS,
                                              'outcome': OUTCOME, 'url': URL,
                                              'seal': True})
rec = json.loads(resp['content'][0]['text'])
check('MCP seal returns the record', rec.get('format') == JOURNEY_FORMAT)
resp2 = server.invoke('a11y_journey_verdict', {'task': TASK, 'steps': STEPS,
                                               'outcome': OUTCOME, 'url': URL})
check('without seal → plain verdict (back-compat)',
      json.loads(resp2['content'][0]['text']).get('mode') == 'journey')
resp3 = server.invoke('a11y_journey_verdict', {'task': TASK, 'steps': STEPS,
                                               'outcome': OUTCOME, 'url': URL,
                                               'verify_record': rec})
check('MCP verify_record verifies', json.loads(
    resp3['content'][0]['text'])['status'] == 'verified')

fails = [n for n, okc in results if not okc]
print(f"\n{len(results) - len(fails)}/{len(results)} checks")
sys.exit(1 if fails else 0)
