"""
Zotero MCP Server
Exposes your Zotero library as tools for Claude via the Model Context Protocol.
"""

import os
import logging
import httpx
import base64
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

# ── Write Tools ───────────────────────────────────────────────────────────────────
@mcp.tool()
async def create_collection(name: str, parent_key: str = None) -> dict:
    """
    Create a new collection in your Zotero library.
    Can be a top-level collection or a sub-collection under an existing one.
 
    Args:
        name: Name of the new collection
        parent_key: Key of the parent collection (optional — omit for top-level)
    """
    payload = {"name": name}
    if parent_key:
        payload["parentCollection"] = parent_key
 
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/collections",
            headers={**zotero_headers(), "Content-Type": "application/json"},
            json=[payload],
        )
        response.raise_for_status()
        data = response.json()
 
    created = data.get("successful", {}).get("0", {})
    return {
        "key": created.get("key"),
        "name": created.get("data", {}).get("name"),
        "parent_collection": created.get("data", {}).get("parentCollection"),
    }
 
 
@mcp.tool()
async def add_item_to_collection(item_key: str, collection_key: str) -> dict:
    """
    Add an existing item to a collection.
    Note: In Zotero, items can belong to multiple collections simultaneously.
 
    Args:
        item_key: The key of the item to add
        collection_key: The key of the target collection
    """
    # First fetch the current item to get its existing collections
    async with httpx.AsyncClient() as client:
        get_response = await client.get(
            f"{BASE_URL}/items/{item_key}",
            headers=zotero_headers(),
            params={"format": "json"},
        )
        get_response.raise_for_status()
        item = get_response.json()
 
    data = item.get("data", {})
    existing_collections = data.get("collections", [])
 
    if collection_key in existing_collections:
        return {"status": "already_in_collection", "item_key": item_key, "collection_key": collection_key}
 
    updated_collections = existing_collections + [collection_key]
 
    async with httpx.AsyncClient() as client:
        patch_response = await client.patch(
            f"{BASE_URL}/items/{item_key}",
            headers={
                **zotero_headers(),
                "Content-Type": "application/json",
                "If-Unmodified-Since-Version": str(item.get("version", 0)),
            },
            json={"collections": updated_collections},
        )
        patch_response.raise_for_status()
 
    return {"status": "success", "item_key": item_key, "collection_key": collection_key}
 
 
@mcp.tool()
async def remove_item_from_collection(item_key: str, collection_key: str) -> dict:
    """
    Remove an item from a specific collection (does not delete the item itself).
 
    Args:
        item_key: The key of the item
        collection_key: The key of the collection to remove it from
    """
    async with httpx.AsyncClient() as client:
        get_response = await client.get(
            f"{BASE_URL}/items/{item_key}",
            headers=zotero_headers(),
            params={"format": "json"},
        )
        get_response.raise_for_status()
        item = get_response.json()
 
    data = item.get("data", {})
    existing_collections = data.get("collections", [])
    updated_collections = [c for c in existing_collections if c != collection_key]
 
    async with httpx.AsyncClient() as client:
        patch_response = await client.patch(
            f"{BASE_URL}/items/{item_key}",
            headers={
                **zotero_headers(),
                "Content-Type": "application/json",
                "If-Unmodified-Since-Version": str(item.get("version", 0)),
            },
            json={"collections": updated_collections},
        )
        patch_response.raise_for_status()
 
    return {"status": "success", "item_key": item_key, "removed_from": collection_key}
 
 
@mcp.tool()
async def update_item_tags(item_key: str, tags: list[str]) -> dict:
    """
    Replace the tags on an item with a new set of tags.
 
    Args:
        item_key: The key of the item to update
        tags: List of tag strings to apply
    """
    async with httpx.AsyncClient() as client:
        get_response = await client.get(
            f"{BASE_URL}/items/{item_key}",
            headers=zotero_headers(),
            params={"format": "json"},
        )
        get_response.raise_for_status()
        item = get_response.json()
 
    tag_objects = [{"tag": t} for t in tags]
 
    async with httpx.AsyncClient() as client:
        patch_response = await client.patch(
            f"{BASE_URL}/items/{item_key}",
            headers={
                **zotero_headers(),
                "Content-Type": "application/json",
                "If-Unmodified-Since-Version": str(item.get("version", 0)),
            },
            json={"tags": tag_objects},
        )
        patch_response.raise_for_status()
 
    return {"status": "success", "item_key": item_key, "tags": tags}
 
 
# ── PDF Tools ─────────────────────────────────────────────────────────────────
 
@mcp.tool()
async def get_item_attachments(item_key: str) -> list[dict]:
    """
    List all attachments for a Zotero item (PDFs, snapshots, links, etc.)
    Use this to find the attachment key before calling get_pdf.
 
    Args:
        item_key: The key of the parent item
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/items/{item_key}/children",
            headers=zotero_headers(),
            params={"format": "json"},
        )
        response.raise_for_status()
        children = response.json()
 
    return [
        {
            "key": child.get("key"),
            "title": child.get("data", {}).get("title", "Untitled"),
            "link_mode": child.get("data", {}).get("linkMode", ""),
            "content_type": child.get("data", {}).get("contentType", ""),
            "filename": child.get("data", {}).get("filename", ""),
        }
        for child in children
        if child.get("data", {}).get("itemType") == "attachment"
    ]
 
 
@mcp.tool()
async def get_pdf(attachment_key: str) -> dict:
    """
    Download a PDF attachment from Zotero and return it as base64 for Claude to read.
    Use get_item_attachments first to find the attachment key.
 
    Args:
        attachment_key: The key of the PDF attachment (not the parent item key)
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        response = await client.get(
            f"{BASE_URL}/items/{attachment_key}/file",
            headers=zotero_headers(),
        )
        response.raise_for_status()
 
        content_type = response.headers.get("content-type", "application/pdf")
        pdf_bytes = response.content
 
    if not pdf_bytes:
        return {"error": "No file content returned. The PDF may not be synced to Zotero's cloud."}
 
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
 
    return {
        "attachment_key": attachment_key,
        "content_type": content_type,
        "size_bytes": len(pdf_bytes),
        "data": pdf_base64,
        "encoding": "base64",
        "note": "Pass the 'data' field to Claude as a base64-encoded PDF document for reading.",
    }

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