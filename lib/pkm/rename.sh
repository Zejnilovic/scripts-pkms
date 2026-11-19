# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/rename.sh: the rewriting of links for rename, and the moves record. Sourced by bin/pkm. Defines functions only.
# A link that resolves to the note is rewritten, outside code spans and fences, so that what the reader sees stays the
# same: [[old]] becomes [[new]], [[old#h]] becomes [[new#h]], and a link written with other words keeps them as its
# display ([[Jane Doe]] becomes [[jane-roe|Jane Doe]]). Environment for the awk programs: OLD, NEW, TEXTS (the link texts
# that resolve to the note), CHANGES (where the changed lines are reported), SELF (yes for the note itself) and ALIAS
# (yes unless --no-alias). The program needs awk_part_of after it.

# awk_rename_links: rewrites the links of one file, line by line, and writes each changed line to CHANGES.
awk_rename_links() {
  cat <<'AWK'
  function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
  function target_of(inner,   t) { t = inner; sub(/\|.*/, "", t); sub(/#.*/, "", t); sub(/\^.*/, "", t); t = trim(t); sub(/.*\//, "", t); return t }
  function rewrite_token(inner,   t, m, raw, suffix, has_alias, alias_text, rest, k, newinner) {
    t = target_of(inner)
    if (!(t in T)) return "[[" inner "]]"
    m = match(inner, /[|#^]/)
    raw = trim(m ? substr(inner, 1, m - 1) : inner)
    suffix = m ? substr(inner, m) : ""
    has_alias = 0; alias_text = ""; rest = suffix
    if (substr(suffix, 1, 1) == "|") {
      has_alias = 1; rest = substr(suffix, 2)
      k = match(rest, /[#^]/)
      if (k) { alias_text = substr(rest, 1, k - 1); rest = substr(rest, k) } else { alias_text = rest; rest = "" }
    }
    if (has_alias) newinner = NEW "|" alias_text rest
    else if (t == OLD) newinner = NEW rest
    else newinner = NEW "|" raw rest
    return "[[" newinner "]]"
  }
  function rewrite_outside(s,   out, tok, inner, start, len) {
    out = ""
    while (match(s, /\[\[[^]]*\]\]/)) {
      start = RSTART; len = RLENGTH
      out = out substr(s, 1, start - 1)
      tok = substr(s, start, len); inner = substr(tok, 3, len - 4)
      out = out rewrite_token(inner)
      s = substr(s, start + len)
    }
    return out s
  }
  function rewrite_line(line,   n, seg, i, result, piece) {
    if (index(line, "[[") == 0) return line
    n = split(line, seg, "`")
    result = ""
    for (i = 1; i <= n; i++) {
      piece = (i % 2 == 1) ? rewrite_outside(seg[i]) : seg[i]
      result = (i == 1) ? piece : result "`" piece
    }
    return result
  }
  BEGIN {
    while ((getline t < ENVIRON["TEXTS"]) > 0) T[t] = 1
    close(ENVIRON["TEXTS"])
    OLD = ENVIRON["OLD"]; NEW = ENVIRON["NEW"]
  }
  FNR == 1 { fence = 0; file = FILENAME; front = ($0 ~ /^---\r?$/); if (front) { print; next } }
  # In the frontmatter, part_of names its note without brackets too (awk_part_of); a value in brackets is rewritten below,
  # as any link. The quotes and the line ending stay as they were.
  front && $0 ~ /^---\r?$/ { front = 0; print; next }
  front {
    v = part_of_value($0)
    if (v != "" && index(v, "[[") == 0 && (part_of_target(v) in T)) {
      q = substr(v, 1, 1); if (q != "\"" && q != "'") q = ""
      b = $0; sub(/\r$/, "", b); a = "part_of: " q NEW q
      print file ":" FNR ": " b " -> " a >> ENVIRON["CHANGES"]
      print a (($0 ~ /\r$/) ? "\r" : "")
      next
    }
  }
  /^[ \t]*(```|~~~)/ { fence = !fence; print; next }
  fence { print; next }
  {
    new = rewrite_line($0)
    if (new != $0) { b = $0; sub(/\r$/, "", b); a = new; sub(/\r$/, "", a); print file ":" FNR ": " b " -> " a >> ENVIRON["CHANGES"] }
    print new
  }
AWK
}

# awk_rename_alias: adds the old name to the aliases of the renamed note, in its frontmatter. A note with no frontmatter
# gets one with that alias; a note with frontmatter and no aliases gets an aliases line; an empty aliases list, an
# inline list and a block list each get the name added.
awk_rename_alias() {
  cat <<'AWK'
  function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
  function log_change(before, after) { print file ":" FNR ": " before " -> " after >> ENVIRON["CHANGES"] }
  function log_added(written) { print file ":" FNR ": + " written >> ENVIRON["CHANGES"] }
  # Lines pkm adds end with the file's own line ending (EOL: a carriage return, or nothing). Comparisons use t, the line
  # without its carriage return; lines pkm keeps are printed as they were.
  BEGIN { OLD = ENVIRON["OLD"]; E = ENVIRON["EOL"]; file = ENVIRON["FILE"]; state = "start"; pending = 0; done = 0 }
  { t = $0; sub(/\r$/, "", t) }
  FNR == 1 {
    if (t == "---") { state = "front"; print; next }
    print "---" E; print "aliases: [" OLD "]" E; print "---" E; print; state = "body"; done = 1
    log_added("aliases: [" OLD "]"); next
  }
  state == "front" {
    if (pending && t !~ /^[ \t]+- /) { print "  - " OLD E; log_added("  - " OLD); pending = 0; done = 1 }
    if (t == "---") {
      if (!done) { print "aliases: [" OLD "]" E; log_added("aliases: [" OLD "]"); done = 1 }
      print; state = "body"; next
    }
    if (t ~ /^aliases:/) {
      v = trim(substr(t, 9))
      if (index(v, OLD) > 0) { done = 1; print; next }
      if (v == "") { print; pending = 1; next }
      if (substr(v, 1, 1) == "[") {
        inner = trim(substr(v, 2, length(v) - 2))
        if (inner == "") nv = "aliases: [" OLD "]"; else nv = "aliases: [" inner ", " OLD "]"
      } else nv = "aliases: " v ", " OLD
      print nv E
      log_change(t, "aliases now include " OLD); done = 1; next
    }
    print; next
  }
  { print }
AWK
}

# rename_moves_append <old> <new>: the moves record, one line per rename or move: date, old, new.
rename_moves_append() {
  mkdir -p .pkm || return 1
  printf '%s\t%s\t%s\n' "$today" "$1" "$2" >> .pkm/moves.tsv
}
