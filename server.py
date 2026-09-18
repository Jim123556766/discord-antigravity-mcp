# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "mcp>=1.0.0",
#     "httpx>=0.27.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
Discord MCP Server for Antigravity
Provides Antigravity with full management capabilities over Discord servers:
- Channels, Categories, and Structure Creation
- Roles and Permission Management
- Messages, Embeds, and Announcements
- Invites and Member Operations
- Direct REST API for arbitrary Discord operations
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

DISCORD_API_BASE = "https://discord.com/api/v10"
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()

# Initialize MCP Server
server = MCPServer("discord")


def get_headers() -> Dict[str, str]:
    token = os.getenv("DISCORD_BOT_TOKEN", BOT_TOKEN).strip()
    if not token:
        raise ValueError(
            "DISCORD_BOT_TOKEN is missing! Set it in your .env file or environment variables."
        )
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "AntigravityDiscordMCP/1.0",
    }


def parse_color(color: Optional[str]) -> int:
    """Convert hex string (e.g. '#FF5733' or 'FF5733' or 'red') to Discord integer color."""
    if not color:
        return 0x5865F2  # Discord Blurple default

    named_colors = {
        "blurple": 0x5865F2,
        "green": 0x57F287,
        "yellow": 0xFEE75C,
        "fuchsia": 0xEB459E,
        "red": 0xED4245,
        "white": 0xFFFFFF,
        "black": 0x000000,
        "gold": 0xF1C40F,
        "blue": 0x3498DB,
        "purple": 0x9B59B6,
        "orange": 0xE67E22,
    }
    lower = color.strip().lower()
    if lower in named_colors:
        return named_colors[lower]

    hex_str = color.lstrip("#")
    try:
        return int(hex_str, 16)
    except ValueError:
        return 0x5865F2


async def _resolve_guild_id(client: httpx.AsyncClient, guild_id: Optional[str] = None) -> str:
    """If guild_id is omitted, auto-resolve the server the bot is in."""
    if guild_id and guild_id.strip():
        return guild_id.strip()

    resp = await client.get(f"{DISCORD_API_BASE}/users/@me/guilds", headers=get_headers())
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch bot guilds: {resp.status_code} - {resp.text}")

    guilds = resp.json()
    if not guilds:
        raise RuntimeError(
            "The bot is not currently inside any Discord server. Please invite the bot to your server first using the invite link!"
        )
    if len(guilds) == 1:
        return str(guilds[0]["id"])

    guild_list = ", ".join([f"'{g['name']}' (ID: {g['id']})" for g in guilds])
    raise ValueError(
        f"The bot is in multiple servers: [{guild_list}]. Please specify 'guild_id' in your request."
    )


# ----------------------------------------------------------------------
# 1. BOT & SERVER INFORMATION TOOLS
# ----------------------------------------------------------------------


@server.tool()
async def discord_get_bot_info() -> str:
    """Returns details about the bot user (username, ID, avatar, connected servers)."""
    async with httpx.AsyncClient() as client:
        me_resp = await client.get(f"{DISCORD_API_BASE}/users/@me", headers=get_headers())
        if me_resp.status_code != 200:
            return f"Error: Discord returned {me_resp.status_code}: {me_resp.text}"
        me = me_resp.json()

        guilds_resp = await client.get(
            f"{DISCORD_API_BASE}/users/@me/guilds", headers=get_headers()
        )
        guilds = guilds_resp.json() if guilds_resp.status_code == 200 else []

        summary = {
            "bot_username": f"{me.get('username')}#{me.get('discriminator', '0')}",
            "bot_id": me.get("id"),
            "connected_servers": [
                {"id": g["id"], "name": g["name"], "owner": g.get("owner", False)}
                for g in guilds
            ],
        }
        return json.dumps(summary, indent=2)


@server.tool()
async def discord_get_server_info(guild_id: Optional[str] = None) -> str:
    """Returns detailed information about a Discord server (name, owner, channel count, role count, member count).
    If guild_id is not provided, the bot's current server is automatically resolved.
    """
    async with httpx.AsyncClient() as client:
        gid = await _resolve_guild_id(client, guild_id)
        resp = await client.get(
            f"{DISCORD_API_BASE}/guilds/{gid}?with_counts=true", headers=get_headers()
        )
        if resp.status_code != 200:
            return f"Error: Discord returned {resp.status_code}: {resp.text}"

        data = resp.json()
        result = {
            "id": data.get("id"),
            "name": data.get("name"),
            "description": data.get("description"),
            "owner_id": data.get("owner_id"),
            "approximate_member_count": data.get("approximate_member_count"),
            "approximate_presence_count": data.get("approximate_presence_count"),
            "roles_count": len(data.get("roles", [])),
        }
        return json.dumps(result, indent=2)


