# Figma MCP Server

Connects Claude Code with the Figma API so the agent can fetch design specs while implementing components. Bundled inside the bug-reviewer project — the `.mcp.json` at the project root registers this server automatically.

## Setup

### 1. Python 3.14+

```bash
brew install python@3.14
```

### 2. Create the venv and install dependencies

Run this from the `figma-mcp-server/` directory:

```bash
cd figma-mcp-server
python3.14 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment variables

Add to your `.env` in the bug-reviewer project root (see `.env.example`):

```env
FIGMA_API_KEY=                                  # Figma → Account → Settings → Personal access tokens
FIGMA_DEFAULT_FILE_KEY=<YOUR_FIGMA_FILE_KEY>    # The Figma file the agent should default to
```

Find the file key in any Figma URL: `figma.com/file/<FILE_KEY>/...`.

### 4. Verify

Start a Claude Code session in the bug-reviewer root and run `/mcp` — `figma-server` should show as connected.

## Tools available

- `search_figma_components` — Find components by name
- `get_component_design_specs` — Get basic design specs
- `get_component_full_specs` — Get comprehensive specs with Tailwind mappings
- `get_component_image` — Export a component as an image URL
- `get_figma_file_info` — Get file metadata
- `get_file_styles` — Get all design-system styles
- `clear_figma_cache` — Clear cached API responses (use after Figma file changes)
