#!/usr/bin/env sh
set -e

echo "🔧 Installing gitx..."

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 is required but not found."
  exit 1
fi

if ! command -v pipx >/dev/null 2>&1; then
  echo "📦 pipx not found, installing locally..."

  python3 -m pip install --user --upgrade pip pipx
  python3 -m pipx ensurepath

  export PATH="$HOME/.local/bin:$PATH"
fi

echo "🚀 Installing gitx via pipx..."
pipx install gitx || pipx upgrade gitx

echo ""
echo "✅ gitx installed!"
echo "👉 Restart your shell or run:"
echo "   export PATH=\"$HOME/.local/bin:\$PATH\""
echo ""
echo "Try:"
echo "   gitx --help"
