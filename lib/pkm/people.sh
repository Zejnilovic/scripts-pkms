# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/people.sh: whose move it is. (for <who>) on a task or a question names who does it or decides: a link, such
# as (for [[jane-doe]]), or the name of a writer of a shared vault, such as (for sam). A task without one on a writer's
# day page is that writer's. Used by tasks --for, the close's == for and check. Sourced by bin/pkm. Defines functions only.

# for_index <names file> <out>: name<TAB>path<TAB>title for each name in the file, resolved as a link is (path and
# title are empty when it names no note).
for_index() {
  local tab
  tab=$(printf '\t')
  : > "$2"
  [ -s "$1" ] || return 0
  LC_ALL=C sort -u "$1" > "$tmp/fi-names"
  link_index "$tmp/fi-index"
  link_slugs "$tmp/fi-names" "$tmp/fi-slugs"
  link_resolve "$tmp/fi-index" "$tmp/fi-slugs" "$tmp/fi-resolved"
  awk -F "$tab" -v OFS="$tab" '
    FILENAME == ARGV[1] { title[$1] = $2; next }
    { p = ($2 == "dead") ? "" : $3; print $1, p, (p != "" && (p in title)) ? title[p] : "" }
  ' "$(cache_dir)/notes.tsv" "$tmp/fi-resolved" > "$2"
}

# for_records: one line per task, question or other line that is someone's, fields separated by the unit separator:
# 1 path, 2 line, 3 kind (task, question, or other: an event or an entry that isn't a question), 4 state of a task,
# 5 key (w:<writer>, n:<path of the note>, or d:<name> for a link to no note), 6 who (the writer's name with a capital,
# the note's title, or the name), 7 assigned (1 with a (for …); 0 for a task on a writer's page without one), 8 the day
# page's date, 9 text. A question is an entry whose text, without its markers, ends with "?".
for_records() {
  local US tab
  US=$(printf '\037')
  tab=$(printf '\t')
  index_ensure
  line_records no > "$tmp/for-lines"
  awk -F "$US" "$(awk_markers)$(awk_links_in)"'
    { v = mval($5, "for"); if (v ~ /^\[\[/ && targets(v, t) > 0) print t[1] }
  ' "$tmp/for-lines" > "$tmp/for-targets"
  for_index "$tmp/for-targets" "$tmp/for-index"
  awk -F "$US" -v OFS="$US" -v tab="$tab" "$(awk_markers)$(awk_links_in)$(awk_plain)"'
    function cap(s) { return toupper(substr(s, 1, 1)) substr(s, 2) }
    FILENAME == ARGV[1] { split($0, f, tab); path[f[1]] = f[2]; title[f[1]] = f[3]; next }
    {
      kind = $3; v = mval($5, "for"); key = ""; who = ""; assigned = 0
      if (kind == "entry" || kind == "event") {
        q = plain_unmark($10); sub(/[ \t]+$/, "", q)
        kind = (kind == "entry" && q ~ /\?$/) ? "question" : "other"
      }
      if (v != "") {
        assigned = 1
        if (v ~ /^\[\[/ && targets(v, t) > 0) {
          n = t[1]
          if (path[n] != "") { key = "n:" path[n]; who = (title[n] != "") ? title[n] : n }
          else { key = "d:" tolower(n); who = n }
        } else { sub(/[ \t]+$/, "", v); key = "w:" tolower(v); who = cap(tolower(v)) }
      } else if (kind == "task" && $7 != "") { key = "w:" $7; who = cap($7) }
      if (key != "") print $1, $2, kind, $4, key, who, assigned, $6, $10
    }
  ' "$tmp/for-index" "$tmp/for-lines"
}

# for_key <who>: the key of a name typed on the command line: w:<writer> for a writer of the vault, else n:<path> of
# the note it names. Fails when it names neither.
for_key() {
  local who tab
  tab=$(printf '\t')
  who=$1; who=${who#\[\[}; who=${who%\]\]}
  vault_writers
  case " $PKM_WRITERS " in *" $(lowercase "$who") "*) printf 'w:%s\n' "$(lowercase "$who")"; return 0 ;; esac
  index_ensure
  printf '%s\n' "$who" > "$tmp/fk-name"
  for_index "$tmp/fk-name" "$tmp/fk-index"
  awk -F "$tab" '$2 != "" { print "n:" $2; found = 1 } END { exit !found }' "$tmp/fk-index"
}

# for_problems: the check problems of (for …): one on a line that is neither a task nor a question.
for_problems() {
  local US
  US=$(printf '\037')
  for_records | awk -F "$US" '$3 == "other" && $7 == 1 {
    print "- " $1 ":" $2 ": (for …) belongs on a task or a question: it says whose move it is"
  }'
}
