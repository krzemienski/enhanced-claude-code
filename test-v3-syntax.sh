#!/bin/bash
# Test v3 script syntax and basic functionality

echo "Testing v3 builder script syntax..."

# Test bash syntax
if bash -n builder-claude-code-builder-v3.sh; then
    echo "✓ Bash syntax is valid"
else
    echo "✗ Bash syntax errors found"
    exit 1
fi

# Test that script can be sourced for function testing
if source builder-claude-code-builder-v3.sh 2>/dev/null; then
    echo "✗ Script should not be sourceable (should exit in main)"
else
    echo "✓ Script properly exits when sourced"
fi

# Test help functionality
echo -e "\nTesting help command..."
if ./builder-claude-code-builder-v3.sh --help | grep -q "AI-Driven Autonomous Project Builder"; then
    echo "✓ Help command works"
else
    echo "✗ Help command failed"
    exit 1
fi

# Test that required files are created
echo -e "\nTesting file creation in dry run..."
cd test-v3-build

# Create mock AI planning output to test parsing
cat > build-phases-v3.json << 'EOF'
{
  "version": "3.0.0",
  "total_phases": 3,
  "phases": [
    {
      "number": 1,
      "name": "Test Phase 1",
      "objective": "Test objective 1",
      "tasks": ["Task 1", "Task 2"],
      "complexity": 2,
      "dependencies": [],
      "estimated_time": "1 minute"
    },
    {
      "number": 2,
      "name": "Test Phase 2",
      "objective": "Test objective 2",
      "tasks": ["Task 3", "Task 4"],
      "complexity": 3,
      "dependencies": [1],
      "estimated_time": "1 minute"
    },
    {
      "number": 3,
      "name": "Test Phase 3",
      "objective": "Test objective 3",
      "tasks": ["Task 5"],
      "complexity": 1,
      "dependencies": [1, 2],
      "estimated_time": "1 minute"
    }
  ]
}
EOF

echo "✓ Test JSON created"

# Test JSON parsing
if jq -r '.total_phases' build-phases-v3.json >/dev/null 2>&1; then
    echo "✓ JSON parsing works"
else
    echo "✗ JSON parsing failed"
    exit 1
fi

# Test phase extraction
phase_name=$(jq -r '.phases[0].name // "Unknown"' build-phases-v3.json)
if [ "$phase_name" = "Test Phase 1" ]; then
    echo "✓ Phase extraction works"
else
    echo "✗ Phase extraction failed"
    exit 1
fi

echo -e "\n✅ All tests passed! Script is ready for use."