@server.tool()
async def discord_list_channels(guild_id: Optional[str] = None) -> str:
    """Lists all channels and categories in a Discord server, organized by hierarchy.
    If guild_id is omitted, auto-resolves the bot's server.
    """
    async with httpx.AsyncClient() as client:
        gid = await _resolve_guild_id(client, guild_id)
        resp = await client.get(
            f"{DISCORD_API_BASE}/guilds/{gid}/channels", headers=get_headers()
        )
        if resp.status_code != 200:
            return f"Error: Discord returned {resp.status_code}: {resp.text}"

        channels = resp.json()
        type_names = {
            0: "text",
            2: "voice",
            4: "category",
            5: "announcement",
            13: "stage",
            15: "forum",
        }

        # Organize categories and channels
        categories = {
            c["id"]: {"id": c["id"], "name": c["name"], "position": c.get("position", 0), "channels": []}
            for c in channels
            if c.get("type") == 4
        }
        uncategorized = []

        for c in channels:
            if c.get("type") == 4:
                continue
            item = {
                "id": c["id"],
                "name": c["name"],
                "type": type_names.get(c.get("type"), f"unknown({c.get('type')})"),
                "position": c.get("position", 0),
                "topic": c.get("topic"),
            }
            parent_id = c.get("parent_id")
            if parent_id and parent_id in categories:
                categories[parent_id]["channels"].append(item)
            else:
                uncategorized.append(item)

        output = {
            "guild_id": gid,
            "total_channels": len(channels),
            "categories": list(categories.values()),
            "uncategorized_channels": uncategorized,
        }
        return json.dumps(output, indent=2)


@server.tool()
async def discord_list_roles(guild_id: Optional[str] = None) -> str:
    """Lists all roles in the Discord server with their IDs, names, color, and permissions.
    If guild_id is omitted, auto-resolves the bot's server.
    """
    async with httpx.AsyncClient() as client:
        gid = await _resolve_guild_id(client, guild_id)
        resp = await client.get(
            f"{DISCORD_API_BASE}/guilds/{gid}/roles", headers=get_headers()
        )
        if resp.status_code != 200:
            return f"Error: Discord returned {resp.status_code}: {resp.text}"

        roles = resp.json()
        sorted_roles = sorted(roles, key=lambda r: r.get("position", 0), reverse=True)
        cleaned = [
            {
                "id": r["id"],
                "name": r["name"],
                "color_hex": f"#{r.get('color', 0):06X}",
                "hoist": r.get("hoist", False),
                "position": r.get("position", 0),
                "permissions": r.get("permissions"),
                "mentionable": r.get("mentionable", False),
            }
            for r in sorted_roles
        ]
        return json.dumps({"guild_id": gid, "roles": cleaned}, indent=2)


# ----------------------------------------------------------------------
# 2. CHANNEL & CATEGORY CREATION & MANAGEMENT TOOLS
# ----------------------------------------------------------------------


@server.tool()
async def discord_create_category(
    name: str, guild_id: Optional[str] = None, position: Optional[int] = None
) -> str:
    """Creates a new category in the Discord server (type: 4).
    Example: name='COMMUNITY CHANNELS'
    """
    async with httpx.AsyncClient() as client:
        gid = await _resolve_guild_id(client, guild_id)
        payload: Dict[str, Any] = {"name": name, "type": 4}
        if position is not None:
            payload["position"] = position

        resp = await client.post(
            f"{DISCORD_API_BASE}/guilds/{gid}/channels",
            headers=get_headers(),
            json=payload,
        )
        if resp.status_code not in (200, 201):
            return f"Error creating category: {resp.status_code} - {resp.text}"

        cat = resp.json()
        return json.dumps(
            {
                "status": "success",
                "message": f"Category '{name}' created successfully!",
                "category_id": cat["id"],
                "category_name": cat["name"],
            },
            indent=2,
        )


