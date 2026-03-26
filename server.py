"""
Zotero MCP Server
Exposes your Zotero library as tools for Claude via the Model Context Protocol.
"""

import os
import logging
import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load credentials from .env file
load_dotenv()

ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")
ZOTERO_USER_ID = os.getenv("ZOTERO_USER_ID")
BASE_URL = f"https://api.zotero.org/users/{ZOTERO_USER_ID}"

# Configure logging to stderr only (stdout would corrupt MCP's JSON-RPC messages)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Zotero Library")


def zotero_headers() -> dict:
    """Return standard Zotero API headers."""
    return {
        "Zotero-API-Key": ZOTERO_API_KEY,
        "Zotero-API-Version": "3",
    }


# ── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_library(query: str, limit: int = 10) -> list[dict]:
    """
    Search your Zotero library by keyword.
    Returns title, authors, year, item type, and abstract for each match.

    Args:
        query: Search term (title, author, keyword, etc.)
        limit: Max number of results to return (default 10)
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/items",
            headers=zotero_headers(),
            params={"q": query, "limit": limit, "format": "json"},
        )
        response.raise_for_status()
        items = response.json()

    results = []
    for item in items:
        data = item.get("data", {})
        results.append({
            "key": item.get("key"),
            "title": data.get("title", "No title"),
            "item_type": data.get("itemType", "unknown"),
            "year": data.get("date", "")[:4] if data.get("date") else "",
            "authors": _format_authors(data.get("creators", [])),
            "abstract": data.get("abstractNote", "")[:300],  # truncate for brevity
            "url": data.get("url", ""),
        })
    return results


@mcp.tool()
async def get_collections() -> list[dict]:
    """
    List all collections (folders) in your Zotero library.
    Returns collection name, key, and item count.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/collections",
            headers=zotero_headers(),
            params={"format": "json"},
        )
        response.raise_for_status()
        collections = response.json()

    return [
        {
            "key": c.get("key"),
            "name": c.get("data", {}).get("name", "Unnamed"),
            "num_items": c.get("meta", {}).get("numItems", 0),
            "parent_collection": c.get("data", {}).get("parentCollection", None),
        }
        for c in collections
    ]


@mcp.tool()
async def get_items_in_collection(collection_key: str, limit: int = 20) -> list[dict]:
    """
    Get items from a specific Zotero collection.

    Args:
        collection_key: The collection key (get this from get_collections)
        limit: Max number of items to return (default 20)
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/collections/{collection_key}/items",
            headers=zotero_headers(),
            params={"limit": limit, "format": "json"},
        )
        response.raise_for_status()
        items = response.json()

    results = []
    for item in items:
        data = item.get("data", {})
        results.append({
            "key": item.get("key"),
            "title": data.get("title", "No title"),
            "item_type": data.get("itemType", "unknown"),
            "year": data.get("date", "")[:4] if data.get("date") else "",
            "authors": _format_authors(data.get("creators", [])),
            "abstract": data.get("abstractNote", "")[:300],
        })
    return results


@mcp.tool()
async def get_item_details(item_key: str) -> dict:
    """
    Get full metadata for a specific Zotero item.

    Args:
        item_key: The item key (get this from search_library or get_items_in_collection)
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/items/{item_key}",
            headers=zotero_headers(),
            params={"format": "json"},
        )
        response.raise_for_status()
        item = response.json()

    data = item.get("data", {})
    return {
        "key": item.get("key"),
        "title": data.get("title", "No title"),
        "item_type": data.get("itemType", "unknown"),
        "authors": _format_authors(data.get("creators", [])),
        "date": data.get("date", ""),
        "abstract": data.get("abstractNote", ""),
        "publication": data.get("publicationTitle", data.get("bookTitle", "")),
        "journal": data.get("journalAbbreviation", ""),
        "doi": data.get("DOI", ""),
        "url": data.get("url", ""),
        "volume": data.get("volume", ""),
        "issue": data.get("issue", ""),
        "pages": data.get("pages", ""),
        "publisher": data.get("publisher", ""),
        "tags": [t.get("tag") for t in data.get("tags", [])],
        "notes": data.get("note", ""),
    }


@mcp.tool()
async def get_recent_items(limit: int = 10) -> list[dict]:
    """
    Get the most recently added items in your Zotero library.

    Args:
        limit: Number of recent items to return (default 10)
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/items",
            headers=zotero_headers(),
            params={"sort": "dateAdded", "direction": "desc", "limit": limit, "format": "json"},
        )
        response.raise_for_status()
        items = response.json()

    results = []
    for item in items:
        data = item.get("data", {})
        results.append({
            "key": item.get("key"),
            "title": data.get("title", "No title"),
            "item_type": data.get("itemType", "unknown"),
            "year": data.get("date", "")[:4] if data.get("date") else "",
            "authors": _format_authors(data.get("creators", [])),
            "date_added": data.get("dateAdded", ""),
        })
    return results


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_authors(creators: list[dict]) -> str:
    """Format a list of Zotero creator objects into a readable string."""
    authors = [
        c for c in creators if c.get("creatorType") == "author"
    ]
    if not authors:
        authors = creators  # fallback: include all creators

    names = []
    for a in authors[:3]:  # limit to first 3
        last = a.get("lastName", "")
        first = a.get("firstName", "")
        if last:
            names.append(f"{last}, {first}".strip(", "))
        else:
            names.append(a.get("name", "Unknown"))

    if len(creators) > 3:
        names.append("et al.")

    return "; ".join(names)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not ZOTERO_API_KEY or not ZOTERO_USER_ID:
        raise EnvironmentError(
            "Missing credentials. Make sure ZOTERO_API_KEY and ZOTERO_USER_ID are set in your .env file."
        )
    logger.info("Starting Zotero MCP server...")
    mcp.run(transport="stdio")