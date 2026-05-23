# CQS weight-sensitivity table

Each scheme reweights the three CQS-craft components
(idiom, comment, hygiene). Pre-registered weights are 0.45 / 0.45 / 0.10.
Rows show the per-condition mean under each scheme plus the Kruskal-Wallis
p-value across the 8 main conditions (excluding `trivial_baseline`).

| Weight scheme | mean (trivial_baseline) | mean (none) | mean (negative_control) | mean (minimal) | mean (generic_coding) | mean (persona_only) | mean (real_agent) | mean (long_directive) | mean (python_coder_agent) | KW p (main conds) |
|---|---|---|---|---|---|---|---|---|---|---|
| pre-reg (0.45/0.45/0.10) | 0.556 | 0.778 | 0.723 | 0.770 | 0.784 | 0.764 | 0.802 | 0.814 | 0.802 | 9.242e-18 |
| idiom-only (1.00/0.00/0.00) | 0.544 | 0.797 | 0.764 | 0.789 | 0.800 | 0.786 | 0.821 | 0.822 | 0.820 | 2.666e-15 |
| comment-only (0.00/1.00/0.00) | 0.562 | 0.767 | 0.683 | 0.755 | 0.775 | 0.748 | 0.790 | 0.817 | 0.791 | 4.475e-16 |
| rubric-only (0.00/0.00/1.00) | 0.584 | 0.744 | 0.724 | 0.749 | 0.752 | 0.743 | 0.770 | 0.770 | 0.768 | 2.425e-10 |
| rubric-heavy (0.30/0.30/0.40) | 0.566 | 0.767 | 0.723 | 0.763 | 0.773 | 0.757 | 0.791 | 0.800 | 0.791 | 1.477e-17 |
| equal-thirds (0.33/0.33/0.34) | 0.563 | 0.769 | 0.724 | 0.765 | 0.776 | 0.759 | 0.794 | 0.803 | 0.793 | 8.228e-18 |
| v1-static-heavy proxy (0.20/0.20/0.60) | 0.572 | 0.759 | 0.724 | 0.758 | 0.766 | 0.753 | 0.784 | 0.790 | 0.783 | 3.694e-16 |