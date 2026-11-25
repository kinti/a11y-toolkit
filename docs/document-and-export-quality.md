# Document screening and export quality review

Reviewed `v5.35.1` (`deb8bc0`) on 25 November 2026. The checks used synthetic documents,
a local HTTP fixture and the public CLI. The findings below describe the released behavior.
The official PyPI installation reproduced the PDF CLI and export results. Its
MCP document tools returned `isError` for invalid PDF and DOCX inputs.

| Priority | Finding | Expected behavior |
|---|---|---|
| P1 | **Document errors can exit successfully.** PDF and the DOCX module returned a JSON error with exit 0 for a non-document. The VTT CLI did the same for an unrecognizable file. A missing PDF or an HTTP 503 fetching captions exited 1 with a traceback in place of JSON. | Invalid inputs and transport failures produce a JSON error and exit 1 from each CLI. Existing findings from completed checks keep their established exit behavior. [PDF](../a11y_toolkit/a11ypdf.py) · [DOCX](../a11y_toolkit/a11ydocx.py) · [WebVTT](../a11y_toolkit/a11yvtt.py) |
| P1 | **Partial document reads can be treated as complete.** A valid single-page PDF of 33,762,043 bytes passed `pdfinfo`, exceeded the screening read limit and returned `truncated: true`. Its evidence artifact was marked `complete` and the pack verified. A caption response cut short of its announced length returned one cue and a score of 100. | Distinguish complete and incomplete input at ingestion. Carry that status into evidence and reconcile it in the standalone verifier. Incomplete input must stay out of complete coverage. [PDF read limit](../a11y_toolkit/a11ypdf.py) · [Caption fetch](../a11y_toolkit/a11yvtt.py) · [Evidence status](../a11y_toolkit/a11yevidence.py) · [Verifier](../scripts/verify_pack.py) |
| P1 | **Export success can conceal an unavailable source.** EARL wrote zero assertions and exited 0 for a failed audit. SARIF wrote zero results and exited 0 for a crawl with one measured page and one HTTP 503. The exported files omitted the source error. | A failed source produces an export error. Any supported partial export carries the failed pages and the measured scope, so a downstream reader can distinguish an empty result from incomplete coverage. [EARL](../a11y_toolkit/a11yact.py) · [SARIF](../a11y_toolkit/a11ysarif.py) |
| P2 | **DOCX results depend on XML prefix spelling.** Rebinding the WordprocessingML prefix in a generated document and its styles preserved the parsed XML tree. Screening went from one table without header rows and `en-US` to zero tables and no language. | Resolve elements and attributes by namespace URI and local name. Equivalent XML produces equivalent findings and counts. [DOCX screening](../a11y_toolkit/a11ydocx.py) · [W3C XML namespaces](https://www.w3.org/TR/xml-names/) |
| P2 | **Invalid WebVTT syntax can score 100.** A misspelled file signature and a cue containing seconds outside the valid range each returned one cue and zero findings. | Validate the file signature and cue timings before counting cues or calculating speed and coverage. [WebVTT screening](../a11y_toolkit/a11yvtt.py) · [W3C WebVTT file structure and cue timings](https://www.w3.org/TR/webvtt1/) |

## Correction in v5.35.2

Document CLI failures produce a JSON `error` and exit 1. The DOCX reader
resolves namespaces, the caption parser skips malformed time intervals, and
the exporters reject incomplete sources. The verifier checks an archived
report's measurement status separately from its existing seal. [Evidence pack schema](evidence-pack-schema.md)
