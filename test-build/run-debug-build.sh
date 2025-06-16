#!/bin/bash

# Clean start
echo "Cleaning build artifacts..."
rm -rf .claude_builder task-tracker-api

# Run build with debug output
echo "Starting debug build..."
claude-code-builder ../test-spec.md --auto-confirm --output-dir . 2>&1 | tee debug-build.log