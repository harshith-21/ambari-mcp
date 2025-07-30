# Makefile for ambari-mcp project

# Variables
PROJECT_DIR = $(shell pwd)
CONFIG_FILE = config.json

# Default target
.PHONY: all
all: config

# Sync dependencies with uv
.PHONY: sync
sync:
	@echo "Syncing dependencies with uv..."
	uv sync
	@echo "Dependencies synced"

# Create config.json
.PHONY: config
config:
	@echo "Creating config.json..."
	@echo '{' > $(CONFIG_FILE)
	@echo '  "mcpServers": {' >> $(CONFIG_FILE)
	@echo '    "ambari-mcp": {' >> $(CONFIG_FILE)
	@echo '      "command": "'$$(which uv)'",' >> $(CONFIG_FILE)
	@echo '      "args": [' >> $(CONFIG_FILE)
	@echo '        "--directory",' >> $(CONFIG_FILE)
	@echo '        "$(PROJECT_DIR)",' >> $(CONFIG_FILE)
	@echo '        "run",' >> $(CONFIG_FILE)
	@echo '        "main.py"' >> $(CONFIG_FILE)
	@echo '      ]' >> $(CONFIG_FILE)
	@echo '    }' >> $(CONFIG_FILE)
	@echo '  }' >> $(CONFIG_FILE)
	@echo '}' >> $(CONFIG_FILE)
	@echo "config.json created"

# Clean up
.PHONY: clean
clean:
	@echo "Cleaning up..."
	rm -f $(CONFIG_FILE)
	uv cache clean
	@echo "Cleanup complete"

# Run the MCP server
.PHONY: run
run:
	@echo "Running ambari-mcp server..."
	uv run main.py

# Help target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  all     - Create config.json"
	@echo "  sync    - Sync dependencies with uv"
	@echo "  config  - Create config.json"
	@echo "  run     - Run the MCP server"
	@echo "  clean   - Remove config.json and clean uv cache"
	@echo "  help    - Show this help message" 