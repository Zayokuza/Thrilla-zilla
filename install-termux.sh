#!/data/data/com.termux/files/usr/bin/bash
set -eu

project_root="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
python_bin="${THRILLA_PYTHON:-python}"

if ! command -v "$python_bin" >/dev/null 2>&1; then
    echo "Python is missing. Install it first:" >&2
    echo "  pkg install python git -y" >&2
    exit 1
fi

"$python_bin" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' || {
    echo "Thrilla requires Python 3.9 or newer." >&2
    exit 1
}

echo "Checking Thrilla before installation..."
PYTHONPATH="$project_root${PYTHONPATH:+:$PYTHONPATH}" \
    "$python_bin" -m compileall -q "$project_root/thrilla"
PYTHONPATH="$project_root${PYTHONPATH:+:$PYTHONPATH}" \
    "$python_bin" -m unittest discover -s "$project_root/tests" -q

if [ -n "${THRILLA_INSTALL_DIR:-}" ]; then
    install_dir="$THRILLA_INSTALL_DIR"
    mkdir -p "$install_dir"
elif [ -n "${PREFIX:-}" ] && [ -d "$PREFIX/bin" ] && [ -w "$PREFIX/bin" ]; then
    install_dir="$PREFIX/bin"
else
    install_dir="$HOME/.local/bin"
    mkdir -p "$install_dir"
fi

launcher="$install_dir/thrilla"
source_launcher="$project_root/bin/thrilla"
if [ -e "$launcher" ] || [ -L "$launcher" ]; then
    existing="$(readlink -f "$launcher" 2>/dev/null || true)"
    expected="$(readlink -f "$source_launcher" 2>/dev/null || true)"
    if [ "$existing" != "$expected" ]; then
        backup="$launcher.previous.$(date +%Y%m%d-%H%M%S)"
        mv "$launcher" "$backup"
        echo "Preserved the previous launcher at $backup"
    fi
fi

chmod +x "$source_launcher"
ln -sfn "$source_launcher" "$launcher"
state_root="${THRILLA_STATE_ROOT:-$HOME/.thrilla-zilla}"
mkdir -p "$state_root"

echo
echo "THRILLA-ZILLA INSTALLED"
echo "Project: $project_root"
echo "Command: $launcher"
echo
echo "Start it with:"
echo "  thrilla"
echo
echo "Quick checks:"
echo "  thrilla doctor"
echo "  thrilla donors --problems"
