#!/usr/bin/env bash
# Source: bzed/dayz-dev-plugin 6112ac5, contributed to this Pack under its MIT licence by its author.
# Extract the code files (scripts, configs) of the installed vanilla game PBOs with dayzmake.
#
# usage: extract-dayz-sources.sh <DayZ-install-dir | mod-dir> <out-dir>
#   e.g. extract-dayz-sources.sh ~/.steam/debian-installation/steamapps/common/DayZ /var/tmp/dayz-sources
#   a Workshop mod dir (steamapps/workshop/content/221100/<id>, with an addons/ folder) works the same way
#
# Searches <install>/dta and <install>/Addons plus the DLC folders <install>/*/addons (case-insensitive).
# Workshop mods are symlinked into the install dir as @xxxx; find does not follow symlinks, so they are skipped.
# Only code is extracted: *.c *.cpp *.h *.hpp *.inc *.json *.cfg *.txt, and config.bin (derapified to config.cpp).
# Models, textures, sounds, layouts and shaders are never read. Files land in <out>/<pbo prefix>/<inner path>,
# e.g. prefix "scripts" -> <out>/scripts/3_Game/..., prefix "DZ\AI" -> <out>/DZ/AI/config.cpp.
# <out>/pbo-map.tsv lists "<prefix>\t<pbo path relative to the install dir>" for every PBO that yielded files
# (scripts/build-api-index.py reads it to tell `dayz-api.py src` which PBO holds a file).
# Needs dayzmake on PATH (>= 1.0.0 recommended). bzed's older armake2 fork (pre-rename, may have bugs) is accepted,
# upstream armake2 is not. Write <out-dir> below /var/tmp (/tmp can be a tmpfs and take up RAM), not below $HOME.
set -eu
[ $# -eq 2 ] || { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
install=$1 out=$2
DZPBO=${DAYZMAKE:-}
if [ -z "$DZPBO" ]; then
  # bzed's fork is the only usable one; it is recognised by --proton-binarize, whether the binary is called
  # dayzmake or armake2 (the fork's name before it was detached and renamed).
  for c in dayzmake armake2; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -h 2>&1 | grep -q -- --proton-binarize; then DZPBO=$c; break; fi
  done
fi
[ -n "$DZPBO" ] || { echo "dayzmake not found on PATH (upstream armake2 will not do: bzed's fork has --proton-binarize)" >&2; exit 1; }
[ "$DZPBO" = dayzmake ] || echo "note: using $DZPBO; dayzmake >= 1.0.0 is recommended (the pre-rename armake2 binary may have bugs)" >&2
[ -d "$install" ] || { echo "$install is not a directory" >&2; exit 1; }
mkdir -p "$out"
tmp=$(mktemp -d /var/tmp/dayz-extract.XXXXXX)
trap 'rm -rf "$tmp"' EXIT

find "$install" -maxdepth 2 -type d \( -name dta -o -iname addons \) -print0 | sort -z |
while IFS= read -r -d '' dir; do
  find "$dir" -maxdepth 1 -type f -name '*.pbo' -print0 | sort -z |
  while IFS= read -r -d '' pbo; do
    "$DZPBO" inspect "$pbo" > "$tmp/list" 2>/dev/null || { echo "skip (unreadable): $pbo" >&2; continue; }
    prefix=$(sed -n 's/^- prefix=//p' "$tmp/list" | tr -d '\r' | tr '\\' '/')
    [ -n "$prefix" ] || prefix=$(basename "$pbo" .pbo)
    # file rows: "<path>   <method> <orig> <packed>"; keep code files and config.bin
    sed -n '/^====/,$p' "$tmp/list" | sed 1d |
      sed -E 's/[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]*$//' |
      grep -iE '(\.(c|cpp|h|hpp|inc|json|cfg|txt)|(^|\\)config\.bin)$' > "$tmp/want" || true
    [ -s "$tmp/want" ] || continue
    n=0
    while IFS= read -r inner; do
      inner=${inner%$'\r'}
      rel=$(printf '%s' "$inner" | tr '\\' '/')
      dest="$out/$prefix/$rel"
      mkdir -p "$(dirname "$dest")"
      case $rel in
        *config.bin)
          rm -f "$tmp/config.bin"
          "$DZPBO" cat "$pbo" "$inner" "$tmp/config.bin" >/dev/null 2>&1 &&
            "$DZPBO" derapify -f "$tmp/config.bin" "${dest%.bin}.cpp" >/dev/null 2>&1 ||
            echo "derapify failed: $pbo $inner" >&2 ;;
        *) "$DZPBO" cat "$pbo" "$inner" "$dest" >/dev/null 2>&1 || echo "cat failed: $pbo $inner" >&2 ;;
      esac
      n=$((n + 1))
    done < "$tmp/want"
    echo "$n files  $prefix  <- ${pbo#"$install"/}"
    printf '%s\t%s\n' "$prefix" "${pbo#"$install"/}" >> "$out/pbo-map.tsv"
  done
done