@server.tool()
async def discord_create_channel(
    name: str,
    channel_type: str = "text",
    guild_id: Optional[str] = None,
    category_id: Optional[str] = None,
    topic: Optional[str] = None,
    nsfw: bool = False,
) -> str:
    """Creates a channel in the Discord server.
    - channel_type: 'text' (default), 'voice', 'announcement', 'forum', or 'stage'
    - category_id: ID of the category under which this channel should be placed
    - topic: Channel topic description
    """
    type_map = {
        "text": 0,
        "voice": 2,
        "category": 4,
        "announcement": 5,
        "news": 5,
        "stage": 13,
        "forum": 15,
    }
    ctype = type_map.get(channel_type.lower(), 0)

    async with httpx.AsyncClient() as client:
        gid = await _resolve_guild_id(client, guild_id)
        payload: Dict[str, Any] = {
            "name": name,
            "type": ctype,
            "nsfw": nsfw,
        }
        if category_id:
            payload["parent_id"] = category_id.strip()
        if topic and ctype in (0, 5):
            payload["topic"] = topic

        resp = await client.post(
            f"{DISCORD_API_BASE}/guilds/{gid}/channels",
            headers=get_headers(),
            json=payload,
        )
        if resp.status_code not in (200, 201):
            return f"Error creating channel: {resp.status_code} - {resp.text}"

        ch = resp.json()
        return json.dumps(
            {
                "status": "success",
                "message": f"Channel '{name}' ({channel_type}) created successfully!",
                "channel_id": ch["id"],
                "channel_name": ch["name"],
                "category_id": ch.get("parent_id"),
            },
            indent=2,
        )


@server.tool()
async def discord_delete_channel(channel_id: str) -> str:
    """Deletes a channel or category by its channel ID."""
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{DISCORD_API_BASE}/channels/{channel_id.strip()}",
            headers=get_headers(),
        )
        if resp.status_code not in (200, 204):
            return f"Error deleting channel {channel_id}: {resp.status_code} - {resp.text}"
        return json.dumps(
            {"status": "success", "message": f"Channel {channel_id} deleted successfully."}
        )


@server.tool()
async def discord_modify_channel(
    channel_id: str,
    name: Optional[str] = None,
    topic: Optional[str] = None,
    category_id: Optional[str] = None,
    nsfw: Optional[bool] = None,
) -> str:
    """Modifies an existing channel's properties (name, topic, category/parent, nsfw)."""
    payload: Dict[str, Any] = {}
    if name:
        payload["name"] = name
    if topic is not None:
        payload["topic"] = topic
    if category_id is not None:
        payload["parent_id"] = category_id.strip() if category_id else None
    if nsfw is not None:
        payload["nsfw"] = nsfw

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{DISCORD_API_BASE}/channels/{channel_id.strip()}",
            headers=get_headers(),
            json=payload,
        )
        if resp.status_code != 200:
            return f"Error updating channel {channel_id}: {resp.status_code} - {resp.text}"
        data = resp.json()
        return json.dumps(
            {
                "status": "success",
                "message": f"Channel {channel_id} updated.",
                "name": data.get("name"),
                "topic": data.get("topic"),
                "category_id": data.get("parent_id"),
            },
            indent=2,
        )


# ----------------------------------------------------------------------
# 3. ROLE MANAGEMENT TOOLS
# ----------------------------------------------------------------------


@server.tool()
async def discord_create_role(
    name: str,
    color_hex: Optional[str] = None,
    hoist: bool = False,
    mentionable: bool = False,
    guild_id: Optional[str] = None,
) -> str:
    """Creates a role in the Discord server.
    - color_hex: Hex code like '#FF0000' or color name like 'red', 'gold', 'blurple'
    - hoist: Whether to display this role separately in the member sidebar
    - mentionable: Whether anyone can mention this role
    """
    async with httpx.AsyncClient() as client:
        gid = await _resolve_guild_id(client, guild_id)
        color_val = parse_color(color_hex) if color_hex else 0

        payload = {
            "name": name,
            "color": color_val,
            "hoist": hoist,
            "mentionable": mentionable,
        }

        resp = await client.post(
            f"{DISCORD_API_BASE}/guilds/{gid}/roles",
            headers=get_headers(),
            json=payload,
        )
        if resp.status_code not in (200, 201):
            return f"Error creating role '{name}': {resp.status_code} - {resp.text}"

        role = resp.json()
        return json.dumps(
            {
                "status": "success",
                "message": f"Role '{name}' created successfully!",
                "role_id": role["id"],
                "role_name": role["name"],
                "color_hex": f"#{role.get('color', 0):06X}",
            },
            indent=2,
        )


