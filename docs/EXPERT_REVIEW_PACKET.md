# Expert Review Packet

This packet is for independent technical, clinical, or public-health review of the Radiology
Access Shock Tracker. It is not a completed review record. Use it to collect reviewer decisions,
questions, and sign-off evidence before expanding publication claims beyond the current reviewed
North Carolina validation package.

## Review Scope

Reviewers should evaluate whether the repository supports its current claims:

- 51-jurisdiction source-access and package-readiness coverage for all 50 states plus DC.
- Reviewed North Carolina row-level validation package with no observed facility-change findings.
- Publication-readiness gates that block incomplete provenance, placeholder facility snapshots, and
  unresolved state review gates.
- Desktop and GitHub Release packaging for the dashboard.

Reviewers should not treat this packet as evidence for:

- clinical decision support;
- confirmed facility closures;
- causal access deterioration;
- utilization impact;
- row-level all-state facility findings outside the reviewed NC package.

## Evidence To Inspect

| Evidence | Location |
|---|---|
| Project status | `STATUS.md` |
| Production status and limitations | `README.md` |
| Methods and metrics | `docs/METHODS.md` |
| Data-source provenance | `docs/DATA_SOURCES.md` |
| Operations and review gates | `docs/OPERATIONS.md` |
| Architecture and data flow | `docs/ARCHITECTURE.md` |
| All-state package summary | `outputs/all_states_data_package.md` |
| Production audit | `outputs/production_audit.md` |
| Validation report | `docs/validation/COMPILED_TEST_REPORT.md` |
| Journal package guide | `docs/JOURNAL_REPORT_PACKAGE.md` |
| Manuscript working draft | `docs/MANUSCRIPT_DRAFT.md` |

## Reviewer Checklist

| Area | Reviewer decision | Notes |
|---|---|---|
| Claims match evidence and limitations | Pending | |
| FDA MQSA source handling is appropriately caveated | Pending | |
| Census ACS county and tract context is used responsibly | Pending | |
| HRSA candidate-site assumptions are clearly labeled as planning assumptions | Pending | |
| SVI and PLACES context are not overinterpreted | Pending | |
| Facility-change signals require primary-source verification | Pending | |
| Route-time methods and OSRM limitations are clearly stated | Pending | |
| Readiness gates block non-reviewed or placeholder outputs | Pending | |
| Dashboard and release documentation are clear for non-author users | Pending | |
| Manuscript draft avoids causal or clinical claims | Pending | |

Reviewer decision values should be one of: `approve`, `approve_with_minor_comments`,
`revise_before_publication`, or `reject_current_claims`.

## Sign-Off Record

| Reviewer | Role | Date | Decision | Evidence notes |
|---|---|---|---|---|
| Pending | Pending | Pending | Pending | Pending |

Do not change README or STATUS expert-review rows to `Complete` until this table identifies an
independent reviewer, review date, decision, and evidence notes.

For GitHub-tracked reviews, open an issue with
`.github/ISSUE_TEMPLATE/expert_review.yml`. The issue form records reviewer identity, evidence
bundle, scope, required checks, findings, decision, and decision date. Link the closed issue from
this sign-off table before changing project status.

## Common Review Questions

1. Are the publication claims limited to software, methods, readiness, and the reviewed NC
   no-observed-change validation package?
2. Are all-state outputs framed as package readiness rather than row-level facility findings?
3. Do source limitations remain visible near any result that a policymaker might interpret as a
   finding?
4. Does the review gate behavior fail closed when MQSA review, ACS context, or routing evidence is
   missing?
5. Are desktop release users warned that the builds are unsigned and the software is a research
   prototype?
