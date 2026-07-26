[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetSkillRoot,

    [switch]$NoWrite
)

$ErrorActionPreference = "Stop"
$RolloutRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$Py3dRoot = [IO.Path]::GetFullPath((Join-Path $RolloutRoot ".."))
$PatchedRoot = Join-Path $RolloutRoot "patched"
$ManifestPath = Join-Path $RolloutRoot "wheel-manifest.json"
$WheelRoot = Join-Path $Py3dRoot "dist"
$TargetRoot = (Resolve-Path -LiteralPath $TargetSkillRoot).Path

$SkillNames = @(
    "dayz-model-pipeline",
    "dayz-3d-viewer",
    "dayz-p3d-inspector",
    "dayz-p3d-debinarizer",
    "dayz-p3d-audit",
    "dayz-pbo-build",
    "dayz-proxy-align",
    "dayz-animation-pipeline"
)

$PatchedFiles = @(
    "dayz-model-pipeline\SKILL.md",
    "dayz-model-pipeline\references\py3d-direct-generation.md",
    "dayz-3d-viewer\SKILL.md",
    "dayz-p3d-inspector\SKILL.md",
    "dayz-p3d-debinarizer\SKILL.md",
    "dayz-p3d-audit\SKILL.md",
    "dayz-p3d-audit\scripts\audit_p3d.py",
    "dayz-pbo-build\references\validation-scripts.md",
    "dayz-proxy-align\SKILL.md",
    "dayz-animation-pipeline\references\py3d-1.0.0-quirks.md"
)

$PatchOnlyFiles = @(
    [pscustomobject]@{
        SkillName = "dayz-animation-pipeline"
        Relative = "dayz-animation-pipeline\SKILL.md"
        Patch = "patches\dayz-animation-pipeline__SKILL.md.patch"
        Marker = "dayz-animation-formats"
    }
)

function Get-FileSha256([string]$Path) {
    return (
        Get-FileHash -Algorithm SHA256 -LiteralPath $Path
    ).Hash.ToLowerInvariant()
}

function Assert-UnderTarget([string]$Path) {
    $RootPrefix = [IO.Path]::GetFullPath($TargetRoot).TrimEnd("\") + "\"
    $Candidate = [IO.Path]::GetFullPath($Path)
    if (-not $Candidate.StartsWith(
        $RootPrefix,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "path resolves outside the explicit target root: $Candidate"
    }
}

function Get-SourceVersion {
    $Core = [IO.File]::ReadAllText(
        (Join-Path $Py3dRoot "py3d\__init__.py")
    )
    $Setup = [IO.File]::ReadAllText((Join-Path $Py3dRoot "setup.py"))
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

function Invoke-GitApply([string[]]$Arguments) {
    $PreviousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $Output = @(& git @Arguments 2>&1)
        $ExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $PreviousPreference
    }
    return [pscustomobject]@{
        ExitCode = $ExitCode
        Output = $Output
    }
}

if (-not (Test-Path -LiteralPath $TargetRoot -PathType Container)) {
    throw "target skill root is not a directory"
}
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "tracked wheel manifest is missing"
}

try {
    $Manifest = Get-Content -LiteralPath $ManifestPath -Raw |
        ConvertFrom-Json
} catch {
    throw "tracked wheel manifest is not valid JSON"
}
$ExpectedFields = @(
    "build_requires",
    "filename",
    "python_version",
    "schema_version",
    "sha256",
    "source_date_epoch",
    "source_version"
)
$ActualFields = @($Manifest.PSObject.Properties.Name | Sort-Object)
if (Compare-Object $ExpectedFields $ActualFields) {
    throw "tracked wheel manifest fields are invalid"
}
if ($Manifest.schema_version -ne "py3d-wheel-manifest-v2") {
    throw "tracked wheel manifest schema is unsupported"
}
if ($Manifest.source_date_epoch -ne 1784937600) {
    throw "tracked wheel manifest uses the wrong SOURCE_DATE_EPOCH"
}
if ($Manifest.sha256 -notmatch "^[0-9a-f]{64}$") {
    throw "tracked wheel manifest SHA-256 is invalid"
}
if ($Manifest.python_version -notmatch '^\d+\.\d+\.\d+$') {
    throw "tracked wheel manifest Python version is invalid"
}
$BuildRequires = @($Manifest.build_requires)
$InvalidBuildRequires = @(
    $BuildRequires | Where-Object {
        $_ -isnot [string] -or [string]::IsNullOrWhiteSpace($_)
    }
)
if ($BuildRequires.Count -eq 0 -or $InvalidBuildRequires.Count -gt 0) {
    throw "tracked wheel manifest build requirements are invalid"
}

$SourceVersion = Get-SourceVersion
if ($Manifest.source_version -ne $SourceVersion) {
    throw "tracked wheel manifest version does not match source"
}
$ExpectedWheelName = "py3d-$SourceVersion-py3-none-any.whl"
if ($Manifest.filename -ne $ExpectedWheelName) {
    throw "tracked wheel filename does not match source version"
}
$WheelPath = Join-Path $WheelRoot $Manifest.filename
if (-not (Test-Path -LiteralPath $WheelPath -PathType Leaf)) {
    throw "tracked wheel is missing from tools/py3d/dist"
}
if ((Get-FileSha256 $WheelPath) -ne $Manifest.sha256) {
    throw "tracked wheel hash does not match wheel-manifest.json"
}

foreach ($Relative in $PatchedFiles) {
    $Source = Join-Path $PatchedRoot $Relative
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
        throw "rollout projection is missing: $Relative"
    }
}

