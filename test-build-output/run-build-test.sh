#!/bin/bash

echo "=== CLAUDE CODE BUILDER FUNCTIONAL TEST ==="
echo "Test started at: $(date)"
echo "Working directory: $(pwd)"

# Clean previous builds
rm -rf todo-api .claude-code-builder build.log

# Run the build with monitoring
echo -e "\nStarting Claude Code Builder..."
echo "Command: claude-code-builder ../test-todo-app-spec.md --output-dir . --auto-confirm --max-turns 30"

# Start build in background
claude-code-builder ../test-todo-app-spec.md \
    --output-dir . \
    --auto-confirm \
    --max-turns 30 \
    --verbose \
    2>&1 | tee build.log &

BUILD_PID=$!
echo "Build process started with PID: $BUILD_PID"

# Monitor function
monitor() {
    local check_count=0
    local last_line_count=0
    
    while kill -0 $BUILD_PID 2>/dev/null; do
        check_count=$((check_count + 1))
        echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Check #$check_count at $(date +%H:%M:%S)"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Get current line count
        current_lines=$(wc -l < build.log 2>/dev/null || echo 0)
        new_lines=$((current_lines - last_line_count))
        last_line_count=$current_lines
        
        echo "Progress: $new_lines new lines since last check"
        
        # Show recent activity
        echo -e "\nRecent activity:"
        tail -15 build.log 2>/dev/null | grep -E "(Phase|✓|✗|Building|Created|Error)" | tail -5 || echo "  Waiting for output..."
        
        # Check for phase completion
        phase_count=$(grep -c "Phase.*completed" build.log 2>/dev/null || echo 0)
        echo -e "\nPhases completed: $phase_count"
        
        # File statistics
        if [ -d todo-api ]; then
            file_count=$(find todo-api -type f 2>/dev/null | wc -l)
            echo "Files created: $file_count"
            
            # Recent files
            echo -e "\nRecent files:"
            find todo-api -type f -newer build.log 2>/dev/null | tail -5 | sed 's/^/  /'
        fi
        
        # Error check
        error_count=$(grep -c "ERROR\|Failed\|Traceback" build.log 2>/dev/null || echo 0)
        if [ $error_count -gt 0 ]; then
            echo -e "\n⚠️  Errors detected: $error_count"
            echo "Latest error:"
            grep -E "ERROR|Failed|Traceback" build.log | tail -1
        fi
        
        sleep 15
    done
}

# Run monitor
monitor

# Build finished
echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "BUILD COMPLETED at $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

wait $BUILD_PID
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n✅ BUILD SUCCESSFUL!"
    
    # Final statistics
    if [ -d todo-api ]; then
        echo -e "\nProject statistics:"
        echo "  Total files: $(find todo-api -type f | wc -l)"
        echo "  Python files: $(find todo-api -name "*.py" | wc -l)"
        echo "  Test files: $(find todo-api -path "*/tests/*" -name "*.py" | wc -l)"
        
        echo -e "\nProject structure:"
        tree todo-api -I "__pycache__|*.pyc" 2>/dev/null || find todo-api -type f | sort
    fi
    
    # Check key files
    echo -e "\nKey file verification:"
    for file in "todo-api/src/main.py" "todo-api/src/models.py" "todo-api/src/auth.py" "todo-api/requirements.txt"; do
        if [ -f "$file" ]; then
            echo "  ✓ $file ($(wc -l < "$file") lines)"
        else
            echo "  ✗ $file MISSING"
        fi
    done
else
    echo -e "\n❌ BUILD FAILED with exit code: $EXIT_CODE"
    
    echo -e "\nError analysis:"
    echo "Total errors: $(grep -c "ERROR" build.log 2>/dev/null || echo 0)"
    
    echo -e "\nLast 20 lines of log:"
    tail -20 build.log
fi

echo -e "\nBuild log saved to: build.log"
echo "Full output available for analysis."