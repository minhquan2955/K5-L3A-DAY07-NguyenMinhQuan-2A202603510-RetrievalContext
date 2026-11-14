# Day07 frozen benchmark

`cases.json` contains 24 Vietnamese questions: 17 dev (15 answerable, 2 unanswerable) and 7 held-out test (5 answerable, 2 unanswerable).

The first 15 dev cases copy Day06 q01-q15 exactly, including the original Vietnamese questions, expected answers, explicit filters, primary evidence, and alternative evidence. `day6_origin_id` provides the mapping. Day06 q16-q20 are excluded. Five new answerable test items were authored from different target concepts from all Day06 questions and the information-system-components smoke question. No retrieval scores, agent answers, or test outcomes informed their construction.

## Schema and isolation

Each case has `id`, `split`, `question`, `answerable`, `gold`, `filter`, and `provenance`. Answerable cases have `expected_answer`. A gold entry contains `source_id`, `page`, and `evidence`; copied entries also preserve their original page/offset metadata and identify primary versus alternative evidence. Unanswerable cases omit `expected_answer`, have empty `gold`, and include `absence_reason` and `absence_check`.

Only the question and its explicit filter may become answer-agent inputs. Keep expected answers, gold, absence checks, and provenance outside model prompts and retrieval queries. Use only dev rows to develop or select configurations. Open test rows for evaluation only after the selected configuration and selection criteria are locked. Results must not be used to alter test questions or their difficulty.

## Evidence and absence checks

`page` is the 1-based physical position in the local 83-page PDF, not a full-book page number. `source_id` matches the B505 chunk `document_id`. The corpus contains all 505 original B chunks from the included 58 substantive source pages. Evidence matching uses original Day06 `canonical_text`: NFC Unicode normalization and whitespace collapse, without translation, paraphrase, case conversion, or word repair.

Each gold entry is an independently sufficient alternative (OR). A strict single-chunk retrieval hit requires its complete evidence on the specified source/page in one candidate chunk. Unanswerable cases are excluded from retrieval denominators. Context coverage may be checked after source-order merging of adjacent chunks on the same page; do not invent missing source words.

There is one preserved limitation: `d7-dev13` (Day06 q13) has valid evidence on physical page 53, but its complete original quote crosses B chunk boundaries. Its evidence remains unchanged. A single B chunk cannot satisfy the strict full-quote metric; a context assembled from the necessary adjacent chunks may satisfy it. Report this limitation rather than rewriting the original gold or silently relaxing the retrieval metric.

`source_review.json` records correct-page evidence containment checks, matching B chunk IDs, and the q13 limitation. Absence checks scan every B chunk, every included source page, and all 83 physical PDF pages, using source-language terms and reading the matching topic passages for the requested detail. Per-case term hits, page scopes, reasons, and limitations are recorded in `cases.json`; absence is not inferred from a top-k miss. These are AI-assisted source checks. Independent student review is **pending**; no human review is claimed.

## Freeze and reproducibility

`freeze.json` records the case-file SHA256, split IDs, UTC freeze timestamp, original PDF/B505/Day06-label/manifest/normalization-code snapshots, and source-review hash before Day07 evaluation. Verify `cases_sha256` against the bytes of `cases.json` before running an evaluation. Recheck source snapshot hashes before interpreting results. This freeze describes benchmark construction, not configuration selection; the runner must produce its own dev-selection lock before evaluating test.

Any later case edit requires a new freeze and rerunning the comparisons. Keep the original Day06 source read-only. The included source uses English, while the questions and expected answers use Vietnamese; no Day06 question was translated or rewritten.
