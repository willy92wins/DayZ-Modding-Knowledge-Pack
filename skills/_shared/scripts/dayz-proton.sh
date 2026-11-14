#!/bin/sh
# Run DayZ Tools (Steam app 830640) and DayZDiag on Linux through Proton.
#
#   dayz-proton.sh doctor                         what is installed, versions, prefixes, dayzmake
#   dayz-proton.sh init [<P-root>]                create the private tools prefix, register the game, map P:
#   dayz-proton.sh winpath <path>                 the Windows path a tool sees for a Linux path
#   dayz-proton.sh tool <Tool> [args...]          run a console tool, print its output, return its exit code
#   dayz-proton.sh gui  <Tool> [args...]          run a GUI tool on the current display
#   dayz-proton.sh binarize <P-root> <addon> <out> [file.p3d|file.rtm ...]
#                                                 BI binarize.exe in a confined sandbox, run from the P: root
#   dayz-proton.sh headless start <state> <Tool|DayZDiag> [args...]   GUI tool in a headless sway
#   dayz-proton.sh headless shot  <state> <out.png>
#   dayz-proton.sh headless stop  <state>
#
# Tools: AddonBuilder BankRev Binarize CfgConvert DSCheckSignatures DSCreateKey DSSignFile FileBank
#        ImageToPAA ImageToPAAGUI ObjectBuilder Publisher TerrainBuilder TexView Workbench, and DayZDiag
#        (the diag executable from the game folder, run in the private *game* prefix).
#
# Why: DayZ (221100) and DayZ Tools (830640) are separate Steam apps, so Proton gives each its own
# Wine prefix, and nothing the Windows tools expect to share crosses between them: the game's
# HKLM\SOFTWARE\(WOW6432Node\)Bohemia Interactive\DayZ "main" key is empty in the tools prefix, and
# the P: drive (subst on Windows; Wine has no subst) exists in neither. `init` builds private
# prefixes under DAYZ_PROTON_HOME and leaves Steam's own prefixes alone. In the tools prefix it
# replays what Steam does on a first launch (installscript.vdf registry, VC++ runtime with MFC from
# Steamworks Shared), adds the game key, spends the one failing first .NET start, and maps P: (a
# dosdevices symlink) in both prefixes. Run it once; it takes about two minutes.
#
# Rules learned the hard way (2026-11-03, Proton Hotfix and GE-Proton11-1, Debian testing):
# - One display per prefix at a time: a prefix's wineserver is bound to the display its first
#   program used; others die with "X Error ... BadWindow ... X_UnmapWindow". `headless start`
#   refuses a busy prefix and `headless stop` stops its wineserver.
# - 32-bit tools run with PROTON_USE_WOW64=1 (default here), or GDI dialogs show no text when the
#   host has no i386 FreeType. DAYZ_PROTON_RUNTIME=1 starts Proton inside the Steam Linux Runtime
#   instead, as Steam does; GDI tools crashed there on this host.
# - Object Builder asks for BI's licence on its first start: run `gui ObjectBuilder` once on your
#   desktop and answer it yourself.
#
# Arguments that are absolute Linux paths (/x/y, or -opt=/x/y) are rewritten to Windows paths: P:\...
# inside the P: root, Z:\... elsewhere. Pass `--` to stop the rewriting for the remaining arguments.
#
# Environment: STEAM_ROOT (auto), PROTON (tool name or path; default: Proton Hotfix, else GE-Proton*,
# else Proton - Experimental), DAYZ_PROTON_HOME (default ${XDG_DATA_HOME:-~/.local/share}/dayz-proton),
# DAYZ_P (P: root, default: what `init` recorded), DAYZ_PROTON_CWD (working directory of `tool`),
# DAYZ_PROTON_PREFIX=steam to use Steam's compatdata/<appid> prefixes instead (then `init` writes the
# game key and P: into them, nothing else).
set -eu

me=$(cd "$(dirname "$0")" && pwd -P)/$(basename "$0")
die() { echo "dayz-proton: $*" >&2; exit 1; }