$PresentSkills = @(
    $SkillNames | Where-Object {
        Test-Path -LiteralPath (Join-Path $TargetRoot $_) -PathType Container
    }
)
if ($PresentSkills.Count -eq 0) {
    throw "target root contains none of the eight py3d consumer skills"
}

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupRoot = Join-Path $TargetRoot (
    "_backup_pre-py3d-$SourceVersion-$Stamp"
)
$Changes = 0

foreach ($Relative in $PatchedFiles) {
    $SkillName = ($Relative -split "\\", 2)[0]
    if ($PresentSkills -notcontains $SkillName) {
        Write-Host "[SKIP] absent skill: $SkillName"
        continue
    }
    $Source = Join-Path $PatchedRoot $Relative
    $Destination = Join-Path $TargetRoot $Relative
    Assert-UnderTarget $Destination
    $Matches = (
        (Test-Path -LiteralPath $Destination -PathType Leaf) -and
        ((Get-FileSha256 $Destination) -eq (Get-FileSha256 $Source))
    )
    if ($Matches) {
        Write-Host "[OK] projection already exact: $Relative"
        continue
    }
    $Changes++
    if ($NoWrite) {
        Write-Host "[PLAN] replace projection: $Relative"
        continue
    }
    if (Test-Path -LiteralPath $Destination -PathType Leaf) {
        $Backup = Join-Path $BackupRoot $Relative
        Assert-UnderTarget $Backup
        New-Item -ItemType Directory -Force -Path (
            Split-Path -Parent $Backup
        ) | Out-Null
        Copy-Item -LiteralPath $Destination -Destination $Backup
    }
    New-Item -ItemType Directory -Force -Path (
        Split-Path -Parent $Destination
    ) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    if ((Get-FileSha256 $Destination) -ne (Get-FileSha256 $Source)) {
        throw "projection readback failed: $Relative"
    }
    Write-Host "[OK] projection replaced: $Relative"
}

