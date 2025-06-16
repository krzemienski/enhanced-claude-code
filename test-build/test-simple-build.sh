#!/bin/bash

# Clean up
rm -rf .claude_builder task-tracker-api

# Create a simple spec
cat > simple-spec.md << 'EOF'
# Simple Test Project

Create a simple Python module with:
- A main.py file with a hello world function
- A test.py file with a test for the function
EOF

# Run build
echo "Starting simple build test..."
claude-code-builder simple-spec.md --auto-confirm --output-dir . --max-turns 5 2>&1 | tee simple-build.log