# ---------------------------------------------------------------- Steam, apps, Proton
find_steam() {
    if [ -n "${STEAM_ROOT:-}" ]; then echo "$STEAM_ROOT"; return; fi
    for d in "$HOME/.steam/debian-installation" "$HOME/.steam/steam" "$HOME/.local/share/Steam" \
             "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam"; do
        [ -d "$d/steamapps" ] && { (cd "$d" && pwd -P); return; }
    done
    die "no Steam install found (set STEAM_ROOT)"
}
STEAM_ROOT=$(find_steam)

libraries() {
    echo "$STEAM_ROOT"
    sed -n 's/^[[:space:]]*"path"[[:space:]]*"\(.*\)"[[:space:]]*$/\1/p' \
        "$STEAM_ROOT/steamapps/libraryfolders.vdf" 2>/dev/null | sed 's/\\\\/\\/g'
}

# manifest <appid> -> path of appmanifest_<appid>.acf, empty if not installed
manifest() {
    libraries | while IFS= read -r lib; do
        [ -f "$lib/steamapps/appmanifest_$1.acf" ] && { echo "$lib/steamapps/appmanifest_$1.acf"; break; }
    done || true  # not found: the loop's status is the failed test, which set -e turned into an exit
}
acf() { sed -n "s/^[[:space:]]*\"$2\"[[:space:]]*\"\(.*\)\"/\1/p" "$1" | head -n 1; }

# appdir <appid> -> install folder
appdir() {
    m=$(manifest "$1"); [ -n "$m" ] || return 1
    echo "$(dirname "$m")/common/$(acf "$m" installdir)"
}

find_proton() {
    p=${PROTON:-}
    if [ -n "$p" ]; then
        for c in "$p" "$STEAM_ROOT/compatibilitytools.d/$p" "$STEAM_ROOT/steamapps/common/$p"; do
            [ -x "$c/proton" ] && { echo "$c/proton"; return; }
            [ -f "$c" ] && [ "$(basename "$c")" = proton ] && { echo "$c"; return; }
        done
        die "Proton tool '$p' not found"
    fi
    for c in "$STEAM_ROOT/steamapps/common/Proton Hotfix" \
             $(ls -d "$STEAM_ROOT"/compatibilitytools.d/GE-Proton* 2>/dev/null | sort -V -r) \
             "$STEAM_ROOT/steamapps/common/Proton - Experimental"; do
        [ -x "$c/proton" ] && { echo "$c/proton"; return; }
    done
    c=$(ls -d "$STEAM_ROOT"/steamapps/common/Proton\ [0-9]* 2>/dev/null | sort -V | tail -n 1)
    [ -n "$c" ] && [ -x "$c/proton" ] && { echo "$c/proton"; return; }
    die "no Proton found (install one through Steam or set PROTON)"
}

H=${DAYZ_PROTON_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/dayz-proton}

# The Steam Linux Runtime container a Proton build asks for (toolmanifest.vdf require_tool_appid).
find_runtime() {
    id=$(sed -n 's/.*"require_tool_appid"[[:space:]]*"\([0-9]*\)".*/\1/p' "$(dirname "$PROTON_BIN")/toolmanifest.vdf" 2>/dev/null)
    [ -n "$id" ] || return 0
    d=$(appdir "$id" 2>/dev/null) || return 0
    [ -x "$d/_v2-entry-point" ] && echo "$d/_v2-entry-point"
    return 0
}

