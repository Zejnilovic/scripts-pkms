# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/index.sh: the cache, a speed-up that never changes an answer. It keeps, in .pkm/cache (or PKM_CACHE_DIR):
#   manifest.tsv  path, mtime, size, kind (note or file) of every file the index knows
#   notes.tsv     path, title, type, status, summary, aliases (comma-joined)
#   fields.tsv    path, key, value: the frontmatter of each note
#   links.tsv     path, line, target: every link in each note, outside code spans and fences
#   names.tsv     name, type, path, aliases: what a link can name (day and close pages included)
# A file is read again when it is new, or its mtime or size differs from the manifest; a file the manifest has and the
# vault doesn't is dropped. Each batch of changed notes is read in one awk pass. Each file is written to a temporary
# name and moved into place, and the manifest last, so an interrupted run leaves a cache that is read again next time.
# Sourced by bin/pkm. Defines functions only.

# cache_schema: what the cache files hold, written to its version file. A cache of another version, or with none (pkm
# 0.1.0's), is read again in full, since other rules made its rows. 2: part_of counts as a link.
cache_schema=2

# cache_dir: the cache folder: PKM_CACHE_DIR, or .pkm/cache in the vault.
cache_dir() {
  if [ -n "${PKM_CACHE_DIR:-}" ]; then printf '%s\n' "$PKM_CACHE_DIR"; else printf '%s\n' ".pkm/cache"; fi
}

# pkm_stats <list file>: "path<TAB>mtime<TAB>size" for each path in the list. stat takes its flavour from the system:
# GNU on Linux and Git Bash, BSD on macOS. The paths go through xargs in batches, so 10,000 files cost a few calls.
pkm_stats() {
  local tab
  tab=$(printf '\t')
  [ -s "$1" ] || return 0
  if stat -c %Y . >/dev/null 2>&1; then
    tr '\n' '\0' < "$1" | xargs -0 stat -c '%Y %s %n' 2>/dev/null
  else
    tr '\n' '\0' < "$1" | xargs -0 stat -f '%m %z %N' 2>/dev/null
  fi | awk -v OFS="$tab" '{ m = $1; s = $2; sub(/^[0-9]+ [0-9]+ /, ""); print $0, m, s }'
}

