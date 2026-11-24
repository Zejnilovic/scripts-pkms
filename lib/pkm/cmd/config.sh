# shellcheck shell=bash
# lib/pkm/cmd/config.sh: pkm config: the settings with their values and where each comes from; config <key> <value>
# sets one.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

# config_line <key>: "key<TAB>value<TAB>source" for one setting. A default with <type> or <name> names the key's suffix.
config_line() {
  local info def suffix pair
  info=$(setting_known "$1") || return 1
  def=${info#*|}
  suffix=${1#*_}
  def=${def//<type>/$suffix}
  def=${def//<name>/$suffix}
  [ "$def" != - ] || def=""
  pair=$(config_with_source "$1" "$def")
  printf '%s\t%s\n' "$1" "$pair"
}

# config_set <key> <value> <user yes|no>: writes key=value in the file the key's scope names: .pkm/config for a vault
# setting, the user config for a user setting, and for one of both the vault's, or the user's with --user. A key
# already set gets the new value on its last line; else the line is appended. The file's line ending is kept. Prints
# <file>:<line>: key=value.
config_set() {
  local key=$1 value=$2 user=$3 info scope def file eol tab cr n
  tab=$(printf '\t'); cr=$(printf '\r')
  info=$(setting_known "$key") || die 2 "Unknown setting: $key. pkm config lists every setting."
  scope=${info%%|*}; def=${info#*|}
  case $value in
    '') die 2 "pkm config $key needs a value; pkm config $key shows the one it has." ;;
    *"$tab"*|*"$cr"*|*'
'*) die 2 "A setting's value is one line, without tabs: $key" ;;
  esac
  case $def in
    yes|no) case $value in yes|no) ;; *) die 2 "$key is yes or no, got: $value" ;; esac ;;
  esac
  case $scope.$user in
    vault.yes) die 2 "$key is a vault setting: it goes in .pkm/config, without --user." ;;
    vault.no|both.no) file=.pkm/config ;;
    *) file=$(user_config_file) ;;
  esac
  mkdir -p "$(dirname "$file")" || die 1 "Can't create $(dirname "$file")."
  [ -f "$file" ] || : > "$file"
  eol=$(eol_of "$file")
  n=$(KEY=$key awk '{ t = $0; sub(/\r$/, "", t) } t ~ "^[ \t]*" ENVIRON["KEY"] "[ \t]*=" { n = NR } END { print n + 0 }' "$file")
  if [ "$n" -gt 0 ]; then
    LINE="$key=$value$eol" awk -v n="$n" '{ if (NR == n) print ENVIRON["LINE"]; else print }' "$file" > "$tmp/config-new"
  else
    # A last line without its line end gets one first, so the new line starts on its own.
    { cat "$file"; if [ -s "$file" ] && [ -n "$(tail -c 1 "$file")" ]; then printf '\n'; fi; printf '%s=%s%s\n' "$key" "$value" "$eol"; } > "$tmp/config-new"
    n=$(awk 'END { print NR }' "$tmp/config-new")
  fi
  cat "$tmp/config-new" > "$file" || die 1 "Can't write $file."
  printf '%s:%s: %s=%s\n' "$file" "$n" "$key" "$value"
}

cmd_config() {
  local key="" value="" count=0 user=no arg
  for arg in "$@"; do
    case $arg in
      --user) user=yes ;;
      *) count=$((count + 1)); if [ "$count" = 1 ]; then key=$arg; else value=$arg; fi ;;
    esac
  done
  [ "$count" -le 2 ] || die 2 "Usage: pkm config [<key> [<value>] [--user]]"
  if [ "$count" -eq 2 ]; then config_set "$key" "$value" "$user"; return $?; fi
  [ "$user" = no ] || die 2 "Usage: pkm config <key> <value> --user"
  if [ "$count" -eq 1 ]; then set -- "$key"; else set --; fi
  if [ $# -eq 1 ]; then
    setting_known "$1" > /dev/null || die 2 "Unknown setting: $1. pkm config lists every setting."
    config_line "$1"
    return 0
  fi
  while IFS='|' read -r key _ _ _; do
    case $key in
      *"<"*)
        for name in $({ file_keys .pkm/config; file_keys "$(user_config_file)"; } | grep "^${key%%<*}" | LC_ALL=C sort -u); do
          config_line "$name"
        done ;;
      *) config_line "$key" ;;
    esac
  done <<EOF
$(settings_list)
EOF
}
