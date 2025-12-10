#!/usr/bin/env sh
set -e

GITX_URL="https://parisius.github.io/gitx/gitx.py"
INSTALL_DIR="$HOME/.local/bin"
GITX_PATH="$INSTALL_DIR/gitx"

echo "▸ Installing gitx into $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

echo "▸ Fetching gitx.py..."
curl -fsSL "$GITX_URL" -o "$GITX_PATH"
chmod +x "$GITX_PATH"

echo ""
echo "✔ gitx installed at: $GITX_PATH"

if ! echo "$PATH" | grep -q "$INSTALL_DIR"; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Add this to your ~/.bashrc or ~/.zshrc:"
  echo ""
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo ""
  echo "Then reload your shell."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

echo ""
echo "Try: gitx help"
echo "Done!"