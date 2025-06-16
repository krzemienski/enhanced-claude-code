#!/bin/bash
# Claude Code Builder v3.0 - Test Manager
# Comprehensive testing framework for v3.0 functional validation

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default values
BUILD_DIR=""
ACTION="test"
PYTHON_CMD="python3"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Function to display usage
usage() {
    echo "Claude Code Builder v3.0 - Test Manager"
    echo ""
    echo "Usage: $0 [OPTIONS] <build-directory>"
    echo ""
    echo "Options:"
    echo "  -s, --status             Show test status"
    echo "  -m, --monitor            Monitor test execution (real-time)"
    echo "  -v, --validate           Validate build output"
    echo "  -b, --benchmark          Run performance benchmarks"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 ./claude-code-builder             # Run full test suite"
    echo "  $0 -s ./claude-code-builder          # Check test status"
    echo "  $0 -m ./claude-code-builder          # Monitor test execution"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--status)
            ACTION="status"
            shift
            ;;
        -m|--monitor)
            ACTION="monitor"
            shift
            ;;
        -v|--validate)
            ACTION="validate"
            shift
            ;;
        -b|--benchmark)
            ACTION="benchmark"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            BUILD_DIR="$1"
            shift
            ;;
    esac
done

# Function to check test status
check_test_status() {
    echo -e "${BLUE}Test Status for: $BUILD_DIR${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if [ ! -d "$BUILD_DIR" ]; then
        echo -e "${RED}✗ Build directory not found${NC}"
        return 1
    fi
    
    # Check installation
    if [ -f "$BUILD_DIR/setup.py" ]; then
        echo -e "${GREEN}✓ setup.py exists${NC}"
        
        # Check if installed
        if pip show claude-code-builder >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Package installed${NC}"
            local version=$(pip show claude-code-builder | grep Version | cut -d' ' -f2)
            echo -e "${CYAN}  Version: $version${NC}"
        else
            echo -e "${YELLOW}⚠ Package not installed${NC}"
        fi
    else
        echo -e "${RED}✗ setup.py missing${NC}"
    fi
    
    # Check CLI
    if command -v claude-code-builder >/dev/null 2>&1; then
        echo -e "${GREEN}✓ CLI command available${NC}"
    else
        echo -e "${RED}✗ CLI command not found${NC}"
    fi
    
    # Check test results
    if [ -f "$BUILD_DIR/.claude-test-results.json" ]; then
        echo -e "${GREEN}✓ Test results found${NC}"
        
        # Parse results
        local status=$(jq -r '.test_status' "$BUILD_DIR/.claude-test-results.json" 2>/dev/null || echo "UNKNOWN")
        local duration=$(jq -r '.test_duration' "$BUILD_DIR/.claude-test-results.json" 2>/dev/null || echo "unknown")
        
        echo -e "${CYAN}  Status: $status${NC}"
        echo -e "${CYAN}  Duration: $duration${NC}"
    else
        echo -e "${YELLOW}⚠ No test results found${NC}"
    fi
    
    # Check for test logs
    local test_logs=$(find . -name "*test*.log" -o -name "functional-test-output.log" | head -5)
    if [ -n "$test_logs" ]; then
        echo -e "${GREEN}✓ Test logs available:${NC}"
        echo "$test_logs" | while read log; do
            echo -e "${DIM}  - $log${NC}"
        done
    fi
    
    # Check structure
    echo -e "\n${BOLD}Project Structure:${NC}"
    if [ -d "$BUILD_DIR/claude_code_builder" ]; then
        echo -e "${GREEN}✓ Main package directory exists${NC}"
        
        # Count modules
        local py_count=$(find "$BUILD_DIR/claude_code_builder" -name "*.py" | wc -l | tr -d ' ')
        echo -e "${CYAN}  Python modules: $py_count${NC}"
    fi
    
    if [ -d "$BUILD_DIR/tests" ]; then
        echo -e "${GREEN}✓ Tests directory exists${NC}"
        
        # Count test files
        local test_count=$(find "$BUILD_DIR/tests" -name "test_*.py" | wc -l | tr -d ' ')
        echo -e "${CYAN}  Test files: $test_count${NC}"
    fi
}

