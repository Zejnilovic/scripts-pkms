# shellcheck shell=bash
# lib/pkm/cmd/completion.sh: pkm completion bash|zsh prints the shell's tab completion script. The script runs
# pkm __complete <words before the cursor> <word at the cursor>, which prints the candidates one a line, or :dirs or
# :files for the shell to complete paths itself. Commands and options come from command_table and command_options, so
# they never drift from the code; note names, template types, cycles and named vaults come from pkm itself. It writes
# nothing, and prints nothing when it can't tell (outside a vault, for example).
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_completion() {
  case ${1:-} in
    bash) cat <<'EOF'
# bash completion for pkm, printed by pkm completion bash. In ~/.bashrc: source <(pkm completion bash)
_pkm() {
  local line=${COMP_LINE:0:COMP_POINT} cur="" out word
  local -a words
  # Split on spaces only: bash would also split at the : of path:line.
  case "$line" in *[[:space:]]) ;; *) cur=${line##*[[:space:]]} ;; esac
  read -r -a words <<<"${line%"$cur"}"
  out=$(command pkm __complete "${words[@]:1}" "$cur" 2>/dev/null)
  COMPREPLY=()
  case "$out" in
    :dirs) compopt -o filenames 2>/dev/null; COMPREPLY=($(compgen -d -- "$cur")); return ;;
    :files) compopt -o filenames 2>/dev/null; COMPREPLY=($(compgen -f -- "$cur")); return ;;
  esac
  local trim=${cur%"${cur##*:}"}
  while IFS= read -r word; do
    case "$word" in "$cur"?*) COMPREPLY+=("${word#"$trim"}") ;; esac
  done <<<"$out"
}
complete -F _pkm pkm
EOF
      ;;
    zsh) cat <<'EOF'
#compdef pkm
# zsh completion for pkm, printed by pkm completion zsh. In ~/.zshrc, after compinit: source <(pkm completion zsh)
_pkm() {
  local -a out
  out=("${(@f)$(command pkm __complete "${(@)words[2,CURRENT-1]}" "${words[CURRENT]}" 2>/dev/null)}")
  case $out[1] in
    :dirs) _files -/ ;;
    :files) _files ;;
    *) compadd -- "${(@)out:#}" ;;
  esac
}
if [ "$funcstack[1]" = _pkm ]; then _pkm "$@"; else compdef _pkm pkm; fi
EOF
      ;;
    *) die 2 "Usage: pkm completion bash|zsh, for example in ~/.zshrc: source <(pkm completion zsh)" ;;
  esac
}

# complete_value_option <option>: succeeds for an option that takes the next word as its value.
complete_value_option() {
  case $1 in
    --vault|-V|--day|--due|--start|--every|--link|--stale|--name|--since|--type|--show|--quiet|--lines|--date|\
    --about|--under|--limit|--cycle|--answer|--require) return 0 ;;
  esac
  return 1
}

# complete_pkm <args>: runs pkm on the vault the words named, for its listing; prints nothing when it fails.
complete_pkm() {
  if [ -n "$c_name" ]; then bash "$pkm_home/bin/pkm" -V "$c_name" "$@"
  elif [ -n "$c_vault" ]; then bash "$pkm_home/bin/pkm" --vault "$c_vault" "$@"
  else bash "$pkm_home/bin/pkm" "$@"
  fi 2>/dev/null </dev/null
}

complete_notes() { complete_pkm names --limit 100000 | cut -f 1; }
complete_types() { complete_pkm templates | cut -f 1; }
complete_cycles() { complete_pkm cycle | cut -f 1; }
complete_days() { printf '%s\n' today tomorrow monday tuesday wednesday thursday friday saturday sunday; }

# cmd_complete <word>... <word at the cursor>: the candidates for the word at the cursor.
cmd_complete() {
  local c_vault="" c_name="" want="" cmd="" n=0 first="" cur across=no
  while [ $# -gt 1 ]; do
    if [ -n "$want" ]; then
      case $want in
        --vault) c_vault=$1 ;;
        -V) c_name=$1 ;;
        --vaults) case $1 in tasks|upcoming|since) cmd=$1 ;; *) across=yes ;; esac ;;
      esac
      want=""
    else
      case $1 in
        --vault|-V|--vaults) [ -n "$cmd" ] || want=$1 ;;
        -*) if [ -n "$cmd" ] && complete_value_option "$1"; then want=$1; fi ;;
        *) if [ -z "$cmd" ]; then cmd=$1; else n=$((n + 1)); [ "$n" != 1 ] || first=$1; fi ;;
      esac
    fi
    shift
  done
  cur=${1:-}
  case $c_vault in \~|\~/*) c_vault=$HOME${c_vault#\~} ;; esac

  case $want in
    --vault) echo :dirs; return ;;
    -V) complete_pkm vaults | cut -f 1; return ;;
    --vaults) complete_pkm vaults | cut -f 1; printf '%s\n' tasks upcoming since; return ;;
    --type) complete_types; return ;;
    --link|--about|--under) complete_notes; return ;;
    --cycle) complete_cycles; return ;;
    --every) printf '%s\n' 1d 1w 1m 1y; complete_cycles | grep -vx week; return ;;
    --due|--start|--day) complete_days; return ;;
    ?*) return ;;
  esac

  case $cur in
    -*)
      if [ -z "$cmd" ]; then echo --vault -V --vaults --help --version
      elif [ "$cmd" = new ] && [ "$first" = close ]; then command_options close
      else command_options "$cmd"; fi | tr ' ' '\n' | grep -v '^$'
      return ;;
  esac

  if [ -z "$cmd" ] && [ "$across" = yes ]; then printf '%s\n' tasks upcoming since; return; fi
  case $cmd:$n in
    :0|help:0) { command_table | cut -d '|' -f 1; extension_table | cut -f 1; } ;;
    tasks:0) printf '%s\n' open waiting someday 'done' ;;
    new:0) { complete_types; echo close; } | LC_ALL=C sort -u ;;
    backlinks:0|path:0|get:0|rename:0|mv:0|links:0) complete_notes ;;
    evidence:0) echo -; complete_notes ;;
    recall:0) echo add; complete_notes ;;
    recall:1) [ "$first" != add ] || complete_notes ;;
    post:0|strike:0|moved:0) echo :files ;;
    post:1) complete_notes ;;
    mv:1) echo :dirs ;;
    cycle:0) complete_cycles ;;
    since:0) echo last; complete_cycles ;;
    config:0) complete_pkm config | cut -f 1 ;;
    templates:0) echo eject ;;
    templates:1) [ "$first" != eject ] || complete_types ;;
    completion:0) printf '%s\n' bash zsh ;;
    example:0) example_names ;;
    example:1) echo :dirs ;;
  esac
  return 0
}
