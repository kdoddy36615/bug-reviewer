#!/usr/bin/env python3
"""
Figma MCP Server - Connects Claude Code with Figma API

Features:
- Search for components by name
- Get detailed design specs with Tailwind mappings
- Export component images
- Get component hierarchy with full specs
- Automatic caching to reduce API calls
"""
import sys
import logging
from typing import Any, List, Optional
from mcp.server.fastmcp import FastMCP
from figma_client import FigmaClient

# CRITICAL: For stdio transport, NEVER write to stdout
logging.basicConfig(
	level=logging.INFO,
	stream=sys.stderr,
	format='[%(asctime)s] %(levelname)s: %(message)s'
)

# Initialize MCP server with 5-minute cache TTL
mcp = FastMCP("figma-server")
figma = FigmaClient(cache_ttl=300)


@mcp.tool()
async def search_figma_components(
	component_name: str,
	file_key: str = None,
	include_types: List[str] = None,
	max_results: int = 20
) -> dict:
	"""
	Search for Figma components by name.

	Args:
		component_name: Name of the component to search for (case-insensitive)
		file_key: Optional Figma file key (uses FIGMA_DEFAULT_FILE_KEY if not provided)
		include_types: Optional list of node types to include (default: COMPONENT, COMPONENT_SET, FRAME, INSTANCE)
		max_results: Maximum number of results to return (default: 20)

	Returns:
		Dictionary with matching components including their IDs, names, types, and dimensions
	"""
	try:
		target_file = file_key or figma.default_file_key
		if not target_file:
			return {
				"success": False,
				"error": "No file_key provided and FIGMA_DEFAULT_FILE_KEY not set"
			}

		matches = await figma.search_components_in_file(
			target_file,
			component_name,
			include_types,
			max_results
		)

		return {
			"success": True,
			"matches": matches,
			"count": len(matches),
			"file_key": target_file,
			"hint": "Use get_component_full_specs with a component ID to get detailed design specifications"
		}
	except Exception as e:
		logging.error(f"Error searching components: {e}")
		return {"success": False, "error": str(e)}


@mcp.tool()
async def get_component_design_specs(file_key: str, node_id: str) -> dict:
	"""
	Get basic design specifications for a component (use get_component_full_specs for detailed specs).

	Args:
		file_key: Figma file key
		node_id: Component node ID

	Returns:
		Basic design specs including dimensions, colors, typography, spacing
	"""
	try:
		details = await figma.get_component_details(file_key, node_id)
		node_data = details.get("nodes", {}).get(node_id, {})
		document = node_data.get("document", {})

		specs = figma.extract_full_design_specs(document)
		specs["success"] = True
		specs["file_key"] = file_key
		specs["node_id"] = node_id

		return specs
	except Exception as e:
		logging.error(f"Error getting component specs: {e}")
		return {"success": False, "error": str(e)}


@mcp.tool()
async def get_component_full_specs(
	file_key: str,
	node_id: str,
	include_children: bool = True,
	max_depth: int = 3
) -> dict:
	"""
	Get comprehensive design specifications for a component with Tailwind CSS mappings.

	This is the primary tool for implementing Figma designs. It extracts:
	- Dimensions (width, height)
	- Colors (hex, rgba, rgb values)
	- Typography (font family, size as px/rem/tailwind, weight, line-height)
	- Spacing (padding, gaps with Tailwind class suggestions)
	- Border radius (with Tailwind rounded-* suggestions)
	- Effects (shadows, blur)
	- Full children hierarchy (optional)

	Args:
		file_key: Figma file key
		node_id: Component node ID (get this from search_figma_components)
		include_children: Whether to include child component specs (default: True)
		max_depth: Maximum depth for children recursion (default: 3)

	Returns:
		Comprehensive design specs with Tailwind-compatible values
	"""
	try:
		if include_children:
			specs = await figma.get_component_with_children(file_key, node_id, max_depth)
		else:
			details = await figma.get_component_details(file_key, node_id)
			node_data = details.get("nodes", {}).get(node_id, {})
			document = node_data.get("document", {})
			specs = figma.extract_full_design_specs(document)

		specs["success"] = True
		specs["file_key"] = file_key
		specs["node_id"] = node_id

		return specs
	except Exception as e:
		logging.error(f"Error getting full component specs: {e}")
		return {"success": False, "error": str(e)}


@mcp.tool()
async def get_component_image(
	file_key: str,
	node_id: str,
	format: str = "png",
	scale: float = 2.0
) -> dict:
	"""
	Export a Figma component as an image URL.

	Args:
		file_key: Figma file key
		node_id: Component node ID
		format: Image format - "png", "svg", "jpg", or "pdf" (default: png)
		scale: Image scale 0.01-4 (default: 2.0 for retina)

	Returns:
		Dictionary with image URL that can be used to download the component image
	"""
	try:
		result = await figma.get_image(file_key, node_id, format, scale)
		images = result.get("images", {})
		image_url = images.get(node_id)

		return {
			"success": True,
			"image_url": image_url,
			"format": format,
			"scale": scale,
			"node_id": node_id,
			"hint": "This URL is temporary and expires. Download or view it promptly."
		}
	except Exception as e:
		logging.error(f"Error exporting image: {e}")
		return {"success": False, "error": str(e)}


@mcp.tool()
async def get_figma_file_info(file_key: str) -> dict:
	"""
	Get information about a Figma file.

	Args:
		file_key: Figma file key (from URL: figma.com/file/{file_key}/...)

	Returns:
		File information including name, last modified, thumbnail URL
	"""
	try:
		file_data = await figma.get_file(file_key)
		return {
			"success": True,
			"name": file_data.get("name"),
			"last_modified": file_data.get("lastModified"),
			"thumbnail_url": file_data.get("thumbnailUrl"),
			"version": file_data.get("version"),
		}
	except Exception as e:
		logging.error(f"Error getting file info: {e}")
		return {"success": False, "error": str(e)}


@mcp.tool()
async def get_file_styles(file_key: str = None) -> dict:
	"""
	Get all styles (colors, typography, effects) defined in a Figma file.
	Useful for understanding the design system before implementing components.

	Args:
		file_key: Optional Figma file key (uses default if not provided)

	Returns:
		Dictionary with all defined styles in the file
	"""
	try:
		target_file = file_key or figma.default_file_key
		if not target_file:
			return {
				"success": False,
				"error": "No file_key provided and FIGMA_DEFAULT_FILE_KEY not set"
			}

		styles = await figma.get_file_styles(target_file)
		return {
			"success": True,
			"styles": styles.get("meta", {}).get("styles", []),
			"file_key": target_file
		}
	except Exception as e:
		logging.error(f"Error getting file styles: {e}")
		return {"success": False, "error": str(e)}


@mcp.tool()
async def clear_figma_cache() -> dict:
	"""
	Clear the Figma API cache. Use this if you need fresh data after Figma file changes.

	Returns:
		Number of cache entries cleared
	"""
	try:
		count = figma.cache.clear()
		return {
			"success": True,
			"cleared": count,
			"message": f"Cleared {count} cached entries"
		}
	except Exception as e:
		logging.error(f"Error clearing cache: {e}")
		return {"success": False, "error": str(e)}


# Run the server
if __name__ == "__main__":
	mcp.run()