@server.tool()
async def discord_delete_role(role_id: str, guild_id: Optional[str] = None) -> str:
    """Deletes a role from the Discord server by role_id."""
    async with httpx.AsyncClient() as client:
        gid = await _resolve_guild_id(client, guild_id)
        resp = await client.delete(
            f"{DISCORD_API_BASE}/guilds/{gid}/roles/{role_id.strip()}",
            headers=get_headers(),
        )
        if resp.status_code not in (200, 204):
            return f"Error deleting role {role_id}: {resp.status_code} - {resp.text}"
        return json.dumps(
            {"status": "success", "message": f"Role {role_id} deleted successfully."}
        )


@server.tool()
async def discord_assign_role(
    user_id: str, role_id: str, guild_id: Optional[str] = None
) -> str:
    """Assigns a role to a member in the server."""
    async with httpx.AsyncClient() as client:
        gid = await _resolve_guild_id(client, guild_id)
        resp = await client.put(
            f"{DISCORD_API_BASE}/guilds/{gid}/members/{user_id.strip()}/roles/{role_id.strip()}",
            headers=get_headers(),
        )
        if resp.status_code not in (200, 204):
            return f"Error assigning role: {resp.status_code} - {resp.text}"
        return json.dumps(
            {
                "status": "success",
                "message": f"Role {role_id} assigned to user {user_id} successfully.",
            }
        )


@server.tool()
async def discord_remove_role(
    user_id: str, role_id: str, guild_id: Optional[str] = None
) -> str:
    """Removes a role from a member in the server."""
    async with httpx.AsyncClient() as client:
        gid = await _resolve_guild_id(client, guild_id)
        resp = await client.delete(
            f"{DISCORD_API_BASE}/guilds/{gid}/members/{user_id.strip()}/roles/{role_id.strip()}",
            headers=get_headers(),
        )
        if resp.status_code not in (200, 204):
            return f"Error removing role: {resp.status_code} - {resp.text}"
        return json.dumps(
            {
                "status": "success",
                "message": f"Role {role_id} removed from user {user_id} successfully.",
            }
        )


# ----------------------------------------------------------------------
# 4. MESSAGES & EMBEDS TOOLS
# ----------------------------------------------------------------------


@server.tool()
async def discord_send_message(channel_id: str, content: str) -> str:
    """Sends a text message to a specific Discord channel."""
    async with httpx.AsyncClient() as client:
        payload = {"content": content}
        resp = await client.post(
            f"{DISCORD_API_BASE}/channels/{channel_id.strip()}/messages",
            headers=get_headers(),
            json=payload,
        )
        if resp.status_code not in (200, 201):
            return f"Error sending message: {resp.status_code} - {resp.text}"

        msg = resp.json()
        return json.dumps(
            {
                "status": "success",
                "message_id": msg["id"],
                "channel_id": msg["channel_id"],
                "content": msg["content"],
            },
            indent=2,
        )


@server.tool()
async def discord_send_embed(
    channel_id: str,
    title: str,
    description: str,
    color_hex: Optional[str] = "#5865F2",
    fields_json: Optional[str] = None,
    footer_text: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    image_url: Optional[str] = None,
) -> str:
    """Sends a rich styled embed message to a Discord channel.
    - fields_json: Optional JSON array of objects: [{"name": "Field Title", "value": "Field text", "inline": true}]
    - footer_text: Footer string
    - thumbnail_url: URL for thumbnail on top-right
    - image_url: Main large image URL
    """
    embed: Dict[str, Any] = {
        "title": title,
        "description": description,
        "color": parse_color(color_hex),
    }

    if footer_text:
        embed["footer"] = {"text": footer_text}
    if thumbnail_url:
        embed["thumbnail"] = {"url": thumbnail_url}
    if image_url:
        embed["image"] = {"url": image_url}
    if fields_json:
        try:
            fields = json.loads(fields_json)
            if isinstance(fields, list):
                embed["fields"] = fields
        except Exception as e:
            return f"Invalid fields_json format: {e}"

    async with httpx.AsyncClient() as client:
        payload = {"embeds": [embed]}
        resp = await client.post(
            f"{DISCORD_API_BASE}/channels/{channel_id.strip()}/messages",
            headers=get_headers(),
            json=payload,
        )
        if resp.status_code not in (200, 201):
            return f"Error sending embed: {resp.status_code} - {resp.text}"

        msg = resp.json()
        return json.dumps(
            {
                "status": "success",
                "message_id": msg["id"],
                "channel_id": msg["channel_id"],
                "embed_title": title,
            },
            indent=2,
        )


