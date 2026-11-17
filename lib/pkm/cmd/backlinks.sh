# shellcheck shell=bash
# lib/pkm/cmd/backlinks.sh: pkm backlinks: every line that links a note, by its name, slug or alias, archive included.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_backlinks() {
  local name="" since="" target status dest
  while [ $# -gt 0 ]; do
    case $1 in
      --since) { [ $# -ge 2 ] && is_date "$2"; } || die 2 "--since needs a date YYYY-MM-DD"; since=$2; shift 2 ;;
      *) [ -z "$name" ] || die 2 "Usage: pkm backlinks <name> [--since YYYY-MM-DD]"; name=$1; shift ;;
    esac
  done
  [ -n "$name" ] || die 2 "Usage: pkm backlinks <name> [--since YYYY-MM-DD]"
  target=${name#\[\[}; target=${target%\]\]}; target=${target%%|*}; target=${target%%#*}; target=${target##*/}
  printf '%s\n' "$target" > "$tmp/backlinks-target"
  link_build "$tmp/backlinks-target"
  dest=$(awk -F '\t' -v t="$target" '$1 == t { print $3; exit }' "$tmp/lb-resolved")
  status=$(awk -F '\t' -v t="$target" '$1 == t { print $2; exit }' "$tmp/lb-resolved")
  # A name with no note yet still has backlinks: the lines that write it, as the name is written.
  if [ "$status" = dead ] || [ -z "$dest" ]; then dest=""; fi
  # The lines that link the note, then their text, read once from each file that has one.
  awk -F "$(printf '\t')" -v OFS="$(printf '\t')" -v dest="$dest" -v target="$target" -v since="$since" '
    (dest != "" && $6 == dest) || (dest == "" && $3 == target) {
      b = $1; sub(/.*\//, "", b)
      if (since != "" && b ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/ && substr(b, 1, 10) < since) next
      print $1, $2
    }
  ' "$tmp/lb-links" > "$tmp/bl-rows"
  [ -s "$tmp/bl-rows" ] || die 1 "No note or link named $target."
  ROWS="$tmp/bl-rows" awk '
    BEGIN {
      while ((getline r < ENVIRON["ROWS"]) > 0) {
        split(r, f, "\t"); key = f[1] SUBSEP f[2]
        if (!(key in want)) order[++n] = key
        want[key] = 1
        if (!(f[1] in seen)) { seen[f[1]] = 1; files[++nf] = f[1] }
      }
      for (k = 1; k <= nf; k++) {
        ln = 0
        while ((getline l < files[k]) > 0) { ln++; sub(/\r$/, "", l); if ((files[k] SUBSEP ln) in want) text[files[k] SUBSEP ln] = l }
        close(files[k])
      }
      for (i = 1; i <= n; i++) if (order[i] in text) {
        split(order[i], f, SUBSEP); t = text[order[i]]; gsub(/\t/, " ", t)
        print f[1] ":" f[2] ": " t
      }
    }
  ' /dev/null
}
