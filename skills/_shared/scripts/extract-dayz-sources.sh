#!/usr/bin/env bash
# Source: bzed/dayz-dev-plugin 6112ac5, contributed to this Pack under its MIT licence by its author.
# Extract the code files (scripts, configs) of the installed vanilla game PBOs with dayzmake.
#
# usage: extract-dayz-sources.sh [--force] <DayZ-install-dir | mod-dir> <out-dir>
#   e.g. extract-dayz-sources.sh ~/.steam/debian-installation/steamapps/common/DayZ /var/tmp/dayz-sources
#   a Workshop mod dir (steamapps/workshop/content/221100/<id>, with an addons/ folder) works the same way
#   --force allows replacing a non-empty <out-dir> that has no pbo-map.tsv (not an earlier extraction). [EXACT][CLAIM-EXTRACT-FORCE]
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
# Extraction goes to a staging directory next to <out-dir> and is promoted only on complete success,
# so a re-extraction after a game update drops removed files and never duplicates pbo-map.tsv rows.
set -eu
force=0
if [ "${1:-}" = "--force" ]; then force=1; shift; fi
[ $# -eq 2 ] || { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
install=$1 out=$2
DZPBO=${DAYZMAKE:-}
if [ -z "$DZPBO" ]; then
  for c in dayzmake armake2; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -h 2>&1 | grep -q -- --proton-binarize; then DZPBO=$c; break; fi
  done
fi
[ -n "$DZPBO" ] || { echo "dayzmake not found on PATH (upstream armake2 will not do: bzed's fork has --proton-binarize)" >&2; exit 1; }
[ "$DZPBO" = dayzmake ] || echo "note: using $DZPBO; dayzmake >= 1.0.0 is recommended (the pre-rename armake2 binary may have bugs)" >&2
[ -d "$install" ] || { echo "$install is not a directory" >&2; exit 1; }

# Interrupted promotion from an earlier run: refuse and name the recovery.
for old in "$out".old.*; do
  [ -e "$old" ] || continue
  echo "error: a previous promotion was interrupted; recover with: mv -- $(printf '%q' "$old") $(printf '%q' "$out")" >&2
  exit 1
done
if [ -e "$out" ] && [ ! -f "$out/pbo-map.tsv" ] && [ "$force" != 1 ]; then
  if [ -d "$out" ] && [ -n "$(ls -A "$out" 2>/dev/null)" ]; then
    echo "error: $out is non-empty and has no pbo-map.tsv (not an earlier extraction); refusing to replace it (use --force to override)" >&2; exit 1
  fi
  if [ ! -d "$out" ]; then
    echo "error: $out exists and is not an earlier extraction; refusing to replace it (use --force to override)" >&2; exit 1
  fi
fi

out_parent=$(dirname "$out")
mkdir -p "$out_parent"
lock="$out.lock"
if ! mkdir "$lock" 2>/dev/null; then echo "error: another extraction is running (lock $lock exists)" >&2; exit 1; fi
staging="$out.new.$$"
tmp=$(mktemp -d /var/tmp/dayz-extract.XXXXXX)
cleanup() { rm -rf "$tmp"; rm -rf "$lock"; }
trap cleanup EXIT
mkdir -p "$staging"

failed=0
note_fail() { echo "error: $*" >&2; failed=1; }

# valid_name <name-after-backslash-conversion>: reject empty, absolute, drive, .. segment, controls.
valid_name() {
  local s=$1
  [ -n "$s" ] || return 1
  case $s in /*|[A-Za-z]:*) return 1 ;; esac
  case "/$s/" in */../*) return 1 ;; esac
  case $s in */) return 1 ;; esac
  if [[ $s =~ [[:cntrl:]] ]]; then return 1; fi
  return 0
}
# dest_ok <dest>: resolved path under staging and no symlink on dest or any ancestor under staging.
dest_ok() {
  local dest=$1 resolved staging_resolved p
  staging_resolved=$(realpath -m "$staging")
  resolved=$(realpath -m "$dest")
  case $resolved in "$staging_resolved"/*) ;; *) return 1 ;; esac
  p=$dest
  while [ "$p" != "$staging" ] && [ "$p" != "/" ]; do
    if [ -L "$p" ]; then return 1; fi
    p=$(dirname "$p")
  done
  return 0
}

: > "$staging/pbo-map.tsv"
while IFS= read -r -d '' dir; do
  while IFS= read -r -d '' pbo; do
    if ! "$DZPBO" inspect "$pbo" > "$tmp/list" 2>/dev/null; then echo "skip (unreadable): $pbo" >&2; failed=1; continue; fi
    prefix=$(sed -n 's/^- prefix=//p' "$tmp/list" | tr -d '\r' | tr '\\' '/')
    [ -n "$prefix" ] || prefix=$(basename "$pbo" .pbo)
    if ! valid_name "$prefix"; then note_fail "invalid PBO prefix '$prefix' in $pbo; skipping PBO"; continue; fi
    # Validate listing structure; parse rows after ====.
    : > "$tmp/want"
    listing_bad=0
    seen_rows=0
    while IFS= read -r row || [ -n "$row" ]; do
      if [ "$seen_rows" = 0 ]; then case $row in ====*) seen_rows=1 ;; *) continue ;; esac; continue; fi
      row=${row%$'\r'}
      [ -n "$row" ] || continue
      if [[ $row =~ ^(.*)[[:space:]]+([^[:space:]]+)[[:space:]]+([0-9]+)[[:space:]]+([0-9]+)[[:space:]]*$ ]]; then
        inner_raw=${BASH_REMATCH[1]}
        orig_size=${BASH_REMATCH[3]}
        # trim trailing whitespace of inner
        inner_raw=${inner_raw%"${inner_raw##*[![:space:]]}"}
        printf '%s\t%s\n' "$orig_size" "$inner_raw" >> "$tmp/want"
      else
        listing_bad=1
      fi
    done < "$tmp/list"
    if [ "$listing_bad" = 1 ]; then note_fail "invalid listing structure in $pbo; skipping PBO"; continue; fi
    n=0
    pbo_failed=0
    while IFS=$'\t' read -r orig_size inner; do
      rel=$(printf '%s' "$inner" | tr '\\' '/')
      lower=${rel,,}
      case $lower in
        *.c|*.cpp|*.h|*.hpp|*.inc|*.json|*.cfg|*.txt|*config.bin) ;;
        *) continue ;;
      esac
      if ! valid_name "$rel"; then note_fail "invalid entry name '$inner' in $pbo; skipping entry"; pbo_failed=1; continue; fi
      is_config=0
      dest_rel=$rel
      case $lower in *config.bin) is_config=1; dest_rel=${rel%.[bB][iI][nN]}.cpp; dest_rel=${rel%.*}.cpp ;; esac
      dest="$staging/$prefix/$dest_rel"
      if ! dest_ok "$(dirname "$dest")"; then note_fail "destination escapes staging for '$inner' in $pbo"; pbo_failed=1; continue; fi
      if [ -L "$dest" ]; then note_fail "destination is a symlink for '$inner' in $pbo"; pbo_failed=1; continue; fi
      mkdir -p "$(dirname "$dest")"
      if [ -L "$dest" ]; then note_fail "destination is a symlink for '$inner' in $pbo"; pbo_failed=1; continue; fi
      if [ "$is_config" = 1 ]; then
        rm -f "$tmp/config.bin"
        cat_out=$("$DZPBO" cat "$pbo" "$inner" "$tmp/config.bin" 2>&1) || cat_out="$cat_out"
        if [ ! -f "$tmp/config.bin" ] || { [ "$orig_size" != 0 ] && [ ! -s "$tmp/config.bin" ]; } || case $cat_out in *"not found"*) true;; *) false;; esac; then
          note_fail "cat failed: $pbo $inner"; pbo_failed=1; continue
        fi
        if ! "$DZPBO" derapify -f "$tmp/config.bin" "$dest" >/dev/null 2>&1 || [ ! -f "$dest" ]; then
          note_fail "derapify failed: $pbo $inner"; pbo_failed=1; continue
        fi
      else
        cat_out=$("$DZPBO" cat "$pbo" "$inner" "$dest" 2>&1) || cat_out="$cat_out"
        if case $cat_out in *"not found"*) true;; *) false;; esac || [ ! -f "$dest" ] || { [ "$orig_size" != 0 ] && [ ! -s "$dest" ]; }; then
          note_fail "cat failed: $pbo $inner"; pbo_failed=1; continue
        fi
      fi
      n=$((n + 1))
    done < "$tmp/want"
    if [ "$pbo_failed" = 1 ]; then failed=1; fi
    [ "$n" -gt 0 ] || continue
    echo "$n files  $prefix  <- ${pbo#"$install"/}"
    printf '%s\t%s\n' "$prefix" "${pbo#"$install"/}" >> "$staging/pbo-map.tsv"
  done < <(find "$dir" -maxdepth 1 -type f -name '*.pbo' -print0 | sort -z)
done < <(find "$install" -maxdepth 2 -type d \( -name dta -o -iname addons \) -print0 | sort -z)

if [ "$failed" != 0 ]; then
  echo "error: extraction failed; partial staging kept at $staging (nothing was promoted)" >&2
  # Keep staging: disable its removal (it is only removed on promotion below); trap only cleans tmp/lock.
  exit 1
fi

# Promote: move old aside, rename new in, then remove old.
old_backup=
if [ -e "$out" ] || [ -L "$out" ]; then
  old_backup="$out.old.$$"
  if ! mv -- "$out" "$old_backup"; then echo "error: could not move $out aside; leaving it intact" >&2; exit 1; fi
fi
if ! mv -- "$staging" "$out"; then
  echo "error: could not promote $staging to $out" >&2
  if [ -n "$old_backup" ]; then mv -- "$old_backup" "$out" || echo "error: restore failed; old tree is at $old_backup" >&2; fi
  exit 1
fi
if [ -n "$old_backup" ]; then rm -rf "$old_backup"; fi
