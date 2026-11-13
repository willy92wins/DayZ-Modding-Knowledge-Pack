#!/bin/sh
# Source: bzed/dayz-dev-plugin 6112ac5, contributed to this Pack under its MIT licence by its author.
# Print N random ports (default 3) for a DayZ test server: game, Steam query, RCon.
#
# Each port is free for both UDP and TCP right now, is not a DayZ/Steam default
# (2302-2306, 27015-27016), and is at least 10 away from the others, because the server
# also uses ports next to the game port.
#
# Usage: free-ports.sh [N]      e.g.  set -- $(free-ports.sh 3); GAME=$1 QUERY=$2 RCON=$3
set -eu
exec python3 - "${1:-3}" <<'PY'
import random, socket, sys

want = int(sys.argv[1])
avoid = set(range(2300, 2310)) | {27015, 27016, 27017}
picked = []

def free(p):
    for kind in (socket.SOCK_DGRAM, socket.SOCK_STREAM):
        s = socket.socket(socket.AF_INET, kind)
        try:
            s.bind(("0.0.0.0", p))
        except OSError:
            return False
        finally:
            s.close()
    return True

while len(picked) < want:
    p = random.randint(20000, 59000)
    if p in avoid or any(abs(p - q) < 10 for q in picked) or not free(p):
        continue
    picked.append(p)
print(*picked)
PY
