#!/bin/sh
# Source: bzed/dayz-dev-plugin 6112ac5, contributed to this Pack under its MIT licence by its author.
# Run the DayZ *client* in a headless sway session: no monitor, nothing shown on your desktop.
#
#   dayz-client-headless.sh [-e] start <state-dir> [DayZ args...]   start sway + the game, return at once
#   dayz-client-headless.sh        shot  <state-dir> <out.png>      screenshot of the headless output
#   dayz-client-headless.sh        stop  <state-dir>                stop the game and the session
#   dayz-client-headless.sh        status                           list running DayZ clients (exit 1 if any)
#
# -e = the experimental client (app 1024020, "DayZ Exp") instead of stable (221100, "DayZ").
# Only ONE game runs at a time: `start` refuses while any DayZ client is running (even the
# user's own). Servers are different: run as many as you like, each on its own tree and ports.
# Stop the game as soon as the test is over; it holds the GPU, ~10 GB of RAM and the Steam account.
#
# Steam must be running (the game talks to the Steam client). `steam -applaunch` is NOT used: it
# hands the launch to the running Steam, which would open the window on your real desktop. This
# runs the same chain Steam does (Steam Linux Runtime -> Proton -> DayZ_x64.exe) from inside the
# headless session, so the game inherits that session's WAYLAND_DISPLAY/DISPLAY.
#
# Needs: sway (wlroots), grim, a Steam install of DayZ (221100) with a Proton tool selected.
# Environment: STEAM_ROOT (default ~/.steam/debian-installation), PROTON (name of the Proton tool,
# default GE-Proton11-1; the tool Steam selected for 221100 is not read), RES (default 1280x720).
# Mod folders (@name) must exist in the DayZ install dir; symlinks to workshop items are fine.
# No path is interpolated into sway.conf or game.sh: sway runs ./game.sh from the state dir and
# game.sh reads "$state/env" values written with single-quote quoting. Real sway was not run by
# the offline tests; a fake sway emulates its exec parsing there.
set -eu
LF='
'
app=221100 dir=DayZ
if [ "${1:-}" = "-e" ]; then app=1024020 dir="DayZ Exp"; shift; fi
STEAM_ROOT=${STEAM_ROOT:-$HOME/.steam/debian-installation}
PROTON=${PROTON:-GE-Proton11-1}
RES=${RES:-1280x720}
running_games() { ps -eo pid,args | grep '[D]ayZ_x64\.exe' || true; }
die() { echo "dayz-client-headless: $*" >&2; exit 1; }
sh_quote() {
    _q=$1
    printf "'"
    while :; do
        case $_q in
            *"'"*) printf "%s'\\''" "${_q%%\'*}"; _q=${_q#*\'} ;;
            *) printf "%s'" "$_q"; break ;;
        esac
    done
}
no_newline() {
    case $1 in *"$LF"*) die "a path or value containing a newline is not allowed" ;; esac
}
proc_starttime() {
    _ps_stat=$(cat "/proc/$1/stat" 2>/dev/null) || return 1
    _ps_rest=${_ps_stat##*)}
    _ps_i=0
    for _ps_f in $_ps_rest; do
        _ps_i=$((_ps_i + 1))
        if [ "$_ps_i" = 20 ]; then printf '%s\n' "$_ps_f"; return 0; fi
    done
    return 1
}
sway_cmdline_matches() {
    _sc_cur=$(mktemp) || return 1
    if ! tr '\0' '\n' < "/proc/$1/cmdline" > "$_sc_cur" 2>/dev/null; then rm -f "$_sc_cur"; return 1; fi
    SWAYCONF="$2/sway.conf" awk '
        function base(p,   n, a) { n = split(p, a, "/"); return a[n] }
        NR == 1 { first = $0 }
        { prev2 = prev1; prev1 = $0; n = NR }
        END { if (n != 3 || prev2 != "-c" || prev1 != ENVIRON["SWAYCONF"]) exit 1; if (base(first) == "sway") exit 0; exit 1 }' "$_sc_cur"
    _sc_rc=$?
    rm -f "$_sc_cur"
    [ "$_sc_rc" = 0 ]
}
# identity: first line starttime, then exact argv as NUL-separated bytes.
sway_identity_ok() {
    [ -d "/proc/$1" ] || return 1
    case $1 in ''|*[!0-9]*) return 1 ;; esac
    [ -f "$2/sway.identity" ] || return 1
    _si_recorded=$(head -n 1 "$2/sway.identity" 2>/dev/null) || return 1
    [ -n "$_si_recorded" ] || return 1
    _si_now=$(proc_starttime "$1") || return 1
    [ "$_si_now" = "$_si_recorded" ] || return 1
    _si_cur=$(mktemp) || return 1
    _si_rec=$(mktemp) || { rm -f "$_si_cur"; return 1; }
    if ! cat "/proc/$1/cmdline" > "$_si_cur" 2>/dev/null; then rm -f "$_si_cur" "$_si_rec"; return 1; fi
    _si_len=$(printf '%s' "$_si_recorded" | wc -c); _si_len=$(printf '%s' "$_si_len" | tr -d ' ')
    if ! tail -c "+$((_si_len + 2))" "$2/sway.identity" > "$_si_rec" 2>/dev/null; then rm -f "$_si_cur" "$_si_rec"; return 1; fi
    if ! cmp -s "$_si_cur" "$_si_rec"; then rm -f "$_si_cur" "$_si_rec"; return 1; fi
    rm -f "$_si_cur" "$_si_rec"
    sway_cmdline_matches "$1" "$2"
}
state_launcher_alive() {
    _la_state=$1; _la_tmp=$(mktemp) || return 2
    if [ -f "$_la_state/sway.pid" ]; then
        _la_pid=$(cat "$_la_state/sway.pid" 2>/dev/null) || _la_pid=
        if [ -n "$_la_pid" ] && [ -d "/proc/$_la_pid" ]; then
            if sway_cmdline_matches "$_la_pid" "$_la_state"; then rm -f "$_la_tmp"; return 0; fi
            if tr '\0' '\n' < "/proc/$_la_pid/cmdline" > "$_la_tmp" 2>/dev/null; then
                if grep -Fq 'exec sway' "$_la_tmp" && grep -Fxq "$_la_state" "$_la_tmp"; then rm -f "$_la_tmp"; return 0; fi
            elif [ -d "/proc/$_la_pid" ]; then rm -f "$_la_tmp"; return 2; fi
        fi
    fi
    [ -d /proc ] || { rm -f "$_la_tmp"; return 2; }
    _la_unknown=0
    for _la_entry in /proc/[0-9]*; do
        [ -d "$_la_entry" ] || continue
        if ! tr '\0' '\n' < "$_la_entry/cmdline" > "$_la_tmp" 2>/dev/null; then [ -d "$_la_entry" ] && _la_unknown=1; continue; fi
        [ -s "$_la_tmp" ] || continue
        if grep -Fq "$_la_state/sway.conf" "$_la_tmp"; then rm -f "$_la_tmp"; return 0; fi
        if grep -Fq 'exec sway' "$_la_tmp" && grep -Fxq "$_la_state" "$_la_tmp"; then rm -f "$_la_tmp"; return 0; fi
    done
    rm -f "$_la_tmp"
    if [ "$_la_unknown" = 1 ]; then return 2; fi
    return 1
}
failed_start_signal() {
    [ -s "$1/sway.pid" ] || return 0
    _fs_pid=$(cat "$1/sway.pid" 2>/dev/null) || _fs_pid=
    case $_fs_pid in ''|*[!0-9]*) return 0 ;; esac
    [ -d "/proc/$_fs_pid" ] || return 0
    _fs_cmd=$(tr '\0' '\n' < "/proc/$_fs_pid/cmdline" 2>/dev/null) || _fs_cmd=
    case $_fs_cmd in
        *'exec sway'*) kill "$_fs_pid" 2>/dev/null || true ;;
        *) if sway_cmdline_matches "$_fs_pid" "$1"; then kill "$_fs_pid" 2>/dev/null || true; fi ;;
    esac
    return 0
}
failed_start_cleanup() {
    : > "$1/sway.cancel"
    failed_start_signal "$1"
    _fc_i=0
    while [ "$_fc_i" -lt 5 ]; do sleep 0.1; _fc_i=$((_fc_i + 1)); failed_start_signal "$1"; done
    rm -f "$1/sway.pid" "$1/sway.identity"
}

