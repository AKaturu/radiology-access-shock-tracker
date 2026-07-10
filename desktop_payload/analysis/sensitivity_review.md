# Sensitivity Analysis Review

## Summary

- Scenarios evaluated: 5
- Counties evaluated: 100
- Access metric: travel_time_minutes
- Largest absolute score change: 0.0
- Largest absolute rank shift: 0
- Scenario-county alert-level changes: 0

## Review Boundary

- This report checks whether county shock rankings are stable under alternate weights.
- It supports reviewer sign-off; it does not establish causal or clinical validation.
- Treat large rank or alert-level shifts as prompts for methods review before publication.

## Scenario Summary

| Scenario | Top county | Max score delta | Max rank shift | Alert changes | Description |
| --- | --- | --- | --- | --- | --- |
| Baseline | Alamance County (37001) | 0.0 | 0 | 0 | Current published exploratory weighting. |
| Mean Access Heavy | Alamance County (37001) | 0.0 | 0 | 0 | Places more emphasis on broad average access deterioration. |
| Tail Access Heavy | Alamance County (37001) | 0.0 | 0 | 0 | Places more emphasis on 90th-percentile access deterioration. |
| Threshold Heavy | Alamance County (37001) | 0.0 | 0 | 0 | Places more emphasis on populations newly beyond the access threshold. |
| Vulnerability Heavy | Alamance County (37001) | 0.0 | 0 | 0 | Increases the effect of community vulnerability on the composite score. |

## Highest Impact Rows

| Scenario | County | Baseline score | Sensitivity score | Score delta | Rank delta | Alert change |
| --- | --- | --- | --- | --- | --- | --- |
| All scenarios | No material score, rank, or alert-level movement | - | - | 0.0 | 0 | No change |

## Reviewer Sign-Off Checklist

- [ ] Scenario definitions match the intended publication question.
- [ ] Top-ranked counties remain plausible after alternate weighting assumptions.
- [ ] Alert-level changes have been reviewed against source and routing limitations.
- [ ] Any publication text describes sensitivity results as exploratory robustness checks.
