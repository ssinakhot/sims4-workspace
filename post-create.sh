#!/bin/bash

# Update package lists
sudo apt-get update

# Install cmake
sudo apt-get install -y cmake

# Initialize and update git submodules
git submodule update --init --recursive

# Clean up package lists
sudo apt-get clean

# Change directory to pycdc
cd pycdc

# Run cmake
cmake .

# Build the project using all available processors
make -j$(nproc)