# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/frontmatter.sh: setting frontmatter values (new --set, set), the address of a repository (new --url), and the
# folder of a note's parent (the part_of_folders setting). Sourced by bin/pkm. Defines functions only.

# fm_pair <key=value> <pairs file> <command>: checks one key=value and appends key<TAB>value to the pairs file. A key
# starts with a letter and has letters, digits, '_' and '-'; a value is one line. url and items take one http(s)
# address. A wrong pair is a usage error (exit 2).
fm_pair() {
  local pair=$1 key value tab cr
  tab=$(printf '\t'); cr=$(printf '\r')
  case $pair in *=*) ;; *) die 2 "pkm $3: a value is key=value, such as status=active: $pair" ;; esac
  key=${pair%%=*}; value=${pair#*=}
  case $key in
    [A-Za-z]*) case $key in *[!A-Za-z0-9_-]*) die 2 "pkm $3: a key has only letters, digits, '_' and '-': $key" ;; esac ;;
    *) die 2 "pkm $3: a key starts with a letter: $key" ;;
  esac
  case $value in
    *"$tab"*|*"$cr"*|*'
'*) die 2 "pkm $3: a value is one line, without tabs: $key" ;;
  esac
  value=$(printf '%s' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  case $key in
    url|items)
      case $value in
        '') ;;
        http://*|https://*) case $value in *' '*) die 2 "pkm $3: $key is one http(s) address, without spaces: $value" ;; esac ;;
        *) die 2 "pkm $3: $key is one http:// or https:// address: $value" ;;
      esac ;;
  esac
  printf '%s\t%s\n' "$key" "$value" >> "$2"
}

# fm_value <pairs file> <key>: the value the pairs give the key (the last one wins); fails when they don't name it.
fm_value() {
  awk -F '\t' -v k="$2" '$1 == k { v = substr($0, length(k) + 2); found = 1 } END { if (found) print v; exit !found }' "$1"
}

