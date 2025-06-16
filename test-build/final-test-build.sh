#!/bin/bash

echo "=== FINAL BUILD TEST ==="
echo "Cleaning up previous build..."
rm -rf .claude_builder task-tracker-api

echo -e "\nStarting build of test-spec.md..."
claude-code-builder ../test-spec.md --auto-confirm --output-dir . 2>&1 | tee final-build.log &

BUILD_PID=$!
echo "Build started with PID: $BUILD_PID"

# Monitor build progress
while kill -0 $BUILD_PID 2>/dev/null; do
    echo -e "\n=== $(date +%H:%M:%S) ==="
    
    # Check recent activity
    tail -5 final-build.log | grep -E "(Phase|✓|✗|completed|failed|Running)"
    
    # Check files created
    if [ -d task-tracker-api ]; then
        FILE_COUNT=$(find task-tracker-api -type f | wc -l)
        echo "Files created: $FILE_COUNT"
    fi
    
    sleep 15
done

echo -e "\n=== BUILD COMPLETED ==="
echo "Final status:"
tail -20 final-build.log | grep -E "(Build|✓|✗|failed|success)"

# Check if build was successful
if grep -q "Build failed" final-build.log; then
    echo -e "\n❌ Build FAILED"
    echo "Error details:"
    grep -A5 "failed" final-build.log | tail -20
else
    echo -e "\n✅ Build SUCCESSFUL"
    echo "Files created:"
    find task-tracker-api -type f | head -20
fi