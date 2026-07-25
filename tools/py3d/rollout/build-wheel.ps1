[CmdletBinding()]
param(
    [string]$Python = "python",
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"
$SourceDateEpoch = 1784937600
$SourceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$ManifestPath = Join-Path $PSScriptRoot "wheel-manifest.json"
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $PSScriptRoot "..\dist"
}
$TemporaryBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$TemporaryRoot = Join-Path $TemporaryBase (
    "py3d-wheel-r21-" + [Guid]::NewGuid().ToString("N")
)

function Get-SingleWheel([string]$Stage) {
    New-Item -ItemType Directory -Path $Stage | Out-Null
    & $Python -m pip wheel --no-deps --no-cache-dir $SourceRoot --wheel-dir $Stage |
        ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
        throw "pip wheel failed with exit code $LASTEXITCODE"
    }
    $Wheels = @(Get-ChildItem -LiteralPath $Stage -File -Filter "*.whl")
    if ($Wheels.Count -ne 1) {
        throw "expected exactly one wheel in staging, found $($Wheels.Count)"
    }
    return $Wheels[0]
}

function Get-SourceVersion {
    $Core = [IO.File]::ReadAllText(
        (Join-Path $SourceRoot "py3d\__init__.py")
    )
    $Setup = [IO.File]::ReadAllText((Join-Path $SourceRoot "setup.py"))
    $CoreMatch = [regex]::Match(
        $Core, '(?m)^__version__\s*=\s*"(?<version>\d+\.\d+\.\d+)"\s*$'
    )
    $SetupMatch = [regex]::Match(
        $Setup, '(?m)^\s*version\s*=\s*"(?<version>\d+\.\d+\.\d+)",\s*$'
    )
    if (-not $CoreMatch.Success -or -not $SetupMatch.Success) {
        throw "could not resolve both py3d version markers"
    }
    $CoreVersion = $CoreMatch.Groups["version"].Value
    $SetupVersion = $SetupMatch.Groups["version"].Value
    if ($CoreVersion -ne $SetupVersion) {
        throw "py3d version markers disagree: $CoreVersion vs $SetupVersion"
    }
    return $CoreVersion
}

$HadEpoch = Test-Path Env:SOURCE_DATE_EPOCH
$PreviousEpoch = $env:SOURCE_DATE_EPOCH
try {
    New-Item -ItemType Directory -Path $TemporaryRoot | Out-Null
    $env:SOURCE_DATE_EPOCH = [string]$SourceDateEpoch
    $WheelA = Get-SingleWheel (Join-Path $TemporaryRoot "first")
    $WheelB = Get-SingleWheel (Join-Path $TemporaryRoot "second")

    if ($WheelA.Name -ne $WheelB.Name) {
        throw "repeated builds produced different wheel filenames"
    }
    $HashA = (Get-FileHash -Algorithm SHA256 -LiteralPath $WheelA.FullName).Hash.ToLowerInvariant()
    $HashB = (Get-FileHash -Algorithm SHA256 -LiteralPath $WheelB.FullName).Hash.ToLowerInvariant()
    if ($HashA -ne $HashB) {
        throw "repeated builds are not reproducible: $HashA vs $HashB"
    }

    $Version = Get-SourceVersion
    $ExpectedName = "py3d-$Version-py3-none-any.whl"
    if ($WheelA.Name -ne $ExpectedName) {
        throw "wheel filename '$($WheelA.Name)' does not match '$ExpectedName'"
    }

    New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
    $ResolvedOutput = (Resolve-Path -LiteralPath $OutputDirectory).Path
    $Destination = Join-Path $ResolvedOutput $WheelA.Name
    Copy-Item -LiteralPath $WheelA.FullName -Destination $Destination -Force
    $CopiedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Destination).Hash.ToLowerInvariant()
    if ($CopiedHash -ne $HashA) {
        throw "copied wheel hash does not match the reproducible build"
    }

    $Manifest = [ordered]@{
        schema_version = "py3d-wheel-manifest-v1"
        filename = $WheelA.Name
        sha256 = $HashA
        source_date_epoch = $SourceDateEpoch
        source_version = $Version
    }
    $ManifestText = (
        ($Manifest | ConvertTo-Json -Depth 3) -replace "`r`n", "`n"
    ) + "`n"
    [IO.File]::WriteAllText(
        $ManifestPath,
        $ManifestText,
        (New-Object Text.UTF8Encoding($false))
    )

    Write-Host "py3d wheel reproducible: $($WheelA.Name)"
    Write-Host "SHA-256: $HashA"
    Write-Host "Manifest: $ManifestPath"
} finally {
    if ($HadEpoch) {
        $env:SOURCE_DATE_EPOCH = $PreviousEpoch
    } else {
        Remove-Item Env:SOURCE_DATE_EPOCH -ErrorAction SilentlyContinue
    }
    $NormalizedBase = $TemporaryBase.TrimEnd("\") + "\"
    $NormalizedTask = [IO.Path]::GetFullPath($TemporaryRoot).TrimEnd("\") + "\"
    if (-not $NormalizedTask.StartsWith(
        $NormalizedBase,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "refusing to remove temporary path outside the temp root"
    }
    if (Test-Path -LiteralPath $TemporaryRoot) {
        Remove-Item -LiteralPath $TemporaryRoot -Recurse -Force
    }
}
