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
# 7. BOT ADDITION, CONFIGURATION & EMBEDDED AUTOMATION TOOLS
# ----------------------------------------------------------------------

import webbrowser

BOT_CATALOG: Dict[str, Dict[str, Any]] = {
    "ticket_tool": {
        "id": "557628352828014614",
        "name": "Ticket Tool",
        "purpose": "Επαγγελματικό σύστημα Support Tickets με Web Dashboard",
        "default_command": "$setup",
        "recommended_channel": "📩・άνοιγμα-ticket",
        "permissions": 8,
    },
    "pingcord": {
        "id": "581096794776109066",
        "name": "Pingcord",
        "purpose": "Αυτόματες ειδοποιήσεις για TikTok Live, TikTok Videos, YouTube & Twitch",
        "default_command": "!pingcord",
        "recommended_channel": "🔴・live-alerts",
        "permissions": 277025508416,
    },
    "carl_bot": {
        "id": "235148962103951360",
        "name": "Carl-bot",
        "purpose": "Προηγμένο Moderation, Reaction Roles & Server Logs",
        "default_command": "!help",
        "recommended_channel": "🚨・mod-logs",
        "permissions": 8,
    },
    "giveaway_bot": {
        "id": "396434947269197824",
        "name": "GiveawayBot",
        "purpose": "Αυτόματοι διαγωνισμοί & Giveaways για τα μέλη και τα Lives",
        "default_command": "!gcreate",
        "recommended_channel": "💬・γενική-συζήτηση",
        "permissions": 277025508416,
    },
    "mee6": {
        "id": "159985870458322944",
        "name": "MEE6",
        "purpose": "Leveling, XP, Auto-moderation & Music",
        "default_command": "!levels",
        "recommended_channel": "🤖・bot-εντολές",
        "permissions": 8,
    },
    "probot": {
        "id": "282859044593598464",
        "name": "ProBot",
        "purpose": "Custom Welcome Images, Auto-roles, Levels & Protection",
        "default_command": "#help",
        "recommended_channel": "🤖・bot-εντολές",
        "permissions": 8,
    },
    "jockie_music": {
        "id": "411916947773587456",
        "name": "Jockie Music",
        "purpose": "Αναπαραγωγή μουσικής σε Voice Channels",
        "default_command": "m!play",
        "recommended_channel": "🤖・bot-εντολές",
        "permissions": 3148800,
    },
}


@server.tool()
async def discord_list_bot_catalog() -> str:
    """Lists popular Discord bots available for instant addition and automated setup.
    Includes bots for Tickets, Live Streaming Announcements (TikTok/YouTube), Moderation, Giveaways, and Music.
    """
    catalog_list = []
    for key, info in BOT_CATALOG.items():
        catalog_list.append({
            "key": key,
            "bot_name": info["name"],
            "client_id": info["id"],
            "purpose": info["purpose"],
            "default_command": info["default_command"],
            "recommended_channel": info["recommended_channel"],
        })
    return json.dumps({"status": "success", "bots": catalog_list}, indent=2, ensure_ascii=False)


