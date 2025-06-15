#\!/bin/bash
export MEM0_API_KEY="m0-3tPdTjpcv6BNJxc0PihMTQ1jAR1XywG6yJ55YPxb"

# Create MCP config
cat > .mcp.json << 'MCPEOF'
{
  "mcpServers": {
    "mem0-mcp": {
      "command": "npx",
      "args": ["-y", "@mem0/mcp"],
      "env": {
        "MEM0_API_KEY": "m0-3tPdTjpcv6BNJxc0PihMTQ1jAR1XywG6yJ55YPxb"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "test"
      }
    }
  }
}
MCPEOF

# Test command
echo "Testing MCP access with whitelisting..."
echo "Use mem0-mcp__add-memory to store 'Test memory' with user_id='test'" | \
claude --model claude-opus-4-20250514 \
  --mcp-config .mcp.json \
  --mcp-allow mem0-mcp__add-memory \
  --mcp-allow github__search_repositories \
  --dangerously-skip-permissions \
  --max-turns 1

rm .mcp.json