# prun <exe> [args]: `proton run`, by default bare with PROTON_USE_WOW64=1.
# The measured tool/font workaround uses WoW64; inspect installed PE headers for bitness.
# Bare and without WoW64, Proton runs them against the host's i386 libraries, and without an i386
# FreeType their dialogs show no text at all. Inside the Steam Linux Runtime container
# (DAYZ_PROTON_RUNTIME=1, what Steam itself does) GDI tools died on a fontconfig/X error here.
# WoW64 runs them through the 64-bit host libraries, which fixed both (measured 2026-11-03).
prun() {
    if [ "${DAYZ_PROTON_RUNTIME:-0}" = 1 ] && rt=$(find_runtime) && [ -n "$rt" ]; then
        "$rt" --verb=run -- "$PROTON_BIN" run "$@"
    else
        PROTON_USE_WOW64=${PROTON_USE_WOW64:-1} "$PROTON_BIN" run "$@"
    fi
}


# prefix_dir <appid> -> the STEAM_COMPAT_DATA_PATH used for that app
prefix_dir() {
    if [ "${DAYZ_PROTON_PREFIX:-}" = steam ]; then
        m=$(manifest "$1"); [ -n "$m" ] || die "app $1 is not installed"
        echo "$(dirname "$m")/compatdata/$1"
    elif [ "$1" = 830640 ]; then echo "$H/tools"
    else echo "$H/game"
    fi
}

p_root() {
    if [ -n "${DAYZ_P:-}" ]; then echo "$DAYZ_P"; return; fi
    [ -f "$H/p-root" ] && cat "$H/p-root"
    return 0
}