cmd=${1:-}; state=${2:-}
if [ "$cmd" = status ]; then
    g=$(running_games)
    [ -z "$g" ] && { echo "no DayZ client running"; exit 0; }
    echo "$g" | cut -c1-120; exit 1
fi
[ -n "$cmd" ] && [ -n "$state" ] || { sed -n "2,13p" "$0" >&2; exit 2; }
no_newline "$state"
shift 2
# Resolve state without creating it yet (for start's pre-scan).
case $state in /*) _abs=$state ;; *) _abs=$(pwd -P)/$state ;; esac
_work=$_abs; _suffix=
while [ ! -d "$_work" ]; do _b=$(basename "$_work"); _suffix=/$_b$_suffix; _p=$(dirname "$_work"); [ "$_p" != "$_work" ] || break; _work=$_p; done
if [ -d "$_work" ]; then _anc=$(cd "$_work" && pwd -P); if [ "$_anc" = / ]; then _resolved=$_suffix; else _resolved=$_anc$_suffix; fi; [ -n "$_resolved" ] || _resolved=/; else _resolved=$_abs; fi
no_newline "$_resolved"

if [ "$cmd" = start ]; then
    _alive_rc=0; state_launcher_alive "$_resolved" || _alive_rc=$?
    if [ "$_alive_rc" != 1 ]; then die "state $_resolved still has a running sway or launcher; run stop first or wait"; fi
    if [ -e "$_resolved/sway.pid" ] || [ -e "$_resolved/sway.identity" ] || [ -e "$_resolved/sway.cancel" ]; then
        echo "dayz-client-headless: removing stale sway files in $_resolved" >&2
        rm -f "$_resolved/sway.pid" "$_resolved/sway.identity" "$_resolved/sway.cancel"
    fi
fi
mkdir -p "$state"
state=$(cd "$state" && pwd -P)
no_newline "$state"

case "$cmd" in
start)
    g=$(running_games)
    if [ -n "$g" ]; then echo "a DayZ client is already running; one game at a time. Stop it first:" >&2; echo "$g" | cut -c1-120 >&2; exit 1; fi
    command -v sway >/dev/null 2>&1 || die "sway is needed for headless runs"
    command -v setsid >/dev/null 2>&1 || die "setsid is needed for headless runs"
    case $RES in *[!0-9x]*|*[!0-9]x*|*x*[!0-9]*|'') die "RES must match <width>x<height>" ;; esac
    case $RES in [0-9]*x[0-9]*) ;; *) die "RES must match <width>x<height>" ;; esac
    game=$STEAM_ROOT/steamapps/common/$dir
    [ -f "$game/DayZ_x64.exe" ] || { echo "no DayZ client in $game" >&2; exit 1; }
    tool=$STEAM_ROOT/compatibilitytools.d/$PROTON
    [ -d "$tool" ] || tool=$STEAM_ROOT/steamapps/common/$PROTON
    [ -d "$tool" ] || { echo "Proton tool '$PROTON' not found (set PROTON=)" >&2; exit 1; }
    no_newline "$STEAM_ROOT"; no_newline "$game"; no_newline "$tool"
    : > "$state/args"
    for a in -nolauncher -skipintro -window -nosplash -noPause "$@"; do no_newline "$a"; printf '%s\n' "$a" >> "$state/args"; done
    {
        printf 'STATE=%s\n' "$(sh_quote "$state")"
        printf 'GAME=%s\n' "$(sh_quote "$game")"
        printf 'TOOL=%s\n' "$(sh_quote "$tool")"
        printf 'STEAM_ROOT=%s\n' "$(sh_quote "$STEAM_ROOT")"
        printf 'APP=%s\n' "$(sh_quote "$app")"
    } > "$state/env"
    cat > "$state/game.sh" <<'EOS'
#!/bin/sh
cd "$(dirname "$0")" || exit 1
. ./env
echo "$WAYLAND_DISPLAY" > "$STATE/wayland-display"
export STEAM_COMPAT_DATA_PATH="$STEAM_ROOT/steamapps/compatdata/$APP"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT"
export STEAM_COMPAT_INSTALL_PATH="$GAME"
export STEAM_COMPAT_APP_ID=$APP SteamAppId=$APP SteamGameId=$APP
export PROTON_ENABLE_WAYLAND=1
export PROTON_BATTLEYE_RUNTIME="$STEAM_ROOT/steamapps/common/Proton BattlEye Runtime"
cd "$GAME" || exit 1
set --
while IFS= read -r a; do set -- "$@" "$a"; done < "$STATE/args"
exec "$STEAM_ROOT/steamapps/common/SteamLinuxRuntime_4/_v2-entry-point" --verb=run -- "$TOOL/proton" run "$GAME/DayZ_x64.exe" "$@"
EOS
    chmod +x "$state/game.sh"
    {
        printf 'output HEADLESS-1 resolution %s position 0 0\n' "$RES"
        printf 'xwayland enable\n'
        printf 'for_window [app_id="dayz_x64.exe"] fullscreen enable\n'
        printf 'exec ./game.sh > game.log 2>&1\n'
    } > "$state/sway.conf"
    rm -f "$state/wayland-display"
    ( cd "$state" && WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 setsid sh -c '[ ! -e "$1/sway.cancel" ] || exit 0; echo $$ > "$1/sway.pid"; if [ -e "$1/sway.cancel" ]; then rm -f "$1/sway.pid"; exit 0; fi; exec sway -c "$1/sway.conf"' sh "$state" > "$state/sway.log" 2>&1 & )
    _wait=${DAYZ_CLIENT_START_WAIT_TENTHS:-50}
    case $_wait in ''|*[!0-9]*) die "DAYZ_CLIENT_START_WAIT_TENTHS must be a non-negative integer" ;; esac
    _i=0; _ready=0; pid=
    while [ "$_i" -lt "$_wait" ]; do
        sleep 0.1; _i=$((_i + 1))
        if [ -s "$state/sway.pid" ]; then
            pid=$(cat "$state/sway.pid" 2>/dev/null) || pid=
            case $pid in ''|*[!0-9]*) pid= ;; esac
            if [ -n "$pid" ] && [ -d "/proc/$pid" ]; then
                _comm=$(cat "/proc/$pid/comm" 2>/dev/null) || _comm=
                if [ "$_comm" = sway ] && sway_cmdline_matches "$pid" "$state"; then _ready=1; break; fi
            fi
        fi
    done
    if [ "$_ready" != 1 ]; then failed_start_cleanup "$state"; die "sway did not start in $state (see $state/sway.log)"; fi
    _start=$(proc_starttime "$pid") || { failed_start_cleanup "$state"; die "sway did not stay up (see $state/sway.log)"; }
    { printf '%s\n' "$_start"; cat "/proc/$pid/cmdline"; } > "$state/sway.identity"
    rm -f "$state/sway.cancel"
    echo "sway pid $pid, state in $state"
    ;;
shot)
    [ -s "$state/wayland-display" ] || { echo "no session in $state" >&2; exit 1; }
    out=${1:?usage: shot <state-dir> <out.png>}
    WAYLAND_DISPLAY=$(cat "$state/wayland-display") grim "$out"
    ;;
stop)
    pid=$(cat "$state/sway.pid" 2>/dev/null || true)
    [ -n "$pid" ] || { echo "no session in $state" >&2; exit 1; }
    case $pid in ''|*[!0-9]*)
        echo "dayz-client-headless: sway pid in $state is not a plain decimal; not signalling it" >&2
        rm -f "$state/sway.pid" "$state/sway.identity"; exit 0 ;;
    esac
    if ! sway_identity_ok "$pid" "$state"; then
        echo "dayz-client-headless: the sway in $state is not verified as this session's (stale or foreign pid $pid); not signalling it" >&2
        rm -f "$state/sway.pid" "$state/sway.identity"
        exit 0
    fi
    kill "$pid" 2>/dev/null || true
    rm -f "$state/sway.pid" "$state/sway.identity"
    ;;
*)
    echo "unknown command: $cmd" >&2; exit 2;;
esac
