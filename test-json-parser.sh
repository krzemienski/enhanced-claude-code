#!/bin/bash

# Test script for JSON stream parser
cd /home/nick/enhanced-claude-code

# Source the builder script to get the parse function
source builder-claude-code-builder.sh

# Test with sample Claude stream JSON
cat << 'EOF' | parse_enhanced_stream_output
{"type": "content_block_start", "index": 0, "content_block": {"type": "text"}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "I'll help you test the JSON parsing. Let me use a tool to demonstrate."}}
{"type": "content_block_stop", "index": 0}
{"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "test123", "name": "mem0__search-memories"}}
{"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": "{\"query\": \"test\", \"userId\": \"test-user\"}"}}
{"type": "content_block_stop", "index": 1}
{"type": "message_stop"}
EOF

echo "Test completed!"