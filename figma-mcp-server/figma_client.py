import os
import httpx
import hashlib
import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

class FigmaCache:
	"""Simple file-based cache to reduce API calls and token usage"""

	def __init__(self, cache_dir: str = ".figma_cache", ttl_seconds: int = 300):
		self.cache_dir = Path(cache_dir)
		self.cache_dir.mkdir(exist_ok=True)
		self.ttl = ttl_seconds

	def _get_cache_key(self, *args) -> str:
		"""Generate cache key from arguments"""
		key_string = ":".join(str(arg) for arg in args)
		return hashlib.md5(key_string.encode()).hexdigest()

	def get(self, *args) -> Optional[Dict]:
		"""Get cached data if valid"""
		cache_key = self._get_cache_key(*args)
		cache_file = self.cache_dir / f"{cache_key}.json"

		if cache_file.exists():
			try:
				data = json.loads(cache_file.read_text())
				if time.time() - data.get("timestamp", 0) < self.ttl:
					return data.get("value")
			except (json.JSONDecodeError, KeyError):
				pass
		return None

	def set(self, value: Any, *args) -> None:
		"""Cache a value"""
		cache_key = self._get_cache_key(*args)
		cache_file = self.cache_dir / f"{cache_key}.json"
		cache_file.write_text(json.dumps({
			"timestamp": time.time(),
			"value": value
		}))

	def clear(self) -> int:
		"""Clear all cache files, return count deleted"""
		count = 0
		for f in self.cache_dir.glob("*.json"):
			f.unlink()
			count += 1
		return count


