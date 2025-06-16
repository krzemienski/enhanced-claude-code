#!/bin/bash

# Start the build in background
export ANTHROPIC_API_KEY="YOUR_API_KEY_HERE"

echo "Starting Claude Code Builder..."
claude-code-builder ../test-spec.md --output-dir . --auto-confirm --enable-research --discover-mcp --stream-output --verbose --log-file build.log 2>&1 | tee build-output.log &
BUILD_PID=$!

echo "Build started with PID: $BUILD_PID"
echo "Monitoring build progress..."

# Monitor the build
while kill -0 $BUILD_PID 2>/dev/null; do
    echo -e "\n=== Build Status Check at $(date) ==="
    
    # Check for errors in the log
    if [ -f build.log ]; then
        echo "Recent errors:"
        grep -i "error\|failed\|exception" build.log | tail -5
    fi
    
    # Check progress
    if [ -f build-output.log ]; then
        echo -e "\nCurrent phase:"
        grep -E "Phase [0-9]+/[0-9]+:|✓|✗|⟳" build-output.log | tail -5
        
        echo -e "\nFiles created:"
        find task-tracker-api -type f 2>/dev/null | wc -l
    fi
    
    sleep 15
done

echo -e "\n=== Build completed ==="
echo "Exit status: $(wait $BUILD_PID; echo $?)"

# Final summary
echo -e "\nFinal status:"
tail -20 build-output.log