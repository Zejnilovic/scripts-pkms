# shellcheck shell=bash
# lib/pkm/core.sh: what every command uses: errors, the clock, files, rendering templates, and the task
# text of notes. Sourced by bin/pkm. Defines functions and settings only.
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"

# scripts/bump.sh sets this, and scripts/check.py matches it with VERSION.
# shellcheck disable=SC2034 # read by bin/pkm (version) and by cmd/version.sh
pkm_version=0.3.0

die() { code=$1; shift; printf '%s\n' "$*" >&2; exit "$code"; }

now=${PKM_NOW:-$(date +%Y%m%d%H%M%S)}
case $now in
  [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]) ;;
  *) die 2 "PKM_NOW must look like YYYYMMDDHHMMSS, got: $now" ;;
esac
today="${now:0:4}-${now:4:2}-${now:6:2}"
clock="${now:8:2}:${now:10:2}"

# refuse_existing <path>: exits 1 when something is already at the path, visible to pkm or hidden by .pkmignore. The path is
# printed on stdout, and the reason on stderr, so a caller can say which file is in the way.
refuse_existing() {
  local hidden=""
  if [ ! -e "$1" ] && [ ! -L "$1" ]; then return 0; fi
  if ! files yes '*' | grep -qxF -- "$1"; then hidden=" .pkmignore hides it from pkm, so no command names it."; fi
  echo "$1"
  die 1 "$1 already exists, and pkm won't replace it.$hidden"
}

plural() { if [ "$1" = 1 ]; then echo "$2"; else echo "${2}s"; fi; }

number() { case $1 in ''|*[!0-9]*) die 2 "$2 must be a whole number, got: $1" ;; esac; }

# vault_rg <archive: yes|no> <templates: yes|no> <ripgrep arguments>: ripgrep over the vault with pkm's rules. Only
# .pkmignore is read, in gitignore syntax: .gitignore, .ignore and .rgignore are not. Dot files and folders, and
# node_modules, are always left out; archive/ and the templates folder are left out unless the arguments say yes.
# A positive --glob would override .pkmignore, so names are filtered by vault_files, not here.
vault_rg() {
  local archive=$1 templates=$2 ignore folder
  shift 2
  command -v rg >/dev/null 2>&1 || die 2 "pkm needs ripgrep (rg): brew install ripgrep, or your system's package manager. pkm doctor lists the tools a vault expects."
  ignore=.pkmignore
  if [ ! -f "$ignore" ]; then ignore="$tmp/no-ignore"; : > "$ignore"; fi
  folder=$(config templates templates)
  set -- --glob '!/node_modules' "$@"
  [ "$archive" = yes ] || set -- --glob '!/archive' "$@"
  [ "$templates" = yes ] || set -- --glob "!/$folder" "$@"
  rg --no-ignore --ignore-file "$ignore" "$@"
}

