#!/bin/bash

# Define the line to be added
line="export USERPROFILE=\"/mnt/c/Users/$(powershell.exe echo '$env:USERNAME' | tr -d '\r\n')\""

# Check the current shell and update the appropriate rc file
if [ -n "$BASH_VERSION" ]; then
    rc_file=~/.bashrc
elif [ -n "$ZSH_VERSION" ]; then
    rc_file=~/.zshrc
else
    echo "Unsupported shell"
    exit 1
fi

# Add the line to the rc file if it doesn't already exist
if ! grep -Fxq "$line" "$rc_file"; then
    echo "$line" >> "$rc_file"
    echo "Added to $rc_file"
else
    echo "Line already exists in $rc_file"
fi

# Source the rc file
source "$rc_file"
echo "Sourced $rc_file"
