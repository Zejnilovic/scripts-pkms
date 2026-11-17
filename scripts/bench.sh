#!/usr/bin/env bash
# Times pkm on a synthetic vault of about N files: day pages in month folders, notes with links, aliases and tasks,
# and a .pkmignore. It times a cold index, then each warm command. Targets: cold index under 3 s; each warm command
# under 1 s. Exits 1 when a target is missed. Works with bash 3.2 (macOS) and Git Bash. Usage: bash scripts/bench.sh 10000
set -u
n=${1:-10000}
case $n in ''|*[!0-9]*) echo "usage: bash scripts/bench.sh <number of files>" >&2; exit 2 ;; esac
root=$(cd "$(dirname "$0")/.." && pwd)
pkm="$root/bin/pkm"
work=$(mktemp -d "${TMPDIR:-/tmp}/pkm-bench.XXXXXX") || exit 2
trap 'rm -rf "$work"' EXIT
vault="$work/vault"
mkdir -p "$vault/.pkm" "$vault/archive/old" "$vault/drafts" "$work/config"
echo "format=1" > "$vault/.pkm/config"
printf '%s\n' '# Synthetic vault' 'drafts/' > "$vault/.pkmignore"
# One awk pass writes the files: half day pages, half notes, a few archived notes, and a folder pkm ignores.
awk -v n="$n" -v root="$vault" '
  function w(path, text) { print text > path; close(path) }
  BEGIN {
    for (i = 1; i <= n; i++) {
      if (i % 2 == 0) {
        mm = sprintf("%02d", 1 + int(i / 62) % 12); dd = sprintf("%02d", 1 + i % 28)
        dir = root "/daybook/2026/" mm; system("mkdir -p \"" dir "\"")
        name = "2026-" mm "-" dd "-" i
        w(dir "/" name ".md", "# " name "\n\n## Tasks\n\n- [ ] Task " i " (due 2026-12-" dd ")\n\n## Log\n\n- 09:00 [[note-" (i - 1) "]] and [[alias-" (i - 3) "]] mention budget " i "\n- 10:00 Plain line " i "\n")
      } else {
        dir = (i % 20 == 1) ? root "/archive/old" : root "/notes"
        if (dir == root "/notes") system("mkdir -p \"" dir "\"")
        kind = (i % 4 == 1) ? "person" : "project"
        task = (i % 10 == 1) ? "\n- [ ] Follow up on note " i " (due 2026-12-" sprintf("%02d", 1 + i % 28) ")\n" : ""
        w(dir "/note-" i ".md", "---\ntype: " kind "\nstatus: active\naliases: [Alias " i "]\n---\n\n# Note " i "\n\nSee [[note-" (i - 2) "]] and [[note-" (i - 4) "]] about the budget.\n" task)
      }
    }
    system("mkdir -p \"" root "/drafts\"")
    for (i = 1; i <= int(n / 100); i++) w(root "/drafts/draft-" i ".md", "# Draft " i "\n\n[[note-1]]\n")
  }
' /dev/null
files_count=$(find "$vault" -type f | wc -l | tr -d ' ')
export PKM_NOW=20261116083000 XDG_CONFIG_HOME="$work/config"
cd "$vault" || exit 2
# timed <command...>: prints the wall-clock seconds and the exit status, measured by python's clock.
timed() {
  python3 -c 'import subprocess, sys, time
t = time.perf_counter()
r = subprocess.run(sys.argv[1:], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("%.2f %d" % (time.perf_counter() - t, r.returncode))' "$@"
}
read -r cold_s cold_rc <<EOF
$(rm -rf .pkm/cache; timed /bin/bash "$pkm" index)
EOF
echo "Synthetic vault: $files_count files in $vault"
echo "cold index: ${cold_s} s (exit $cold_rc)"
status=0
[ "$cold_rc" = 0 ] || status=1
awk -v s="$cold_s" 'BEGIN { exit (s + 0 < 3) ? 0 : 1 }' || status=1
note=$((n / 4 * 2 + 1))
for command in "find budget" "backlinks note-$note" "tasks" "path note-$note" "names"; do
  # shellcheck disable=SC2086 # the command words are split on purpose
  timed /bin/bash "$pkm" $command > /dev/null
  read -r warm_s warm_rc <<EOF
$(timed /bin/bash "$pkm" $command)
EOF
  echo "warm $command: ${warm_s} s (exit $warm_rc)"
  [ "$warm_rc" = 0 ] || [ "$warm_rc" = 1 ] || status=1
  awk -v s="$warm_s" 'BEGIN { exit (s + 0 < 1) ? 0 : 1 }' || status=1
done
if [ "$status" = 0 ]; then echo "Targets met: cold index under 3 s, each warm command under 1 s."
else echo "A target was missed." >&2; fi
exit "$status"