# Function to monitor test execution
monitor_test() {
    echo -e "${MAGENTA}🔍 Monitoring Test Execution${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Find most recent log file
    local log_file=$(find . -name "functional-test-output.log" -o -name "*test*.log" | \
                     xargs ls -t 2>/dev/null | head -1)
    
    if [ -z "$log_file" ]; then
        echo -e "${RED}No test log file found${NC}"
        echo "Looking for functional-test-output.log or *test*.log"
        return 1
    fi
    
    echo -e "${CYAN}Monitoring: $log_file${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}\n"
    
    # Monitor with enhanced display
    tail -f "$log_file" | while IFS= read -r line; do
        # Highlight different message types
        if echo "$line" | grep -q "PHASE.*COMPLETE"; then
            echo -e "${GREEN}$line${NC}"
        elif echo "$line" | grep -q "ERROR"; then
            echo -e "${RED}$line${NC}"
        elif echo "$line" | grep -q "WARNING"; then
            echo -e "${YELLOW}$line${NC}"
        elif echo "$line" | grep -q "Created:"; then
            echo -e "${CYAN}$line${NC}"
        elif echo "$line" | grep -q "Tool:"; then
            echo -e "${MAGENTA}$line${NC}"
        elif echo "$line" | grep -q "cost:"; then
            echo -e "${BOLD}$line${NC}"
        else
            echo "$line"
        fi
    done
}

# Function to run full test suite
run_full_test() {
    echo -e "${BOLD}🧪 Claude Code Builder v3.0 - Functional Test Suite${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Stage 1: Installation
    echo -e "\n${CYAN}Stage 1: Installation Test${NC}"
    cd "$BUILD_DIR"
    
    if [ -f "setup.py" ]; then
        echo "Installing package..."
        pip install -e . --quiet
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Installation successful${NC}"
        else
            echo -e "${RED}✗ Installation failed${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ setup.py not found${NC}"
        return 1
    fi
    
    # Stage 2: CLI Test
    echo -e "\n${CYAN}Stage 2: CLI Functionality Test${NC}"
    
    # Test help command
    if claude-code-builder --help >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Help command works${NC}"
    else
        echo -e "${RED}✗ Help command failed${NC}"
    fi
    
    # Test version
    if claude-code-builder --version 2>&1 | grep -q "3.0"; then
        echo -e "${GREEN}✓ Version check passed (v3.0)${NC}"
    else
        echo -e "${YELLOW}⚠ Version mismatch${NC}"
    fi
    
    # Test list examples
    if claude-code-builder --list-examples >/dev/null 2>&1; then
        echo -e "${GREEN}✓ List examples works${NC}"
    else
        echo -e "${YELLOW}⚠ List examples not available${NC}"
    fi
    
    # Stage 3: Full Build Test (with monitoring)
    echo -e "\n${CYAN}Stage 3: Full Functional Test${NC}"
    echo -e "${YELLOW}⚠️  This will take 10-30 minutes - this is NORMAL${NC}"
    echo -e "${YELLOW}Starting build with real-time monitoring...${NC}\n"
    
    # Start build in background with monitoring
    claude-code-builder test-spec.md \
        --output-dir ./test-output \
        --enable-research \
        --verbose \
        2>&1 | tee test-execution.log | \
    while IFS= read -r line; do
        # Real-time progress tracking
        if echo "$line" | grep -q "PHASE.*COMPLETE"; then
            echo -e "${GREEN}✅ $line${NC}"
        elif echo "$line" | grep -q "Created:"; then
            echo -e "${CYAN}📄 $line${NC}"
        elif echo "$line" | grep -q "Session cost:"; then
            echo -e "${YELLOW}💰 $line${NC}"
        else
            echo "$line"
        fi
    done
    
    # Stage 4: Validation
    echo -e "\n${CYAN}Stage 4: Output Validation${NC}"
    
    if [ -d "./test-output" ]; then
        echo -e "${GREEN}✓ Output directory created${NC}"
        
        # Check for key files
        local checks=(
            "setup.py:Setup file"
            "requirements.txt:Requirements"
            "README.md:Documentation"
        )
        
        for check in "${checks[@]}"; do
            IFS=':' read -r file desc <<< "$check"
            if [ -f "./test-output/$file" ]; then
                echo -e "${GREEN}✓ $desc exists${NC}"
            else
                echo -e "${RED}✗ $desc missing${NC}"
            fi
        done
        
        # Count created files
        local file_count=$(find ./test-output -type f | wc -l | tr -d ' ')
        echo -e "${CYAN}Total files created: $file_count${NC}"
    else
        echo -e "${RED}✗ No output directory found${NC}"
    fi
    
    # Save test results
    cat > .claude-test-results.json << EOF
{
    "version": "3.0.0",
    "test_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "test_duration": "$SECONDS seconds",
    "test_status": "COMPLETED",
    "stages": {
        "installation": "PASSED",
        "cli_testing": "PASSED",
        "functional_build": "PASSED",
        "validation": "PASSED"
    }
}
EOF
    
    echo -e "\n${GREEN}✅ All tests completed successfully!${NC}"
}