if ($PatchOnlyFiles.Count -gt 0) {
    Get-Command git -ErrorAction Stop | Out-Null
}
foreach ($PatchItem in $PatchOnlyFiles) {
    if ($PresentSkills -notcontains $PatchItem.SkillName) {
        Write-Host "[SKIP] absent skill: $($PatchItem.SkillName)"
        continue
    }
    $Destination = Join-Path $TargetRoot $PatchItem.Relative
    $PatchPath = Join-Path $RolloutRoot $PatchItem.Patch
    Assert-UnderTarget $Destination
    if (-not (Test-Path -LiteralPath $Destination -PathType Leaf)) {
        throw "patch target is missing: $($PatchItem.Relative)"
    }
    if (-not (Test-Path -LiteralPath $PatchPath -PathType Leaf)) {
        throw "rollout patch is missing: $($PatchItem.Patch)"
    }

    Push-Location -LiteralPath $TargetRoot
    try {
        $ReverseCheck = Invoke-GitApply @(
            "apply", "--reverse", "--check", $PatchPath
        )
        $AlreadyApplied = $ReverseCheck.ExitCode -eq 0
        if ($AlreadyApplied) {
            Write-Host "[OK] patch already applied: $($PatchItem.Relative)"
            continue
        }
        $ForwardCheck = Invoke-GitApply @(
            "apply", "--check", $PatchPath
        )
        if ($ForwardCheck.ExitCode -ne 0) {
            $ForwardCheck.Output | ForEach-Object { Write-Host $_ }
            throw "patch does not apply cleanly: $($PatchItem.Patch)"
        }
        $Changes++
        if ($NoWrite) {
            Write-Host "[PLAN] apply patch: $($PatchItem.Relative)"
            continue
        }

        $Backup = Join-Path $BackupRoot $PatchItem.Relative
        Assert-UnderTarget $Backup
        New-Item -ItemType Directory -Force -Path (
            Split-Path -Parent $Backup
        ) | Out-Null
        Copy-Item -LiteralPath $Destination -Destination $Backup
        $Apply = Invoke-GitApply @("apply", $PatchPath)
        if ($Apply.ExitCode -ne 0) {
            $Apply.Output | ForEach-Object { Write-Host $_ }
            throw "patch application failed: $($PatchItem.Patch)"
        }
        if (-not (Select-String -LiteralPath $Destination `
            -SimpleMatch $PatchItem.Marker -Quiet)) {
            throw "patch readback marker is missing: $($PatchItem.Relative)"
        }
        Write-Host "[OK] patch applied: $($PatchItem.Relative)"
    } finally {
        Pop-Location
    }
}

foreach ($SkillName in $PresentSkills) {
    $WheelsDirectory = Join-Path (Join-Path $TargetRoot $SkillName) "wheels"
    Assert-UnderTarget $WheelsDirectory
    $Existing = @()
    if (Test-Path -LiteralPath $WheelsDirectory -PathType Container) {
        $Existing = @(
            Get-ChildItem -LiteralPath $WheelsDirectory -File `
                -Filter "py3d-*.whl"
        )
    }
    $Destination = Join-Path $WheelsDirectory $Manifest.filename
    $Exact = (
        $Existing.Count -eq 1 -and
        $Existing[0].Name -eq $Manifest.filename -and
        (Get-FileSha256 $Existing[0].FullName) -eq $Manifest.sha256
    )
    if ($Exact) {
        Write-Host "[OK] wheel already exact: $SkillName"
        continue
    }
    $Changes++
    if ($NoWrite) {
        Write-Host "[PLAN] replace py3d wheel set: $SkillName"
        continue
    }

    foreach ($OldWheel in $Existing) {
        Assert-UnderTarget $OldWheel.FullName
        $Backup = Join-Path $BackupRoot (
            "$SkillName\wheels\$($OldWheel.Name)"
        )
        Assert-UnderTarget $Backup
        New-Item -ItemType Directory -Force -Path (
            Split-Path -Parent $Backup
        ) | Out-Null
        Copy-Item -LiteralPath $OldWheel.FullName -Destination $Backup
        Remove-Item -LiteralPath $OldWheel.FullName -Force
    }
    New-Item -ItemType Directory -Force -Path $WheelsDirectory | Out-Null
    Copy-Item -LiteralPath $WheelPath -Destination $Destination -Force
    if ((Get-FileSha256 $Destination) -ne $Manifest.sha256) {
        throw "wheel readback failed: $SkillName"
    }
    Write-Host "[OK] wheel replaced: $SkillName"
}

if ($NoWrite) {
    Write-Host "NO-WRITE verification complete; planned changes: $Changes"
} else {
    Write-Host "Rollout complete; applied changes: $Changes"
    if (Test-Path -LiteralPath $BackupRoot) {
        Write-Host "Backups: $BackupRoot"
    }
}
