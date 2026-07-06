# Roadmap

## MVP: access-shock surveillance

- 50-state FDA/MQSA, Census ACS/Gazetteer, CDC PLACES, CDC/ATSDR SVI, and HRSA source-access workflows
- reviewed North Carolina mammography facility snapshots
- new listings, possible closures, relocations, and possible service reductions
- population-weighted geographic access change
- vulnerability-adjusted county alerts
- CMS screening utilization signal
- mobile/fixed candidate response ranking
- reproducible policy brief generation
- production completion, data-quality, geocoder-confidence, identifier-crosswalk, and route-uncertainty reporting

## Next production steps

1. Approve and merge the active 50-state source-access PR.
2. Configure production-data credentials, especially `CENSUS_API_KEY`, in the local runner and
   GitHub secrets.
3. Rebuild the all-state package with ACS county and tract context using the local builder or the
   `all-states data package` GitHub Actions workflow.
4. Resolve all all-state package readiness gates and mark publication status only after review
   evidence is complete.
5. Add multiple pre/post CMS periods and causal-study export tables.
6. Review, geocode, route, and readiness-audit additional state packages before publishing
   findings outside North Carolina.
7. Expand sensitivity-analysis reports beyond CSV outputs for reviewer signoff.

## Reserved future applications

The following are intentionally outside the first application so they can become distinct future research and software projects:

- diagnostic-resolution access after an abnormal screen;
- multimodality screening access, including low-dose CT;
- advanced equity-constrained facility or mobile-route optimization;
- radiology workforce vulnerability and provider-loss simulation.
