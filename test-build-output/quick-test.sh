#!/bin/bash

echo "=== QUICK CLAUDE CODE BUILDER TEST ==="
echo "Running with minimal configuration for speed"
echo ""

# Clean up
rm -rf todo-api .claude-code-builder build.log

# Run with auto-confirm and capture output
echo "Starting build at $(date +%H:%M:%S)..."
echo "This may take several minutes. Output will be shown when complete."
echo ""

# Run the build capturing both stdout and stderr
claude-code-builder ../test-todo-app-spec.md \
    --output-dir . \
    --auto-confirm \
    --max-turns 20 \
    --min-phases 3 \
    --min-tasks-per-phase 3 \
    --phase-timeout 300 \
    --no-validate \
    --verbose \
    2>&1 | tee build.log

EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo "Build finished at $(date +%H:%M:%S)"
echo "Exit code: $EXIT_CODE"

# Check results
if [ $EXIT_CODE -eq 0 ] && [ -d todo-api ]; then
    echo ""
    echo "✅ BUILD SUCCESSFUL!"
    echo ""
    echo "Created files:"
    find todo-api -type f -name "*.py" | head -10
    echo ""
    echo "Total: $(find todo-api -type f | wc -l) files"
else
    echo ""
    echo "❌ BUILD FAILED"
    echo ""
    echo "Error details:"
    grep -E "ERROR|Failed|Exception" build.log | tail -10
fi