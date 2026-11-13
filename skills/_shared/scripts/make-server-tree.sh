#!/bin/sh
# Source: bzed/dayz-dev-plugin 6112ac5, contributed to this Pack under its MIT licence by its author.
# Build (or refresh) a private DayZ Server directory tree that symlinks into the Steam install.
#
# The Steam install is never written to. Everything the server or you write lands in the tree:
#   <tree>/serverDZ.cfg          copied once, yours to edit
#   <tree>/profiles/             use as -profiles=profiles
#   <tree>/mpmissions/<m>/       real directories with per-file symlinks, so the server's
#                                storage_1/ persistence is written here, not into Steam
#   <tree>/keys/, battleye/      real directories with per-file symlinks (add your own .bikey)
#   <tree>/@Mod                  your mods: symlinks to builds or workshop items (not created here)
#   everything else              one symlink per top-level entry of the Steam install
#
# To edit a Steam-provided file, replace its symlink with a copy:
#   cp --remove-destination "$(readlink <tree>/mpmissions/<m>/init.c)" <tree>/mpmissions/<m>/init.c
# Re-running refreshes the symlinks after a Steam update; real files in the tree are kept.
#
# Usage: make-server-tree.sh <tree> [<steam DayZServer dir>]   (default: find-dayzserver.sh)
set -eu

[ $# -ge 1 ] || { echo "usage: $0 <tree> [<steam DayZServer dir>]" >&2; exit 2; }
tree=$1
src=${2:-$("$(dirname "$0")/find-dayzserver.sh")}
src=$(cd "$src" && pwd -P)
mkdir -p "$tree"
tree=$(cd "$tree" && pwd -P)
case "$tree/" in "$src"/*) echo "error: the tree must be outside the Steam install" >&2; exit 2;; esac

# link_entry SRC DST: symlink DST -> SRC unless DST is a real file/dir of ours.
link_entry() {
    if [ -L "$2" ] || [ ! -e "$2" ]; then
        ln -sfn "$1" "$2"
    fi
}

# link_contents SRCDIR DSTDIR: real DSTDIR, one symlink per entry of SRCDIR.
link_contents() {
    [ -L "$2" ] && rm "$2"
    mkdir -p "$2"
    for f in "$1"/* "$1"/.[!.]*; do
        [ -e "$f" ] || [ -L "$f" ] || continue
        case "${f##*/}" in storage_*) continue;; esac   # persistence stays per tree
        link_entry "$f" "$2/${f##*/}"
    done
}

for f in "$src"/*; do
    name=${f##*/}
    case "$name" in
        core|core.*|@*) continue ;;                      # crash dumps, mods: not the server's
        serverDZ.cfg) [ -e "$tree/$name" ] || cp "$f" "$tree/$name" ;;
        keys|battleye) link_contents "$f" "$tree/$name" ;;
        mpmissions)
            mkdir -p "$tree/mpmissions"
            for m in "$f"/*/; do
                m=${m%/}
                link_contents "$m" "$tree/mpmissions/${m##*/}"
            done ;;
        *) link_entry "$f" "$tree/$name" ;;
    esac
done
mkdir -p "$tree/profiles"

# Drop symlinks whose target Steam removed in an update.
find "$tree" -path "$tree/profiles" -prune -o -type l ! -exec test -e {} \; -print | while IFS= read -r l; do
    case "$(readlink "$l")" in "$src"/*) rm "$l" ;; esac
done

echo "$tree"
