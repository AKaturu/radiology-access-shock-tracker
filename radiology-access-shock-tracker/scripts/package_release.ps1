param(
    [string]$ProjectName = "radiology-access-shock-tracker"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$GitRoot = (& git -C $ProjectRoot rev-parse --show-toplevel).Trim()
$Commit = (& git -C $GitRoot rev-parse --short HEAD).Trim()
$DistRoot = Join-Path $ProjectRoot "dist"
$GitHubDist = Join-Path $DistRoot "github"
$JournalDist = Join-Path $DistRoot "journal"
$JournalStage = Join-Path $JournalDist "$ProjectName-journal-bundle-$Commit"

function Assert-UnderProject {
    param([string]$Path)
    $resolvedParent = Resolve-Path -LiteralPath (Split-Path -Parent $Path) -ErrorAction SilentlyContinue
    if ($null -eq $resolvedParent) {
        return
    }
    $full = [System.IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to operate outside project root: $Path"
    }
}

function Reset-Directory {
    param([string]$Path)
    Assert-UnderProject -Path $Path
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Copy-Into {
    param(
        [string]$Source,
        [string]$Destination
    )
    $targetDir = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

function Write-TextFile {
    param(
        [string]$Path,
        [string]$Content
    )
    $targetDir = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    Set-Content -LiteralPath $Path -Value $Content -Encoding UTF8
}

function Get-ArtifactRelativePath {
    param(
        [string]$Root,
        [string]$Path
    )
    $trimChars = @(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd($trimChars)
    $pathFull = [System.IO.Path]::GetFullPath($Path)
    $rootPrefix = $rootFull + [System.IO.Path]::DirectorySeparatorChar
    if (-not $pathFull.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to calculate artifact path outside journal stage: $Path"
    }
    return $pathFull.Substring($rootPrefix.Length).Replace("\", "/")
}

New-Item -ItemType Directory -Force -Path $GitHubDist, $JournalDist | Out-Null

$GitHubZip = Join-Path $GitHubDist "$ProjectName-source-$Commit.zip"
if (Test-Path -LiteralPath $GitHubZip) {
    Remove-Item -LiteralPath $GitHubZip -Force
}
& git -C $GitRoot archive `
    --format zip `
    --prefix "$ProjectName/" `
    --output $GitHubZip `
    "HEAD:$ProjectName"

Reset-Directory -Path $JournalStage

$AnalysisDir = Join-Path $ProjectRoot "work/self-hosted-osrm/analysis-tract-self-hosted-osrm"
$RouteDir = Join-Path $ProjectRoot "work/self-hosted-osrm"

$copies = @(
    @("README.md", "project/README.md"),
    @("LICENSE", "project/LICENSE"),
    @("CITATION.cff", "project/CITATION.cff"),
    @("docs/METHODS.md", "docs/methods.md"),
    @("docs/DATA_SOURCES.md", "docs/data_sources.md"),
    @("docs/OPERATIONS.md", "docs/operations.md"),
    @("docs/JOURNAL_REPORT_PACKAGE.md", "docs/journal_report_package.md"),
    @("docs/CHATGPT_JOURNAL_PROMPT.md", "CHATGPT_JOURNAL_PROMPT.md"),
    @("docs/validation/COMPILED_TEST_REPORT.md", "validation/compiled_test_report.md"),
    @("data/snapshots/2026-06-19/facilities.csv", "snapshots/2026-06-19/facilities.csv"),
    @("data/snapshots/2026-06-19/metadata.json", "snapshots/2026-06-19/metadata.json"),
    @("data/snapshots/2026-06-20/facilities.csv", "snapshots/2026-06-20/facilities.csv"),
    @("data/snapshots/2026-06-20/metadata.json", "snapshots/2026-06-20/metadata.json"),
    @("data/source_metadata/fda-mqsa-public-2026-06-20.metadata.json", "source_metadata/fda-mqsa-public-2026-06-20.metadata.json"),
    @("data/counties.csv", "analysis_inputs/counties.csv"),
    @("data/population_points_tracts.csv", "analysis_inputs/population_points_tracts.csv"),
    @("data/candidate_sites.csv", "analysis_inputs/candidate_sites.csv"),
    @("data/candidate_sites_review.metadata.json", "analysis_inputs/candidate_sites_review.metadata.json"),
    @("work/self-hosted-osrm/2026-06-20_tract_nearest20_self_hosted_osrm_matrix.csv", "routing/tract_nearest20_self_hosted_osrm_matrix.csv"),
    @("work/self-hosted-osrm/2026-06-20_tract_nearest20_self_hosted_osrm_matrix.metadata.json", "routing/tract_nearest20_self_hosted_osrm_matrix.metadata.json"),
    @("work/self-hosted-osrm/2026-06-20_tract_nearest20_self_hosted_osrm_review.csv", "routing/tract_nearest20_self_hosted_osrm_review.csv"),
    @("work/self-hosted-osrm/analysis-tract-self-hosted-osrm/manifest.json", "analysis_outputs/analysis_manifest.json"),
    @("work/self-hosted-osrm/analysis-tract-self-hosted-osrm/readiness_audit.md", "analysis_outputs/readiness_audit.md"),
    @("work/self-hosted-osrm/analysis-tract-self-hosted-osrm/readiness_audit.json", "analysis_outputs/readiness_audit.json"),
    @("work/self-hosted-osrm/analysis-tract-self-hosted-osrm/policy_brief.md", "analysis_outputs/policy_brief.md"),
    @("work/self-hosted-osrm/analysis-tract-self-hosted-osrm/policy_brief.html", "analysis_outputs/policy_brief.html"),
    @("work/self-hosted-osrm/analysis-tract-self-hosted-osrm/facility_events.csv", "analysis_outputs/facility_events.csv"),
    @("work/self-hosted-osrm/analysis-tract-self-hosted-osrm/county_shocks.csv", "analysis_outputs/county_shocks.csv"),
    @("work/self-hosted-osrm/analysis-tract-self-hosted-osrm/intervention_rankings.csv", "analysis_outputs/intervention_rankings.csv"),
    @("work/self-hosted-osrm/analysis-tract-self-hosted-osrm/sensitivity_analysis.csv", "analysis_outputs/sensitivity_analysis.csv"),
    @("docs/assets/github/dashboard-overview.png", "figures/dashboard-overview.png"),
    @("docs/assets/github/county-shocks.png", "figures/county-shocks.png"),
    @("docs/assets/github/interventions.png", "figures/interventions.png"),
    @("docs/assets/github/readiness-audit.png", "figures/readiness-audit.png"),
    @("docs/assets/github/sensitivity.png", "figures/sensitivity.png"),
    @("docs/assets/github/mobile-overview.png", "figures/mobile-overview.png"),
    @("docs/assets/github/dashboard-walkthrough.webm", "figures/dashboard-walkthrough.webm")
)

foreach ($pair in $copies) {
    $source = Join-Path $ProjectRoot $pair[0]
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Required packaging source is missing: $source"
    }
    Copy-Into -Source $source -Destination (Join-Path $JournalStage $pair[1])
}

$BundleReadme = @"
# Radiology Access Shock Tracker Journal Bundle

Bundle commit: $Commit
Generated: $((Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"))

## Purpose

This bundle supports a journal-style software, methods, or public-health informatics write-up.
It is designed for drafting with ChatGPT while keeping the claims bounded by reviewed artifacts.

## Current Evidence Boundary

- Reviewed NC MQSA snapshots: 2026-06-19 and 2026-06-20.
- Facility records: 289 active records in each snapshot.
- Route matrix: 52,680 of 52,680 tract-nearest facility pairs routed.
- Route provider: self-hosted Project OSRM Docker container, driving profile.
- Readiness audit: READY with 0 blockers and 0 warnings.
- Facility event signals: 0.
- Warning or critical county shocks: 0.
- HRSA candidate assumptions: 771 rows.

Do not use this bundle to claim longitudinal deterioration, causal utilization effects, or
facility-level annual capacity. A future FDA MQSA source update must be reviewed before trend
claims are appropriate.

## How To Use With ChatGPT

1. Upload this bundle or the selected files requested in `CHATGPT_JOURNAL_PROMPT.md`.
2. Paste the prompt from `CHATGPT_JOURNAL_PROMPT.md`.
3. Ask for a software/methods manuscript first.
4. Ask for journal-specific formatting only after choosing a target journal.

## Folder Map

- `analysis_outputs/`: generated real analysis package and readiness evidence.
- `analysis_inputs/`: reviewed public-data inputs used by the analysis package.
- `routing/`: finalized self-hosted OSRM route review and matrix metadata.
- `snapshots/`: reviewed MQSA facility snapshots and checksum metadata.
- `source_metadata/`: archived source provenance.
- `docs/`: methods, data-source, operations, and journal guidance.
- `figures/`: synthetic dashboard screenshots and walkthrough media for UI context.
- `validation/`: compiled local validation report.
"@
Write-TextFile -Path (Join-Path $JournalStage "README_JOURNAL_BUNDLE.md") -Content $BundleReadme

$Outline = @"
# Manuscript Outline

## Working Title

Radiology Access Shock Tracker: An Open-Source Workflow for Mammography Facility Snapshot Review,
Route-Time Access Analysis, and Publication-Readiness Auditing

## Structured Abstract

### Background
Mammography facility availability can change over time, but public facility files require review
before they can support access surveillance.

### Objective
Describe an open-source workflow for reviewed facility snapshots, tract-level route-time access
analysis, candidate response-site review, and publication-readiness auditing.

### Methods
Summarize MQSA source archiving, review gates, deterministic facility identifiers, tract population
points, self-hosted OSRM routing, shock scoring, sensitivity analysis, HRSA candidate assumptions,
and readiness auditing.

### Results
Report the current bounded demonstration: 289 active NC facility records in each reviewed snapshot,
52,680 routed tract-nearest pairs, readiness READY with 0 blockers/warnings, 0 facility event
signals, and 0 warning or critical county shocks.

### Conclusions
The workflow demonstrates a conservative and reproducible route-time access surveillance pipeline.
Future source updates and primary-source verification are required before longitudinal claims.

## Main Text

1. Introduction
2. Objective
3. System Architecture
4. Data Sources
5. Review and Finalization Gates
6. Route-Time Matrix Generation
7. Access and Shock Metrics
8. Candidate Response-Site Assumptions
9. Publication-Readiness Audit
10. Demonstration Results
11. Limitations
12. Reproducibility
13. Discussion
14. Conclusion

## Required Limitations

- FDA MQSA public data do not provide stable tracker IDs, coordinates, facility-level annual
  capacity, or facility-level procedure counts.
- Current real-data outputs are a no-change validation run, not trend findings.
- OSRM free-flow travel times omit traffic and operational access barriers.
- HRSA candidates are planning assumptions, not mammography provider claims.
- The shock score is exploratory and not clinically validated.
"@
Write-TextFile -Path (Join-Path $JournalStage "MANUSCRIPT_OUTLINE.md") -Content $Outline

$manifestRows = Get-ChildItem -LiteralPath $JournalStage -Recurse -File | ForEach-Object {
    $relative = Get-ArtifactRelativePath -Root $JournalStage -Path $_.FullName
    [ordered]@{
        path = $relative
        bytes = $_.Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
    }
}
$EvidenceManifest = [ordered]@{
    package_name = "$ProjectName-journal-bundle"
    commit = $Commit
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    files = @($manifestRows)
}
Write-TextFile `
    -Path (Join-Path $JournalStage "EVIDENCE_MANIFEST.json") `
    -Content (($EvidenceManifest | ConvertTo-Json -Depth 5) + "`n")

$JournalZip = Join-Path $JournalDist "$ProjectName-journal-bundle-$Commit.zip"
if (Test-Path -LiteralPath $JournalZip) {
    Remove-Item -LiteralPath $JournalZip -Force
}
Compress-Archive -LiteralPath $JournalStage -DestinationPath $JournalZip -CompressionLevel Optimal

$PackageManifest = [ordered]@{
    commit = $Commit
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    github_source_zip = @{
        path = $GitHubZip
        bytes = (Get-Item -LiteralPath $GitHubZip).Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $GitHubZip).Hash.ToLowerInvariant()
    }
    journal_bundle_zip = @{
        path = $JournalZip
        bytes = (Get-Item -LiteralPath $JournalZip).Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $JournalZip).Hash.ToLowerInvariant()
    }
}
Write-TextFile `
    -Path (Join-Path $DistRoot "release-package-manifest-$Commit.json") `
    -Content (($PackageManifest | ConvertTo-Json -Depth 5) + "`n")

Write-Host "GitHub source ZIP: $GitHubZip"
Write-Host "Journal bundle ZIP: $JournalZip"
Write-Host "Package manifest: $(Join-Path $DistRoot "release-package-manifest-$Commit.json")"
