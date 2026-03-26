# Zotero MCP Server

A custom [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that connects your Zotero library to Claude Desktop. Once connected, you can search your library, browse collections, and retrieve full citation metadata directly in conversation.

## Available Tools

| Tool | Description |
|---|---|
| `search_library` | Search your library by keyword (title, author, topic, etc.) |
| `get_collections` | List all your Zotero collections/folders |
| `get_items_in_collection` | Fetch items from a specific collection |
| `get_item_details` | Get full metadata for a specific item |
| `get_recent_items` | Get the most recently added items |

---

## Requirements

- Python 3.10 or higher
- A Zotero account with an API key ([create one here](https://www.zotero.org/settings/keys))
- Claude Desktop installed

---

## Setup

### 1. Get your Zotero credentials

Go to [zotero.org/settings/keys](https://www.zotero.org/settings/keys) and note your **User ID** and create a new **API Key** (read-only access is sufficient).

> ⚠️ Treat your API key like a password — never share it or commit it to version control.

### 2. Install dependencies

Make sure you're using Python 3.10+. Then run:

```bash
py -3.10 -m pip install -r requirements.txt
```

### 3. Test the server

```bash
py -3.10 server.py
```

You should see: `Starting Zotero MCP server...`

If it starts without errors, you're ready to connect.

---

## Connecting to Claude Desktop

### Find your config file

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows (standard install):** `**Windows**: `AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json`

You can also access it from Claude Desktop: **File → Settings → Developer → Edit Config**

### Add the MCP server config

```json
{
  "mcpServers": {
    "zotero": {
      "command": "C:\\Windows\\py.exe",
      "args": ["-3.10", "C:\\full\\path\\to\\server.py"],
      "env": {
        "ZOTERO_USER_ID": "your_user_id_here",
        "ZOTERO_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

A few things to note:
- Use double backslashes `\\` in all Windows paths inside JSON
- Replace the `args` path with the actual location of `server.py` on your machine
- If you have an existing `preferences` block in your config, just add `mcpServers` alongside it — don't replace the whole file

### Verify the connection

After restarting Claude Desktop, go to **Settings → Developer** to confirm the Zotero server shows a **running** status. You can also click **View Logs** to see tool registration and any errors.

---

## Connecting to Claude Code

```bash
claude mcp add zotero py -- -3.10 /absolute/path/to/server.py
```

---

## Troubleshooting

**Server shows "running" but tools aren't working**
Check the logs in Settings → Developer → View Logs for error messages. The most common issue is a missing `await` on async HTTP calls.

**`mcp` package won't install**
The `mcp` package requires Python 3.10+. Run `py -0` to list installed versions and make sure you're using the right one.

**`python` command not found by Claude Desktop**
Claude Desktop may not inherit your terminal's PATH. Use the full path to your Python executable in the config (e.g., `C:\\Windows\\py.exe`) rather than just `"python"`.

**Config file not being picked up**
On Windows Store installs, Claude Desktop reads from `C:\Users\<you>\AppData\Roaming\Claude\` — not the virtualized LocalCache path. Create the file there if it doesn't exist.

---

## Security Notes

- Never commit your `.env` file or paste your API key into chat (`.gitignore` is included to help)
- Use a read-only Zotero API key unless you intend to add write tools
- Your credentials are passed via environment variables and never leave your machine