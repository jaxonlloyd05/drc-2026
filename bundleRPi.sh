#!/bin/bash
set -e

# ─────────────────────────────────────────────
#  bundleRPi.sh
#  Builds the USB deployment package for Raspberry Pi 4 (ARM64 / Raspberry Pi OS)
# ─────────────────────────────────────────────

PLATFORM="rpi"
PKG_DIR="./usb_package"
WHEELS_DIR="$PKG_DIR/wheels"
SRC_DIR="$PKG_DIR/src"

echo "[1/5] Preparing dist directory..."
if [ -d "$PKG_DIR" ]; then
  echo "      Removing existing $PKG_DIR..."
  rm -rf "$PKG_DIR"
fi
mkdir -p "$WHEELS_DIR" "$SRC_DIR"


echo "[2/5] Writing install.sh for Raspberry Pi 4..."
cat > "$PKG_DIR/install.sh" << 'EOF'
#!/bin/bash
set -e

ROBOT_DIR="/home/pi/robot"
USB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> [RPi4] Installing robot code from USB..."

# Detect script location (USB mount point)
echo "    USB source: $USB_DIR"
echo "    Install target: $ROBOT_DIR"

# Create target directory
mkdir -p "$ROBOT_DIR"

# Copy source code
echo "    Copying src/..."
cp -r "$USB_DIR/src" "$ROBOT_DIR/"

# Copy requirements.txt
echo "    Copying requirements.txt..."
cp "$USB_DIR/requirements.txt" "$ROBOT_DIR/"

# Install Python wheels from USB (no internet required)
echo "    Installing Python dependencies from local wheels..."
pip3 install \
  --no-index \
  --find-links="$USB_DIR/wheels" \
  -r "$USB_DIR/requirements.txt"

echo ""
echo "==> Installation complete."
echo "    Source code is at: $ROBOT_DIR/src"
echo "    To start manually: python3 $ROBOT_DIR/src/main.py"
echo "    See README.md on USB for systemd and udev setup."
EOF
chmod +x "$PKG_DIR/install.sh"


echo "[3/5] Copying requirements.txt..."
if [ ! -f "./reqs.txt" ]; then
  echo "ERROR: reqs.txt not found in current directory."
  exit 1
fi
cp "./reqs.txt" "$PKG_DIR/requirements.txt"


echo "[4/5] Downloading wheels for Raspberry Pi 4 (linux_aarch64, cp311)..."
pip3 download \
  --dest "$WHEELS_DIR" \
  --platform linux_aarch64 \
  --python-version 311 \
  --only-binary=:all: \
  -r "./reqs.txt" || {
    echo ""
    echo "  WARNING: Some packages may not have aarch64 binary wheels available."
    echo "  Attempting fallback with source packages..."
    pip3 download \
      --dest "$WHEELS_DIR" \
      --platform linux_aarch64 \
      --python-version 311 \
      -r "./reqs.txt"
  }

echo "[5/5] Copying ./src into $SRC_DIR..."
if [ ! -d "./src" ]; then
  echo "ERROR: ./src directory not found in current directory."
  exit 1
fi
cp -r "./src/." "$SRC_DIR/"


echo ""
echo "────────────────────────────────────────"
echo " Bundle complete: $PKG_DIR"
echo " Platform:        Raspberry Pi 4 (aarch64)"
echo "────────────────────────────────────────"
echo " Contents:"
find "$PKG_DIR" -not -path "$WHEELS_DIR/*" | sed 's|[^/]*/|  |g'
echo " Wheels downloaded: $(ls "$WHEELS_DIR" | wc -l) file(s)"
echo "────────────────────────────────────────"
echo " Next step: see docs/robot-install-guide.md"
echo "────────────────────────────────────────"