# ---------------------------------------------------------------- paths
# winpath <linux path> -> P:\... when inside the P: root, else Z:\...
winpath() {
    case $1 in /*) a=$1 ;; *) a=$(pwd -P)/$1 ;; esac
    d=$(dirname "$a"); b=$(basename "$a")
    [ -d "$d" ] && a=$(cd "$d" && pwd -P)/$b
    a=${a%/.}
    pr=$(p_root)
    if [ -n "$pr" ] && { [ "$a" = "$pr" ] || [ "${a#"$pr"/}" != "$a" ]; }; then
        r=${a#"$pr"}; r=${r#/}
        printf 'P:\\%s\n' "$(printf '%s' "$r" | tr / '\\')"
    else
        printf 'Z:%s\n' "$(printf '%s' "$a" | tr / '\\')"
    fi
}

# ---------------------------------------------------------------- tools
# tool_exe <Tool> -> "<kind> <path>" ; kind = con | gui | game
tool_exe() {
    T=$(appdir 830640 2>/dev/null)/Bin
    case $1 in
        AddonBuilder)      echo "con $T/AddonBuilder/AddonBuilder.exe" ;;
        Binarize)          echo "con $T/Binarize/binarize.exe" ;;
        CfgConvert)        echo "con $T/CfgConvert/CfgConvert.exe" ;;
        DSSignFile|DSCheckSignatures|DSCreateKey)
                           echo "con $T/DsUtils/$1.exe" ;;
        DSUtils)           echo "gui $T/DsUtils/DSUtils.exe" ;;
        FileBank|BankRev)  echo "con $T/PboUtils/$1.exe" ;;
        ImageToPAA)        echo "con $T/ImageToPAA/ImageToPAA.exe" ;;
        ImageToPAAGUI)     echo "gui $T/ImageToPAA/imageToPaaGUI.exe" ;;
        TexView)           echo "gui $T/ImageToPAA/TexView.exe" ;;
        ObjectBuilder)     echo "gui $T/ObjectBuilder/ObjectBuilder.exe" ;;
        Publisher)         echo "gui $T/Publisher/Publisher.exe" ;;
        TerrainBuilder)    echo "gui $T/TerrainBuilder/terrainBuilder.exe" ;;
        Workbench)         echo "gui $T/Workbench/WorkbenchApp.exe" ;;
        DayZDiag)          g=$(appdir 221100) || die "DayZ (221100) is not installed"
                           echo "game $g/DayZDiag_x64.exe" ;;
        *) die "unknown tool '$1' (see: $me with no arguments)" ;;
    esac
}

proton_env() {   # proton_env <appid>
    pfx=$(prefix_dir "$1"); mkdir -p "$pfx"
    export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT" STEAM_COMPAT_DATA_PATH="$pfx"
    export SteamAppId="$1" SteamGameId="$1" STEAM_COMPAT_APP_ID="$1"
    PROTON_BIN=$(find_proton)
}

ensure_prefix() {   # ensure_prefix <appid>: create the Wine prefix once
    proton_env "$1"
    [ -d "$STEAM_COMPAT_DATA_PATH/pfx/dosdevices" ] && return 0
    echo "dayz-proton: creating prefix $STEAM_COMPAT_DATA_PATH (once, ~10 s)" >&2
    prun cmd.exe /c exit >/dev/null 2>&1 || true
    if [ "$1" = 830640 ] && [ "${DAYZ_PROTON_PREFIX:-}" != steam ]; then
        import_registry; install_vcredist; warm_dotnet
    fi
    return 0
}

# The first .NET tool started in a fresh prefix never finishes: AddonBuilder crashed (DXVK error)
# without WoW64 and hung after its constructor with it; every later start works (2026-11-03).
# Spend that one start on a throwaway pack, time-boxed, then stop the prefix's wineserver.
warm_dotnet() {
    ab=$(appdir 830640)/Bin/AddonBuilder/AddonBuilder.exe
    [ -f "$ab" ] || return 0
    wd=$(mktemp -d "${TMPDIR:-/tmp}/dayz-proton-warm.XXXXXX"); mkdir -p "$wd/src" "$wd/out"
    echo warm > "$wd/src/readme.txt"
    echo "dayz-proton: warming up .NET in the new prefix (once, up to 90 s)" >&2
    ( cd "$(dirname "$ab")" && timeout 90 sh -c 'PROTON_USE_WOW64=${PROTON_USE_WOW64:-1} "$1" run "$2" "$3" "$4" -packonly -prefix=warm' \
        sh "$PROTON_BIN" "$ab" "$(winpath "$wd/src")" "$(winpath "$wd/out")" ) >/dev/null 2>&1 || true
    WINEPREFIX=$STEAM_COMPAT_DATA_PATH/pfx "$(dirname "$PROTON_BIN")/files/bin/wineserver" -k >/dev/null 2>&1 || true
    rm -rf "$wd"
}

# What Steam writes into the tools prefix on first launch (installscript.vdf "Registry"), which a
# private prefix never gets: without it TexView stops at "Missing registry entry
# HKEY_LOCAL_MACHINE/Software\BIStudio\TextureConvert". Plus the game's "main" key, which on Windows
# the DayZ installer writes and which no Proton prefix of 830640 has (the game lives in 221100's).
# HKLM keys go to both registry views, including WOW6432Node for tools that read it.
import_registry() {
    td=$(appdir 830640) || return 0
    wtd=$(winpath "$td" | sed 's/\\/\\\\/g')
    reg=$STEAM_COMPAT_DATA_PATH/dayz-proton.reg
    {
        printf 'Windows Registry Editor Version 5.00\r\n'
        DIR=$wtd awk '
            /"Registry"/ { inreg = 1; next }
            inreg && /"Run Process"/ { exit }
            inreg && match($0, /^[[:space:]]*"(HKEY_[^"]*)"[[:space:]]*$/) {
                k = $0; sub(/^[[:space:]]*"/, "", k); sub(/"[[:space:]]*$/, "", k); gsub(/\\\\/, "\\", k)
                n = 1; keys[1] = k
                if (k ~ /^HKEY_LOCAL_MACHINE\\SOFTWARE\\/) { w = k; sub(/SOFTWARE\\/, "SOFTWARE\\WOW6432Node\\", w); keys[++n] = w }
                next
            }
            inreg && n && match($0, /^[[:space:]]*"[^"]*"[[:space:]]+"[^"]*"[[:space:]]*$/) {
                split($0, f, "\""); v = f[4]
                while ((i = index(v, "%INSTALLDIR%")) > 0) v = substr(v, 1, i - 1) ENVIRON["DIR"] substr(v, i + 12)
                for (i = 1; i <= n; i++) vals[keys[i]] = vals[keys[i]] sprintf("\"%s\"=\"%s\"\r\n", f[2], v)
                if (!(keys[1] in seen)) { seen[keys[1]] = 1; order[++m] = keys[1]; if (n > 1) order[++m] = keys[2] }
            }
            END { for (i = 1; i <= m; i++) printf "\r\n[%s]\r\n%s", order[i], vals[order[i]] }
        ' "$td/installscript.vdf"
        g=$(appdir 221100 2>/dev/null) && {
            wg=$(winpath "$g" | sed 's/\\/\\\\/g')
            for k in 'HKEY_LOCAL_MACHINE\SOFTWARE\Bohemia Interactive\DayZ' \
                     'HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Bohemia Interactive\DayZ'; do
                printf '\r\n[%s]\r\n"main"="%s"\r\n' "$k" "$wg"
            done
        }
    } > "$reg"
    prun regedit /S "$(winpath "$reg")" >/dev/null 2>&1 || echo "dayz-proton: registry import failed ($reg)" >&2
}

# A prefix has one wineserver, and its desktop is bound to the display the first program of the
# prefix started on. Programs started later on another display (or after that display is gone, e.g.
# a stopped headless sway) die with "X Error ... BadWindow ... X_UnmapWindow". So: one display per
# prefix at a time, and stop the wineserver whenever a session ends.
prefix_wineserver() {   # pids of the wineserver serving prefix $1 (a compatdata dir)
    for p in $(pgrep -x wineserver 2>/dev/null); do
        tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null | grep -qx "WINEPREFIX=$1/pfx/\{0,1\}" && echo "$p"
    done
    return 0
}
stop_wineserver() {   # stop_wineserver <appid>
    pfx=$(prefix_dir "$1"); PROTON_BIN=${PROTON_BIN:-$(find_proton)}
    WINEPREFIX=$pfx/pfx "$(dirname "$PROTON_BIN")/files/bin/wineserver" -k >/dev/null 2>&1 || true
}

# The VC++ runtime with MFC (Object Builder needs mfc140.dll). Steam installs it from Steamworks
# Shared/_CommonRedist on an app's first launch; a private prefix has to do it itself.
install_vcredist() {
    [ -f "$STEAM_COMPAT_DATA_PATH/pfx/drive_c/windows/syswow64/mfc140.dll" ] && return 0
    sw=$(appdir 228980 2>/dev/null) || sw=
    vd=$(ls -d "$sw"/_CommonRedist/vcredist/20* 2>/dev/null | sort -r | while IFS= read -r d; do
        [ -f "$d/VC_redist.x86.exe" ] && { echo "$d"; break; }; done)
    [ -n "$vd" ] || { echo "dayz-proton: no VC++ redistributable in Steamworks Shared (app 228980); Object Builder will not start" >&2; return 0; }
    echo "dayz-proton: installing the VC++ runtime from $vd (once)" >&2
    for a in x86 x64; do (cd "$vd" && timeout 300 sh -c 'PROTON_USE_WOW64=1 "$1" run "$2" /q /norestart' sh "$PROTON_BIN" "./VC_redist.$a.exe") >/dev/null 2>&1 || true; done
}

# rewrite_args: one argument per line on stdout, absolute paths converted
rewrite_args() {
    raw=0
    for a in "$@"; do
        if [ $raw = 1 ]; then printf '%s\n' "$a"; continue; fi
        case $a in
            --) raw=1 ;;
            /*) winpath "$a" ;;
            -*=/*) printf '%s=%s\n' "${a%%=*}" "$(winpath "${a#*=}")" ;;
            *) printf '%s\n' "$a" ;;
        esac
    done
}

run_tool() {   # run_tool con|gui <Tool> [args]
    mode=$1; name=$2; shift 2
    set -- "$name" "$@"
    spec=$(tool_exe "$1"); kind=${spec%% *}; exe=${spec#* }; shift
    [ -f "$exe" ] || die "$exe not found (is DayZ Tools, app 830640, installed?)"
    app=830640; [ "$kind" = game ] && app=221100
    ensure_prefix "$app"
    args=$(mktemp); rewrite_args "$@" > "$args"
    set --; while IFS= read -r a; do set -- "$@" "$a"; done < "$args"; rm -f "$args"
    cd "${DAYZ_PROTON_CWD:-$(dirname "$exe")}"
    if [ "$mode" = gui ] || [ "$kind" != con ]; then
        prun "$exe" "$@"; exit $?
    fi
    # Console tools: several (DS*, ImageToPAA) print nothing on Proton's console, so run them
    # through cmd with their output redirected to a file, then show it. cmd passes the exit code on.
    out=$(mktemp -d "${TMPDIR:-/tmp}/dayz-proton.XXXXXX")
    # A .bat file keeps quoting intact: Proton escapes quotes inside a `cmd /c "..."` string.
    {
        printf '@echo off\r\n'
        printf '"%s"' "$(winpath "$exe")"
        for a in "$@"; do
            a=$(printf '%s' "$a" | sed 's/%/%%/g')
            case $a in *' '*|*'&'*|*'('*|*')'*|*'^'*|*'|'*|*'<'*|*'>'*) printf ' "%s"' "$a" ;; *) printf ' %s' "$a" ;; esac
        done
        printf ' > "%s" 2>&1\r\nexit /b %%errorlevel%%\r\n' "$(winpath "$out/log.txt")"
    } > "$out/run.bat"
    rpt=$(dirname "$(dirname "$exe")")/Logs/AddonBuilder.rpt
    rpt_lines=$(cat "$rpt" 2>/dev/null | wc -l)
    rc=0
    prun cmd.exe /c "$(winpath "$out/run.bat")" >"$out/proton.txt" 2>&1 || rc=$?
    [ -f "$out/log.txt" ] && tr -d '\r' < "$out/log.txt"
    # AddonBuilder exits 0 on a failed build; the result is only in its rpt ("[ResultCode]=1").
    if [ "$name" = AddonBuilder ] && [ -f "$rpt" ]; then
        tail -n +"$((rpt_lines + 1))" "$rpt" | tr -d '\r' | grep -E '\[(ERROR|FATAL)\]|ResultCode' | cut -c1-300 >&2 || true
        res=$(tail -n +"$((rpt_lines + 1))" "$rpt" | tr -d '\r' | sed -n 's/.*\[ResultCode\]=\([0-9]*\).*/\1/p' | tail -n 1)
        [ -n "$res" ] && [ "$res" != 0 ] && [ $rc = 0 ] && rc=$res
        [ -n "$res" ] || { [ $rc = 0 ] && rc=1; echo "dayz-proton: AddonBuilder wrote no ResultCode (see $rpt)" >&2; }
    fi
    [ $rc = 0 ] || grep -v -E 'fsync|radv|FreeType|freetype|2\.0\.5|freetype\.org' "$out/proton.txt" >&2 || true
    rm -rf "$out"
    return $rc
}

