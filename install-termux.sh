#!/data/data/com.termux/files/usr/bin/bash
set -eu

project_root="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
python_bin="${THRILLA_PYTHON:-python}"

if ! command -v "$python_bin" >/dev/null 2>&1; then
    echo "Python is missing. Install it first:" >&2
    echo "  pkg install python git -y" >&2
    exit 1
fi

"$python_bin" -c \
    'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' || {
    echo "Thrilla requires Python 3.9 or newer." >&2
    exit 1
}

if [ -n "${THRILLA_INSTALL_DIR:-}" ]; then
    install_dir="$THRILLA_INSTALL_DIR"
elif [ -n "${PREFIX:-}" ] && [ -d "$PREFIX/bin" ] && [ -w "$PREFIX/bin" ]; then
    install_dir="$PREFIX/bin"
else
    install_dir="$HOME/.local/bin"
fi

mkdir -p "$install_dir"

state_root="${THRILLA_STATE_ROOT:-${THRILLA_HOME:-$HOME/.thrilla-zilla}}"
launcher="$install_dir/thrilla"

commit="$(
    git -C "$project_root" rev-parse --short=12 HEAD 2>/dev/null ||
    printf 'local-source'
)"

if [ -n "$(git -C "$project_root" status --porcelain 2>/dev/null || true)" ]; then
    commit="${commit}-dirty"
fi

timestamp="$(date -u +%Y%m%d-%H%M%S)"

if [ -e "$launcher" ] || [ -L "$launcher" ]; then
    backup="$launcher.pre-atomic-$timestamp"
    cp -a "$launcher" "$backup"
    echo "Preserved existing launcher: $backup"
fi

echo "Installing verified atomic Thrilla release..."

PYTHONPATH="$project_root${PYTHONPATH:+:$PYTHONPATH}" \
"$python_bin" -m thrilla release install \
    --project-root "$project_root" \
    --state-root "$state_root" \
    --commit "$commit" \
    --timestamp "$timestamp" \
    --launcher "$launcher" \
    --launcher-platform posix

echo
echo "THRILLA-ZILLA ATOMIC INSTALL COMPLETE"
echo "State:    $state_root"
echo "Launcher: $launcher"
echo
echo "Verify:"
echo "  thrilla --version"
echo "  thrilla release status --json"
echo
echo "Rollback:"
echo "  thrilla release rollback"
