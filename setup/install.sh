#!/usr/bin/env sh
set -e

# ==============================================================================
# Utility Functions
# ==============================================================================

detect_distro() {
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "$ID"
  elif [ -f /etc/lsb-release ]; then
    . /etc/lsb-release
    echo "$DISTRIB_ID" | tr '[:upper:]' '[:lower:]'
  elif command -v sw_vers >/dev/null 2>&1; then
    echo "macos"
  else
    echo "unknown"
  fi
}

is_externally_managed() {
  python3 -c "import sysconfig; import os; print(os.path.exists(os.path.join(sysconfig.get_path('stdlib'), 'EXTERNALLY-MANAGED')))" 2>/dev/null | grep -q "True"
}

# ==============================================================================
# Python Validation
# ==============================================================================

validate_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 is required but not found."
    return 1
  fi
  return 0
}

# ==============================================================================
# Pipx Installation & Validation
# ==============================================================================

install_pipx_apt() {
  echo "📦 Installing pipx via apt..."
  if command -v sudo >/dev/null 2>&1; then
    sudo apt update && sudo apt install -y pipx
  else
    apt update && apt install -y pipx
  fi
}

install_pipx_dnf() {
  echo "📦 Installing pipx via dnf..."
  if command -v sudo >/dev/null 2>&1; then
    sudo dnf install -y pipx
  else
    dnf install -y pipx
  fi
}

install_pipx_pacman() {
  echo "📦 Installing pipx via pacman..."
  if command -v sudo >/dev/null 2>&1; then
    sudo pacman -S --noconfirm python-pipx
  else
    pacman -S --noconfirm python-pipx
  fi
}

install_pipx_brew() {
  echo "📦 Installing pipx via brew..."
  brew install pipx
}

install_pipx_pip() {
  echo "📦 Installing pipx via pip..."
  python3 -m pip install --user --upgrade pip pipx
  python3 -m pipx ensurepath
}

install_pipx() {
  _distro=$(detect_distro)

  if is_externally_managed; then
    echo "⚠️  Externally managed Python environment detected (PEP 668)"
    case "$_distro" in
      ubuntu|debian|linuxmint|pop)
        install_pipx_apt
        ;;
      fedora|rhel|centos|rocky|alma)
        install_pipx_dnf
        ;;
      arch|manjaro|endeavouros)
        install_pipx_pacman
        ;;
      macos)
        if command -v brew >/dev/null 2>&1; then
          install_pipx_brew
        else
          echo "❌ Homebrew not found. Please install pipx manually."
          return 1
        fi
        ;;
      *)
        echo "❌ Unknown distro '$_distro' with externally managed environment."
        echo "   Please install pipx manually using your package manager."
        return 1
        ;;
    esac
  else
    install_pipx_pip
  fi
}

ensure_pipx() {
  if ! command -v pipx >/dev/null 2>&1; then
    echo "📦 pipx not found, installing..."
    install_pipx
    export PATH="$HOME/.local/bin:$PATH"
  fi

  if ! command -v pipx >/dev/null 2>&1; then
    echo "❌ pipx installation failed."
    return 1
  fi
  echo "🔧 pipx is installed"

  pipx ensurepath >/dev/null 2>&1 || true
  return 0
}

# ==============================================================================
# Main Installation
# ==============================================================================

install_gitx() {
  echo "🔧 Installing gitx..."

  if ! validate_python; then
    exit 1
  fi

  if ! ensure_pipx; then
    exit 1
  fi

  echo "🚀 Installing gitx via pipx..."
  pipx install gitx-cli || pipx upgrade gitx-cli

  echo ""
  echo "✅ gitx installed!"
  echo "👉 Restart your shell or run:"
  echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo ""
  echo "Try:"
  echo "   gitx --help"
}

# ==============================================================================
# Script Entry Point
# ==============================================================================

show_help() {
  echo "Usage: $0 [command]"
  echo ""
  echo "Commands:"
  echo "  install         Install gitx (default)"
  echo "  ensure-pipx     Ensure pipx is installed"
  echo "  validate-python Validate python3 is available"
  echo "  detect-distro   Detect the current Linux distribution"
  echo "  help            Show this help message"
}

# Main entry point with subcommand support
case "${1:-install}" in
  install)
    install_gitx
    ;;
  ensure-pipx)
    ensure_pipx
    ;;
  validate-python)
    validate_python
    ;;
  detect-distro)
    detect_distro
    ;;
  help|--help|-h)
    show_help
    ;;
  *)
    install_gitx
    ;;
esac
