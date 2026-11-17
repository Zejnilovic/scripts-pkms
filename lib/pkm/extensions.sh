# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/extensions.sh: extensions. An unknown command pkm <name> runs pkm-<name> from PATH, with the same arguments, the
# vault in PKM_VAULT, and its exit status, as git does. Built-in commands always win. Names are lowercase letters, digits
# and hyphens. Extensions are found on PATH only: a shared vault cloned from git must not be able to run a script. Sourced
# by bin/pkm. Defines functions only.

# extension_name_ok <name>: succeeds for a name an extension may have.
extension_name_ok() {
  printf '%s\n' "$1" | grep -Eq '^[a-z0-9][a-z0-9-]*$'
}

# run_extension <name> <args...>: runs pkm-<name> from PATH in place of pkm (it does not return when it runs). Fails when
# there is no such extension, so the caller can say the command is unknown.
run_extension() {
  local name=$1 found
  shift
  extension_name_ok "$name" || return 1
  found=$(command -v "pkm-$name") || return 1
  [ -f "$found" ] && [ -x "$found" ] || return 1
  PKM_VAULT=$vault exec "$found" "$@"
}

# extension_table: "name<TAB>Extension<TAB>summary" for each extension on PATH, the first one found for a name. A built-in
# name is not listed, since it is the command.
extension_table() {
  printf '%s\n' "$PATH" | tr ':' '\n' | while IFS= read -r dir; do
    [ -n "$dir" ] && [ -d "$dir" ] || continue
    for file in "$dir"/pkm-*; do
      [ -f "$file" ] && [ -x "$file" ] || continue
      name=${file##*/pkm-}
      extension_name_ok "$name" || continue
      is_builtin "$name" && continue
      printf '%s\tExtension\tan extension on PATH: pkm-%s\n' "$name" "$name"
    done
  done | awk -F "$(printf '\t')" '!seen[$1]++'
}
