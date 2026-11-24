# shellcheck shell=bash
# lib/pkm/cmd/check.sh: pkm check: broken links, duplicate names, secrets, merge conflicts and notices.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_check() {
  local urls=no arg
  for arg in "$@"; do
    case $arg in
      --urls) urls=yes ;;
      *) die 2 "pkm check has no option $arg: pkm help check lists its options." ;;
    esac
  done
  files yes '*.md' > "$tmp/notes"
  files yes '*' > "$tmp/all"
  : > "$tmp/problems"
  : > "$tmp/notices"

  # Two notes with one name are two things a link can't tell apart.
  sed -e 's|.*/||' -e 's|\.md$||' "$tmp/notes" | LC_ALL=C sort | uniq -d > "$tmp/duplicates"
  if [ -s "$tmp/duplicates" ]; then
    awk 'NR == FNR { dup[$0] = 1; next }
         { n = $0; sub(/.*\//, "", n); sub(/\.md$/, "", n); if (n in dup) paths[n] = paths[n] ", " $0 }
         END { for (n in paths) print "- duplicate name " n ": " substr(paths[n], 3) }' \
      "$tmp/duplicates" "$tmp/notes" | LC_ALL=C sort >> "$tmp/problems"
  fi

  # Links resolve by file name, slug or alias (lib/pkm/links.sh). A dead link is a problem; a link that works only
  # through its slug or alias is a notice, so the link can say the name in full. Code spans and fences are skipped.
  link_build ""
  awk -F '\t' '$5 == "dead" { print $3 }' "$tmp/lb-links" | LC_ALL=C sort -u > "$tmp/dead-targets"
  # A dead link whose file exists but is left out of the vault by .pkmignore says so, rather than only that it is dead.
  : > "$tmp/ignored-targets"
  while IFS= read -r t; do
    [ -n "$t" ] || continue
    find . -path './.*' -prune -o -type f \( -name "$t" -o -name "$t.md" \) -print 2>/dev/null \
      | sed 's|^\./||' > "$tmp/found"
    while IFS= read -r f; do
      if [ -n "$f" ] && ! grep -qxF -- "$f" "$tmp/all"; then echo "$t" >> "$tmp/ignored-targets"; break; fi
    done < "$tmp/found"
  done < "$tmp/dead-targets"
  awk -F '\t' -v ignored="$tmp/ignored-targets" -v dead_out="$tmp/dead-problems" -v notice_out="$tmp/link-notices" '
    BEGIN {
      while ((getline line < ignored) > 0) ignored_t[line] = 1
      close(ignored)
    }
    $5 == "dead" {
      msg = "- " $1 ":" $2 ": broken link [[" $3 "]]"
      if ($3 in ignored_t) msg = msg ": the file is in .pkmignore, so pkm leaves it out of the vault"
      print msg > dead_out
      next
    }
    $5 == "slug" || $5 == "alias" {
      d = $6; sub(/.*\//, "", d); sub(/\.md$/, "", d)
      print "- " $1 ":" $2 ": [[" $3 "]] works only in pkm, through the " $5 " of " d ": write [[" d "|" $3 "]]" > notice_out
    }
  ' "$tmp/lb-links"
  touch "$tmp/dead-problems" "$tmp/link-notices"
  cat "$tmp/dead-problems" >> "$tmp/problems"
  cat "$tmp/link-notices" >> "$tmp/notices"
  { check_part_of; check_items; } >> "$tmp/problems"
  if [ "$(config part_of_folders no)" = yes ]; then check_part_of_folders >> "$tmp/notices"; fi
  # Alias clashes: an alias on two notes leaves links to it unclear.
  awk -F '\t' '
    $1 == "A" { key = $2 SUBSEP $3; if (!(key in seen)) { seen[key] = 1; count[$2]++; paths[$2] = paths[$2] ", " $3 } }
    END { for (a in count) if (count[a] > 1) print "- alias " a " is on more than one note: " substr(paths[a], 3) }
  ' "$tmp/lb-index" | LC_ALL=C sort >> "$tmp/problems"
  # A file name that isn't a slug can't be reached by a link written from its words.
  awk -F '\t' '
    NR == FNR { slug[$1] = $2; next }
    $1 == "N" && ($2 in slug) && slug[$2] != $2 { print "- " $3 ": the file name isn'"'"'t a slug: name it " slug[$2] ".md" }
  ' "$tmp/lb-slugs" "$tmp/lb-index" | LC_ALL=C sort >> "$tmp/notices"

  # Secrets are checked on every line, code blocks included.
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  scan "$tmp/notes" "$(awk_secret)"'
    FNR == 1 { file = rel(FILENAME) }
    secret($0) { print "- " file ":" FNR ": looks like a secret: move it to a password manager, or mark the line pkm-ignore-secret" }
  ' -v q="'" >> "$tmp/problems"

  # Recall marks: a question ends with (recall YYYY-MM-DD <N>d), outside code and struck lines; a mark in a task box is a
  # task, not a question.
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  scan "$tmp/notes" "$(recall_awk)"'
    FNR == 1 { file = rel(FILENAME); fence = 0; front = 0 }
    FNR == 1 && $0 == "---" { front = 1; next }
    front { if ($0 == "---") front = 0; next }
    /^[ \t]*(```|~~~)/ { fence = !fence; next }
    fence { next }
    {
      c = $0; sub(/\r$/, "", c); gsub(/`[^`]*`/, "", c)
      if (index(c, "(recall") == 0) next
      t = c; sub(/^[ \t]*([-*+]|[0-9]+[.)])[ \t]+/, "", t)
      if (t ~ /^~~/) next
      if (c ~ /^[ \t]*[-*+][ \t]+\[.\]/) { print "- " file ":" FNR ": a recall mark belongs on a question, not in a task box: take the box out, or the mark"; next }
      if (!recall_parse(recall_inner(c))) print "- " file ":" FNR ": malformed recall mark: a question ends with (recall YYYY-MM-DD <N>d), such as (recall 2026-11-16 7d)"
    }
  ' >> "$tmp/problems"

  # A merge leaves conflict markers in notes and templates; people paste them into notes. Lines inside code
  # blocks are examples, not conflicts.
  {
    vault_files yes yes '*.md'
    for f in AGENTS.md CLAUDE.md; do [ ! -f "$f" ] || echo "$f"; done
  } | LC_ALL=C sort > "$tmp/conflict-files"
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  scan "$tmp/conflict-files" '
    FNR == 1 { file = rel(FILENAME); fence = 0 }
    /^[ \t]*(```|~~~)/ { fence = !fence; next }
    !fence && $0 ~ markers {
      print "- " file ":" FNR ": merge conflict, probably from a merge: keep one side and remove the <<<<<<<, ======= and >>>>>>> lines"
    }
  ' -v markers="$conflict_markers" >> "$tmp/problems"

  # A task marker that can't be read, or a relative date outside a day page, is a problem in the task's place. So is an
  # event that can't be read, or whose (every …), (until …) or (skip …) can't be used (docs/format.md, Events 6), and a
  # (for …) on a line that is neither a task nor a question.
  {
    task_records yes | awk -F "$(printf '\037')" '$11 != "" { print "- " $1 ":" $2 ": " $11 }'
    event_problems
    for_problems
  } >> "$tmp/problems"

  # Web addresses are checked only when asked (--urls): one GET per distinct address, 8 at a time, 5 s each. An address
  # that doesn't answer, or answers 404 or 410, is reported at each place it is used. Other statuses count as answered.
  if [ "$urls" = yes ]; then
    command -v curl >/dev/null 2>&1 || die 2 "check --urls needs curl: install it, or run check without --urls. pkm doctor lists the tools."
    external_addresses "$tmp/notes" > "$tmp/url-places"
    cut -f3 "$tmp/url-places" | LC_ALL=C sort -u > "$tmp/url-list"
    : > "$tmp/url-status"
    if [ -s "$tmp/url-list" ]; then
      # shellcheck disable=SC2016 # the script for each address: its $1 is the address
      tr '\n' '\0' < "$tmp/url-list" | xargs -0 -P 8 -n 1 bash -c \
        'code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 -L "$1" 2>/dev/null); [ -n "$code" ] || code=000; printf "%s\t%s\n" "$1" "$code"' _ \
        > "$tmp/url-status"
    fi
    awk -F '\t' 'NR == FNR { status[$1] = $2; next }
      { code = status[$3]
        if (code == "" || code == "000") print "- " $1 ":" $2 ": no answer: " $3
        else if (code == "404" || code == "410") print "- " $1 ":" $2 ": " code ": " $3 }
    ' "$tmp/url-status" "$tmp/url-places" >> "$tmp/problems"
  fi

  count=$(wc -l < "$tmp/notes" | tr -d ' ')
  echo "Checked $count $(plural "$count" note)."
  if [ -s "$tmp/problems" ]; then echo; echo "Problems:"; cat "$tmp/problems"; fi
  if [ -s "$tmp/notices" ]; then echo; echo "Notices:"; cat "$tmp/notices"; fi
  [ -s "$tmp/problems" ] && return 1
  echo "No problems found."
}

# check_part_of_folders: with part_of_folders=yes, a notice for each note outside its parent's folder, with the move
# that puts it there. Notes in archive/, and types with a folder_<type> setting of their own, are left alone.
check_part_of_folders() {
  local tab child parent type folder name ln
  tab=$(printf '\t')
  tree_parents "$tmp/pf-parents"
  while IFS="$tab" read -r child parent; do
    case $parent in archive/*) continue ;; esac
    type=$(awk -F "$tab" -v p="$child" '$1 == p { print $3; exit }' "$(cache_dir)/notes.tsv")
    [ -z "$(config "folder_$type" "")" ] || continue
    folder=$(fm_folder_of "$parent")
    [ "${child%/*}" != "$folder" ] || continue
    name=$(basename "$child" .md)
    ln=$(awk '/^part_of:/ { print FNR; exit }' "$child")
    echo "- $child:${ln:-1}: part_of $(basename "$parent" .md), so it belongs in $folder/: pkm mv $name $folder"
  done < "$tmp/pf-parents"
}

# check_part_of: the problems of part_of, after link_build: a list where one note belongs (part_of names one note), a
# note that names itself, and notes that name each other in a circle, which no tree can show. A circle is reported
# once, at the part_of line of its first note by name, as its names in order and back to the first.
check_part_of() {
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  scan "$tmp/notes" "$(awk_part_of)"'
    FNR == 1 { file = rel(FILENAME); front = ($0 == "---"); next }
    front && $0 ~ /^---\r?$/ { front = 0; next }
    front {
      v = part_of_value($0)
      if (v != "" && part_of_list(v)) print "L\t" file "\t" FNR
      else if (v != "") print "P\t" file "\t" FNR
    }
  ' > "$tmp/part-of-lines"
  awk -F '\t' '
    function name(p,   n) { n = p; sub(/.*\//, "", n); sub(/\.md$/, "", n); return n }
    FILENAME == ARGV[1] {
      if ($1 == "L") print "- " $2 ":" $3 ": part_of names one note: keep one, and link the others"
      else { want[$2 SUBSEP $3] = 1; where[$2] = $3 }
      next
    }
    ($1 SUBSEP $2) in want && $6 != "" { parent[$1] = $6 }
    END {
      for (p in parent) if (parent[p] == p) { print "- " p ":" where[p] ": part_of names the note itself"; delete parent[p] }
      for (p in parent) {
        # Follow the parents from p; a circle is found when the walk comes back to p.
        q = parent[p]; steps = 0
        while (q in parent && q != p && steps < 1000) { q = parent[q]; steps++ }
        if (q != p) continue
        first = p; q = parent[p]
        while (q != p) { if (name(q) < name(first)) first = q; q = parent[q] }
        if (first != p || (first in told)) continue
        told[first] = 1; ring = name(first); q = parent[first]
        while (q != first) { ring = ring ", " name(q); q = parent[q] }
        print "- " first ":" where[first] ": part_of goes round in a circle: " ring ", " name(first) ": take it out of one of them"
      }
    }
  ' "$tmp/part-of-lines" "$tmp/lb-links" | LC_ALL=C sort
}

# check_items: the problems of items (docs/format.md, Links 6): an item whose note has no items line, at the item's place,
# and a url or items line whose value is not one http(s) address, at that line. An item of a missing note is already a
# broken link, and an item of a note whose items value is wrong is reported at that value.
check_items() {
  item_addresses "$tmp/notes" | awk -F '\t' '
    $5 == "none" { print "- " $1 ":" $2 ": [[" $3 "]]#" $4 " is an item, but " $3 " has no items line: add one to its frontmatter, or write the number apart from the link" }
  ' > "$tmp/item-problems"
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  scan "$tmp/notes" "$(awk_items_in)"'
    FNR == 1 { file = rel(FILENAME); front = ($0 == "---"); next }
    front && $0 == "---" { front = 0; next }
    front && match($0, /^(url|items):/) {
      key = substr($0, 1, RLENGTH - 1); v = substr($0, RLENGTH + 1); gsub(/^[ \t]+|[ \t]+$/, "", v)
      if (v != "" && web_value(v) == "") print "- " file ":" FNR ": " key " is not one http:// or https:// address: write the whole address, such as " key ": https://github.com/acme-example/apollo-web" (key == "items" ? "/issues/" : "")
    }
  ' >> "$tmp/item-problems"
  LC_ALL=C sort "$tmp/item-problems"
}
