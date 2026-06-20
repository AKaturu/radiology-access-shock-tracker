# ChatGPT Journal Drafting Prompt

Use this prompt in ChatGPT after uploading the journal bundle or linking the repository files.

```text
You are helping draft a journal-style software/methods manuscript for an open-source public-health
informatics project called Radiology Access Shock Tracker.

Goal:
Write a careful, publication-appropriate manuscript draft. Frame it as a software/methods or
informatics workflow paper, not as a definitive public-health findings paper.

Files to use:
- README_JOURNAL_BUNDLE.md
- MANUSCRIPT_OUTLINE.md
- analysis_manifest.json
- readiness_audit.md
- policy_brief.md
- facility_events.csv
- county_shocks.csv
- intervention_rankings.csv
- sensitivity_analysis.csv
- matrix_metadata.json
- compiled_test_report.md
- methods.md
- data_sources.md
- operations.md

Facts you may state:
- The project builds reviewed, checksum-versioned MQSA facility snapshots.
- The current reviewed NC snapshots are 2026-06-19 and 2026-06-20.
- Each reviewed snapshot contains 289 active NC facility records.
- The self-hosted OSRM workflow routed 52,680 of 52,680 tract-nearest facility pairs.
- There were 0 unreachable route rows.
- The readiness audit was READY with 0 blockers and 0 warnings.
- The 2026-06-19 to 2026-06-20 comparison produced 0 facility event signals.
- There were 0 warning or critical county shocks.
- Sensitivity analysis covered 5 scenarios.
- HRSA service-delivery candidate assumptions include 771 rows.

Do not invent:
- Any later MQSA snapshot after 2026-06-20.
- Any facility closures, relocations, or service losses.
- Any deterioration trend.
- Any causal utilization effect.
- Any facility-level annual capacity or procedure volume.
- Any claim that HRSA candidate locations provide mammography.

Required caveats:
- FDA MQSA public data do not include stable tracker IDs, coordinates, annual capacity, or
  facility-level procedure counts.
- Coordinates and active status are reviewed fields.
- OSRM travel times are free-flow driving estimates without live traffic.
- Tract centroids are approximations.
- The shock score is exploratory and not clinically validated.
- Candidate rankings are planning assumptions and require domain review.

Write:
1. A structured abstract.
2. A manuscript draft with headings.
3. A limitations section that is explicit and conservative.
4. A reproducibility/data availability section.
5. A short cover-letter style summary for a journal editor.

Tone:
Precise, restrained, and scientifically cautious. Prefer "workflow", "demonstration",
"surveillance signal", and "publication-readiness gate" over strong causal language.
```