@server.tool()
async def discord_add_bot(
    bot_name_or_id: str,
    guild_id: Optional[str] = None,
    user_token: Optional[str] = None,
    open_browser: bool = True,
) -> str:
    """Adds a Discord bot to the server or generates its 1-Click invite URL.
    - bot_name_or_id: Name from catalog (e.g. 'ticket_tool', 'pingcord', 'carl_bot', 'giveaway_bot') or raw Client ID
    - guild_id: Target server ID (auto-resolved if omitted)
    - user_token: Optional Discord User Authorization Token for 100% headless automated addition
    - open_browser: If true and no user_token, automatically opens the OAuth2 authorization page in default browser
    """
    bot_key = bot_name_or_id.strip().lower()
    bot_info = BOT_CATALOG.get(bot_key)

    if bot_info:
        client_id = bot_info["id"]
        bot_name = bot_info["name"]
        perms = bot_info["permissions"]
    else:
        client_id = bot_name_or_id.strip()
        bot_name = f"Bot ({client_id})"
        perms = 8

    async with httpx.AsyncClient() as client:
        gid = await _resolve_guild_id(client, guild_id)

        # 1. Check if user provided a Discord user token for headless OAuth2 authorization
        token = user_token or os.getenv("DISCORD_USER_TOKEN", "").strip()
        if token:
            auth_headers = {
                "Authorization": token,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            }
            auth_payload = {
                "guild_id": gid,
                "permissions": str(perms),
                "authorize": True,
            }
            auth_resp = await client.post(
                f"{DISCORD_API_BASE}/oauth2/authorize?client_id={client_id}&scope=bot%20applications.commands",
                headers=auth_headers,
                json=auth_payload,
            )
            if auth_resp.status_code in (200, 204):
                return json.dumps({
                    "status": "success",
                    "mode": "headless_automatic",
                    "bot_name": bot_name,
                    "client_id": client_id,
                    "guild_id": gid,
                    "message": f"Successfully added {bot_name} to server {gid} headlessly!",
                }, indent=2, ensure_ascii=False)

        # 2. Generate 1-Click invite URL with pre-selected guild
        invite_url = (
            f"https://discord.com/oauth2/authorize?client_id={client_id}"
            f"&scope=bot%20applications.commands&permissions={perms}&guild_id={gid}&disable_guild_select=true"
        )

        if open_browser:
            try:
                webbrowser.open(invite_url)
            except Exception:
                pass

        return json.dumps({
            "status": "success",
            "mode": "1_click_authorization",
            "bot_name": bot_name,
            "client_id": client_id,
            "guild_id": gid,
            "invite_url": invite_url,
            "browser_opened": open_browser,
            "message": f"Invite URL generated for {bot_name}. Authorized window opened in browser!",
        }, indent=2, ensure_ascii=False)


@server.tool()
async def discord_configure_bot(
    bot_name_or_id: str,
    guild_id: Optional[str] = None,
    target_channel_id: Optional[str] = None,
    setup_command: Optional[str] = None,
) -> str:
    """Configures an installed bot in the server:
    1. Finds the bot among server members and assigns the '🤖 Bots' role
    2. Grants specific channel permissions if target_channel_id is provided
    3. Sends the initial setup command into the target channel
    """
    bot_key = bot_name_or_id.strip().lower()
    bot_info = BOT_CATALOG.get(bot_key)
    client_id = bot_info["id"] if bot_info else bot_name_or_id.strip()
    bot_name = bot_info["name"] if bot_info else f"Bot {client_id}"
    cmd = setup_command or (bot_info["default_command"] if bot_info else None)

    async with httpx.AsyncClient() as client:
        gid = await _resolve_guild_id(client, guild_id)

        # 1. Assign '🤖 Bots' role
        roles_resp = await client.get(f"{DISCORD_API_BASE}/guilds/{gid}/roles", headers=get_headers())
        bot_role_id = None
        if roles_resp.status_code == 200:
            for r in roles_resp.json():
                if "bot" in r.get("name", "").lower():
                    bot_role_id = r["id"]
                    break

        role_assigned = False
        if bot_role_id:
            assign_resp = await client.put(
                f"{DISCORD_API_BASE}/guilds/{gid}/members/{client_id}/roles/{bot_role_id}",
                headers=get_headers(),
            )
            role_assigned = assign_resp.status_code in (200, 204)

        # 2. Grant permissions on target channel
        perms_set = False
        if target_channel_id:
            allow_flags = 1024 | 2048 | 16384 | 32768 | 65536
            perm_payload = {
                "id": client_id,
                "type": 1,
                "allow": str(allow_flags),
                "deny": "0",
            }
            p_resp = await client.put(
                f"{DISCORD_API_BASE}/channels/{target_channel_id.strip()}/permissions/{client_id}",
                headers=get_headers(),
                json=perm_payload,
            )
            perms_set = p_resp.status_code in (200, 204)

        # 3. Send setup command into channel if requested
        cmd_sent = False
        if cmd and target_channel_id:
            msg_resp = await client.post(
                f"{DISCORD_API_BASE}/channels/{target_channel_id.strip()}/messages",
                headers=get_headers(),
                json={"content": cmd},
            )
            cmd_sent = msg_resp.status_code in (200, 201)

        return json.dumps({
            "status": "success",
            "bot_name": bot_name,
            "client_id": client_id,
            "guild_id": gid,
            "role_assigned": role_assigned,
            "permissions_set": perms_set,
            "setup_command_sent": cmd if cmd_sent else None,
            "message": f"Configuration for {bot_name} completed!",
        }, indent=2, ensure_ascii=False)


