# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/moved.sh: pkm moved <path:line> <when>: a task or an event whose date changed. The old line is struck (as
# pkm strike does) and written again with the new date: in its (at …) when it has one, else in its (due …). In a note,
# and on today's page, the new line goes right below the old one. From another day's page it goes on today's page, a
# task under Tasks and an event in the Log with the time now, linking the day it came from before its markers. Prints
# path:line: text of the new line. Sourced by bin/pkm. Defines functions only.

cmd_moved() {
  local usage="Usage: pkm moved <path:line> <when>, such as pkm moved daybook/2026/11/2026-11-12.md:7 friday"
  [ $# -ge 2 ] || die 2 "$usage"
  local spec=$1 path ln total US result status new raw prefix eol cr here page loc kind
  shift
  case $spec in
    *.md:*) path=${spec%:*}; ln=${spec##*:} ;;
    *) die 2 "$usage" ;;
  esac
  case $ln in ''|*[!0-9]*) die 2 "A line is a whole number: $spec" ;; esac
  case $path in /*|../*|*/../*) die 2 "$path is outside the vault." ;; esac
  [ -f "$path" ] || die 2 "No file $path in the vault."
  total=$(awk 'END { print NR }' "$path")
  [ "$ln" -ge 1 ] && [ "$ln" -le "$total" ] || die 2 "Line $ln is outside $path, which has $total lines."
  US=$(printf '\037')
  here=no
  if page=$(day_path "$today" 2>/dev/null) && [ "$page" = "$path" ]; then here=yes; fi
  # The new line, from the scanner's record of the old one: status (ok, or the exit code), kind, then the text or why not.
  result=$(line_records no | PATHWANT=$path LINEWANT=$ln WHEN="$*" awk -F "$US" -v OFS="$US" -v today="$today" \
    -v clock="$clock" -v here="$here" "$(awk_dates)$(awk_markers)$(awk_events)"'
    function fail(code, why) { print code, "", why; found = 1; exit }
    # put(t, key, v): the line with the value of its first (key …) set to v; (@ …) counts as (at …), and a 📅 date as
    # (due …). A line without the marker gets it at its end.
    function put(t, key, v,   rest, done, i, j, c, k, sp, e, out) {
      out = ""; rest = t
      while ((i = index(rest, "(")) > 0) {
        j = index(substr(rest, i + 1), ")"); if (j == 0) break
        c = substr(rest, i + 1, j - 1); sp = index(c, " "); k = sp ? substr(c, 1, sp - 1) : c
        if (!done && (k == key || (key == "at" && k == "@")) && (key != "at" || at_value(substr(c, sp + 1)))) {
          out = out substr(rest, 1, i) k " " v ")"; done = 1
        } else out = out substr(rest, 1, i + j)
        rest = substr(rest, i + j + 1)
      }
      t = out rest
      if (done) return t
      e = "\360\237\223\205 "; i = index(t, e)
      if (key == "due" && i > 0) {
        rest = substr(t, i + length(e)); sub(/^[^ )]*/, "", rest)
        return substr(t, 1, i - 1) "(due " v ")" rest
      }
      sub(/ +$/, "", t)
      return t " (" key " " v ")"
    }
    # linked(t, name): the line with " ([[name]])" before its first marker, in place of a day link already there.
    function linked(t, name,   i, j, c, rest, pos, e, head) {
      pos = 0; rest = t
      while ((i = index(rest, "(")) > 0) {
        j = index(substr(rest, i + 1), ")"); if (j == 0) break
        c = substr(rest, i + 1, j - 1)
        if (line_markers("(" c ")") != "") { pos = length(t) - length(rest) + i; break }
        rest = substr(rest, i + j + 1)
      }
      e = index(t, "\360\237\223\205 "); if (e > 0 && (pos == 0 || e < pos)) pos = e
      if (pos == 0) { sub(/ +$/, "", t); return t " ([[" name "]])" }
      head = substr(t, 1, pos - 1); sub(/ +$/, "", head)
      sub(/ \(\[\[[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][^]]*\]\]\)$/, "", head)
      return head " ([[" name "]]) " substr(t, pos)
    }
    $1 != ENVIRON["PATHWANT"] || $2 != ENVIRON["LINEWANT"] { next }
    {
      found = 1; kind = $3; m = $5; t = $10; when = ENVIRON["WHEN"]; gsub(/[ \t]+/, " ", when); sub(/^ /, "", when); sub(/ $/, "", when)
      if ($8 == "close") fail(1, "a close page is a record of its period: move the line where it was first written")
      if (kind == "task" && $4 != "open") fail(1, "it is a " $4 " task: only an open task or an event can move")
      if (kind != "task" && kind != "event") fail(1, "it is not an open task or an event: it has no date to move")
      if (kind == "event" && mval(m, "every") != "" && $6 == "")
        fail(1, "it comes back with (every " mval(m, "every") "): to move one time, add (skip <date>) to it and write that time as an event of its own")
      if (mhas(m, "at")) {
        p = event_when(when, today)
        if (p != "") fail(2, "can'\''t read the new time " when ": use a date, a date and HH:MM or HH:MM-HH:MM, or <date> to <date>")
        nf = EV_FIRST; nl = EV_LAST; ns = EV_START; ne = EV_END
        n = split(when, w, " ")
        old = mval(m, "at"); gsub(/[ \t]+/, " ", old)
        if (event_when(old, $6) == "" && n == 1) {
          if (EV_START != "") { split(old, o, " "); v = nf " " o[2] }
          else if (EV_LAST != EV_FIRST) v = nf " to " iso(ymd(nf) + ymd(EV_LAST) - ymd(EV_FIRST))
          else v = nf
        } else if (ns != "") v = nf " " ns (ne != "" ? "-" ne : "")
        else if (nl != nf) v = nf " to " nl
        else v = nf
        t = put(t, "at", v)
      } else {
        v = day_word(when, today)
        if (index(when, " ") || !is_day(v)) fail(2, "can'\''t read the new day " when ": a task'\''s date is YYYY-MM-DD, today, tomorrow, +3d, +2w or a weekday")
        t = put(t, "due", v)
      }
      if ($6 != "" && here != "yes") {
        name = $1; sub(/.*\//, "", name); sub(/\.md$/, "", name)
        t = linked(t, name)
        if (kind == "event") { sub(/^[-*+] /, "", t); sub(/^[0-2][0-9]:[0-5][0-9] /, "", t); t = "- " clock " " t }
        print "away", kind, t
      } else print "below", kind, t
    }
    END { if (!found) print 1, "", "it is not an open task or an event: it has no date to move" }
  ')
  status=${result%%"$US"*}
  result=${result#*"$US"}
  kind=${result%%"$US"*}
  new=${result#*"$US"}
  case $status in
    1|2) die "$status" "Line $ln of $path can't move: $new." ;;
  esac
  ( cmd_strike "$path:$ln" ) > /dev/null || exit $?
  if [ "$status" = away ]; then
    page=$(day_ensure "$today") || exit $?
    if [ "$kind" = task ]; then loc=$(section_add "$page" Tasks "$new" no) || exit $?
    else printf '%s\n' "$new" > "$tmp/moved-line"; loc=$(log_add "$page" "$tmp/moved-line" no) || exit $?; fi
    echo "$page:$loc: $new"
    return 0
  fi
  # Right below the old line, with its indent and its line end.
  raw=$(sed -n "${ln}p" "$path")
  cr=$(printf '\r'); eol=""
  case $raw in *"$cr") eol=$cr ;; esac
  prefix=$(printf '%s\n' "$raw" | sed 's/[^[:space:]].*$//')
  NEW="$prefix$new$eol" awk -v ln="$ln" '{ print } NR == ln { print ENVIRON["NEW"] }' "$path" > "$tmp/moved-page"
  cat "$tmp/moved-page" > "$path" || die 1 "Can't write $path."
  echo "$path:$((ln + 1)): $new"
}