# ---------------------------------------------------------------- binarize sandbox
# binarize.exe walks Wine's Z: drive (= / by default) for minutes; it is only usable with a Z: that
# holds nothing but the sandbox. It resolves texture paths relative to its current directory, so it
# must run from the P: root or alpha textures are silently lost.
do_binarize() {
    [ $# -ge 3 ] || die "usage: binarize <P-root> <addon path under P:> <out dir> [files...]"
    proot=$(cd "$1" && pwd -P); addon=$2; out=$3; shift 3
    [ -d "$proot/$addon" ] || die "$proot/$addon does not exist"
    T=$(appdir 830640)/Bin/Binarize; [ -f "$T/binarize.exe" ] || die "DayZ Tools Binarize not found"
    sb=$H/binarize; mkdir -p "$sb/out" "$sb/prefix"
    if [ ! -f "$sb/Binarize/binarize.exe" ] || [ "$T/binarize.exe" -nt "$sb/Binarize/binarize.exe" ]; then
        rm -rf "$sb/Binarize"; cp -r "$T" "$sb/Binarize"
    fi
    export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT" STEAM_COMPAT_DATA_PATH="$sb/prefix"
    export SteamAppId=830640 SteamGameId=830640
    PROTON_BIN=$(find_proton)
    [ -d "$sb/prefix/pfx/dosdevices" ] || prun cmd.exe /c exit >/dev/null 2>&1 || true
    ln -sfn "$sb" "$sb/prefix/pfx/dosdevices/z:"
    ln -sfn "$proot" "$sb/prefix/pfx/dosdevices/p:"
    rm -rf "$sb/out"/*
    waddon=$(printf '%s' "$addon" | tr / '\\')
    cd "$proot"
    rc=0
    prun cmd.exe /c "Z:\\Binarize\\binarize.exe -norecurse -always -maxProcesses=0 P:\\$waddon Z:\\out $* > Z:\\out\\binarize.log 2>&1" \
        > /dev/null 2>&1 || rc=$?
    mkdir -p "$out"
    tr -d '\r' < "$sb/out/binarize.log" 2>/dev/null | grep -v '^$' | tail -n 40 || true
    rm -f "$sb/out/binarize.log"
    cp -r "$sb/out/." "$out/"
    echo "dayz-proton: binarize exit $rc, output in $out" >&2
    return $rc
}

# ---------------------------------------------------------------- headless sway
do_headless() {
    sub=${1:-}; state=${2:-}
    [ -n "$sub" ] && [ -n "$state" ] || die "usage: headless start|shot|stop <state> ..."
    shift 2; mkdir -p "$state"; state=$(cd "$state" && pwd -P)
    case $sub in
    start)
        [ $# -ge 1 ] || die "usage: headless start <state> <Tool> [args...]"
        command -v sway >/dev/null || die "sway is needed for headless runs"
        app=830640; [ "$1" = DayZDiag ] && app=221100
        busy=$(prefix_wineserver "$(prefix_dir $app)")
        [ -z "$busy" ] || die "prefix $(prefix_dir $app) is in use (wineserver $busy): one display per prefix; stop that session first"
        echo $app > "$state/app"
        : > "$state/args"; for a in "$@"; do printf '%s\n' "$a" >> "$state/args"; done
        cat > "$state/run.sh" <<EOF
#!/bin/sh
echo "\$WAYLAND_DISPLAY" > "$state/wayland-display"
set --
while IFS= read -r a; do set -- "\$@" "\$a"; done < "$state/args"
exec "$me" gui "\$@"
EOF
        chmod +x "$state/run.sh"
        printf 'output HEADLESS-1 resolution %s position 0 0\nxwayland enable\nexec %s/run.sh > %s/run.log 2>&1\n' \
            "${RES:-1600x900}" "$state" "$state" > "$state/sway.conf"
        rm -f "$state/wayland-display"
        WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 setsid nohup sway -c "$state/sway.conf" \
            > "$state/sway.log" 2>&1 &
        echo $! > "$state/sway.pid"
        echo "headless sway $(cat "$state/sway.pid"), log $state/run.log" ;;
    shot)
        [ -s "$state/wayland-display" ] || die "no session in $state"
        command -v grim >/dev/null || die "grim is needed for screenshots"
        WAYLAND_DISPLAY=$(cat "$state/wayland-display") grim "${1:?usage: headless shot <state> <out.png>}" ;;
    stop)
        pid=$(cat "$state/sway.pid" 2>/dev/null) || die "no session in $state"
        kill "$pid" 2>/dev/null || true; rm -f "$state/sway.pid"
        [ -f "$state/app" ] && stop_wineserver "$(cat "$state/app")" ;;
    *) die "unknown headless command '$sub'" ;;
    esac
}

# ---------------------------------------------------------------- init / doctor
do_init() {
    if [ $# -ge 1 ]; then
        pr=$(cd "$1" && pwd -P) || die "$1 does not exist"
        mkdir -p "$H"; printf '%s\n' "$pr" > "$H/p-root"
    fi
    ensure_prefix 830640
    import_registry
    [ "${DAYZ_PROTON_PREFIX:-}" = steam ] || install_vcredist
    appdir 221100 >/dev/null 2>&1 || echo "dayz-proton: DayZ (221100) not installed; game key skipped" >&2
    echo "tools prefix $STEAM_COMPAT_DATA_PATH: registry from installscript.vdf + DayZ 'main' imported"
    pr=$(p_root)
    if [ -n "$pr" ]; then
        for app in 830640 221100; do
            proton_env $app; ensure_prefix $app
            ln -sfn "$pr" "$STEAM_COMPAT_DATA_PATH/pfx/dosdevices/p:"
            echo "prefix $app: P: -> $pr"
        done
    else
        echo "no P: root given; run '$me init <dir>' to map P:"
    fi
    stop_wineserver 830640; stop_wineserver 221100
}

# check_dayzmake: the native packer is bzed's armake2 fork, renamed dayzmake at v1.0.0. Upstream
# armake2 is built for Arma (it leaves *.c out of the signature, and dayzmake adds DayZ-only functions);
# a fork build from before the rename is called armake2.
check_dayzmake() {
    url="https://github.com/bzed/dayzmake (v1.0.0 or later)"
    b=
    for c in dayzmake armake2; do command -v $c >/dev/null && { b=$c; break; }; done
    if [ -z "$b" ]; then echo "dayzmake:    missing (native PBO build/sign; $url)"; return 0; fi
    if ! $b -h 2>&1 | grep -q -- --proton-binarize; then
        echo "dayzmake:    '$b' is upstream armake2, which leaves *.c out of signatures; install $url"
        return 0
    fi
    ver=$($b --version 2>&1 | grep -m1 -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)
    case $ver in
        ''|0.*) echo "dayzmake:    '$b' is the fork from before the rename (v${ver:-?}); upgrade to $url" ;;
        *) echo "dayzmake:    $b v$ver (ok)" ;;
    esac
}

do_doctor() {
    echo "Steam root:  $STEAM_ROOT"
    echo "Proton:      $(find_proton 2>&1)"
    echo "Prefixes:    tools=$(prefix_dir 830640)  game=$(prefix_dir 221100)"
    echo "P: root:     $(p_root)"
    for app in 221100 223350 830640 1024020 1042420; do
        m=$(manifest $app)
        if [ -z "$m" ]; then printf '%-8s not installed\n' $app; continue; fi
        d=$(appdir $app); st=$(acf "$m" StateFlags)
        v=
        for b in "$d/DayZ_x64.exe" "$d/DayZServer"; do
            [ -f "$b" ] && v=$(strings -n7 "$b" 2>/dev/null | grep -m1 -oE '\b1\.[0-9]{2}\.[0-9]{6}\b' || true)
        done
        flag=; [ "$st" = 4 ] || flag="  (StateFlags $st: update pending or incomplete)"
        printf '%-8s %-26s build %-9s %s%s\n' $app "$(acf "$m" name)" "$(acf "$m" buildid)" "${v:+v$v}" "$flag"
    done
    check_dayzmake
    for c in sway grim; do command -v $c >/dev/null || echo "$c:        missing (needed for headless GUI runs)"; done
    echo "Client and server must report the same v1.30.xxxxxx, or the client is refused (0x00020013)."
}

cmd=${1:-}; [ $# -gt 0 ] && shift
case $cmd in
    doctor)   do_doctor ;;
    init)     do_init "$@" ;;
    winpath)  winpath "${1:?usage: winpath <path>}" ;;
    tool)     run_tool con "$@" ;;
    gui)      run_tool gui "$@" ;;
    binarize) do_binarize "$@" ;;
    headless) do_headless "$@" ;;
    *) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$me" >&2; exit 2 ;;
esac
