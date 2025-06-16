#\!/bin/bash

# Export API key
export ANTHROPIC_API_KEY="YOUR_API_KEY_HERE"

# Start the build in background and monitor
echo "Starting Claude Code Builder..."
claude-code-builder ../test-spec.md \
  --output-dir . \
  --auto-confirm \
  --enable-research \
  --discover-mcp \
  --stream-output \
  --verbose \
  --log-file build.log \
  2>&1 | tee build-output.log &

BUILD_PID=$\!
echo "Build started with PID: $BUILD_PID"

# Monitor function
monitor_build() {
    echo "Monitoring build progress..."
    
    while kill -0 $BUILD_PID 2>/dev/null; do
        echo ""
        echo "=== Build Status at $(date) ==="
        
        # Check last 10 lines of log
        if [ -f build.log ]; then
            echo "Recent log entries:"
            tail -10 build.log
        fi
        
        # Check for any phase completion
        if [ -f build-output.log ]; then
            echo "Current phase:"
            grep -E "(Phase|Building|Completed)" build-output.log | tail -5
        fi
        
        # Sleep for 15 seconds
        sleep 15
    done
    
    echo ""
    echo "=== Build completed ==="
    echo "Exit status: $?"
    
    # Show final log entries
    echo ""
    echo "Final log entries:"
    tail -20 build.log
    
    # Show build summary
    echo ""
    echo "Build summary:"
    grep -E "(SUCCESS|ERROR|FAILED)" build-output.log | tail -10
}

# Run the monitor
monitor_build
EOF < /dev/null