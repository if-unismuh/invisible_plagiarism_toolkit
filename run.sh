#!/bin/bash
#
# Invisible Plagiarism Toolkit - Main Runner
# Wrapper script untuk menjalankan main.py dengan PYTHONPATH yang benar
#

# Set PYTHONPATH ke src directory
export PYTHONPATH="$(dirname "$0")/src:$PYTHONPATH"

# Run main.py dengan semua argumen yang diberikan
python "$(dirname "$0")/main.py" "$@"