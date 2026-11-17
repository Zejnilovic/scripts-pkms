# shellcheck shell=bash
# lib/pkm/cmd/config.sh: pkm config: the settings with their values and where each comes from.
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

cmd_config() {
  local key
  [ $# -le 1 ] || die 2 "Usage: pkm config [<key>]"
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
