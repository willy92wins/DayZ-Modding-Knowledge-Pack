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
set -eu

app=221100 dir=DayZ                       # stable client
if [ "${1:-}" = "-e" ]; then app=1024020 dir="DayZ Exp"; shift; fi   # experimental client

STEAM_ROOT=${STEAM_ROOT:-$HOME/.steam/debian-installation}
PROTON=${PROTON:-GE-Proton11-1}
RES=${RES:-1280x720}

# Any DayZ client, stable or experimental, ours or the user's own. The [D] keeps grep out of its own match.
running_games() { ps -eo pid,args | grep '[D]ayZ_x64\.exe' || true; }

cmd=${1:-}; state=${2:-}
if [ "$cmd" = status ]; then
    g=$(running_games)
    [ -z "$g" ] && { echo "no DayZ client running"; exit 0; }
    echo "$g" | cut -c1-120; exit 1
fi
[ -n "$cmd" ] && [ -n "$state" ] || { sed -n "2,13p" "$0" >&2; exit 2; }
shift 2
mkdir -p "$state"
state=$(cd "$state" && pwd -P)

case "$cmd" in
start)
    # One game at a time: a Steam account can run only one game, and two clients on one machine
    # fight over the GPU, the prefix and the Steam connection. Refuse instead of starting a second.
    g=$(running_games)
    if [ -n "$g" ]; then
        echo "a DayZ client is already running; one game at a time. Stop it first:" >&2
        echo "$g" | cut -c1-120 >&2; exit 1
    fi
    game=$STEAM_ROOT/steamapps/common/$dir
    [ -f "$game/DayZ_x64.exe" ] || { echo "no DayZ client in $game" >&2; exit 1; }
    tool=$STEAM_ROOT/compatibilitytools.d/$PROTON
    [ -d "$tool" ] || tool=$STEAM_ROOT/steamapps/common/$PROTON
    [ -d "$tool" ] || { echo "Proton tool '$PROTON' not found (set PROTON=)" >&2; exit 1; }

    # DayZ args, one per line, so a ';' in -mod=@a;@b never reaches a shell or sway's parser.
    : > "$state/args"
    for a in -nolauncher -skipintro -window -nosplash -noPause "$@"; do printf '%s\n' "$a" >> "$state/args"; done

    cat > "$state/game.sh" <<EOF
#!/bin/sh
echo "\$WAYLAND_DISPLAY" > "$state/wayland-display"
export STEAM_COMPAT_DATA_PATH="$STEAM_ROOT/steamapps/compatdata/$app"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT"
export STEAM_COMPAT_INSTALL_PATH="$game"
export STEAM_COMPAT_APP_ID=$app SteamAppId=$app SteamGameId=$app
export PROTON_ENABLE_WAYLAND=1
export PROTON_BATTLEYE_RUNTIME="$STEAM_ROOT/steamapps/common/Proton BattlEye Runtime"
cd "$game"
set --
while IFS= read -r a; do set -- "\$@" "\$a"; done < "$state/args"
exec "$STEAM_ROOT/steamapps/common/SteamLinuxRuntime_4/_v2-entry-point" --verb=run -- \\
    "$tool/proton" run "$game/DayZ_x64.exe" "\$@"
EOF
    chmod +x "$state/game.sh"
    cat > "$state/sway.conf" <<EOF
output HEADLESS-1 resolution $RES position 0 0
xwayland enable
for_window [app_id="dayz_x64.exe"] fullscreen enable
exec $state/game.sh > $state/game.log 2>&1
EOF
    rm -f "$state/wayland-display"
    WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 \
        nohup sway -c "$state/sway.conf" > "$state/sway.log" 2>&1 &
    echo $! > "$state/sway.pid"
    echo "sway pid $(cat "$state/sway.pid"), state in $state"
    ;;
shot)
    [ -s "$state/wayland-display" ] || { echo "no session in $state" >&2; exit 1; }
    out=${1:?usage: shot <state-dir> <out.png>}
    WAYLAND_DISPLAY=$(cat "$state/wayland-display") grim "$out"
    ;;
stop)
    # The game's main thread is called enfMain; take it down through the Wine tree of our sway.
    pid=$(cat "$state/sway.pid" 2>/dev/null || true)
    [ -n "$pid" ] || { echo "no session in $state" >&2; exit 1; }
    kill "$pid" 2>/dev/null || true      # sway exiting ends its clients, game included
    rm -f "$state/sway.pid"
    ;;
*)
    echo "unknown command: $cmd" >&2; exit 2;;
esac
