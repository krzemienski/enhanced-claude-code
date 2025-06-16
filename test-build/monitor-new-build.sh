#!/bin/bash

# Clean start
echo "Cleaning up previous build artifacts..."
rm -rf .claude-code-builder task-tracker-api .mcp.json

# Start the build
echo "Starting new build..."
claude-code-builder ../test-spec.md --auto-confirm --output-dir . 2>&1 | tee build-new.log &

BUILD_PID=$!

echo "Build started with PID: $BUILD_PID"
echo "Monitoring build progress..."

# Monitor the build
while kill -0 $BUILD_PID 2>/dev/null; do
    echo -e "\n=== $(date) ==="
    
    # Check if build log exists and show recent activity
    if [ -f build-new.log ]; then
        echo "Recent build activity:"
        tail -n 10 build-new.log | grep -E "(✓|✗|Phase|Error|failed|success)"
    fi
    
    # Check for created files
    if [ -d task-tracker-api ]; then
        echo -e "\nFiles created in task-tracker-api:"
        find task-tracker-api -type f -newer build-new.log 2>/dev/null | head -10
    fi
    
    sleep 10
done

echo -e "\n=== Build completed ==="
echo "Final status:"
tail -n 20 build-new.log