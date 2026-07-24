# apply-s2-rollout.ps1 v3 - Rollout py3d fork (wheel vigente 1.3.0, S3) + diagnostico de roots (D2=B)
# v3 2026-06-07: wheel/sha -> 1.3.0 (plan S3); check de P:\py3d HEAD ahora DINAMICO
# contra el bundle (git ls-remote) - el hash hardcodeado driftaba en cada release.
# v2 2026-06-07: la app Claude es Store-packaged -> el root (a) real vive bajo
# %LOCALAPPDATA%\Packages\<Claude>\LocalCache\Roaming\... (el path %APPDATA%\Claude
# es una vista virtualizada solo visible dentro de la app). Los dirs dayz-* de
# .agents\skills parecen symlinks de la migracion plugin-canonical 2026-06-05:
# este script los DIAGNOSTICA y no los toca (gate: divergencia -> reportar).
# PowerShell 5.1+, ASCII only.

$ErrorActionPreference = 'Continue'
$BASE   = '<dayz-projects>\LF_RollingStone_dev\_tools\py3d'
$ROLL   = Join-Path $BASE 'rollout'
$WHEEL  = Join-Path $BASE 'dist\py3d-1.3.0-py3-none-any.whl'
$WHEEL_SHA = 'AEBEB9FAFD48DAE5B8AAF726B2FF98C7DA0F6E00A637BD1476BA6C8B2A410713'
$STAMP  = Get-Date -Format 'yyyyMMdd-HHmmss'
$PLUGIN_TAIL = 'Claude\local-agent-mode-sessions\skills-plugin\d07d091e-4ce6-408d-9a98-a6b2afe12743\2e9b9ae7-571b-4eee-9a6c-075b7f119743\skills'

$skills = @('dayz-model-pipeline','dayz-3d-viewer','dayz-p3d-inspector','dayz-p3d-debinarizer',
            'dayz-p3d-audit','dayz-pbo-build','dayz-proxy-align','dayz-animation-pipeline')
$files = @('dayz-model-pipeline\SKILL.md',
           'dayz-model-pipeline\references\py3d-direct-generation.md',
           'dayz-3d-viewer\SKILL.md',
           'dayz-p3d-inspector\SKILL.md',
           'dayz-p3d-debinarizer\SKILL.md',
           'dayz-p3d-audit\SKILL.md',
           'dayz-p3d-audit\scripts\audit_p3d.py',
           'dayz-pbo-build\references\validation-scripts.md',
           'dayz-proxy-align\SKILL.md',
           'dayz-animation-pipeline\references\py3d-1.0.0-quirks.md')
$forkFiles = @('dayz-model-pipeline\SKILL.md',
               'dayz-model-pipeline\references\py3d-direct-generation.md',
               'dayz-3d-viewer\SKILL.md',
               'dayz-p3d-inspector\SKILL.md',
               'dayz-p3d-debinarizer\SKILL.md',
               'dayz-p3d-audit\scripts\audit_p3d.py',
               'dayz-pbo-build\references\validation-scripts.md',
               'dayz-proxy-align\SKILL.md')

$global:fails = 0
function OK($m)   { Write-Host "[OK]   $m" }
function FAIL($m) { Write-Host "[FAIL] $m" -ForegroundColor Red; $global:fails++ }
function SKIP($m) { Write-Host "[SKIP] $m" -ForegroundColor Yellow }
function INFO($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }
function FHash($p) { (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash }

Write-Host "=== GATE: wheel y rollout ==="
if (-not (Test-Path -LiteralPath $WHEEL)) { FAIL "wheel no encontrada"; exit 1 }
if ((FHash $WHEEL) -ne $WHEEL_SHA) { FAIL "sha256 de la wheel NO coincide"; exit 1 } else { OK "wheel sha256 correcta" }

Write-Host "`n=== Localizando root (a) real (app Store-packaged) ==="
$candidates = @("$env:APPDATA\$PLUGIN_TAIL")
Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match 'Claude|Anthropic' } |
  ForEach-Object { $candidates += (Join-Path $_.FullName "LocalCache\Roaming\$PLUGIN_TAIL") }