@server.tool()
async def discord_pin_message(channel_id: str, message_id: str) -> str:
    """Pins a message in a channel (great for rules, notices, pinned links)."""
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{DISCORD_API_BASE}/channels/{channel_id.strip()}/pins/{message_id.strip()}",
            headers=get_headers(),
        )
        if resp.status_code not in (200, 204):
            return f"Error pinning message: {resp.status_code} - {resp.text}"
        return json.dumps(
            {"status": "success", "message": f"Message {message_id} pinned successfully."}
        )


@server.tool()
async def discord_create_invite(
    channel_id: str, max_age_seconds: int = 86400, max_uses: int = 0
) -> str:
    """Creates an instant invite link for the specified channel.
    max_age_seconds: 0 for permanent, 86400 for 24 hours (default).
    max_uses: 0 for unlimited (default).
    """
    async with httpx.AsyncClient() as client:
        payload = {"max_age": max_age_seconds, "max_uses": max_uses, "unique": True}
        resp = await client.post(
            f"{DISCORD_API_BASE}/channels/{channel_id.strip()}/invites",
            headers=get_headers(),
            json=payload,
        )
        if resp.status_code not in (200, 201):
            return f"Error creating invite: {resp.status_code} - {resp.text}"

        inv = resp.json()
        code = inv["code"]
        return json.dumps(
            {
                "status": "success",
                "invite_code": code,
                "invite_url": f"https://discord.gg/{code}",
                "channel_id": channel_id,
            },
            indent=2,
        )


# ----------------------------------------------------------------------
# 5. BATCH HIGH-LEVEL SERVER ARCHITECTURE BUILDER
# ----------------------------------------------------------------------


