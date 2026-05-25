# Repo layout & reproduce

```
.
├── README.md                                 this file
├── PREAMBLES.md                              verbatim text of all 12 preambles tested
├── RELATED_WORK.md                           literature situating (covers v1 + v2)
├── preamble_quality_experiment/              v1 (instrument-correction motivation)
└── preamble_quality_experiment_v2/           v2 (active design)
    ├── HYPOTHESIS.md                         three hypothesis cycles, current = Re-revised ACTIVE
    ├── SPEC_V2.md                            pre-registration + A1–A5 amendment log
    ├── CONCLUSIONS.md                        full conclusions, debate scorecard, confound probes
    ├── REPORT_ADDENDUM.md                    methodology journey, pre-flight phases, probe lessons
    ├── INVESTIGATION_LOG.jsonl               51 chronological audit entries
    ├── preamble_quality_v2_main.py           main-run script
    ├── confound_probes.py                    post-hoc probe script (A, B, C)
    ├── analysis_addendum.py                  mixed-effects M0/M1/M2 + sensitivity
    ├── figures.py                            5 matplotlib/seaborn figures
    └── experiment_v2_results/                main-run REPORT, MIXED_EFFECTS, WEIGHT_SENSITIVITY,
                                              JSONL data, figures/, confound_probe_results/
```

To reproduce:

```bash
export OPENROUTER_API_KEY=<your key>
cd preamble_quality_experiment_v2/

uv run preamble_quality_v2_main.py --slice    # 4-sample smoke test
uv run preamble_quality_v2_main.py            # full main run (~1 hour)
uv run analysis_addendum.py                   # mixed-effects + weight sensitivity
uv run confound_probes.py                     # post-hoc probes (~5 min)
uv run figures.py                             # regenerate the 5 figures
```

All scripts use PEP 723 inline dependencies — `uv run` installs everything; no virtualenv needed.
