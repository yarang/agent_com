#!/bin/bash
set -e

# AI Agent Communication System - Installation Script
# Installs project dependencies using uv package manager

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo ""
    print_message "${BLUE}" "========================================"
    print_message "${BLUE}" "$1"
    print_message "${BLUE}" "========================================"
    echo ""
}

check_uv() {
    if ! command -v uv &> /dev/null; then
        print_message "${YELLOW}" "uv is not installed. Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
        print_message "${GREEN}" "uv installed successfully!"
    else
        print_message "${GREEN}" "uv is already installed: $(uv --version)"
    fi
}

create_venv() {
    print_header "Creating Virtual Environment"
    if [ ! -d ".venv" ]; then
        print_message "${YELLOW}" "Creating virtual environment with uv..."
        uv venv
        print_message "${GREEN}" "Virtual environment created!"
    else
        print_message "${GREEN}" "Virtual environment already exists."
    fi
}

install_dependencies() {
    print_header "Installing Dependencies"
    local install_type=${1:-"dev"}
    if [ "$install_type" = "dev" ]; then
        print_message "${YELLOW}" "Installing dependencies with dev extras..."
        uv pip install -e ".[dev,redis]"
    elif [ "$install_type" = "redis" ]; then
        print_message "${YELLOW}" "Installing dependencies with redis support..."
        uv pip install -e ".[redis]"
    else
        print_message "${YELLOW}" "Installing dependencies..."
        uv pip install -e .
    fi
    print_message "${GREEN}" "Dependencies installed successfully!"
}

main() {
    print_header "AI Agent Communication System - Installation"
    local install_type="dev"
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-dev) install_type="basic"; shift ;;
            --help) echo "Usage: $0 [--no-dev]"; exit 0 ;;
            *) shift ;;
        esac
    done
    check_uv
    create_venv
    install_dependencies "$install_type"
    print_header "Installation Complete!"
    print_message "${GREEN}" "Activate the virtual environment:"
    echo "  source .venv/bin/activate"
    echo ""
    print_message "${BLUE}" "Or use uv run:"
    echo "  uv run python -m mcp_broker.main"
    echo "  uv run pytest tests/"
}

main "$@"
