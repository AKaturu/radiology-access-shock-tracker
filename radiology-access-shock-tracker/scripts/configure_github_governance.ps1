param(
    [string]$Repository = $env:GITHUB_REPOSITORY,
    [string]$Branch = "main",
    [string]$ProtectionJson = ".github/branch-protection.main.json",
    [string[]]$SecretNames = @("CENSUS_API_KEY", "OPENROUTESERVICE_API_KEY"),
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

function Require-Gh {
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if ($null -eq $gh) {
        throw "GitHub CLI 'gh' is not installed or not on PATH."
    }
    gh auth status 1>$null
}

function Resolve-Repository {
    param([string]$InputRepository)
    if ($InputRepository) {
        return $InputRepository
    }
    $repo = gh repo view --json nameWithOwner --jq ".nameWithOwner"
    if (-not $repo) {
        throw "Set -Repository or GITHUB_REPOSITORY to owner/name."
    }
    return $repo
}

function Set-RepositorySecret {
    param(
        [string]$RepositoryName,
        [string]$SecretName
    )
    $value = [Environment]::GetEnvironmentVariable($SecretName)
    if (-not $value) {
        Write-Warning "Skipping $SecretName because the environment variable is not set."
        return
    }
    if ($Apply) {
        $value | gh secret set $SecretName --repo $RepositoryName
        Write-Host "Set GitHub secret: $SecretName"
    } else {
        Write-Host "Would set GitHub secret: $SecretName"
    }
}

function Set-BranchProtection {
    param(
        [string]$RepositoryName,
        [string]$BranchName,
        [string]$JsonPath
    )
    if (-not (Test-Path -LiteralPath $JsonPath)) {
        throw "Branch protection JSON not found: $JsonPath"
    }
    if ($Apply) {
        gh api `
            --method PUT `
            "repos/$RepositoryName/branches/$BranchName/protection" `
            --input $JsonPath `
            1>$null
        Write-Host "Applied branch protection to $RepositoryName#$BranchName"
    } else {
        Write-Host "Would apply branch protection from $JsonPath to $RepositoryName#$BranchName"
    }
}

Require-Gh
$resolvedRepository = Resolve-Repository -InputRepository $Repository

foreach ($secretName in $SecretNames) {
    Set-RepositorySecret -RepositoryName $resolvedRepository -SecretName $secretName
}
Set-BranchProtection `
    -RepositoryName $resolvedRepository `
    -BranchName $Branch `
    -JsonPath $ProtectionJson

if (-not $Apply) {
    Write-Host "Dry run complete. Re-run with -Apply after reviewing the planned changes."
}
