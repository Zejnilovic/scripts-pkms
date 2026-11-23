# shellcheck shell=bash
# lib/pkm/cmd/find.sh: pkm find: the lines of the vault that have every word given, in any order, as path:line: text.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_find() {
  local live=no words="" first insensitive flag archive
  while [ $# -gt 0 ]; do
    case $1 in
      --live) live=yes; shift ;;
      *) words="$words$1
"; shift ;;
    esac
  done
  if [ -z "$words" ]; then
    # On a terminal, the words are asked for (ask.sh).
    need_answer "Usage: pkm find [--live] <word> [<word>...]"
    ask_text "Find: "
    words=$(printf '%s\n' "$answer" | tr -s '[:blank:]' '\n' | grep -v '^$')
    words="$words
"
  fi
  first=$(printf '%s' "$words" | head -n 1)
  # Smart case: lowercase words match any case; a word with a capital letter matches exactly.
  case $words in
    *[A-Z]*) insensitive=no; flag=-s ;;
    *) insensitive=yes; flag=-i ;;
  esac
  archive=yes; [ "$live" = no ] || archive=no
  # ripgrep finds the first word; the awk checks every word on the line. The archive is included unless --live.
  vault_rg "$archive" no -tmd --no-heading --with-filename --line-number "$flag" -F -e "$first" . > "$tmp/find-hits" || true
  WORDS=$words INSENSITIVE=$insensitive awk '
    BEGIN {
      n = split(ENVIRON["WORDS"], w, "\n"); ci = ENVIRON["INSENSITIVE"] == "yes"; k = 0
      for (i = 1; i <= n; i++) if (w[i] != "") { k++; need[k] = ci ? tolower(w[i]) : w[i] }
    }
    {
      if (!match($0, /^[^:]+:[0-9]+:/)) next
      head = substr($0, 1, RLENGTH - 1); text = substr($0, RLENGTH + 1)
      sub(/^\.\//, "", head)
      if (head ~ /^(AGENTS|CLAUDE)\.md:/) next
      cmp = ci ? tolower(text) : text
      for (i = 1; i <= k; i++) if (index(cmp, need[i]) == 0) next
      print head ": " text
      hits++
    }
    END { exit hits ? 0 : 1 }
  ' "$tmp/find-hits"
}
