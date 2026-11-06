# OVH idle-shelve agent. Runs inside the Windows instance every 5 min (scheduled task, SYSTEM).
# Shelves its own instance through the OVH API after N idle minutes.
# Busy = an RDP/console session in WTSActive state, OR DayZServer running with inbound traffic
#        above dayz_rx_kb_per_min (a connected player sends a steady UDP stream).
# A disconnected RDP session (window closed without signing out) counts as idle.
param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$dir   = 'C:\ovh-agent'
$cfg   = Get-Content "$dir\config.json" -Raw | ConvertFrom-Json
$stateF = "$dir\state.json"
$logF  = "$dir\agent.log"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Log($m) { "$(Get-Date -Format s) $m" | Add-Content -Path $logF -Encoding UTF8 }

Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public static class Wts {
  [StructLayout(LayoutKind.Sequential)] public struct SI { public int Id; public IntPtr Name; public int State; }
  [DllImport("wtsapi32.dll")] static extern bool WTSEnumerateSessions(IntPtr h, int r, int v, out IntPtr p, out int c);
  [DllImport("wtsapi32.dll")] static extern void WTSFreeMemory(IntPtr p);
  public static int ActiveUserSessions() {
    IntPtr p; int c; int n = 0;
    if (!WTSEnumerateSessions(IntPtr.Zero, 0, 1, out p, out c)) return -1;
    int sz = Marshal.SizeOf(typeof(SI));
    for (int i = 0; i < c; i++) {
      SI s = (SI)Marshal.PtrToStructure(new IntPtr(p.ToInt64() + i * sz), typeof(SI));
      if (s.State == 0 && s.Id != 0) n++;   // WTSActive, skip services session 0
    }
    WTSFreeMemory(p); return n;
  }
}
'@ -ErrorAction SilentlyContinue

function Invoke-Ovh($method, $path) {
  $url = "$($cfg.endpoint)$path"
  $ts  = (Invoke-RestMethod -Uri "$($cfg.endpoint)/auth/time" -TimeoutSec 20).ToString()
  $pre = "$($cfg.as)+$($cfg.ck)+$method+$url++$ts"
  $sha = [Security.Cryptography.SHA1]::Create()
  $hex = -join ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($pre)) | ForEach-Object { $_.ToString('x2') })
  $h = @{ 'X-Ovh-Application' = $cfg.ak; 'X-Ovh-Consumer' = $cfg.ck; 'X-Ovh-Timestamp' = $ts; 'X-Ovh-Signature' = "`$1`$$hex" }
  Invoke-RestMethod -Method $method -Uri $url -Headers $h -ContentType 'application/json' -TimeoutSec 60
}

$now  = Get-Date
$boot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
$rx   = (Get-NetAdapterStatistics | Measure-Object -Property ReceivedBytes -Sum).Sum
$st   = if (Test-Path $stateF) { Get-Content $stateF -Raw | ConvertFrom-Json } else { $null }

# State survives shelve (it is on disk): never carry an idle timer across a reboot/unshelve.
$idleSince = if ($st -and [datetime]$st.idleSince -gt $boot) { [datetime]$st.idleSince } else { $now }

$sessions = [Wts]::ActiveUserSessions()
$dayz = Get-Process -Name 'DayZServer_x64','DayZServer' -ErrorAction SilentlyContinue
$rxRate = 0
if ($st -and $st.rx -and [datetime]$st.at -gt $boot) {
  $mins = [math]::Max(1, ($now - [datetime]$st.at).TotalMinutes)
  $rxRate = [math]::Round((($rx - [double]$st.rx) / 1KB) / $mins)
}
$busyRdp  = $sessions -ne 0          # -1 (API failure) also counts as busy: fail towards keeping the user's session
$busyDayz = $dayz -and $rxRate -ge $cfg.dayz_rx_kb_per_min
if ($busyRdp -or $busyDayz) { $idleSince = $now }
$idleMin = [math]::Round(($now - $idleSince).TotalMinutes)

@{ idleSince = $idleSince.ToString('o'); at = $now.ToString('o'); rx = $rx } | ConvertTo-Json | Set-Content $stateF -Encoding UTF8
$line = "sessions=$sessions dayz=$([bool]$dayz) rxKBmin=$rxRate idle=${idleMin}m/$($cfg.idle_minutes)"

if ($idleMin -ge $cfg.idle_minutes) {
  if ($DryRun) { Log "$line -> WOULD shelve (dry run)"; exit 0 }
  Log "$line -> shelve"
  try { Invoke-Ovh 'POST' "/cloud/project/$($cfg.project)/instance/$($cfg.instance)/shelve" | Out-Null }
  catch { Log "shelve failed: $($_.Exception.Message)"; exit 1 }
} elseif ($DryRun -or $now.Minute -lt 5) {
  Log $line   # heartbeat about once an hour, every run in dry-run
}