class FigmaClient:
	"""Wrapper for Figma REST API with caching"""

	def __init__(self, cache_ttl: int = 300):
		self.api_key = os.getenv("FIGMA_API_KEY")
		if not self.api_key:
			raise ValueError("FIGMA_API_KEY environment variable not set")

		self.base_url = "https://api.figma.com/v1"
		self.headers = {"X-Figma-Token": self.api_key}
		self.default_file_key = os.getenv("FIGMA_DEFAULT_FILE_KEY")
		self.cache = FigmaCache(ttl_seconds=cache_ttl)

	async def _request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
		"""Make cached API request"""
		cache_key = ("request", endpoint, str(params or {}))
		cached = self.cache.get(*cache_key)
		if cached:
			return cached

		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.get(
				f"{self.base_url}{endpoint}",
				params=params,
				headers=self.headers
			)
			response.raise_for_status()
			data = response.json()
			self.cache.set(data, *cache_key)
			return data

	async def get_file(self, file_key: str, geometry: str = "paths") -> Dict[str, Any]:
		"""Get Figma file details with optional geometry"""
		return await self._request(f"/files/{file_key}", {"geometry": geometry})

	async def get_file_styles(self, file_key: str) -> Dict[str, Any]:
		"""Get all styles defined in file"""
		return await self._request(f"/files/{file_key}/styles")

	async def get_component_details(self, file_key: str, node_ids: str) -> Dict[str, Any]:
		"""Get specific component/node details with styles"""
		return await self._request(f"/files/{file_key}/nodes", {"ids": node_ids})

	async def get_file_components(self, file_key: str) -> Dict[str, Any]:
		"""Get all components in a file (published only)"""
		return await self._request(f"/files/{file_key}/components")

	async def get_image(self, file_key: str, node_ids: str, format: str = "png", scale: float = 2) -> Dict[str, Any]:
		"""Export nodes as images"""
		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.get(
				f"{self.base_url}/images/{file_key}",
				params={"ids": node_ids, "format": format, "scale": scale},
				headers=self.headers
			)
			response.raise_for_status()
			return response.json()

	def _search_node_tree(self, node: Dict[str, Any], query: str, results: List[Dict[str, Any]],
						   include_types: List[str] = None, max_results: int = 50) -> None:
		"""Recursively search through node tree for components matching query"""
		if len(results) >= max_results:
			return

		node_type = node.get("type", "")
		node_name = node.get("name", "")

		types_to_match = include_types or ["COMPONENT", "COMPONENT_SET", "FRAME", "INSTANCE"]

		if query.lower() in node_name.lower() and node_type in types_to_match:
			results.append({
				"id": node.get("id"),
				"name": node_name,
				"type": node_type,
				"description": node.get("description", ""),
				"absoluteBoundingBox": node.get("absoluteBoundingBox"),
			})

		if "children" in node:
			for child in node["children"]:
				self._search_node_tree(child, query, results, include_types, max_results)

	async def search_components_in_file(self, file_key: str, query: str,
										 include_types: List[str] = None, max_results: int = 50) -> List[Dict[str, Any]]:
		"""Search for components in file by name"""
		file_data = await self.get_file(file_key)
		results = []
		document = file_data.get("document", {})
		self._search_node_tree(document, query, results, include_types, max_results)
		return results

	def _extract_color(self, color: Dict) -> Dict[str, Any]:
		"""Extract color as multiple formats"""
		if not color:
			return None
		r = int(color.get("r", 0) * 255)
		g = int(color.get("g", 0) * 255)
		b = int(color.get("b", 0) * 255)
		a = color.get("a", 1)

		return {
			"rgba": f"rgba({r}, {g}, {b}, {a})",
			"hex": f"#{r:02x}{g:02x}{b:02x}" + (f"{int(a*255):02x}" if a < 1 else ""),
			"rgb": {"r": r, "g": g, "b": b, "a": a}
		}

	def _px_to_rem(self, px: float, base: int = 16) -> str:
		"""Convert pixels to rem"""
		return f"{px / base}rem"

	def _extract_typography(self, style: Dict) -> Dict[str, Any]:
		"""Extract typography as Tailwind-compatible values"""
		if not style:
			return None

		font_size = style.get("fontSize", 16)
		line_height = style.get("lineHeightPx", font_size * 1.5)
		letter_spacing = style.get("letterSpacing", 0)

		# Map font weights to Tailwind
		weight_map = {
			100: "thin", 200: "extralight", 300: "light", 400: "normal",
			500: "medium", 600: "semibold", 700: "bold", 800: "extrabold", 900: "black"
		}
		font_weight = style.get("fontWeight", 400)

		return {
			"fontFamily": style.get("fontFamily"),
			"fontSize": {
				"px": font_size,
				"rem": self._px_to_rem(font_size),
				"tailwind": self._px_to_tailwind_size(font_size)
			},
			"fontWeight": {
				"value": font_weight,
				"tailwind": weight_map.get(font_weight, "normal")
			},
			"lineHeight": {
				"px": line_height,
				"ratio": round(line_height / font_size, 2) if font_size else 1.5
			},
			"letterSpacing": {
				"px": letter_spacing,
				"em": f"{letter_spacing / font_size:.3f}em" if font_size else "0em"
			},
			"textAlign": style.get("textAlignHorizontal", "LEFT").lower(),
			"textTransform": "uppercase" if style.get("textCase") == "UPPER" else "none"
		}

	def _px_to_tailwind_size(self, px: float) -> str:
		"""Map pixel size to closest Tailwind class"""
		sizes = {
			12: "xs", 14: "sm", 16: "base", 18: "lg", 20: "xl",
			24: "2xl", 30: "3xl", 36: "4xl", 48: "5xl", 60: "6xl",
			72: "7xl", 96: "8xl", 128: "9xl"
		}
		closest = min(sizes.keys(), key=lambda x: abs(x - px))
		return f"text-{sizes[closest]}"

	def _extract_spacing(self, node: Dict) -> Dict[str, Any]:
		"""Extract spacing (padding, gaps) from auto-layout nodes"""
		if node.get("layoutMode") is None:
			return None

		return {
			"paddingTop": node.get("paddingTop", 0),
			"paddingRight": node.get("paddingRight", 0),
			"paddingBottom": node.get("paddingBottom", 0),
			"paddingLeft": node.get("paddingLeft", 0),
			"itemSpacing": node.get("itemSpacing", 0),
			"layoutMode": node.get("layoutMode"),  # HORIZONTAL or VERTICAL
			"primaryAxisAlignItems": node.get("primaryAxisAlignItems"),
			"counterAxisAlignItems": node.get("counterAxisAlignItems"),
			"tailwind": self._spacing_to_tailwind(node)
		}

	def _spacing_to_tailwind(self, node: Dict) -> Dict[str, str]:
		"""Convert Figma spacing to Tailwind classes"""
		def px_to_tw_spacing(px: float) -> str:
			# Tailwind spacing scale
			scale = {0: "0", 1: "px", 2: "0.5", 4: "1", 6: "1.5", 8: "2", 10: "2.5",
					 12: "3", 14: "3.5", 16: "4", 20: "5", 24: "6", 28: "7", 32: "8",
					 36: "9", 40: "10", 44: "11", 48: "12", 56: "14", 64: "16",
					 80: "20", 96: "24", 112: "28", 128: "32", 144: "36", 160: "40"}
			closest = min(scale.keys(), key=lambda x: abs(x - px))
			return scale[closest]

		pt, pr, pb, pl = (node.get(f"padding{d}", 0) for d in ["Top", "Right", "Bottom", "Left"])
		gap = node.get("itemSpacing", 0)
		layout = node.get("layoutMode", "")

		classes = []

		# Flex direction
		if layout == "HORIZONTAL":
			classes.append("flex-row")
		elif layout == "VERTICAL":
			classes.append("flex-col")

		# Gap
		if gap > 0:
			classes.append(f"gap-{px_to_tw_spacing(gap)}")

		# Padding (use shorthand when possible)
		if pt == pr == pb == pl and pt > 0:
			classes.append(f"p-{px_to_tw_spacing(pt)}")
		else:
			if pt > 0: classes.append(f"pt-{px_to_tw_spacing(pt)}")
			if pr > 0: classes.append(f"pr-{px_to_tw_spacing(pr)}")
			if pb > 0: classes.append(f"pb-{px_to_tw_spacing(pb)}")
			if pl > 0: classes.append(f"pl-{px_to_tw_spacing(pl)}")

		return {
			"classes": " ".join(classes),
			"flexDirection": "flex-row" if layout == "HORIZONTAL" else "flex-col"
		}

	def _extract_border_radius(self, node: Dict) -> Dict[str, Any]:
		"""Extract border radius with Tailwind mapping"""
		radius = node.get("cornerRadius", 0)
		radii = node.get("rectangleCornerRadii", [radius, radius, radius, radius])

		# Tailwind border-radius scale
		tw_map = {0: "none", 2: "sm", 4: "DEFAULT", 6: "md", 8: "lg",
				  12: "xl", 16: "2xl", 24: "3xl", 9999: "full"}

		def to_tw(r: float) -> str:
			if r >= 9999:
				return "full"
			closest = min(tw_map.keys(), key=lambda x: abs(x - r))
			return tw_map[closest]

		return {
			"uniform": radius,
			"corners": {
				"topLeft": radii[0] if radii else radius,
				"topRight": radii[1] if len(radii) > 1 else radius,
				"bottomRight": radii[2] if len(radii) > 2 else radius,
				"bottomLeft": radii[3] if len(radii) > 3 else radius,
			},
			"tailwind": f"rounded-{to_tw(radius)}" if radius > 0 else ""
		}

	def extract_full_design_specs(self, node: Dict) -> Dict[str, Any]:
		"""Extract comprehensive design specifications from a node"""
		specs = {
			"name": node.get("name"),
			"type": node.get("type"),
			"dimensions": {
				"width": node.get("absoluteBoundingBox", {}).get("width"),
				"height": node.get("absoluteBoundingBox", {}).get("height"),
			}
		}

		# Extract fills (background colors)
		fills = node.get("fills", [])
		if fills:
			specs["fills"] = []
			for fill in fills:
				if fill.get("type") == "SOLID" and fill.get("visible", True):
					specs["fills"].append({
						"type": "SOLID",
						"color": self._extract_color(fill.get("color")),
						"opacity": fill.get("opacity", 1)
					})
				elif fill.get("type") == "GRADIENT_LINEAR":
					specs["fills"].append({
						"type": "GRADIENT",
						"gradientStops": [
							{"color": self._extract_color(stop.get("color")), "position": stop.get("position")}
							for stop in fill.get("gradientStops", [])
						]
					})

		# Extract strokes (borders)
		strokes = node.get("strokes", [])
		if strokes:
			specs["strokes"] = [{
				"color": self._extract_color(stroke.get("color")),
				"weight": node.get("strokeWeight", 1),
				"align": node.get("strokeAlign", "INSIDE")
			} for stroke in strokes if stroke.get("visible", True)]

		# Typography (for text nodes)
		if node.get("type") == "TEXT":
			specs["typography"] = self._extract_typography(node.get("style", {}))
			specs["characters"] = node.get("characters", "")

		# Spacing & layout
		spacing = self._extract_spacing(node)
		if spacing:
			specs["layout"] = spacing

		# Border radius
		if node.get("cornerRadius", 0) > 0 or node.get("rectangleCornerRadii"):
			specs["borderRadius"] = self._extract_border_radius(node)

		# Effects (shadows, blur)
		effects = node.get("effects", [])
		if effects:
			specs["effects"] = []
			for effect in effects:
				if effect.get("visible", True):
					effect_data = {
						"type": effect.get("type"),
					}
					if effect.get("type") in ["DROP_SHADOW", "INNER_SHADOW"]:
						effect_data.update({
							"color": self._extract_color(effect.get("color")),
							"offset": {"x": effect.get("offset", {}).get("x", 0),
									   "y": effect.get("offset", {}).get("y", 0)},
							"radius": effect.get("radius", 0),
							"spread": effect.get("spread", 0)
						})
					specs["effects"].append(effect_data)

		return specs

	def _collect_children_specs(self, node: Dict, depth: int = 0, max_depth: int = 3) -> List[Dict]:
		"""Recursively collect specs for child nodes"""
		if depth > max_depth:
			return []

		children_specs = []
		for child in node.get("children", []):
			child_spec = self.extract_full_design_specs(child)
			child_spec["depth"] = depth
			child_spec["children"] = self._collect_children_specs(child, depth + 1, max_depth)
			children_specs.append(child_spec)

		return children_specs

	async def get_component_with_children(self, file_key: str, node_id: str, max_depth: int = 3) -> Dict[str, Any]:
		"""Get component with full children hierarchy and specs"""
		details = await self.get_component_details(file_key, node_id)
		node_data = details.get("nodes", {}).get(node_id, {})
		document = node_data.get("document", {})

		specs = self.extract_full_design_specs(document)
		specs["children"] = self._collect_children_specs(document, 0, max_depth)

		return specs
