#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

git config --global --add safe.directory /workspaces/sims4-workspace

# Update package lists
sudo apt-get update

# Install cmake
sudo apt-get install -y cmake

# Initialize and update git submodules
git submodule update --init --recursive

# Clean up package lists
sudo apt-get clean

# Change directory to pycdc
cd "$PROJECT_DIR/pycdc"

# Run cmake
cmake .

# Build the project using all available processors
make -j$(nproc)
