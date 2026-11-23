# shellcheck shell=bash
# lib/pkm/ask.sh: asking on a terminal. A command missing the text, task or note it needs asks for it when pkm runs on
# a terminal (stdin and stderr) and the picker setting is not off; scripts, editors and agents get the usage error
# (exit 2) as before. Prompts and lists go to stderr, so stdout keeps the command's result. An empty answer cancels
# (exit 1). Picking uses fzf when the picker setting is auto or fzf and fzf is installed, else a numbered list.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"

# picker_kind: sets picker to fzf, list or off, from the picker setting (auto, fzf, list or off). It runs in pkm's own
# shell, not in $(...), so a wrong setting ends pkm.
picker_kind() {
  picker=$(config picker auto)
  case $picker in
    auto|fzf) if command -v fzf >/dev/null 2>&1; then picker=fzf; else picker=list; fi ;;
    list|off) ;;
    *) die 2 "The picker setting must be auto, fzf, list or off, got: $picker" ;;
  esac
}

# can_ask: succeeds when pkm may ask: stdin and stderr are a terminal and the picker setting is not off.
can_ask() {
  [ -t 0 ] && [ -t 2 ] || return 1
  picker_kind
  [ "$picker" != off ]
}

# need_answer <usage>: a missing argument. Without a terminal, dies with the usage (exit 2).
need_answer() {
  can_ask || die 2 "$1"
}

# ask_line <prompt>: reads one line from the terminal into answer, with line editing. Fails on an empty line or the end
# of input.
ask_line() {
  answer=""
  IFS= read -r -e -p "$1" answer || { echo >&2; return 1; }
  case $answer in *[![:space:]]*) return 0 ;; esac
  return 1
}

# ask_text <prompt>: like ask_line, and an empty answer cancels (exit 1).
ask_text() {
  ask_line "$1" || die 1 "Cancelled: nothing changed."
}

# pick <prompt> <file>: the user picks one line of the file, whose lines are key<TAB>shown text, and answer is its key.
# Fails when the user cancels. In the numbered list, words narrow the list and a number picks.
pick() {
  local prompt=$1 file=$2 tab n shown_max choice
  tab=$(printf '\t')
  [ -s "$file" ] || return 1
  picker_kind
  if [ "$picker" = fzf ]; then
    choice=$(fzf --prompt "$prompt> " --delimiter "$tab" --with-nth 2.. --height 40% --reverse --no-multi \
      --tiebreak index < "$file") || return 1
    answer=${choice%%"$tab"*}
    [ -n "$answer" ]
    return
  fi
  shown_max=$(config limit 30)
  cp "$file" "$tmp/pick-list"
  while :; do
    n=$(wc -l < "$tmp/pick-list" | tr -d ' ')
    MAX=$shown_max awk -F "$tab" '
      NR <= ENVIRON["MAX"] + 0 { printf "%3d  %s\n", NR, $2 }
      END { if (NR > ENVIRON["MAX"] + 0) printf "     and %d more: type words to narrow the list\n", NR - ENVIRON["MAX"] }
    ' "$tmp/pick-list" >&2
    ask_line "$prompt: a number, or words to narrow the list (Enter cancels): " || return 1
    answer=$(printf '%s' "$answer" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
    case $answer in
      *[!0-9]*)
        WORDS=$answer awk -F "$tab" '
          BEGIN { n = split(tolower(ENVIRON["WORDS"]), word, " ") }
          { text = tolower($2); for (i = 1; i <= n; i++) if (!index(text, word[i])) next; print }
        ' "$tmp/pick-list" > "$tmp/pick-narrow"
        if [ -s "$tmp/pick-narrow" ]; then mv "$tmp/pick-narrow" "$tmp/pick-list"
        else printf 'Nothing in the list has: %s\n' "$answer" >&2; fi ;;
      *)
        if [ "$answer" -ge 1 ] && [ "$answer" -le "$n" ]; then
          answer=$(sed -n "${answer}p" "$tmp/pick-list" | cut -f 1)
          return 0
        fi
        printf 'Pick a number from 1 to %s.\n' "$n" >&2 ;;
    esac
  done
}

# pick_one <prompt> <file> <message when empty>: pick, and the file empty or a cancel ends pkm (exit 1).
pick_one() {
  [ -s "$2" ] || die 1 "$3"
  pick "$1" "$2" || die 1 "Cancelled: nothing changed."
}

# ask_tasks <file>: the open tasks, in the order of pkm tasks, as key<TAB>shown lines for pick: path:line, then the
# task's text without its box and the path:line.
ask_tasks() {
  (cmd_tasks) > "$tmp/ask-tasks" 2>/dev/null || true
  awk '
    match($0, /^[^:]*\.md:[0-9]+: /) {
      key = substr($0, 1, RLENGTH - 2); text = substr($0, RLENGTH + 1); sub(/^- \[ \] /, "", text)
      print key "\t" text "  " key
    }
  ' "$tmp/ask-tasks" > "$1"
}

# ask_notes <file>: every note's name, as key<TAB>shown lines for pick: the name and its type.
ask_notes() {
  (cmd_names) 2>/dev/null | awk -F '\t' -v OFS='\t' '{ print $1, $1 "  (" $2 ")" }' > "$1" || true
}

# ask_note <usage>: a note's name, picked from the vault's notes, into answer.
ask_note() {
  need_answer "$1"
  ask_notes "$tmp/ask-notes"
  pick_one "Note" "$tmp/ask-notes" "No notes in the vault yet: pkm new <type> <title> makes one."
}
