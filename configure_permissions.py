# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
Configures permissions across all channels in PanosLIVE Discord server:
- Read-only for @everyone in #κανόνες, #ανακοινώσεις, #tiktok-feed
- Hidden Category for Staff (#staff-chat, #mod-logs, Staff Voice)
- Listen-only for community in Live Lounge (Panos)
- Backfills 'TikTok Community' role to all existing server members
"""

import asyncio
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import httpx
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
if not TOKEN:
    print("Error: DISCORD_BOT_TOKEN missing!")
    sys.exit(1)

DISCORD_API_BASE = "https://discord.com/api/v10"
HEADERS = {
    "Authorization": f"Bot {TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "AntigravityDiscordPermissions/1.0",
}

# Bitwise flags
VIEW_CHANNEL = 1 << 10           # 1024
SEND_MESSAGES = 1 << 11          # 2048
READ_MESSAGE_HISTORY = 1 << 16   # 65536
CONNECT = 1 << 20                # 1048576
SPEAK = 1 << 21                  # 2097152
PRIORITY_SPEAKER = 1 << 8        # 256
CREATE_PUBLIC_THREADS = 1 << 35
CREATE_PRIVATE_THREADS = 1 << 36
SEND_MESSAGES_IN_THREADS = 1 << 38


async def set_permission_overwrite(client: httpx.AsyncClient, channel_id: str, overwrite_id: str, allow: int, deny: int, is_role: bool = True):
    payload = {
        "id": str(overwrite_id),
        "type": 0 if is_role else 1,
        "allow": str(allow),
        "deny": str(deny),
    }
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/permissions/{overwrite_id}"
    resp = await client.put(url, headers=HEADERS, json=payload)
    if resp.status_code not in (200, 204):
        print(f"  ❌ Error setting perm on {channel_id} for {overwrite_id}: {resp.status_code} - {resp.text}")
    return resp.status_code in (200, 204)


async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Resolve guild
        resp = await client.get(f"{DISCORD_API_BASE}/users/@me/guilds", headers=HEADERS)
        guilds = resp.json()
        guild_id = guilds[0]["id"]
        everyone_id = guild_id

        # 2. Fetch roles
        r_resp = await client.get(f"{DISCORD_API_BASE}/guilds/{guild_id}/roles", headers=HEADERS)
        roles = {r["name"]: r["id"] for r in r_resp.json()}

        creator_role = next((rid for name, rid in roles.items() if "Creator" in name), None)
        head_mod_role = next((rid for name, rid in roles.items() if "Head Moderator" in name), None)
        mod_role = next((rid for name, rid in roles.items() if name.startswith("⚔️ Moderator")), None)
        vip_role = next((rid for name, rid in roles.items() if "VIP" in name), None)
        community_role = next((rid for name, rid in roles.items() if "Community" in name), None)

        staff_roles = [r for r in [creator_role, head_mod_role, mod_role] if r]

        # 3. Fetch channels
        ch_resp = await client.get(f"{DISCORD_API_BASE}/guilds/{guild_id}/channels", headers=HEADERS)
        channels = ch_resp.json()

        print("🔒 Ρύθμιση Δικαιωμάτων (Channel Permissions)...\n")

        for ch in channels:
            cid = ch["id"]
            cname = ch["name"]
            ctype = ch["type"]

            # --- A. READ-ONLY CHANNELS (κανόνες, ανακοινώσεις, tiktok-feed) ---
            if any(k in cname for k in ["κανόνες", "ανακοινώσεις", "tiktok-feed"]):
                print(f"📌 Ρύθμιση Read-Only για #{cname}...")
                # @everyone: Can view & read history, cannot send messages or create threads
                deny_flags = SEND_MESSAGES | CREATE_PUBLIC_THREADS | CREATE_PRIVATE_THREADS | SEND_MESSAGES_IN_THREADS
                allow_flags = VIEW_CHANNEL | READ_MESSAGE_HISTORY
                await set_permission_overwrite(client, cid, everyone_id, allow=allow_flags, deny=deny_flags)

                # Staff roles: Can send messages
                for s_role in staff_roles:
                    await set_permission_overwrite(client, cid, s_role, allow=SEND_MESSAGES, deny=0)

            # --- B. STAFF ONLY CATEGORY & CHANNELS ---
            elif "STAFF ONLY" in cname or any(k in cname for k in ["staff-chat", "mod-logs", "Staff Voice"]):
                print(f"🛡️ Κλείδωμα Staff-Only για {cname}...")
                # @everyone: Deny VIEW_CHANNEL completely (invisible)
                await set_permission_overwrite(client, cid, everyone_id, allow=0, deny=VIEW_CHANNEL)

                # Staff roles: Allow VIEW_CHANNEL + SEND_MESSAGES + CONNECT
                for s_role in staff_roles:
                    await set_permission_overwrite(client, cid, s_role, allow=VIEW_CHANNEL | SEND_MESSAGES | CONNECT, deny=0)

            # --- C. LIVE LOUNGE VOICE (Panos Stream / Listen Only) ---
            elif "Live Lounge" in cname:
                print(f"🎙️ Ρύθμιση Listen-Only για Voice {cname}...")
                # @everyone: Can CONNECT to listen, but cannot SPEAK
                await set_permission_overwrite(client, cid, everyone_id, allow=CONNECT, deny=SPEAK)

                # Creator & Staff: Can SPEAK & PRIORITY_SPEAKER
                if creator_role:
                    await set_permission_overwrite(client, cid, creator_role, allow=CONNECT | SPEAK | PRIORITY_SPEAKER, deny=0)
                if head_mod_role:
                    await set_permission_overwrite(client, cid, head_mod_role, allow=CONNECT | SPEAK, deny=0)
                if mod_role:
                    await set_permission_overwrite(client, cid, mod_role, allow=CONNECT | SPEAK, deny=0)
                if vip_role:
                    await set_permission_overwrite(client, cid, vip_role, allow=CONNECT | SPEAK, deny=0)

        # 4. BACKFILL: Assign 'TikTok Community' role to all current members
        if community_role:
            print("\n👥 Αυτόματη ανάθεση του ρόλου 'TikTok Community' στα υπάρχοντα μέλη...")
            m_resp = await client.get(f"{DISCORD_API_BASE}/guilds/{guild_id}/members?limit=1000", headers=HEADERS)
            if m_resp.status_code == 200:
                members = m_resp.json()
                for m in members:
                    user = m.get("user", {})
                    if user.get("bot", False):
                        continue
                    uid = user.get("id")
                    current_roles = m.get("roles", [])
                    if community_role not in current_roles:
                        assign_resp = await client.put(
                            f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{uid}/roles/{community_role}",
                            headers=HEADERS,
                        )
                        uname = user.get("username", uid)
                        if assign_resp.status_code in (200, 204):
                            print(f"  ✅ Ο ρόλος TikTok Community δόθηκε στον: {uname}")
                        else:
                            print(f"  ⚠️ Σφάλμα στην ανάθεση για {uname}: {assign_resp.status_code}")
                    else:
                        print(f"  ℹ️ Ο χρήστης {user.get('username')} έχει ήδη το ρόλο.")
            else:
                print(f"  ⚠️ Δεν ήταν δυνατή η ανάγνωση της λίστας μελών (Status {m_resp.status_code}).")

        print("\n✨ ΟΛΑ ΤΑ PERMISSIONS ΚΑΙ ΤΑ ROLES ΡΥΘΜΙΣΤΗΚΑΝ ΕΠΙΤΥΧΩΣ!")


if __name__ == "__main__":
    asyncio.run(main())
