# Finish Day07 basic lab

User authorization: finish remaining basic-lab steps, keep Day06 immutable and questions Vietnamese. No optional 100-page bonus, publishing, commits or pushes in this execution.

## Decisions
Use three measured configurations on the same B505 snapshot: dense baseline (k3, budget1600 chars, one search), lexical experiment (same limits; hypothesis precise keywords help after agent query transformation), hybrid experiment (RRF candidates20, k5, budget4000, three searches; hypothesis combined ranking and context improve evidence coverage). New methods also count as the two improvement attempts; improvements need not succeed. Keep original Vietnamese retrieval results separately from agent-transformed queries.

## Tasks
- [x] Prepare/freeze 17 dev and 7 fresh test cases, with Vietnamese question text and source checks; separate subagent owns benchmark files.
- [x] TDD a minimal benchmark runner, metrics and immutable selection. Gold is consumed only by scoring, never by the model/retriever input. Record errors, token usage, timing and USD unknown.
- [x] Run real gpt-6-luna dev for all three configurations; source-backed assisted audit of context/answers/citations, read at least two dev errors. No human-review claims.
- [x] Select before test: maximize dev context evidence count, then first-tool Hit@3 count, then fewer provider errors, then fewer measured model+embedding tokens, then configuration ID. Persist hashes of cases/config/code and timestamp. Selection uses automatic evidence coverage; answer audit is a separate disclosed check, not hidden tuning.
- [x] Run baseline and selected configuration on held-out test unchanged; if baseline selected, run it once and explicitly report identical comparison. Grade all seven per configuration against source/context; review 5 answerable contexts 0/1/2 and all citations.
- [x] Publish local artifacts, summaries, reproducible commands, completed personal report and submission checklist. Preserve full failed runs and data provenance. Verify Day06 input hashes remain unchanged and all offline tests pass.

## Review focus
Missing evidence is excluded from retrieval denominators. Test cannot run before a valid dev selection. Ranking cutoffs fixed at 1/3 across methods. Citation support needs content inspection, not ID membership alone. Reports distinguish automatic metrics, Codex-assisted labels, independent student review pending, and unknown USD costs. All benchmark artifacts under artifacts/day07 are tracked paths (no secrets).

## Outcome
Frozen dataset: 24 Vietnamese cases. Real agent runs: 51 dev +14 test, no provider/store errors. TF-IDF selected at 2026-11-14T09:01:32.231063+00:00 before all test traces; selection identity verified unchanged. All 65 labels have explicit Codex-assisted provenance. Root corrected TF-IDF dev15 to match causal-claim rubric applied to dense/hybrid. Both baseline and selected test show 5/5 fully grounded answerable responses and 2/2 correct refusals on this small held-out set. No changes after viewing test. Offline suite 31/31; Day06 before/after input+Python source hashes identical; database counts A449/B505/C505 remain. USD unknown, independent student review pending, no commit/push performed. Evidence: artifacts/day07/verification.json and personal report.