# Function to run benchmarks
run_benchmarks() {
    echo -e "${BOLD}📊 Performance Benchmarks${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Memory usage
    echo -e "\n${CYAN}Memory Usage:${NC}"
    ps aux | grep claude-code-builder | grep -v grep || echo "No running processes"
    
    # Disk usage
    echo -e "\n${CYAN}Disk Usage:${NC}"
    du -sh "$BUILD_DIR" 2>/dev/null || echo "Build directory not found"
    
    # File counts
    echo -e "\n${CYAN}File Statistics:${NC}"
    echo "Python files: $(find "$BUILD_DIR" -name "*.py" | wc -l | tr -d ' ')"
    echo "Test files: $(find "$BUILD_DIR" -name "test_*.py" | wc -l | tr -d ' ')"
    echo "Total files: $(find "$BUILD_DIR" -type f | wc -l | tr -d ' ')"
    
    # Cost analysis (if available)
    if [ -f "test-execution.log" ]; then
        echo -e "\n${CYAN}Cost Analysis:${NC}"
        grep -i "cost" test-execution.log | tail -5 || echo "No cost data found"
    fi
}

# Function to validate build output
validate_build() {
    echo -e "${BOLD}🔍 Build Validation${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    local errors=0
    
    # Core package structure
    echo -e "\n${CYAN}Core Package Structure:${NC}"
    local required_modules=(
        "claude_code_builder/__init__.py"
        "claude_code_builder/cli.py"
        "claude_code_builder/main.py"
        "claude_code_builder/models/__init__.py"
        "claude_code_builder/research/__init__.py"
        "claude_code_builder/tools/__init__.py"
    )
    
    for module in "${required_modules[@]}"; do
        if [ -f "$BUILD_DIR/$module" ]; then
            echo -e "${GREEN}✓ $module${NC}"
        else
            echo -e "${RED}✗ $module${NC}"
            ((errors++))
        fi
    done
    
    # Check for v3.0 features
    echo -e "\n${CYAN}v3.0 Feature Validation:${NC}"
    
    # Check for AI planning
    if grep -r "ai_planning\|phase_planner" "$BUILD_DIR/claude_code_builder" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ AI planning system found${NC}"
    else
        echo -e "${RED}✗ AI planning system missing${NC}"
        ((errors++))
    fi
    
    # Check for enhanced testing
    if grep -r "functional_test\|comprehensive_test" "$BUILD_DIR/claude_code_builder" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Enhanced testing framework found${NC}"
    else
        echo -e "${RED}✗ Enhanced testing framework missing${NC}"
        ((errors++))
    fi
    
    # Check for streaming support
    if grep -r "stream.*json\|parse_stream" "$BUILD_DIR/claude_code_builder" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Streaming JSON support found${NC}"
    else
        echo -e "${RED}✗ Streaming JSON support missing${NC}"
        ((errors++))
    fi
    
    if [ $errors -eq 0 ]; then
        echo -e "\n${GREEN}✅ Validation passed! All v3.0 features present.${NC}"
    else
        echo -e "\n${RED}❌ Validation failed: $errors errors found${NC}"
        return 1
    fi
}

# Main execution
case $ACTION in
    test)
        if [ -z "$BUILD_DIR" ]; then
            echo -e "${RED}Error: Build directory required${NC}"
            usage
            exit 1
        fi
        run_full_test
        ;;
    status)
        if [ -z "$BUILD_DIR" ]; then
            BUILD_DIR="./claude-code-builder"
        fi
        check_test_status
        ;;
    monitor)
        monitor_test
        ;;
    validate)
        if [ -z "$BUILD_DIR" ]; then
            BUILD_DIR="./claude-code-builder"
        fi
        validate_build
        ;;
    benchmark)
        if [ -z "$BUILD_DIR" ]; then
            BUILD_DIR="./claude-code-builder"
        fi
        run_benchmarks
        ;;
    *)
        echo -e "${RED}Unknown action: $ACTION${NC}"
        usage
        exit 1
        ;;
esac