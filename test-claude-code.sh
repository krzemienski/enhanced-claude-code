#!/bin/bash
# Test claude-code with a simple prompt

echo "Testing claude-code..."

npx -y @anthropic-ai/claude-code -p --verbose --model claude-opus-4-20250514 --output-format stream-json --dangerously-skip-permissions "Create a simple hello.py file that prints 'Hello, World!'"