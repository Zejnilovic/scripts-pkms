# shellcheck shell=bash
# lib/pkm/sections.sh: the sections of a note, by its headings, for get, post and evidence, and the note a name means.
# A heading is a line of 1 to 6 '#' and a space; a line in frontmatter or a code fence is not one. A section runs from
# its heading to the next heading of the same or a higher level. Sourced by bin/pkm. Defines functions only.
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"

# section_bounds <file> <heading>: "first last" line numbers of the section (heading match in any case and at any level).
# last is the section's last non-blank line, so first and last are equal when the section is empty. Prints nothing when
# no heading matches.
section_bounds() {
  awk -v want="$(lowercase "$2")" '
    { sub(/\r$/, ""); if (NR == 1 && substr($0, 1, 3) == "\357\273\277") $0 = substr($0, 4); blank[NR] = ($0 ~ /^[ \t]*$/) }
    NR == 1 && $0 == "---" { front = 1; next }
    front { if ($0 == "---") front = 0; next }
    /^[ \t]*(```|~~~)/ { fence = !fence; next }
    fence { next }
    match($0, /^#+[ \t]/) {
      level = RLENGTH - 1
      if (level <= 6) {
        text = substr($0, RLENGTH + 1)
        sub(/[ \t]+#+[ \t]*$/, "", text); sub(/^[ \t]+/, "", text); sub(/[ \t]+$/, "", text)
        nh++; hl[nh] = NR; hv[nh] = level; ht[nh] = tolower(text)
      }
    }
    END {
      for (i = 1; i <= nh; i++) if (ht[i] == want) break
      if (i > nh) exit
      start = hl[i]; stop = NR + 1
      for (j = i + 1; j <= nh; j++) if (hv[j] <= hv[i]) { stop = hl[j]; break }
      last = start
      for (k = start + 1; k < stop; k++) if (!blank[k]) last = k
      print start, last
    }
  ' "$1"
}

# resolve_note <name>: the path of the note, attachment or alias the name points to, by the rules of pkm path. Prints
# nothing when no note has the name. Callers have run index_ensure.
resolve_note() {
  printf '%s\n' "$1" > "$tmp/rn-target"
  link_index "$tmp/rn-index"
  link_slugs "$tmp/rn-target" "$tmp/rn-slugs"
  link_resolve "$tmp/rn-index" "$tmp/rn-slugs" "$tmp/rn-resolved"
  awk -F '\t' -v t="$1" '$1 == t && $2 != "dead" { print $3; exit }' "$tmp/rn-resolved"
}

# note_for <name>: the file a name means: a path inside the vault (or with .md added), else the note the name resolves
# to. Prints nothing when there is none.
note_for() {
  case $1 in
    /*|../*|*/../*) ;;
    *) if [ -f "$1" ]; then printf '%s\n' "$1"; return 0; fi
       if [ -f "$1.md" ]; then printf '%s\n' "$1.md"; return 0; fi ;;
  esac
  resolve_note "$1"
}

# named_rows <name or vault path>: "type<TAB>path" for the note a name means (a name in the cache, as path resolves it, but
# not the aliases), or the note at a path in the vault, with or without .md. Callers have run index_ensure.
named_rows() {
  local name p
  name=${1%.md}
  case $1 in
    */*)
      p=${1#./}
      case $p in /*|../*|*/../*) return 0 ;; esac
      case $p in *.md) ;; *) p="$p.md" ;; esac
      awk -F "$(printf '\t')" -v OFS="$(printf '\t')" -v p="$p" '$3 == p && $2 != "attachment" { print $2, $3 }' "$(cache_dir)/names.tsv"
      return 0 ;;
  esac
  awk -F "$(printf '\t')" -v OFS="$(printf '\t')" -v n="$name" '$1 == n && $2 != "attachment" { print $2, $3 }' "$(cache_dir)/names.tsv"
}

# note_type <path>: the type a note has in the cache (day, close, source, person, ...). Callers have run index_ensure.
note_type() {
  awk -F "$(printf '\t')" -v p="$1" '$3 == p { print $2; exit }' "$(cache_dir)/names.tsv"
}
