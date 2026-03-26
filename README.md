# zotero_MPC
# Zotero MCP Server

A custom Model Context Protocol (MCP) server that connects your Zotero library to Claude.

## Tools Exposed

| Tool | Description |
|---|---|
| `search_library` | Search your library by keyword |
| `get_collections` | List all your collections/folders |
| `get_items_in_collection` | Get items from a specific collection |
| `get_item_details` | Get full metadata for a specific item |
| `get_recent_items` | Get most recently added items |

---

## Setup

### 1. Clone / download this folder

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your credentials

```bash
cp .env.example .env
```

Open `.env` and fill in your values:
```
ZOTERO_USER_ID=123456
ZOTERO_API_KEY=your_key_here
```

- **User ID**: found at https://www.zotero.org/settings/keys
- **API Key**: create one at the same page (read-only is enough)

### 5. Test it

```bash
python server.py
```

You should see: `Starting Zotero MCP server...`

---

## Connect to Claude Desktop

Add the following to your Claude Desktop config file:

**Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "zotero": {
      "command": "python",
      "args": ["/absolute/path/to/zotero-mcp/server.py"],
      "env": {
        "ZOTERO_USER_ID": "your_user_id",
        "ZOTERO_API_KEY": "your_api_key"
      }
    }
  }
}
```

> Replace `/absolute/path/to/zotero-mcp/server.py` with the actual path on your machine.

Then restart Claude Desktop. You should see the Zotero tools available.

---

## Connect to Claude Code

```bash
claude mcp add zotero python /absolute/path/to/zotero-mcp/server.py
```

---

## Security Notes

- Never commit `.env` to version control (`.gitignore` covers this)
- Use a **read-only** Zotero API key unless you need write access
- Your credentials never leave your machine