@server.tool()
async def discord_create_webhook(
    channel_id: str,
    name: str = "Antigravity Automated Bot",
    avatar_url: Optional[str] = None,
) -> str:
    """Creates a Discord webhook in a channel. Used for automated stream alerts, tickets, and external feeds."""
    payload: Dict[str, Any] = {"name": name}
    if avatar_url:
        payload["avatar"] = avatar_url

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{DISCORD_API_BASE}/channels/{channel_id.strip()}/webhooks",
            headers=get_headers(),
            json=payload,
        )
        if resp.status_code not in (200, 201):
            return f"Error creating webhook: {resp.status_code} - {resp.text}"

        data = resp.json()
        return json.dumps({
            "status": "success",
            "webhook_id": data.get("id"),
            "name": data.get("name"),
            "channel_id": data.get("channel_id"),
            "webhook_url": f"https://discord.com/api/webhooks/{data.get('id')}/{data.get('token')}",
        }, indent=2)


@server.tool()
async def discord_send_as_bot(
    channel_id: str,
    bot_name: str,
    content: str,
    avatar_url: Optional[str] = None,
    embed_title: Optional[str] = None,
    embed_description: Optional[str] = None,
    embed_color: Optional[str] = "#5865F2",
) -> str:
    """Sends a message or announcement disguised as ANY custom bot (Ticket Bot, TikTok Live Alert, Streamcord, AutoMod)
    using an on-demand Discord Webhook.
    """
    async with httpx.AsyncClient() as client:
        cid = channel_id.strip()
        wh_resp = await client.get(f"{DISCORD_API_BASE}/channels/{cid}/webhooks", headers=get_headers())
        webhook = None
        if wh_resp.status_code == 200:
            webhooks = wh_resp.json()
            for w in webhooks:
                if w.get("name") == bot_name:
                    webhook = w
                    break
            if not webhook and webhooks:
                webhook = webhooks[0]

        if not webhook:
            create_resp = await client.post(
                f"{DISCORD_API_BASE}/channels/{cid}/webhooks",
                headers=get_headers(),
                json={"name": bot_name},
            )
            if create_resp.status_code in (200, 201):
                webhook = create_resp.json()
            else:
                return f"Error creating bot webhook: {create_resp.status_code} - {create_resp.text}"

        wh_url = f"https://discord.com/api/webhooks/{webhook['id']}/{webhook['token']}"
        wh_payload: Dict[str, Any] = {
            "username": bot_name,
            "content": content,
        }
        if avatar_url:
            wh_payload["avatar_url"] = avatar_url

        if embed_title or embed_description:
            embed = {
                "title": embed_title or "",
                "description": embed_description or "",
                "color": parse_color(embed_color),
            }
            wh_payload["embeds"] = [embed]

        exec_resp = await client.post(wh_url, json=wh_payload)
        if exec_resp.status_code not in (200, 204):
            return f"Error sending message as bot: {exec_resp.status_code} - {exec_resp.text}"

        return json.dumps({
            "status": "success",
            "bot_name": bot_name,
            "channel_id": cid,
            "content": content,
            "embed_title": embed_title,
        }, indent=2, ensure_ascii=False)


@server.tool()
async def discord_send_bot_command(channel_id: str, command: str) -> str:
    """Sends a bot configuration command (e.g. '$setup', '!pingcord', '!gcreate') into a Discord channel."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{DISCORD_API_BASE}/channels/{channel_id.strip()}/messages",
            headers=get_headers(),
            json={"content": command.strip()},
        )
        if resp.status_code not in (200, 201):
            return f"Error sending bot command: {resp.status_code} - {resp.text}"

        msg = resp.json()
        return json.dumps({
            "status": "success",
            "command_sent": command,
            "channel_id": channel_id,
            "message_id": msg["id"],
        }, indent=2)


# ----------------------------------------------------------------------
# ENTRYPOINT
# ----------------------------------------------------------------------

if __name__ == "__main__":
    # Runs the stdio MCP server for Antigravity
    server.run(transport="stdio")

