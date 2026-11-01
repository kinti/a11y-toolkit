#!/usr/bin/env python3
"""Section 508 (Revised, 2017) applicability — the GSA decision tree as data.

Source of truth: section508.gov/buy/determine-ict-standards (Step 3,
'Determine Which Standards Apply'), the tree the GSA Accessibility
Requirements Tool automates. This module models it so a11y_scope can
propose applicability for standard='508' the same way it does for
EN 301 549 families:

- three ICT types (content / software / hardware); the toolkit's targets
  map to content-web, content-non-web, software (hardware is listed for
  completeness — no audit exists for it here)
- product questions that change applicability (public-facing, official
  communication, authoring tool, is-assistive-technology)
- WCAG EXCEPTIONS for non-web content/software: 2.4.1, 2.4.5, 3.2.3,
  3.2.4 do not apply (E203/E204)
- chapters beyond WCAG: 302, 502, 503, 602, 603 always for software;
  504 when authoring; hardware chapter list is data (not evaluated here)

The machine pre-answers 'web-based' from the audit target; the human
answers the rest via scope answers keyed '508:<question>'. Nothing here
evaluates — it proposes applicability, declares chapters, and marks
exceptions as proposed-excluded with the standard's own reason.
"""

# WCAG success criteria that do NOT apply to non-web content/software
NON_WEB_EXCEPTIONS = ('2.4.1', '2.4.5', '3.2.3', '3.2.4')

# Revised 508 chapters that apply to software beyond WCAG (504 only when
# the software is also an authoring tool)
SOFTWARE_CHAPTERS = ('302', '502', '503', '602', '603')
AUTHORING_CHAPTER = '504'
CONTENT_CHAPTERS = ('602', '603')

# hardware chapters, listed for the families row (no audit here)
HARDWARE_CHAPTERS = ('302', '402', '403', '404', '405', '406', '407', '408',
                     '409', '410', '411', '412', '413', '414', '415', '602', '603')

STANDARD_NAME = 'Section 508 (Revised, 2017)'


def applicability(target='web', answers=None):
    """Product questions → applicability dict for a 508 scope.

    target: the scope target (web|documents|software). 'web' means
    web-based content/software per the audit itself; 'documents' maps to
    non-web electronic content. 'software' is non-web software unless a
    human answer says the product is web-based.

    answers: scope answers keyed '508:<question>' with
    {'answer': 'yes'|'no', 'reason': str} — human confirmation.
    """
    a = answers or {}

    def answer(q, default):
        item = a.get('508:' + q)
        if isinstance(item, dict) and item.get('answer') in ('yes', 'no'):
            return item['answer'], item.get('reason') or '', 'human'
        return default, '', 'machine'

    web_based, web_reason, web_src = answer('web_based', 'yes' if target == 'web' else 'no')
    public, public_reason, public_src = answer('public_facing', 'pending')
    official, official_reason, official_src = answer('official_comm', 'pending')
    authoring, authoring_reason, authoring_src = answer('authoring_tool', 'pending')

    wcag_applies = True
    exceptions = []
    if target in ('documents', 'software') and web_based == 'no':
        exceptions = list(NON_WEB_EXCEPTIONS)

    chapters = list(CONTENT_CHAPTERS if target in ('web', 'documents')
                    else SOFTWARE_CHAPTERS)
    if target == 'software' and authoring == 'yes':
        chapters.append(AUTHORING_CHAPTER)

    return {
        'standard': STANDARD_NAME,
        'target': target,
        'web_based': {'answer': web_based, 'source': web_src, 'reason': web_reason},
        'public_facing': {'answer': public, 'source': public_src, 'reason': public_reason},
        'official_comm': {'answer': official, 'source': official_src, 'reason': official_reason},
        'authoring_tool': {'answer': authoring, 'source': authoring_src, 'reason': authoring_reason},
        'wcag_applies': wcag_applies,
        'wcag_exceptions': exceptions,
        'chapters': chapters,
    }
