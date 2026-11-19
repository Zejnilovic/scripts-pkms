# shellcheck shell=bash
# lib/pkm/output.sh: the output contract for listing commands. A listing prints one of three shapes: "path:line: text"
# lines (find, backlinks, tasks), bare paths (path), table rows "path | ..." (list), or check's Problems and Notices.
# output_command runs the command and prints its output: as it is, with --abs (absolute paths), as --json (JSON Lines,
# built by jq), with --limit n (the first n records, and a footer on stderr). Exit 1 when a listing has no records.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# The shapes of the listing commands, and the commands that use output_command.
output_shape() {
  case $1 in
    find|backlinks|links|recall) echo lines ;;
    tasks) echo tasks ;;
    check) echo check ;;
    path) echo paths ;;
    list) echo table ;;
    names) echo names ;;
    *) return 1 ;;
  esac
}

# need_jq: exits 2, saying how to get it, when jq (for --json) is missing.
need_jq() {
  command -v jq >/dev/null 2>&1 || die 2 "--json needs jq: brew install jq, or your system's package manager. pkm doctor lists the tools."
}

# output_command <command> <args...>: runs a listing command and prints its output in the form asked for.
output_command() {
  local command=$1 shape json=no abs=no limit="" rc records vault_path
  shift
  shape=$(output_shape "$command") || die 2 "pkm $command has no listing."
  local args=()
  while [ $# -gt 0 ]; do
    case $1 in
      --json) json=yes ;;
      --abs) abs=yes ;;
      --limit) { [ $# -ge 2 ] && number "$2" "--limit"; } || die 2 "--limit needs a whole number"; limit=$2; shift ;;
      *) args+=("$1") ;;
    esac
    shift
  done
  if [ -z "$limit" ]; then limit=$(config limit 30); fi
  [ "$json" = no ] || need_jq
  "cmd_$command" ${args[@]+"${args[@]}"} > "$tmp/listing"
  rc=$?
  vault_path=$(pwd)
  # Each line becomes O (printed as it is) or R (a record): R, the prefix before the path, the path, the rest of the
  # line after the path, the line number, the text, the kind, then the fields of a table row. Fields are separated by
  # the unit separator, which a listing does not contain.
  awk -v shape="$shape" '
    BEGIN { US = "\037"; section = "" }
    function emit(pre, path, rest, ln, text, kind, fields) {
      print "R" US pre US path US rest US ln US text US kind fields
    }
    {
      raw = $0; sub(/\r$/, "", raw)
      if (shape == "check") {
        if (raw == "Problems:") { section = "problem"; print "O" US raw; next }
        if (raw == "Notices:") { section = "notice"; print "O" US raw; next }
        if (section != "" && raw ~ /^- /) {
          t = substr(raw, 3)
          if (match(t, /:[0-9]+: /) && RSTART > 1) emit("- ", substr(t, 1, RSTART - 1), substr(t, RSTART), substr(t, RSTART + 1, RLENGTH - 3), substr(t, RSTART + RLENGTH), section, "")
          else emit("- ", "", t, "", t, section, "")
          next
        }
        print "O" US raw; next
      }
      if (shape == "paths") { if (raw == "") print "O" US raw; else emit("", raw, "", "", "", "", ""); next }
      if (shape == "table") {
        i = index(raw, "\t")
        if (i == 0) { print "O" US raw; next }
        n = split(substr(raw, i + 1), cols, "\t")
        fields = ""
        for (k = 1; k <= n; k++) fields = fields US cols[k]
        emit("", substr(raw, 1, i - 1), substr(raw, i), "", substr(raw, i + 1), "", fields)
        next
      }
      if (shape == "names") {
        n = split(raw, c, "\t")
        if (n < 3) { print "O" US raw; next }
        emit(c[1] "\t" c[2] "\t", c[3], "\t" c[4], "", "", "", US c[1] US c[2] US c[4])
        next
      }
      pre = ""; s = raw
      if (substr(s, 1, 2) == "- ") { pre = "- "; s = substr(s, 3) }
      if (match(s, /:[0-9]+: /) && RSTART > 1) emit(pre, substr(s, 1, RSTART - 1), substr(s, RSTART), substr(s, RSTART + 1, RLENGTH - 3), substr(s, RSTART + RLENGTH), "", "")
      else print "O" US raw
    }
  ' "$tmp/listing" > "$tmp/listing-parts"
  # Records come in one order whatever the search did (ripgrep runs in parallel): by path in byte order, then by line.
  # check keeps its own order, which is documented. The footer and --limit apply to the sorted records.
  if [ "$shape" != check ] && [ "$shape" != tasks ] && [ "$shape" != names ] && [ "$command" != recall ]; then
    US=$(printf '\037')
    { grep '^O' "$tmp/listing-parts" || true; grep '^R' "$tmp/listing-parts" | LC_ALL=C sort -s -t "$US" -k3,3 -k5,5n || true; } > "$tmp/listing-sorted"
    mv "$tmp/listing-sorted" "$tmp/listing-parts"
  fi
  records=$(grep -c '^R' "$tmp/listing-parts")
  if [ "$json" = yes ]; then
    [ -f "$tmp/task-meta" ] || : > "$tmp/task-meta"
    # A task's JSON also has its group, due date and state, from the meta file cmd_tasks wrote for this listing.
    awk -F '\037' -v OFS='\037' -v abs="$abs" -v vault="$vault_path" -v limit="$limit" -v tasks="$shape" '
      FILENAME == ARGV[1] { if (FILENAME == ARGV[1]) meta[$1 ":" $2] = $3 OFS $4 OFS $5; next }
      $1 == "R" {
        n++; if (n > limit) next
        p = $3; key = p ":" $5
        if (abs == "yes" && p != "") p = vault "/" p
        out = p OFS $5 OFS $6 OFS $7
        if (tasks == "tasks") out = out OFS (key in meta ? meta[key] : OFS OFS)
        else for (i = 8; i <= NF; i++) out = out OFS $i
        print out
      }
    ' "$tmp/task-meta" "$tmp/listing-parts" > "$tmp/json-rows"
    if [ "$shape" = tasks ]; then
      jq -R -c 'split("\u001f") as $f
        | {path: $f[0], line: ($f[1] | tonumber), text: $f[2], group: $f[4],
           due: (if $f[5] == "" then null else $f[5] end), state: $f[6]}' "$tmp/json-rows"
    else
    jq -R -c --arg command "$command" 'split("\u001f") as $f
      | {path: (if $f[0] == "" then null else $f[0] end),
         line: (if $f[1] == "" then null else ($f[1] | tonumber) end),
         text: (if $f[2] == "" then null else $f[2] end)}
      | (if $f[3] != "" then . + {kind: $f[3]} else . end)
      | (if ($f | length) > 4 then . + {fields: $f[4:]} else . end)
      | (if $command == "links" then (.url = .text | del(.text)) else . end)' "$tmp/json-rows"
    fi
  else
    awk -F '\037' -v abs="$abs" -v vault="$vault_path" -v limit="$limit" '
      $1 == "O" { print substr($0, 3); next }
      $1 == "R" {
        n++; if (n > limit) next
        p = $3; if (abs == "yes" && p != "") p = vault "/" p
        print $2 p $4
      }
      END { if (n > limit) printf "... %d more (use --limit)\n", n - limit > "/dev/stderr" }
    ' "$tmp/listing-parts"
  fi
  if [ "$shape" != check ] && [ "$rc" = 0 ] && [ "$records" = 0 ]; then rc=1; fi
  return "$rc"
}