# fm_resolve <name>: the path of the note a name, slug, alias or link points to, from the cache. Fails when none does.
fm_resolve() {
  local name=$1 found
  name=${name#\"}; name=${name%\"}; name=${name#\'}; name=${name%\'}
  name=${name#[[}; name=${name%]]}; name=${name%%|*}; name=${name%%#*}; name=${name##*/}; name=${name%.md}
  [ -n "$name" ] || return 1
  index_ensure
  printf '%s\n' "$name" > "$tmp/fm-target"
  link_index "$tmp/fm-index"
  link_slugs "$tmp/fm-target" "$tmp/fm-slugs"
  link_resolve "$tmp/fm-index" "$tmp/fm-slugs" "$tmp/fm-resolved"
  found=$(awk -F '\t' -v t="$name" '$1 == t && $2 != "dead" && $3 ~ /\.md$/ { print $3; exit }' "$tmp/fm-resolved")
  [ -n "$found" ] || return 1
  printf '%s\n' "$found"
}

# fm_parent <pairs file> <command>: the path of the note the pairs' part_of names, or nothing when they set none or set
# it empty. A part_of that names no note exits 1, so a typo never makes a dead link.
fm_parent() {
  local value parent
  value=$(fm_value "$1" part_of) || return 0
  [ -n "$value" ] || return 0
  parent=$(fm_resolve "$value") || die 1 "pkm $2: no note is named $value, so part_of=$value would be a dead link. Make that note first, or check its name with pkm names."
  printf '%s\n' "$parent"
}

# fm_folder_of <parent path>: the folder the notes part_of a note go in, with part_of_folders=yes: a folder named after
# the parent, next to it (notes/apollo.md: notes/apollo). A parent in archive/ gives notes.
fm_folder_of() {
  case $1 in
    archive/*) echo notes ;;
    *) printf '%s\n' "${1%.md}" ;;
  esac
}

# fm_folder_ok <folder> <command>: a folder for notes must be inside the vault.
fm_folder_ok() {
  case $1 in
    ''|/*|..|../*|*/..|*/../*) die 2 "pkm $2: the folder must be inside the vault: $1" ;;
  esac
}

# fm_apply <file> <pairs file> <out> <changes>: the file with each pair's key set to its value. A key in the
# frontmatter gets the new value in its place, and the indented "- " lines of its old list go; a new key goes at the end
# of the frontmatter; a file without frontmatter gets one. The file's line ending and byte order mark are kept. Each
# written line goes to the changes file as <line><TAB><text>.
fm_apply() {
  EOL=$(eol_of "$1") PAIRS=$2 CHANGES=$4 awk '
    function out(s) { print s E; o++ }
    function added(i,   s) { s = (val[keys[i]] == "") ? keys[i] ":" : keys[i] ": " val[keys[i]]; out(s); print o "\t" s > CH; done[keys[i]] = 1 }
    function rest(   i) { for (i = 1; i <= n; i++) if (!(keys[i] in done)) added(i) }
    BEGIN {
      E = ENVIRON["EOL"]; CH = ENVIRON["CHANGES"]; BOM = "\357\273\277"; state = "start"
      while ((getline l < ENVIRON["PAIRS"]) > 0) {
        k = substr(l, 1, index(l, "\t") - 1)
        if (!(k in val)) keys[++n] = k
        val[k] = substr(l, index(l, "\t") + 1)
      }
    }
    { t = $0; sub(/\r$/, "", t) }
    FNR == 1 {
      bom = ""
      if (substr(t, 1, length(BOM)) == BOM) { bom = BOM; t = substr(t, length(BOM) + 1) }
      if (t == "---") { out(bom "---"); state = "front"; next }
      out(bom "---"); rest(); out("---"); state = "body"
      print t E; o++; next
    }
    state == "front" {
      if (skip && t ~ /^[ \t]+- /) next
      skip = 0
      if (t == "---") { rest(); out("---"); state = "body"; next }
      if (match(t, /^[A-Za-z0-9_-]+:/)) {
        k = substr(t, 1, RLENGTH - 1)
        if ((k in val) && !(k in done)) {
          for (i = 1; i <= n; i++) if (keys[i] == k) added(i)
          skip = 1; next
        }
      }
      print; o++; next
    }
    { print; o++ }
    END { if (state == "front") { rest(); out("---") } }
  ' "$1" > "$3"
}

# fm_repo <address>: the repository at an address, as name<TAB>url<TAB>items. GitHub (also git@github.com:owner/repo
# and the short owner/repo), Azure DevOps and GitLab give items; another host gives the address alone. Fails when the
# address is none of these.
fm_repo() {
  local a=$1 host path name url items="" org rest
  a=$(printf '%s' "$a" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  case $a in
    git@ssh.dev.azure.com:v3/*)
      rest=${a#git@ssh.dev.azure.com:v3/}; rest=${rest%.git}
      org=${rest%%/*}; rest=${rest#*/}
      a="https://dev.azure.com/$org/${rest%/*}/_git/${rest##*/}" ;;
    git@*:*) host=${a#git@}; host=${host%%:*}; a="https://$host/${a#*:}" ;;
    ssh://*) a=${a#ssh://}; a=${a#*@}; a="https://$a" ;;
    http://*|https://*) ;;
    *)
      if printf '%s' "$a" | grep -Eq '^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$'; then a="https://github.com/$a"; else return 1; fi ;;
  esac
  a=${a%/}; a=${a%.git}; a=${a%/}
  case $a in *' '*) return 1 ;; esac
  host=${a#*://}; host=${host%%/*}; path=${a#*://"$host"}; path=${path#/}
  [ -n "$path" ] || return 1
  case $host in
    github.com|www.github.com)
      printf '%s' "$path" | grep -Eq '^[^/]+/[^/]+' || return 1
      path=$(printf '%s' "$path" | cut -d/ -f1-2); path=${path%.git}
      url="https://github.com/$path"; items="$url/issues/"; name=${path#*/} ;;
    dev.azure.com|*.visualstudio.com)
      case $path in */_git/*) ;; *) return 1 ;; esac
      rest=${path#*/_git/}; name=${rest%%/*}
      url="https://$host/${path%%/_git/*}/_git/$name"; items="$url/pullrequest/" ;;
    gitlab.com)
      path=${path%%/-/*}; url="https://gitlab.com/$path"; items="$url/-/issues/"; name=${path##*/} ;;
    *) url=$a; name=${path##*/} ;;
  esac
  [ -n "$name" ] || return 1
  printf '%s\t%s\t%s\n' "$name" "$url" "$items"
}