# index_extract <list of notes>: one awk pass. Writes NOTES_OUT (notes.tsv rows) and FIELDS_OUT (fields.tsv rows).
index_extract() {
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  scan "$1" "$(awk_links_in)$(awk_part_of)"'
    function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    function clean(s) { s = trim(s); gsub(/\t/, " ", s); return s }
    function clean_alias(s) { s = trim(s); gsub(/^["'"'"']|["'"'"']$/, "", s); return trim(s) }
    function flush(   k, n, parts, i, w, aliases, type, title2) {
      if (path == "") return
      type = fm["type"]
      if (type == "") type = (path ~ /^daybook\//) ? "day" : ((path ~ /^closes\//) ? "close" : "note")
      title2 = title
      if (title2 == "") { title2 = base(path); sub(/\.md$/, "", title2) }
      aliases = ""
      gsub(/^\[|\]$/, "", fm["aliases"])
      n = split(fm["aliases"], parts, ",")
      for (i = 1; i <= n; i++) { w = clean_alias(parts[i]); if (w != "") aliases = aliases (aliases == "" ? "" : ",") w }
      print path "\t" clean(title2) "\t" clean(type) "\t" clean(fm["status"]) "\t" clean(fm["summary"]) "\t" aliases > ENVIRON["NOTES_OUT"]
      for (k in fm) print path "\t" k "\t" clean(fm[k]) > ENVIRON["FIELDS_OUT"]
    }
    FNR == 1 {
      flush()
      path = rel(FILENAME); split("", fm); title = ""; curkey = ""; fence = 0
      state = ($0 == "---") ? "front" : "body"
      if (state == "front") next
    }
    /^[ \t]*(```|~~~)/ { fence = !fence; next }
    !fence && index($0, "[[") {
      s = $0; gsub(/`[^`]*`/, "", s)
      n = targets(s, found)
      for (i = 1; i <= n; i++) print path "\t" FNR "\t" found[i] > ENVIRON["LINKS_OUT"]
    }
    state == "front" {
      if ($0 == "---") { state = "body"; curkey = ""; next }
      # part_of names its note without brackets as well; with them, the link rule above has counted it already.
      pv = part_of_value($0)
      if (pv != "" && index(pv, "[[") == 0) { pt = part_of_target(pv); if (pt != "") print path "\t" FNR "\t" pt > ENVIRON["LINKS_OUT"] }
      if (curkey != "" && $0 ~ /^[ \t]+- /) { item = $0; sub(/^[ \t]+- /, "", item); fm[curkey] = (fm[curkey] == "" ? "" : fm[curkey] ", ") trim(item); next }
      if (match($0, /^[A-Za-z0-9_-]+:/)) { curkey = substr($0, 1, RLENGTH - 1); fm[curkey] = trim(substr($0, RLENGTH + 1)); next }
      curkey = ""
      next
    }
    title == "" && !fence && /^# / { title = trim(substr($0, 3)) }
    END { flush() }
  ' -v q="'"
}

# index_update <rebuild yes|no> <report yes|no>: brings the cache up to date with the vault.
index_update() {
  local rebuild=$1 report=$2 dir tab
  dir=$(cache_dir)
  tab=$(printf '\t')
  mkdir -p "$dir" || die 2 "Can't create the cache folder $dir."
  if [ "$(cat "$dir/version" 2>/dev/null)" != "$cache_schema" ]; then rebuild=yes; fi
  if [ "$rebuild" = yes ]; then rm -f "$dir/manifest.tsv" "$dir/notes.tsv" "$dir/fields.tsv" "$dir/names.tsv" "$dir/links.tsv"; fi
  # The manifest is trusted only when the other files agree with it: one note row per note, one name per file. A cache
  # that doesn't agree (a part missing, or a run that stopped) is read again in full.
  : > "$tmp/idx-old"
  trusted=no
  if [ -f "$dir/manifest.tsv" ] && [ -f "$dir/notes.tsv" ] && [ -f "$dir/fields.tsv" ] && [ -f "$dir/names.tsv" ] && [ -f "$dir/links.tsv" ] \
    && [ "$(awk -F "$tab" '$4 == "note"' "$dir/manifest.tsv" | wc -l | tr -d ' ')" = "$(wc -l < "$dir/notes.tsv" | tr -d ' ')" ] \
    && [ "$(wc -l < "$dir/manifest.tsv" | tr -d ' ')" = "$(wc -l < "$dir/names.tsv" | tr -d ' ')" ]; then
    cp "$dir/manifest.tsv" "$tmp/idx-old"
    trusted=yes
  else
    # Not trusted: the rows it holds go too, so the rebuild starts from nothing.
    rm -f "$dir/manifest.tsv" "$dir/notes.tsv" "$dir/fields.tsv" "$dir/names.tsv" "$dir/links.tsv"
  fi
  files yes '*' > "$tmp/idx-files"
  pkm_stats "$tmp/idx-files" > "$tmp/idx-stats"
  # New or changed: its mtime or size differs from the manifest. Gone: the manifest has it, the vault doesn't.
  awk -F "$tab" -v OFS="$tab" -v changed="$tmp/idx-changed" -v gone="$tmp/idx-gone" -v now="$tmp/idx-now" '
    FILENAME == ARGV[1] { old[$1] = $2 SUBSEP $3; next }
    FILENAME == ARGV[2] { seen[$1] = 1; kind = ($1 ~ /\.md$/) ? "note" : "file"; print $1, $2, $3, kind > now
      if (!($1 in old) || old[$1] != $2 SUBSEP $3) print $1 > changed }
    END { for (p in old) if (!(p in seen)) print p > gone }
  ' "$tmp/idx-old" "$tmp/idx-stats"
  touch "$tmp/idx-changed" "$tmp/idx-gone" "$tmp/idx-now"
  # Nothing changed and the cache is trusted: nothing to write.
  if [ "$trusted" = yes ] && [ ! -s "$tmp/idx-changed" ] && [ ! -s "$tmp/idx-gone" ]; then
    if [ "$report" = yes ]; then echo "Indexed $(wc -l < "$dir/notes.tsv" | tr -d ' ') notes and $(wc -l < "$dir/manifest.tsv" | tr -d ' ') files: 0 changed, 0 gone."; fi
    return 0
  fi
  cat "$tmp/idx-changed" "$tmp/idx-gone" | LC_ALL=C sort -u > "$tmp/idx-drop"
  grep '\.md$' "$tmp/idx-changed" > "$tmp/idx-changed-notes" || true
  : > "$tmp/idx-notes-new"; : > "$tmp/idx-fields-new"; : > "$tmp/idx-links-new"
  if [ -s "$tmp/idx-changed-notes" ]; then
    NOTES_OUT="$tmp/idx-notes-new" FIELDS_OUT="$tmp/idx-fields-new" LINKS_OUT="$tmp/idx-links-new" index_extract "$tmp/idx-changed-notes"
  fi
  # Merge: the rows of the notes not changed, then the new rows, sorted by path.
  for part in notes fields links; do
    awk -F "$tab" 'FILENAME == ARGV[1] { drop[$0] = 1; next } !($1 in drop)' "$tmp/idx-drop" "$dir/$part.tsv" 2>/dev/null > "$tmp/idx-kept-$part" || : > "$tmp/idx-kept-$part"
    cat "$tmp/idx-kept-$part" "$tmp/idx-$part-new" | LC_ALL=C sort -s -t "$tab" -k1,1 > "$dir/$part.tsv.tmp.$$"
    mv "$dir/$part.tsv.tmp.$$" "$dir/$part.tsv"
  done
  # names: every note by its file name, and every other file by its name, with the note's aliases.
  awk -F "$tab" -v OFS="$tab" '
    FILENAME == ARGV[1] { p = $1; name = p; sub(/.*\//, "", name); sub(/\.md$/, "", name); print name, $3, p, $6; next }
    FILENAME == ARGV[2] && $4 == "file" { name = $1; sub(/.*\//, "", name); print name, "attachment", $1, "" }
  ' "$dir/notes.tsv" "$tmp/idx-now" | LC_ALL=C sort -s -t "$tab" -k1,1 -k3,3 > "$tmp/idx-names"
  # Each file goes to a temporary name in the cache folder and is moved into place; the manifest is written last.
  cp "$tmp/idx-names" "$dir/names.tsv.tmp.$$" && mv "$dir/names.tsv.tmp.$$" "$dir/names.tsv"
  printf '%s\n' "$cache_schema" > "$dir/version.tmp.$$" && mv "$dir/version.tmp.$$" "$dir/version"
  LC_ALL=C sort -t "$tab" -k1,1 "$tmp/idx-now" > "$dir/manifest.tsv.tmp.$$" && mv "$dir/manifest.tsv.tmp.$$" "$dir/manifest.tsv"
  if [ "$report" = yes ]; then
    echo "Indexed $(wc -l < "$dir/notes.tsv" | tr -d ' ') notes and $(wc -l < "$dir/manifest.tsv" | tr -d ' ') files: $(wc -l < "$tmp/idx-changed" | tr -d ' ') changed, $(wc -l < "$tmp/idx-gone" | tr -d ' ') gone."
  fi
}

# index_ensure: the cache is up to date, quietly.
# index_ensure: brings the cache up to date. A command runs it once: the check stats every file in the vault, so a second
# call in the same run would cost as much again and find nothing new.
index_ensure() {
  [ "${index_ensured:-no}" = yes ] && return 0
  index_update no no
  index_ensured=yes
}