# vault_files <archive: yes|no> <templates: yes|no> <name pattern>: the vault's files whose name matches the shell
# pattern, sorted, one path per line from the vault's root. Proposals, AGENTS.md and CLAUDE.md are left out.
vault_files() {
  vault_rg "$1" "$2" --files \
    | sed 's|^\./||' | grep -v -e '^\.' -e '/\.' | grep -v -x -e AGENTS.md -e CLAUDE.md | grep -v '\.proposal\.md$' \
    | PATTERN=$3 awk '
      function glob_re(g,   out, i, c, j) {
        out = ""
        for (i = 1; i <= length(g); i++) {
          c = substr(g, i, 1)
          if (c == "*") out = out ".*"
          else if (c == "?") out = out "."
          else if (c == "[") {
            j = index(substr(g, i), "]")
            if (j > 0) { out = out substr(g, i, j); i += j - 1 } else out = out "\\["
          }
          else if (index(".(){}^$|+\\", c) > 0) out = out "\\" c
          else out = out c
        }
        return out
      }
      BEGIN { re = "^" glob_re(ENVIRON["PATTERN"]) "$" }
      { base = $0; sub(/.*\//, "", base); if (base ~ re) print }
    ' | LC_ALL=C sort
}

# files <yes|no: include archive/> <name pattern>: the vault's own files, sorted, without the templates folder.
files() {
  vault_files "$1" no "$2"
}

# scan <list file> <awk program> [awk options]: runs the program over the files in the list. Paths get a "./"
# prefix so a name with "=" isn't read as an assignment; rel() takes it off again.
# eol_of <file>: the line ending a file uses: a carriage return when its first line ends with one, else nothing.
eol_of() {
  if head -n 1 "$1" 2>/dev/null | grep -q "$(printf '\r')\$"; then printf '\r'; fi
}

scan() {
  list=$1 program=$2
  shift 2
  awk "$@" -v list="$list" '
    BEGIN { while ((getline f < list) > 0) ARGV[ARGC++] = "./" f; close(list) }
    function rel(path) { sub(/^\.\//, "", path); return path }
    function base(path) { sub(/.*\//, "", path); return path }
    # Every line without its carriage return, and without a byte order mark at the start of the file.
    # Lengths are measured, not counted: gawk in a UTF-8 locale counts characters, mawk counts bytes.
    { sub(/\r$/, "") }
    FNR == 1 { bom_mark = "\357\273\277"; if (substr($0, 1, length(bom_mark)) == bom_mark) $0 = substr($0, length(bom_mark) + 1) }
  '"$program" < /dev/null
}

# conflict_markers: the awk pattern for the lines a merge (like git's) leaves around a conflict. "=======" alone
# is also a Markdown heading underline, so only the opening and closing lines count.
conflict_markers='^(<<<<<<<|>>>>>>>)( |$)'

# template_file <file name>: the template a note of this kind is made from. The vault's own templates folder wins,
# then the user's templates (~/.config/pkm/templates), then the default that pkm ships. A missing file gives the
# vault's path, so a message names the place the owner can add it.
template_file() {
  local folder
  folder=$(config templates templates)
  if [ -f "$folder/$1" ]; then printf '%s\n' "$folder/$1"
  elif [ -f "$(user_templates_dir)/$1" ]; then printf '%s\n' "$(user_templates_dir)/$1"
  elif [ -f "$pkm_home/share/pkm/templates/$1" ]; then printf '%s\n' "$pkm_home/share/pkm/templates/$1"
  else printf '%s\n' "$folder/$1"; fi
}

# render <template> <title> <slug> <name> <date> [<list file>]: the template with its placeholders filled in.
# {{title}}, {{date}} and {{time}} are the ones Obsidian's core templates also know. A template with conflict
# markers is refused, so they never reach a note. Callers render into $tmp, so a refusal leaves no file behind.
render() {
  if grep -nE "$conflict_markers" "$1" > "$tmp/markers"; then
    die 2 "$1 has an unresolved merge conflict from a merge (<<<<<<< at line $(head -n 1 "$tmp/markers" | cut -d: -f1)): keep the side you want, remove the <<<<<<<, ======= and >>>>>>> lines, then try again."
  fi
  T_TITLE=$2 T_SLUG=$3 T_NAME=$4 T_DATE=$5 T_TIME=$clock T_LIST=${6:-} awk '
    function swap(s, from, to,   out, i) {
      out = ""
      while ((i = index(s, from)) > 0) { out = out substr(s, 1, i - 1) to; s = substr(s, i + length(from)) }
      return out s
    }
    $0 == "{{list}}" { if (ENVIRON["T_LIST"] != "") while ((getline line < ENVIRON["T_LIST"]) > 0) print line; next }
    {
      s = swap($0, "{{title}}", ENVIRON["T_TITLE"]); s = swap(s, "{{slug}}", ENVIRON["T_SLUG"])
      s = swap(s, "{{name}}", ENVIRON["T_NAME"]); s = swap(s, "{{date}}", ENVIRON["T_DATE"])
      print swap(s, "{{time}}", ENVIRON["T_TIME"])
    }
  ' "$1"
}

translit='s/á/a/g;s/Á/a/g;s/à/a/g;s/À/a/g;s/â/a/g;s/Â/a/g;s/ä/a/g;s/Ä/a/g;s/ã/a/g;s/Ã/a/g;s/å/a/g;s/Å/a/g;s/ā/a/g;s/Ā/a/g;s/ă/a/g;s/Ă/a/g;s/ą/a/g;s/Ą/a/g;s/ç/c/g;s/Ç/c/g;s/ć/c/g;s/Ć/c/g;s/č/c/g;s/Č/c/g;s/ď/d/g;s/Ď/d/g;s/đ/d/g;s/Đ/d/g;s/ð/d/g;s/Ð/d/g;s/é/e/g;s/É/e/g;s/è/e/g;s/È/e/g;s/ê/e/g;s/Ê/e/g;s/ë/e/g;s/Ë/e/g;s/ě/e/g;s/Ě/e/g;s/ē/e/g;s/Ē/e/g;s/ę/e/g;s/Ę/e/g;s/ė/e/g;s/Ė/e/g;s/í/i/g;s/Í/i/g;s/ì/i/g;s/Ì/i/g;s/î/i/g;s/Î/i/g;s/ï/i/g;s/Ï/i/g;s/ī/i/g;s/Ī/i/g;s/į/i/g;s/Į/i/g;s/ľ/l/g;s/Ľ/l/g;s/ĺ/l/g;s/Ĺ/l/g;s/ł/l/g;s/Ł/l/g;s/ň/n/g;s/Ň/n/g;s/ń/n/g;s/Ń/n/g;s/ñ/n/g;s/Ñ/n/g;s/ó/o/g;s/Ó/o/g;s/ò/o/g;s/Ò/o/g;s/ô/o/g;s/Ô/o/g;s/ö/o/g;s/Ö/o/g;s/õ/o/g;s/Õ/o/g;s/ő/o/g;s/Ő/o/g;s/ø/o/g;s/Ø/o/g;s/ō/o/g;s/Ō/o/g;s/ř/r/g;s/Ř/r/g;s/ŕ/r/g;s/Ŕ/r/g;s/š/s/g;s/Š/s/g;s/ś/s/g;s/Ś/s/g;s/ş/s/g;s/Ş/s/g;s/ș/s/g;s/Ș/s/g;s/ť/t/g;s/Ť/t/g;s/ţ/t/g;s/Ţ/t/g;s/ț/t/g;s/Ț/t/g;s/ú/u/g;s/Ú/u/g;s/ù/u/g;s/Ù/u/g;s/û/u/g;s/Û/u/g;s/ü/u/g;s/Ü/u/g;s/ů/u/g;s/Ů/u/g;s/ű/u/g;s/Ű/u/g;s/ū/u/g;s/Ū/u/g;s/ų/u/g;s/Ų/u/g;s/ý/y/g;s/Ý/y/g;s/ÿ/y/g;s/Ÿ/y/g;s/ž/z/g;s/Ž/z/g;s/ź/z/g;s/Ź/z/g;s/ż/z/g;s/Ż/z/g;s/ß/ss/g;s/æ/ae/g;s/Æ/ae/g;s/œ/oe/g;s/Œ/oe/g;s/þ/th/g;s/Þ/th/g'

# slugify <title>: lowercase ASCII words joined by hyphens; letters with accents lose them, other scripts drop out.
slugify() {
  printf '%s' "$1" | LC_ALL=C sed "$translit" | LC_ALL=C tr '[:upper:]' '[:lower:]' \
    | LC_ALL=C sed -e 's/[^a-z0-9][^a-z0-9]*/-/g' -e 's/^-//' -e 's/-$//'
}

lowercase() { printf '%s' "$1" | LC_ALL=C tr '[:upper:]' '[:lower:]' | sed -e 's/^ *//' -e 's/ *$//' -e 's/  */ /g'; }

# awk_links_in: the awk function that yields the link targets on a line, without alias, heading or folder.
awk_links_in() {
  cat <<'AWK'

  function targets(s, out,   n, t) {
    n = 0
    while (match(s, /\[\[[^]]*\]\]/)) {
      t = substr(s, RSTART + 2, RLENGTH - 4); s = substr(s, RSTART + RLENGTH)
      sub(/\|.*/, "", t); sub(/\\$/, "", t); sub(/#.*/, "", t); sub(/\^.*/, "", t)
      gsub(/^[ \t]+|[ \t]+$/, "", t); sub(/.*\//, "", t)
      if (t != "") out[++n] = t
    }
    return n
  }
AWK
}

# awk_part_of: the awk functions for part_of, the frontmatter key that names the one note a note belongs to.
# part_of_value(line) is the value of a "part_of:" line, trimmed, or "" for any other line. part_of_target(value) is the
# name it gives, without quotes, brackets, shown text, heading or folder: "home", "[[home]]" and "[[notes/home|Home]]"
# all give home. A list ([home, car]) gives "" and part_of_list(value) is 1, since a note belongs to one note only.
awk_part_of() {
  cat <<'AWK'

  function part_of_value(line,   v) {
    if (line !~ /^part_of:/) return ""
    v = substr(line, 9); sub(/\r$/, "", v); gsub(/^[ \t]+|[ \t]+$/, "", v)
    return v
  }
  function part_of_list(v) {
    gsub(/^["']|["']$/, "", v)
    return (v ~ /^\[/ && v !~ /^\[\[[^]]*\]\]$/) || (v !~ /^\[\[/ && index(v, ","))
  }
  function part_of_target(v) {
    if (part_of_list(v)) return ""
    gsub(/^["']|["']$/, "", v)
    if (v ~ /^\[\[.*\]\]$/) v = substr(v, 3, length(v) - 4)
    sub(/\|.*/, "", v); sub(/#.*/, "", v); sub(/\^.*/, "", v); sub(/.*\//, "", v)
    gsub(/^[ \t]+|[ \t]+$/, "", v)
    return v
  }
AWK
}


# secret_awk: the awk function secret(line); give awk the single quote as -v q="'". A line with
# pkm-ignore-secret is never a secret.
awk_secret() {
  cat <<'AWK'

    function long_token(s, re, min) { return match(s, re) && RLENGTH >= min }
    function secret(line,   l, rest) {
      if (index(line, "pkm-ignore-secret")) return 0
      l = tolower(line)
      if (l ~ /-----begin [a-z ]*private key-----/) return 1
      if (long_token(l, "akia[0-9a-z]+", 20) || long_token(l, "gh[pousr]_[a-z0-9]+", 40) || long_token(l, "github_pat_[a-z0-9_]+", 30)) return 1
      if (long_token(l, "xox[abprs]-[a-z0-9-]+", 15) || long_token(l, "glpat-[a-z0-9_-]+", 26)) return 1
      if (match(l, /(^|[^a-z0-9])sk-[a-z0-9_-]+/) && RLENGTH >= 23 && substr(l, RSTART, RLENGTH) ~ /[0-9]/) return 1
      if (match(l, keyword)) {
        rest = substr(l, RSTART + RLENGTH)
        if (match(rest, /^[^ \t]+/)) { rest = substr(rest, 1, RLENGTH); gsub(quotes, "", rest) }
        if (length(rest) >= 8 && rest !~ /^[[<{(]/ && rest ~ /[0-9]/ && rest ~ /[a-z0-9]/) return 1
      }
      return 0
    }
    BEGIN {
      quotes = "[\"" q "]"
      keyword = "(password|passwd|secret|token|api[_-]?key|private[_-]?key|access[_-]?key)[a-z0-9_]*[\"" q "]?[ \t]*(:|=|([a-z]+[ \t]+)?([a-z]+[ \t]+)?([a-z]+[ \t]+)?([a-z]+[ \t]+)?is[ \t])[ \t]*[\"" q "]?"
    }
AWK
}

