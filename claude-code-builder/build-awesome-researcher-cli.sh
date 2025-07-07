#!/bin/bash
# Build Awesome Researcher using Claude Code CLI wrapper

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Building Awesome Researcher with Claude CLI${NC}"
echo -e "${GREEN}========================================${NC}"

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}Error: ANTHROPIC_API_KEY not set${NC}"
    echo "Please set: export ANTHROPIC_API_KEY='your-key-here'"
    exit 1
fi

# Check for Claude CLI
if ! command -v claude &> /dev/null; then
    echo -e "${RED}Error: Claude Code CLI not found${NC}"
    echo "Please install: npm install -g @anthropic-ai/claude-code"
    exit 1
fi

# Check for specification
SPEC_FILE="../awesome-researcher-complete-spec.md"
if [ ! -f "$SPEC_FILE" ]; then
    echo -e "${RED}Error: Specification not found at $SPEC_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met${NC}"
echo ""

# Build with our CLI wrapper
echo "Starting build process..."
python3 run-claude-cli-build.py "$SPEC_FILE" \
    --output-dir "./awesome-researcher-build" \
    --max-turns 50

# Check result
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Project location: ./awesome-researcher-build"
    echo ""
    echo "To run the project:"
    echo "  cd awesome-researcher-build"
    echo "  # Follow instructions in README.md"
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Build failed!${NC}"
    echo -e "${RED}========================================${NC}"
fi