@server.tool()
async def discord_create_server_structure(
    structure_json: str, guild_id: Optional[str] = None
) -> str:
    """Batch builds an entire server layout from a JSON structure specification.
    Allows Antigravity to create multiple categories, channels, and roles in one go.

    Example structure_json:
    {
      "roles": [
        {"name": "Admin", "color": "#ED4245", "hoist": true},
        {"name": "Moderator", "color": "#3498DB", "hoist": true},
        {"name": "Member", "color": "#57F287", "hoist": false}
      ],
      "categories": [
        {
          "name": "WELCOME & INFORMATION",
          "channels": [
            {"name": "welcome", "type": "text", "topic": "Welcome new members!"},
            {"name": "rules", "type": "text", "topic": "Server rules and conduct"},
            {"name": "announcements", "type": "announcement", "topic": "Official announcements"}
          ]
        },
        {
          "name": "COMMUNITY CHAT",
          "channels": [
            {"name": "general", "type": "text", "topic": "General chat"},
            {"name": "memes", "type": "text", "topic": "Post your funniest memes"},
            {"name": "bot-commands", "type": "text", "topic": "Bot interaction"}
          ]
        },
        {
          "name": "VOICE LOUNGES",
          "channels": [
            {"name": "General Voice 1", "type": "voice"},
            {"name": "General Voice 2", "type": "voice"},
            {"name": "Gaming Duo", "type": "voice"}
          ]
        }
      ]
    }
    """
    try:
        data = json.loads(structure_json)
    except Exception as e:
        return f"Invalid structure_json format: {e}"

    created_roles = []
    created_categories = []
    created_channels = []

    type_map = {"text": 0, "voice": 2, "category": 4, "announcement": 5, "news": 5}

    async with httpx.AsyncClient() as client:
        gid = await _resolve_guild_id(client, guild_id)

        # 1. Create Roles
        for role_spec in data.get("roles", []):
            r_name = role_spec.get("name")
            if not r_name:
                continue
            r_color = parse_color(role_spec.get("color"))
            r_hoist = role_spec.get("hoist", False)
            r_mention = role_spec.get("mentionable", False)

            resp = await client.post(
                f"{DISCORD_API_BASE}/guilds/{gid}/roles",
                headers=get_headers(),
                json={
                    "name": r_name,
                    "color": r_color,
                    "hoist": r_hoist,
                    "mentionable": r_mention,
                },
            )
            if resp.status_code in (200, 201):
                r_data = resp.json()
                created_roles.append({"id": r_data["id"], "name": r_data["name"]})

        # 2. Create Categories & Channels
        for cat_spec in data.get("categories", []):
            cat_name = cat_spec.get("name")
            if not cat_name:
                continue

            # Create the Category
            cat_resp = await client.post(
                f"{DISCORD_API_BASE}/guilds/{gid}/channels",
                headers=get_headers(),
                json={"name": cat_name, "type": 4},
            )
            if cat_resp.status_code not in (200, 201):
                continue
            cat_data = cat_resp.json()
            cat_id = cat_data["id"]
            created_categories.append({"id": cat_id, "name": cat_name})

            # Create Channels inside this Category
            for ch_spec in cat_spec.get("channels", []):
                ch_name = ch_spec.get("name")
                if not ch_name:
                    continue
                ch_type = type_map.get(ch_spec.get("type", "text").lower(), 0)
                ch_payload = {
                    "name": ch_name,
                    "type": ch_type,
                    "parent_id": cat_id,
                }
                if ch_spec.get("topic") and ch_type in (0, 5):
                    ch_payload["topic"] = ch_spec["topic"]

                ch_resp = await client.post(
                    f"{DISCORD_API_BASE}/guilds/{gid}/channels",
                    headers=get_headers(),
                    json=ch_payload,
                )
                if ch_resp.status_code in (200, 201):
                    ch_data = ch_resp.json()
                    created_channels.append(
                        {
                            "id": ch_data["id"],
                            "name": ch_data["name"],
                            "category": cat_name,
                            "type": ch_spec.get("type", "text"),
                        }
                    )

    return json.dumps(
        {
            "status": "success",
            "guild_id": gid,
            "created_roles": created_roles,
            "created_categories": created_categories,
            "created_channels": created_channels,
            "summary": f"Built {len(created_categories)} categories, {len(created_channels)} channels, and {len(created_roles)} roles successfully!",
        },
        indent=2,
    )


# ----------------------------------------------------------------------
# 6. UNIVERSAL DISCORD REST API EXECUTOR (DO ANYTHING)
# ----------------------------------------------------------------------


@server.tool()
async def discord_raw_api(
    method: str, endpoint: str, body_json: Optional[str] = None
) -> str:
    """Executes ANY Discord API v10 endpoint directly with the bot's credentials.
    Gives Antigravity complete power to perform any action supported by Discord's REST API.
    - method: 'GET', 'POST', 'PATCH', 'PUT', or 'DELETE'
    - endpoint: Discord endpoint starting with '/', e.g. '/guilds/123/emojis', '/channels/456', etc.
    - body_json: Optional JSON string for request payload
    """
    method = method.upper().strip()
    endpoint = endpoint.strip()
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    url = f"{DISCORD_API_BASE}{endpoint}"
    payload = None
    if body_json and body_json.strip():
        try:
            payload = json.loads(body_json)
        except Exception as e:
            return f"Invalid JSON in body_json: {e}"

    async with httpx.AsyncClient() as client:
        try:
            req_kwargs = {"headers": get_headers()}
            if payload is not None:
                req_kwargs["json"] = payload

            resp = await client.request(method, url, **req_kwargs)
            try:
                body = resp.json()
                formatted_body = json.dumps(body, indent=2)
            except Exception:
                formatted_body = resp.text

            return json.dumps(
                {
                    "http_status": resp.status_code,
                    "endpoint": endpoint,
                    "method": method,
                    "response": formatted_body,
                },
                indent=2,
            )
        except Exception as ex:
            return f"Request failed: {type(ex).__name__} - {str(ex)}"


# ----------------------------------------------------------------------
# ENTRYPOINT
# ----------------------------------------------------------------------

if __name__ == "__main__":
    # Runs the stdio MCP server for Antigravity
    server.run(transport="stdio")
