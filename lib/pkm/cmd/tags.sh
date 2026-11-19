# shellcheck shell=bash
# lib/pkm/cmd/tags.sh: pkm tags [--json]: every tag with its count, most used first, then by name; --json gives tag and
# count.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_tags() {
  local json=no arg
  for arg in "$@"; do
    case $arg in
      --json) json=yes ;;
      *) die 2 "Usage: pkm tags [--json]" ;;
    esac
  done
  [ "$json" = no ] || need_jq
  files no '*.md' > "$tmp/tag-files"
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  scan "$tmp/tag-files" '
    function add(t) { t = tolower(t); gsub(/^[ \t"\047]+|[ \t"\047]+$/, "", t); if (t != "") print t }
    FNR == 1 { fence = 0; in_tags = 0; front = ($0 == "---"); if (front) next }
    front {
      if ($0 == "---") { front = 0; next }
      if ($0 ~ /^tags:/) {
        v = $0; sub(/^tags:[ \t]*/, "", v); gsub(/[][]/, "", v); in_tags = 1
        n = split(v, parts, ","); for (i = 1; i <= n; i++) add(parts[i])
      } else if (in_tags && $0 ~ /^[ \t]+- /) { v = $0; sub(/^[ \t]+- /, "", v); add(v) }
      else in_tags = 0
      next
    }
    /^[ \t]*(```|~~~)/ { fence = !fence; next }
    fence || !index($0, "#") { next }
    {
      s = " " $0; gsub(/`[^`]*`/, "", s)
      while (match(s, /[ \t(]#[^ \t0-9#,.;:!?()][^ \t#,.;:!?()]*/)) { add(substr(s, RSTART + 2, RLENGTH - 2)); s = substr(s, RSTART + RLENGTH) }
    }
  ' | LC_ALL=C sort | uniq -c | awk '{ print $1, $2 }' | LC_ALL=C sort -k1,1nr -k2,2 > "$tmp/tags"
  if [ "$json" = no ]; then cat "$tmp/tags"; return 0; fi
  jq -R -c 'capture("^(?<count>[0-9]+) (?<tag>.*)$") | {tag: .tag, count: (.count | tonumber)}' "$tmp/tags"
}
