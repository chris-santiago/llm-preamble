# Investigation logs

Each experiment cycle keeps a chronological audit trail in `INVESTIGATION_LOG.jsonl`. There are two of these files:

- `preamble_quality_experiment/INVESTIGATION_LOG.jsonl` — v1 cycle.
- `preamble_quality_experiment_v2/INVESTIGATION_LOG.jsonl` — v2 cycle (53 entries through investigation completion).

These are **append-only** files. They are written exclusively by `log_entry.py` (one per directory), which auto-increments `seq`, auto-stamps `ts`, and validates the `cat` enum. **Never hand-edit** the JSONL — re-running or sorting in place breaks the chronology that makes the log useful.

## Schema

Each line is a single JSON object with this shape:

| Field | Type | Meaning |
|---|---|---|
| `ts` | string (ISO 8601 UTC) | When the event happened. |
| `step` | string | Which ml-lab step (`pre`, `1`, `2`, `3`, `4`, `4.R2`, `4.R3`, `5`, `6`, `7`) the event belongs to. |
| `seq` | integer | Auto-incrementing sequence number within the file. |
| `cat` | enum | Event category — see below. |
| `action` | string | Short snake_case action name (e.g. `dispatch_critic_r1`, `phase_a_f1_fix_verified`). |
| `detail` | string | One- or two-sentence prose description of what happened. |
| `artifact` | string \| null | Relative path to the file produced or modified, if any. |
| `duration_s` | number \| null | Wall-clock duration for `exec` events. |
| `meta` | object | Free-form structured metadata (numbers, lists, IDs). |

### Categories

The `cat` field is one of:

- `gate` — Gate decision (e.g. Gate 1 approval, pre-flight checklist construction).
- `write` — File written or modified (artifact path required).
- `read` — File read for context (used sparingly; mostly for cross-cycle references).
- `subagent` — Subagent dispatched or returned (`dispatch_*` / `receive_*` pair).
- `exec` — Script executed (`run_poc`, `main_run_complete`); `duration_s` and cost in `meta`.
- `decision` — Substantive design or methodology decision (e.g. `rubric_redesign_locked`).
- `debate` — Debate-protocol stage start markers.
- `review` — Review event (currently unused in v2).
- `audit` — Audit event (currently unused in v2).
- `workflow` — Step boundary, investigation start/end, user correction, mode locks.

## How to read a log

The v2 log is best read top-to-bottom with the [ml-lab debate protocol](ml-lab-workflow.md) as a reference. The story arc:

1. **seq 1–7** — investigation start, PoC write, first run, user correction on hypothesis framing.
2. **seq 8–25** — debate stages A through C, ending with `critique_wins` driven by F1.
3. **seq 26–28** — Gate 1 pre-flight checklist + experiment plan approval.
4. **seq 29–38** — Pre-flight phases A through D2, the rubric redesign (A1), pool macro-iteration (A3/A4), and judge-pool restoration to the full cross-judge matrix (A5).
5. **seq 39–41** — Main-run script built, smoke test passed, main run completed.
6. **seq 42–53** — Analysis addenda, mixed-effects correction, figures, confound probes, documentation passes, v3 idea capture.

## What an outside observer can reconstruct from logs alone

Reading only `INVESTIGATION_LOG.jsonl` (without the spec, conclusions, or any code), a reader can recover:

- **Timeline.** Every event has a UTC timestamp; total wall-clock and per-step durations are derivable.
- **Decisions.** Every spec edit, pool change, rubric change, and judge-pool change is logged with a trigger phrase in `detail` and structured deltas in `meta`.
- **User corrections.** Hypothesis-framing corrections (seq 5), judge-pool regressions caught by the user (seq 37), and methodological challenges (seq 51) all appear as `cat: workflow` or `cat: decision` entries.
- **Near-misses.** Bugs caught before they shipped (F1 unclamped scores, single-judge saturation, missing tier indicator in mixed-effects) are all on the record.
- **Cost trajectory.** PoC ~$0.01, Phase D2 ~$0.07, smoke ~$0.12, main run ~$32, confound probes ~$1 — all from `meta.cost_usd` fields.

## What the logs do not contain

Reading the log alone, you cannot recover:

- **Interpretation.** The logs say *what* changed; `CONCLUSIONS.md`, `REPORT_ADDENDUM.md`, and `SPEC_V2.md §12` say *why* it matters and what it means for the headline result.
- **Verbatim hypothesis or preamble text.** `HYPOTHESIS.md` carries the active hypothesis text; the 9 preambles live in `preamble_quality_v2_main.py` and `PREAMBLES.md`.
- **Actual data.** Generations, judgments, and per-sample CQS live in `experiment_v2_results/*.jsonl` and `*.json`; the log only references them by artifact path.
- **Code-level detail.** The log records that the F1 clamp was added; the diff lives in the script's git history.

## Cross-references

The log is the spine that ties every other artifact together:

- Each [Amendment](amendments.md) (A1–A5) has a matching `cat: decision` or `cat: write` entry in the v2 log.
- Each [debate stage](ml-lab-workflow.md) has matching `cat: subagent` / `cat: debate` / `cat: decision` entries.
- The [pre-registration boundary](pre-registration.md) is enforced by the log: any change to a locked section requires a corresponding logged event.
