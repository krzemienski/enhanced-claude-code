#!/bin/bash

# Direct Claude Code Builder test with minimal overhead
# This script runs claude-code-builder directly without excessive MCP servers

echo "=== DIRECT CLAUDE CODE BUILDER TEST ==="
echo "This test minimizes MCP server overhead for faster execution"
echo ""

# Function to show live progress
monitor_progress() {
    local last_update=""
    
    while true; do
        if [ -f build.log ]; then
            # Get current status
            current=$(tail -1 build.log 2>/dev/null)
            
            # Only show if changed
            if [ "$current" != "$last_update" ] && [ -n "$current" ]; then
                echo "[$(date +%H:%M:%S)] $current"
                last_update="$current"
            fi
            
            # Check for phase completion
            if grep -q "Phase.*completed" <<< "$current"; then
                phase_num=$(grep -o "Phase [0-9]*" <<< "$current")
                echo "  ✓ $phase_num completed"
            fi
            
            # Check for completion
            if grep -q "Build completed successfully" build.log; then
                echo ""
                echo "✅ BUILD SUCCESSFUL!"
                break
            elif grep -q "Build failed" build.log; then
                echo ""
                echo "❌ BUILD FAILED"
                break
            fi
        fi
        
        sleep 0.5
    done
}

# Clean previous attempts
echo "Cleaning previous build artifacts..."
rm -rf todo-api .claude-code-builder build.log
echo "✓ Cleaned"

# Show current environment
echo ""
echo "Environment check:"
echo "  Claude Code Builder: $(which claude-code-builder)"
echo "  Working directory: $(pwd)"
echo "  Specification: ../test-todo-app-spec.md"

# Verify spec exists
if [ ! -f "../test-todo-app-spec.md" ]; then
    echo "❌ ERROR: Specification file not found!"
    exit 1
fi

echo ""
echo "Starting build process..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Start monitoring in background
monitor_progress &
MONITOR_PID=$!

# Run the build with stream output
claude-code-builder ../test-todo-app-spec.md \
    --output-dir . \
    --auto-confirm \
    --max-turns 30 \
    --verbose \
    > build.log 2>&1

BUILD_EXIT=$?

# Stop monitoring
kill $MONITOR_PID 2>/dev/null
wait $MONITOR_PID 2>/dev/null

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Show results
if [ $BUILD_EXIT -eq 0 ] && [ -d todo-api ]; then
    echo "✅ Build completed successfully!"
    echo ""
    echo "Project created:"
    echo "  Directory: $(pwd)/todo-api"
    echo "  Files: $(find todo-api -type f | wc -l)"
    echo "  Python modules: $(find todo-api -name "*.py" | wc -l)"
    echo ""
    echo "Structure:"
    tree todo-api -I "__pycache__|*.pyc" 2>/dev/null || {
        echo "Main directories:"
        find todo-api -type d | head -10
    }
else
    echo "❌ Build failed with exit code: $BUILD_EXIT"
    echo ""
    echo "Last 20 lines of output:"
    tail -20 build.log
fi

echo ""
echo "Full build log: $(pwd)/build.log"