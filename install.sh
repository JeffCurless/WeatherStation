#!/usr/bin/env bash
# weather-station installer.
#
# Creates a dedicated system user, copies weather_station/ to
# /opt/weather-station, writes config.json (unless one already exists),
# installs OS/pip dependencies, installs the systemd unit, and enables the
# service. Safe to re-run: code and unit file are refreshed every time,
# config is left alone unless --force-config is given.
#
# Usage: sudo ./install.sh
#        sudo ./install.sh --dry-run       # preview without changing anything
#        sudo ./install.sh --skip-deps     # skip apt/pip installs (already done, or offline)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

INSTALL_ROOT="/opt/weather-station"
CONFIG_DIR="/etc/weather-station"
SERVICE_USER="weather-station"
FORCE_CONFIG=0
INSTALL_DEPS=1
ENABLE_SERVICE=1
DRY_RUN=0

usage() {
    cat <<EOF
Usage: sudo $0 [options]

Installs weather-station as a systemd service.

Options:
  --install-root PATH   Where to copy code (default: $INSTALL_ROOT)
  --config-dir PATH     Where to write config.json (default: $CONFIG_DIR)
  --force-config        Overwrite an existing config.json with config/config.example.json
  --skip-deps           Install the service but don't try to apt/pip install its
                         dependencies (use if you've already installed them, or
                         have no internet access on this box)
  --no-enable           Install but don't enable/start the service
  --dry-run             Print what would be done without changing anything
  -h, --help            Show this help
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --install-root) INSTALL_ROOT="$2"; shift 2 ;;
        --config-dir) CONFIG_DIR="$2"; shift 2 ;;
        --force-config) FORCE_CONFIG=1; shift ;;
        --skip-deps) INSTALL_DEPS=0; shift ;;
        --no-enable) ENABLE_SERVICE=0; shift ;;
        --dry-run) DRY_RUN=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [ "$DRY_RUN" -eq 0 ] && [ "$(id -u)" -ne 0 ]; then
    echo "error: must run as root (or pass --dry-run to preview)" >&2
    exit 1
fi

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "+ $*"
    else
        "$@"
    fi
}

echo "== weather-station install =="
echo "repo:         $REPO_ROOT"
echo "install root: $INSTALL_ROOT"
echo "config dir:   $CONFIG_DIR"
echo

# --- system user -------------------------------------------------------
if id "$SERVICE_USER" >/dev/null 2>&1; then
    echo "user $SERVICE_USER already exists"
else
    run useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

for grp in gpio spi i2c; do
    if getent group "$grp" >/dev/null 2>&1; then
        run usermod -aG "$grp" "$SERVICE_USER"
    else
        echo "note: group '$grp' doesn't exist on this system, skipping (fine off-Pi)"
    fi
done

# --- copy code -----------------------------------------------------------
run mkdir -p "$INSTALL_ROOT"
run cp -r "$REPO_ROOT/weather_station" "$INSTALL_ROOT/"
run chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_ROOT"

# --- config --------------------------------------------------------------
CONFIG_FILE="$CONFIG_DIR/config.json"
run mkdir -p "$CONFIG_DIR"
if [ -f "$CONFIG_FILE" ] && [ "$FORCE_CONFIG" -eq 0 ]; then
    echo "config exists, leaving it alone: $CONFIG_FILE (use --force-config to overwrite)"
else
    run cp "$REPO_ROOT/config/config.example.json" "$CONFIG_FILE"
    echo "wrote $CONFIG_FILE"
    echo "  -> edit its latitude/longitude for your location (see config/README.md)"
fi
run chown -R "$SERVICE_USER:$SERVICE_USER" "$CONFIG_DIR"

# --- OS/pip dependencies ---------------------------------------------------
# Debian/Raspberry Pi OS (bookworm and newer) mark the system Python as
# "externally managed" (PEP 668), so `pip3 install` outside a venv is
# refused. gpiozero, Pillow, and numpy have proper apt packages, so those
# come from apt; `inky` doesn't, so it goes into a --system-site-packages
# venv, which both gives pip somewhere it's allowed to write and reuses the
# apt-installed Pillow/numpy instead of rebuilding them from source on ARM.
# python3-numpy matters, not just python3-pil: without it, pip pulls its
# own numpy wheel when installing inky, and that wheel dynamically links
# libopenblas.so.0 without bundling it (crash: "ImportError:
# libopenblas.so.0: cannot open shared object file"). python3-lgpio
# matters too: without a modern gpiozero backend installed, it silently
# falls back to its deprecated /sys/class/gpio pin factory, which fails to
# even export a pin on current Raspberry Pi OS kernels. See
# docs/deployment.md for all of this in more detail.
VENV_DIR="$INSTALL_ROOT/venv"

if [ "$INSTALL_DEPS" -eq 1 ]; then
    if command -v apt-get >/dev/null 2>&1; then
        run apt-get install -y python3-pip python3-venv python3-pil python3-numpy python3-gpiozero python3-lgpio fonts-dejavu-core
    else
        echo "note: apt-get not found, skipping OS package install -- see docs/deployment.md"
    fi
fi

if [ "$DRY_RUN" -eq 1 ]; then
    echo "+ python3 -m venv --system-site-packages $VENV_DIR (if not already present)"
elif [ ! -d "$VENV_DIR" ]; then
    python3 -m venv --system-site-packages "$VENV_DIR"
fi

if [ "$INSTALL_DEPS" -eq 1 ]; then
    run "$VENV_DIR/bin/pip" install --upgrade pip
    run "$VENV_DIR/bin/pip" install -r "$REPO_ROOT/requirements.txt"
fi

run chown -R "$SERVICE_USER:$SERVICE_USER" "$VENV_DIR"

# --- systemd unit ----------------------------------------------------------
install_unit() {
    local src="$1" dst="$2"
    local body
    body=$(sed \
        -e "s#/opt/weather-station#$INSTALL_ROOT#g" \
        -e "s#/etc/weather-station#$CONFIG_DIR#g" \
        "$src")
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "+ write $dst:"
        echo "$body" | sed 's/^/    /'
    else
        printf '%s\n' "$body" > "$dst"
        echo "wrote $dst"
    fi
}

install_unit "$REPO_ROOT/systemd/weather-station.service" "/etc/systemd/system/weather-station.service"

run systemctl daemon-reload

if [ "$ENABLE_SERVICE" -eq 1 ]; then
    run systemctl enable --now weather-station
    echo
    echo "done. check status with: systemctl status weather-station"
    echo "                         journalctl -u weather-station -f"
else
    echo
    echo "done (service not enabled)"
fi
