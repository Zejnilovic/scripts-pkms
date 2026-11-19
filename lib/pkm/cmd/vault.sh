# shellcheck shell=bash
# lib/pkm/cmd/vault.sh: pkm vault (the vault's folder) and pkm vaults [--json] (the named vaults of the user config,
# each name<TAB>folder<TAB>ok or missing; --json gives name, path and state).
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_vault() {
  printf '%s\n' "$vault"
}

cmd_vaults() {
  local file name path state json=no arg
  for arg in "$@"; do
    case $arg in
      --json) json=yes ;;
      *) die 2 "Usage: pkm vaults [--json]" ;;
    esac
  done
  [ "$json" = no ] || need_jq
  file=$(user_config_file)
  [ -f "$file" ] || return 0
  awk -F= '/^[[:space:]]*vault_[A-Za-z0-9_-]+[[:space:]]*=/ {
    name = $1; sub(/^[[:space:]]*vault_/, "", name); sub(/[[:space:]]+$/, "", name)
    path = substr($0, index($0, "=") + 1); sub(/^[[:space:]]+/, "", path); sub(/[[:space:]]+$/, "", path)
    print name "\t" path }' "$file" > "$tmp/named-vaults"
  while IFS=$'\t' read -r name path; do
    if [ "${path%%/*}" = "~" ]; then path=$HOME/${path#*/}; fi
    if [ -d "$path/.pkm" ]; then state=ok; else state=missing; fi
    printf '%s\t%s\t%s\n' "$name" "$path" "$state"
  done < "$tmp/named-vaults" > "$tmp/vaults"
  if [ "$json" = no ]; then cat "$tmp/vaults"; return 0; fi
  jq -R -c 'split("\t") as $f | {name: $f[0], path: $f[1], state: $f[2]}' "$tmp/vaults"
}
