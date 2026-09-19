# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
Monitors and configures all requested bots in PanosLIVE Community:
1. Ticket Tool (557628352828014614)
2. Pingcord (581096794776109066)
3. Carl-bot (235148962103951360)
4. GiveawayBot (396434947269197824)
"""

import asyncio
import os
import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
GUILD_ID = "1550519974559486074"
BOTS_ROLE_ID = "1550607544999878699"

DISCORD_API_BASE = "https://discord.com/api/v10"
HEADERS = {
    "Authorization": f"Bot {TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "PanosLIVEBotManager/1.0",
}

BOT_SPECS = {
    "Ticket Tool": {
        "id": "557628352828014614",
        "target_channel": "1550773354259157072",  # 📩・άνοιγμα-ticket
        "setup_command": "$setup",
    },
    "Pingcord": {
        "id": "581096794776109066",
        "target_channel": "1550773370554032198",  # 🔴・live-alerts
        "setup_command": "!pingcord",
    },
    "Carl-bot": {
        "id": "235148962103951360",
        "target_channel": "1550607586133287003",  # 🚨・mod-logs
        "setup_command": "!help",
    },
    "GiveawayBot": {
        "id": "396434947269197824",
        "target_channel": "1550607558476308560",  # 💬・γενική-συζήτηση
        "setup_command": "!gcreate",
    },
}


async def configure_single_bot(client: httpx.AsyncClient, name: str, spec: dict):
    bot_id = spec["id"]
    target_ch = spec["target_channel"]
    cmd = spec["setup_command"]

    # Check if in server
    resp = await client.get(f"{DISCORD_API_BASE}/guilds/{GUILD_ID}/members/{bot_id}", headers=HEADERS)
    if resp.status_code != 200:
        print(f"⏳ {name} (ID: {bot_id}) δεν έχει προστεθεί ακόμα στο server (Status {resp.status_code}).")
        return False

    print(f"\n🎉 Εντοπίστηκε το {name} στο server! Έναρξη αυτόματης ρύθμισης...")

    # 1. Assign 🤖 Bots role
    role_resp = await client.put(f"{DISCORD_API_BASE}/guilds/{GUILD_ID}/members/{bot_id}/roles/{BOTS_ROLE_ID}", headers=HEADERS)
    if role_resp.status_code in (200, 204):
        print(f"  ✅ Ανατέθηκε ο ρόλος '🤖 Bots' στο {name}.")
    else:
        print(f"  ⚠️ Ρόλος bots: {role_resp.status_code}")

    # 2. Grant permissions on target channel
    # VIEW_CHANNEL | SEND_MESSAGES | EMBED_LINKS | ATTACH_FILES | READ_MESSAGE_HISTORY | MANAGE_MESSAGES
    allow_flags = 1024 | 2048 | 16384 | 32768 | 65536 | 8192
    payload = {
        "id": bot_id,
        "type": 1,
        "allow": str(allow_flags),
        "deny": "0",
    }
    perm_resp = await client.put(f"{DISCORD_API_BASE}/channels/{target_ch}/permissions/{bot_id}", headers=HEADERS, json=payload)
    if perm_resp.status_code in (200, 204):
        print(f"  ✅ Ρυθμίστηκαν τα permissions του {name} στο κανάλι.")

    # 3. Send setup command
    msg_resp = await client.post(f"{DISCORD_API_BASE}/channels/{target_ch}/messages", headers=HEADERS, json={"content": cmd})
    if msg_resp.status_code in (200, 201):
        print(f"  ✅ Στάλθηκε η εντολή ρύθμισης '{cmd}' στο κανάλι!")

    return True


async def main():
    print("🤖 Έλεγχος και Ρύθμιση Bots για το PanosLIVE Community...\n")
    async with httpx.AsyncClient() as client:
        found_any = False
        for name, spec in BOT_SPECS.items():
            ok = await configure_single_bot(client, name, spec)
            if ok:
                found_any = True

        if not found_any:
            print("\n👉 Τα παράθυρα εξουσιοδότησης έχουν ανοίξει στον browser σας!")
            print("Πατήστε 'Εξουσιοδότηση' (Authorize) σε κάθε καρτέλα για να μπουν τα bots στο server.")


if __name__ == "__main__":
    asyncio.run(main())