$rootA = $null
foreach ($c in $candidates) {
  if (Test-Path -LiteralPath (Join-Path $c 'dayz-p3d-audit\SKILL.md')) { $rootA = $c; break }
}
if (-not $rootA) {
  # busqueda amplia de cualquier skills-plugin con las skills dentro
  $hits = @(Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match 'Claude|Anthropic' } |
    ForEach-Object { Get-ChildItem (Join-Path $_.FullName 'LocalCache') -Recurse -Depth 6 -Directory -Filter 'dayz-p3d-audit' -ErrorAction SilentlyContinue } |
    ForEach-Object { $_.Parent.FullName } | Select-Object -Unique)
  if ($hits.Count -ge 1) { $rootA = $hits[0]; if ($hits.Count -gt 1) { INFO ("multiples roots candidatos: " + ($hits -join ' | ')) } }
}
if ($rootA) { INFO "root (a) real: $rootA" } else { FAIL "no se encontro el root (a) real - reportar"; }

if ($rootA) {
  Write-Host "`n=== ROOT (a) real: aplicar/verificar 10 archivos + wheels ==="
  $backupDir = Join-Path $rootA "_backup_pre-s2-rollout-$STAMP"
  foreach ($f in $files) {
    $src = Join-Path "$ROLL\patched" $f
    $dst = Join-Path $rootA $f
    if ((Test-Path -LiteralPath $dst) -and ((FHash $dst) -eq (FHash $src))) { OK "ya aplicado (byte-exacto): $f"; continue }
    if (Test-Path -LiteralPath $dst) {
      $bk = Join-Path $backupDir $f
      New-Item -ItemType Directory -Force -Path (Split-Path $bk) | Out-Null
      Copy-Item -LiteralPath $dst -Destination $bk -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
    Copy-Item -LiteralPath $src -Destination $dst -Force
    if ((FHash $dst) -eq (FHash $src)) { OK "aplicado: $f" } else { FAIL "hash mismatch tras copiar: $f" }
  }
  foreach ($s in $skills) {
    if (-not (Test-Path -LiteralPath (Join-Path $rootA $s))) { SKIP "skill ausente en (a): $s"; continue }
    $wd = Join-Path $rootA "$s\wheels"
    New-Item -ItemType Directory -Force -Path $wd | Out-Null
    $wdst = Join-Path $wd (Split-Path $WHEEL -Leaf)
    if ((Test-Path -LiteralPath $wdst) -and ((FHash $wdst) -eq $WHEEL_SHA)) { OK "wheel ya vendorizada: $s" }
    else {
      Copy-Item -LiteralPath $WHEEL -Destination $wdst -Force
      if ((FHash $wdst) -eq $WHEEL_SHA) { OK "wheel vendorizada: $s" } else { FAIL "wheel corrupta en $s" }
    }
  }
  Write-Host "--- R26 root (a) ---"
  $scan = @(); foreach ($s in $skills) { $p = Join-Path $rootA $s; if (Test-Path -LiteralPath $p) { $scan += Get-ChildItem -LiteralPath $p -Recurse -Include *.md,*.py -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch '_backup_pre-s2-rollout' } } }
  INFO ("archivos escaneados: " + $scan.Count)
  if ($scan.Count -eq 0) { FAIL "scan vacio - R26 no evaluable" }
  $p1 = @($scan | Select-String -Pattern 'pip install py3d' | Where-Object { $_.Line -notmatch '\.whl' -and $_.Line -notmatch 'NUNCA|NEVER|NOT use|Do NOT|point-cloud' })
  if ($p1.Count -eq 0) { OK "0 'pip install py3d' desnudo" } else { $p1 | ForEach-Object { Write-Host "   $($_.Path):$($_.LineNumber): $($_.Line.Trim())" }; FAIL "$($p1.Count) install PyPI desnudo" }
  $p2 = @($scan | Select-String -CaseSensitive -Pattern 'from py3d import P3d($|[^D])')
  if ($p2.Count -eq 0) { OK "0 'from py3d import P3d' (casing malo)" } else { $p2 | ForEach-Object { Write-Host "   $($_.Path):$($_.LineNumber)" }; FAIL "$($p2.Count) casing P3d" }
  $p3 = @($scan | Select-String -Pattern 'py3d\.read_p3d' | Where-Object { $_.Line -notmatch 'NO existe|confabulada' })
  if ($p3.Count -eq 0) { OK "0 'py3d.read_p3d' (API confabulada)" } else { $p3 | ForEach-Object { Write-Host "   $($_.Path):$($_.LineNumber)" }; FAIL "$($p3.Count) read_p3d" }
  $missing = @()
  foreach ($ff in $forkFiles) {
    $fp = Join-Path $rootA $ff
    if (-not (Test-Path -LiteralPath $fp)) { $missing += "$ff (no existe)"; continue }
    if (-not (Select-String -LiteralPath $fp -Pattern 'py3d DayZ fork' -Quiet)) { $missing += $ff }
  }
  if ($missing.Count -eq 0) { OK "'py3d DayZ fork' presente en los 8 esperados" } else { $missing | ForEach-Object { Write-Host "   falta en: $_" }; FAIL "frase fork ausente en $($missing.Count)" }
}

