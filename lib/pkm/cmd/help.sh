# shellcheck shell=bash
# lib/pkm/cmd/help.sh: pkm help: the usage text; help --all: one line per command, name<TAB>group<TAB>summary; help
# <command>: that command's summary, its entries in the usage text and its options.
# command_table is the one list of commands; docs/contract.md must describe each of them (a test checks it).
# Sourced by bin/pkm. Defines functions only.

command_table() {
  cat <<'EOF'
day|Capture|the day's page, created when missing; prints its path
add|Capture|an entry at the end of the day's Log, printed as path:line
todo|Tasks|a task for today, under its Tasks section; prints path:line
done|Tasks|marks the one open task that matches as done, or as dropped with --drop; moves a routine on, or to the day --next gives
moved|Tasks|strikes a task or an event whose date changed and writes it again with the new date; prints path:line: text
tasks|Tasks|the open tasks of every note, in groups: overdue, due soon, waiting, the rest
upcoming|Review|birthdays, due tasks, events and dates in the next days
cycle|Review|the period of a cycle holding a date: its first and last day
since|Review|what happened since a date: notes, log, tasks, marked entries and names
close|Review|the close of a period: tasks, open questions, what is due, marked entries, names, quiet notes and ideas
recall|Review|the recall questions due today or earlier; recall <path:line> yes|no moves a question on the ladder; recall add <note> <question> writes one
new|Notes|a note of a type, made from its template
backlinks|Find|every line that links a note, by name, slug or alias
names|Find|every note's name, type, path and aliases, by name, from the cache
index|Find|brings the cache up to date; --rebuild starts it again
rename|Notes|renames a note and rewrites every link that names it; --dry-run lists the changes
mv|Notes|moves a note into a folder; its links keep working
path|Find|the file a name, slug, alias or link points to
find|Find|the lines with every word, in any order
list|Find|the notes whose frontmatter matches
overview|Find|the shape of the vault: areas, projects and resources, each with the notes that are part of it
tags|Find|every tag with its count
check|Check|broken links, duplicate names, alias clashes, secrets, merge conflicts and notices
evidence|Check|each summary line must link its source; --verify checks the links, paths and lines
links|Find|each web address in the notes, with its place (links --external)
get|Notes|a note, or one section of it, between a header and a footer; --lines takes a range
post|Notes|copies lines of a page into a note's section, with the page as their source
strike|Notes|strikes a line through when it is no longer true, and links today's page
doctor|Setup|the tools pkm uses, and the settings
init|Setup|sets up a vault: .pkm/config, .pkm/.gitignore and .pkmignore
vault|Setup|the vault's folder
vaults|Setup|the named vaults of the user config
config|Setup|every setting, its value and where it comes from
templates|Setup|each template type and where it comes from
version|Setup|the pkm release; --require checks a minimum
help|Setup|the usage text; --all lists every command
completion|Setup|the shell's tab completion script, for bash or zsh
EOF
}

# command_options <command>: the long options a command accepts, besides the global ones (--vault and -V, before the
# command). The listing options are for the commands that print a listing.
command_options() {
  case $1 in
    find) echo "--live --json --abs --limit" ;;
    backlinks) echo "--since --under --json --abs --limit" ;;
    path) echo "--json --abs --limit" ;;
    check) echo "--json --abs --limit --urls" ;;
    links) echo "--external --json --abs --limit" ;;
    recall) echo "--json --abs --limit --answer" ;;
    evidence) echo "--verify" ;;
    get) echo "--lines --plain" ;;
    list) echo "--all --show --quiet --under --json --abs --limit" ;;
    overview|tags|vaults) echo "--json" ;;
    upcoming) echo "--ics --json" ;;
    names) echo "--type --json --abs --limit" ;;
    index) echo "--rebuild" ;;
    rename) echo "--dry-run --no-alias" ;;
    tasks) echo "--all --link --for --under --stale --json --abs --limit" ;;
    day) echo "--edit" ;;
    cycle) echo "--date --json" ;;
    since) echo "--about --under --seen --sum --json --limit" ;;
    close) echo "--cycle --date --quarter --json" ;;
    add) echo "--day --file" ;;
    todo) echo "--due --high --low --waiting --someday --start --every --in" ;;
    done) echo "--drop --next" ;;
    new) echo "--name" ;;
    templates) echo "--user" ;;
    version) echo "--require" ;;
    help) echo "--all" ;;
    *) echo "" ;;
  esac
}

# check_options <command> <args...>: an unknown long option is a usage error (exit 2) with one line on stderr.
check_options() {
  local command=$1 key allowed arg
  shift
  # new close takes the options of close (--cycle, --date), not those of new.
  key=$command
  if [ "$command" = new ] && [ "${1:-}" = close ]; then key=close; fi
  allowed=" $(command_options "$key") "
  for arg in "$@"; do
    case $arg in
      --*) case $allowed in *" $arg "*) ;; *) die 2 "pkm $command has no option $arg: pkm help $command lists its options." ;; esac ;;
    esac
  done
}

# is_builtin <name>: succeeds for a command pkm has, and for its help and version spellings.
is_builtin() {
  case $1 in -h|--help|--version) return 0 ;; esac
  command_table | cut -d '|' -f 1 | grep -qx -- "$1"
}

cmd_help() {
  case ${1:-} in
    '') usage ;;
    --all) command_table | awk -F '|' -v OFS='\t' '{ name = $1; group = $2; sub(/^[^|]*[|][^|]*[|]/, ""); print name, group, $0 }'
           extension_table ;;
    -*) die 2 "Usage: pkm help [--all | <command>]" ;;
    *) [ $# -eq 1 ] || die 2 "Usage: pkm help [--all | <command>]"; command_help "$1" ;;
  esac
}

# command_help <name>: "pkm <name> (<group>): <summary>", the command's entries in the usage text, and its options.
command_help() {
  local head options
  head=$(command_table | NAME=$1 awk -F '|' '$1 == ENVIRON["NAME"] {
    name = $1; group = $2; sub(/^[^|]*[|][^|]*[|]/, ""); print "pkm " name " (" group "): " $0 }')
  if [ -z "$head" ]; then
    head=$(extension_table | NAME=$1 awk -F '\t' '$1 == ENVIRON["NAME"] { print "pkm " $1 " (" $2 "): " $3 }')
    [ -n "$head" ] || die 2 "pkm help: there is no command $1; pkm help --all lists them."
    echo "$head"
    return 0
  fi
  echo "$head"
  echo
  # An entry is a line indented by two spaces whose first word is the name, and the lines indented further below it.
  usage | NAME=$1 awk '
    /^  [^ ]/ { split(substr($0, 3), word, " "); on = (word[1] == ENVIRON["NAME"]); if (on) print; next }
    /^   / { if (on) print; next }
    { on = 0 }'
  options=$(command_options "$1")
  if [ -n "$options" ]; then echo; echo "Options: $options"; fi
}
