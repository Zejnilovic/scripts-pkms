# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/across.sh: pkm --vaults [<a,b>] <tasks | upcoming | since> [arguments]: the command in each named vault
# (vault_<name> in the user config), in the order given, or of the vaults= setting when no names are given. Each vault
# with records gets a section, == vault <name>, holding what pkm -V <name> prints, with paths relative to that vault;
# --json adds a vault field to each record instead. Nothing is copied or linked between vaults. Exit 0 when a vault
# had records, 1 when none had, 2 for a wrong call. Sourced by bin/pkm. Defines functions only.

cmd_across() {
  local names=$1 command=$2 json=no arg name list="" rc any=no source="--vaults"
  shift 2
  [ -z "$vault_name" ] && [ -z "$vault_option" ] || die 2 "Use one of --vaults, -V and --vault, not two."
  case $command in
    tasks|upcoming|since) ;;
    *) die 2 "--vaults works with tasks, upcoming and since, not $command." ;;
  esac
  for arg in "$@"; do
    case $arg in
      --json) json=yes ;;
      --ics) die 2 "--ics is one vault's calendar: run pkm -V <name> upcoming --ics in each." ;;
    esac
  done
  if [ -z "$names" ]; then
    names=$(user_config_value vaults); source="vaults= in $(user_config_file)"
    [ -n "$names" ] || die 2 "--vaults needs names, such as pkm --vaults work,family tasks, or vaults=work,family in $(user_config_file)."
  fi
  [ "$json" = no ] || need_jq
  # Every name is checked before any vault is read, so a wrong one prints nothing.
  case ",$names," in *,,*) die 2 "A list of vaults has a name between each comma, got: $names (from $source)." ;; esac
  for name in $(printf '%s\n' "$names" | tr ',' ' '); do
    case $name in
      *[!A-Za-z0-9_-]*) die 2 "A vault name has letters, digits, '-' and '_' only, got: $name (from $source)." ;;
    esac
    arg=$(user_config_value "vault_$name")
    [ -n "$arg" ] || die 2 "No vault named $name: add vault_$name=<folder> to $(user_config_file)."
    [ -d "$arg/.pkm" ] || die 2 "No vault in $arg: it has no .pkm folder (from vault_$name in $(user_config_file))."
    list="$list $name"
  done
  for name in $list; do
    rc=0
    "$BASH" "$pkm_home/bin/pkm" -V "$name" "$command" "$@" > "$tmp/across-out" || rc=$?
    case $rc in
      0) ;;
      1) continue ;;
      *) exit "$rc" ;;
    esac
    [ -s "$tmp/across-out" ] || continue
    any=yes
    if [ "$json" = yes ]; then jq -c --arg vault "$name" '. + {vault: $vault}' "$tmp/across-out"
    else echo "== vault $name"; cat "$tmp/across-out"; fi
  done
  [ "$any" = yes ]
}
