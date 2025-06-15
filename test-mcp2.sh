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
    }
  }
}
MCPEOF

# Test command
echo "Testing MCP access..."
echo "List available MCP tools you have access to" | \
claude --model claude-opus-4-20250514 \
  --mcp-config .mcp.json \
  --dangerously-skip-permissions \
  --max-turns 1

rm .mcp.json
