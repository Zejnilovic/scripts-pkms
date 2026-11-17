# shellcheck shell=bash
# lib/pkm/cmd/version.sh: pkm version, and version --require <x.y> for a caller that needs at least that release.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_version() {
  case ${1:-} in
    '') echo "$pkm_version" ;;
    --require)
      [ $# -eq 2 ] || die 2 "Usage: pkm version --require <x.y>"
      printf '%s\n' "$2" | grep -Eq '^[0-9]+\.[0-9]+(\.[0-9]+)?$' || die 2 "A version looks like 0.1 or 0.1.0, got: $2"
      # Exit 0 when pkm's release is at least the one asked for, else 1; a missing part counts as 0.
      awk -v have="$pkm_version" -v want="$2" 'BEGIN {
        split(have, h, "."); split(want, w, ".")
        for (i = 1; i <= 3; i++) { if (h[i] + 0 > w[i] + 0) exit 0; if (h[i] + 0 < w[i] + 0) exit 1 }
        exit 0 }' ;;
    *) die 2 "Usage: pkm version [--require <x.y>]" ;;
  esac
}