Write-Host "`n=== DIAGNOSTICO root (b) C:\Users\<you>\.agents\skills (NO se toca) ==="
$rootB = 'C:\Users\<you>\.agents\skills'
Remove-Item -LiteralPath (Join-Path $rootB '.probe-write') -ErrorAction SilentlyContinue
foreach ($s in $skills) {
  $p = Join-Path $rootB $s
  if (-not (Test-Path -LiteralPath $p)) { INFO "$s : NO EXISTE"; continue }
  $it = Get-Item -LiteralPath $p -Force
  $lt = $it.LinkType; $tg = $null
  try { $tg = $it.Target } catch {}
  if (-not $lt) { $lt = 'dir-fisico' }
  $resolves = $false
  try { $resolves = Test-Path -LiteralPath (Join-Path $p 'SKILL.md') } catch {}
  $readable = $false
  try { $null = Get-Content -LiteralPath (Join-Path $p 'SKILL.md') -TotalCount 1 -ErrorAction Stop; $readable = $true } catch {}
  INFO ("{0} : tipo={1} target={2} SKILL.md-visible={3} legible={4}" -f $s, $lt, ($tg -join ';'), $resolves, $readable)
}

Write-Host "`n=== DIAGNOSTICO root (c) <skills> ==="
$rootC = '<skills>'
if (Test-Path -LiteralPath $rootC) {
  $items = @(Get-ChildItem -LiteralPath $rootC -Force -ErrorAction SilentlyContinue)
  INFO ("existe; entradas: " + $items.Count + " -> " + (($items | Select-Object -First 12 -ExpandProperty Name) -join ', '))
} else { INFO "no existe (sin copias USER shadow - LL-094 limpio)" }

Write-Host "`n=== P:\py3d (D1) ==="
if (Test-Path 'P:\py3d\.git') {
  $BUNDLE = Join-Path $BASE 'py3d-repo.bundle'
  $expected = $null
  if (Test-Path -LiteralPath $BUNDLE) {
    $ls = (& git ls-remote $BUNDLE refs/heads/dayz-fork 2>$null)
    if ($ls) { $expected = ($ls -split "`t")[0] }
  }
  $head = (& git -C 'P:\py3d' rev-parse HEAD 2>$null)
  if (-not $expected) { SKIP "bundle ilegible - no se pudo derivar HEAD esperado" }
  elseif ($head -eq $expected) { OK ("P:\py3d HEAD = " + $expected.Substring(0,7) + " (== bundle dayz-fork)") }
  else { FAIL "P:\py3d HEAD = '$head' (esperado $expected del bundle)" }
} else { SKIP "P:\py3d no presente" }

Write-Host "`n========================================"
if ($global:fails -eq 0) { Write-Host "RESULTADO: ALL PASSED (diagnosticos en [INFO])"; exit 0 }
else { Write-Host "RESULTADO: $global:fails FAIL(s)" -ForegroundColor Red; exit 1 }
