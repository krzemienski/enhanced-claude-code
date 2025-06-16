#!/bin/bash

# Fast monitoring script for Claude Code Builder
# Uses real-time log tailing and optimized MCP server configuration

echo "=== CLAUDE CODE BUILDER FAST MONITOR ==="
echo "Starting at: $(date)"

# Function to count MCP servers
count_mcp_servers() {
    ps aux | grep -E "(mcp-server|mcp/)" | grep -v grep | wc -l
}

# Function to show build progress
show_progress() {
    if [ -f build.log ]; then
        echo -e "\n━━━ Build Progress ━━━"
        
        # Show current phase
        current_phase=$(grep -o "Phase [0-9]*/[0-9]*:" build.log | tail -1 || echo "Waiting...")
        echo "Current: $current_phase"
        
        # Show recent activity (last 3 meaningful lines)
        echo -e "\nRecent activity:"
        grep -E "(Phase|Building|Created|✓|→)" build.log | tail -3 | sed 's/^/  /'
        
        # Count files created
        if [ -d todo-api ]; then
            file_count=$(find todo-api -type f 2>/dev/null | wc -l)
            echo -e "\nFiles created: $file_count"
        fi
        
        # Check for errors
        error_count=$(grep -c "ERROR\|Failed" build.log 2>/dev/null || echo 0)
        if [ $error_count -gt 0 ]; then
            echo -e "\n⚠️  Errors detected: $error_count"
        fi
    fi
}

# First, show current MCP server count
echo -e "\nMCP Servers running: $(count_mcp_servers)"
echo "This may be causing the slowdown. Consider reducing MCP servers for faster builds."

# Clean and prepare
echo -e "\nCleaning previous build..."
rm -rf todo-api .claude-code-builder build.log

# Create optimized build command
echo -e "\nPreparing optimized build command..."
cat > run-fast-build.sh << 'EOF'
#!/bin/bash

# Run Claude Code Builder with minimal MCP servers for speed
# Only essential MCP servers: filesystem, memory, git

echo "Starting Claude Code Builder with optimized configuration..."
echo "Note: Using minimal MCP servers for faster execution"

# Set environment to reduce MCP server startup
export CLAUDE_CODE_MINIMAL_MCP=true

# Run the build
claude-code-builder ../test-todo-app-spec.md \
    --output-dir . \
    --auto-confirm \
    --max-turns 30 \
    --verbose \
    2>&1 | tee build.log
EOF

chmod +x run-fast-build.sh

echo -e "\nStarting build with real-time monitoring..."
echo "Command: ./run-fast-build.sh"
echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Start build in background
./run-fast-build.sh &
BUILD_PID=$!

# Real-time monitoring with tail
echo "Monitoring PID: $BUILD_PID"
echo "Press Ctrl+C to stop monitoring (build will continue)"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

# Create a monitoring loop that updates every 2 seconds
while kill -0 $BUILD_PID 2>/dev/null; do
    # Clear previous output and show current status
    clear
    echo "=== CLAUDE CODE BUILDER - REAL-TIME MONITOR ==="
    echo "Time: $(date +%H:%M:%S)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    show_progress
    
    echo -e "\n━━━ Live Output (last 10 lines) ━━━"
    tail -10 build.log 2>/dev/null || echo "Waiting for output..."
    
    sleep 2
done

# Build completed
echo -e "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "BUILD COMPLETED at $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Show final results
if [ -d todo-api ]; then
    echo -e "\n✅ Build appears successful!"
    echo "Project statistics:"
    echo "  Total files: $(find todo-api -type f | wc -l)"
    echo "  Python files: $(find todo-api -name "*.py" | wc -l)"
    
    echo -e "\nKey files:"
    for file in "todo-api/src/main.py" "todo-api/requirements.txt"; do
        if [ -f "$file" ]; then
            echo "  ✓ $file"
        else
            echo "  ✗ $file MISSING"
        fi
    done
else
    echo -e "\n❌ Build failed - no output directory created"
fi

echo -e "\nFull log available in: build.log"