# Roadmap

## MVP: access-shock surveillance

- 51-jurisdiction FDA/MQSA, Census ACS/Gazetteer, CDC PLACES, CDC/ATSDR SVI, and HRSA source-access workflows
- reviewed North Carolina mammography facility snapshots
- new listings, possible closures, relocations, and possible service reductions
- population-weighted geographic access change
- vulnerability-adjusted county alerts
- CMS screening utilization signal
- mobile/fixed candidate response ranking
- reproducible policy brief generation
- production completion, data-quality, geocoder-confidence, identifier-crosswalk, and route-uncertainty reporting

## Next production steps

1. Keep production-data credentials, especially `CENSUS_API_KEY`, configured in GitHub secrets.
2. Rebuild the all-state package after source refreshes with the `all-states data package`
   GitHub Actions workflow.
3. Ingest future all-state facility snapshots only from completed MQSA review CSVs with reviewed
   coordinates and approved statuses.
4. Add multiple pre/post CMS periods and causal-study export tables.
5. Complete state-specific routing/readiness packages before publishing row-level findings outside
   North Carolina.
6. Use the sensitivity-review Markdown report during reviewer sign-off for any published ranking
   claims.
7. Complete independent expert review through the GitHub issue workflow before marking expert
   review complete.
8. Review manuscript references against the target journal style and submit only bounded
   software/methods claims until longitudinal and external-validation evidence exists.
9. Add release code signing and macOS notarization after signing certificates and Apple notarization
   credentials are available.

## Reserved future applications

The following are intentionally outside the first application so they can become distinct future research and software projects:

- diagnostic-resolution access after an abnormal screen;
- multimodality screening access, including low-dose CT;
- advanced equity-constrained facility or mobile-route optimization;
- radiology workforce vulnerability and provider-loss simulation.
