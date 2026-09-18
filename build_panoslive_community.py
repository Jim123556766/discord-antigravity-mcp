# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
Builder script for PanosLIVE Greek TikTok Community Discord Server
Creates:
- Roles hierarchy (Owner, Head Mod, Moderator, TikTok VIP, Top Fan, Community Member, etc.)
- Organized Categories & Channels in Greek
- Welcome & Rules Rich Embeds
"""

import asyncio
import json
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
    "User-Agent": "AntigravityDiscordBuilder/1.0",
}


async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Resolve guild
        resp = await client.get(f"{DISCORD_API_BASE}/users/@me/guilds", headers=HEADERS)
        guilds = resp.json()
        if not guilds:
            print("Bot is not in any server!")
            return
        guild_id = guilds[0]["id"]
        guild_name = guilds[0]["name"]
        print(f"🚀 Συνδέθηκε στο Server: {guild_name} (ID: {guild_id})\n")

        # 2. Roles Definition
        roles_to_create = [
            {"name": "👑 Creator / PanosLIVE", "color": 0xFFD700, "hoist": True, "mentionable": True},
            {"name": "🛡️ Head Moderator", "color": 0xED4245, "hoist": True, "mentionable": True},
            {"name": "⚔️ Moderator", "color": 0x3498DB, "hoist": True, "mentionable": True},
            {"name": "⭐ TikTok VIP", "color": 0x9B59B6, "hoist": True, "mentionable": True},
            {"name": "🎬 Content Creator / Collab", "color": 0x1ABC9C, "hoist": True, "mentionable": False},
            {"name": "🔥 Top Fan", "color": 0xE67E22, "hoist": True, "mentionable": False},
            {"name": "👥 TikTok Community", "color": 0x2ECC71, "hoist": False, "mentionable": False},
            {"name": "🤖 Bots", "color": 0x95A5A6, "hoist": True, "mentionable": False},
        ]

        print("🎭 Δημιουργία Ρόλων...")
        created_roles = {}
        for r in roles_to_create:
            res = await client.post(
                f"{DISCORD_API_BASE}/guilds/{guild_id}/roles",
                headers=HEADERS,
                json=r,
            )
            if res.status_code in (200, 201):
                rd = res.json()
                created_roles[r["name"]] = rd["id"]
                print(f"  ✅ Δημιουργήθηκε ο ρόλος: {r['name']}")
            else:
                print(f"  ❌ Σφάλμα στο ρόλο {r['name']}: {res.status_code} - {res.text}")

        # 3. Categories and Channels Definition
        structure = [
            {
                "name": "📌・ΚΑΛΩΣΟΡΙΣΜΑ & INFO",
                "channels": [
                    {"name": "📜・κανόνες", "type": 0, "topic": "Οι βασικοί κανόνες της κοινότητας PanosLIVE"},
                    {"name": "📢・ανακοινώσεις", "type": 0, "topic": "Επίσημες ανακοινώσεις & νέα για το κανάλι PanosLIVE"},
                    {"name": "📱・tiktok-feed", "type": 0, "topic": "Ειδοποιήσεις για νέα TikTok videos & Lives του PanosLIVE"},
                    {"name": "👋・καλωσορίσματα", "type": 0, "topic": "Καλωσόρισμα στα νέα μέλη της παρέας!"},
                ],
            },
            {
                "name": "💬・ΠΑΡΕΑ & CHAT",
                "channels": [
                    {"name": "💬・γενική-συζήτηση", "type": 0, "topic": "Μιλήστε ελεύθερα για ό,τι θέλετε με την κοινότητα!"},
                    {"name": "🤣・memes-αστεία", "type": 0, "topic": "Μοιραστείτε τα καλύτερα memes και αστεία βιντεάκια"},
                    {"name": "📸・φωτογραφίες-setup", "type": 0, "topic": "Φωτογραφίες, setups, κατοικίδια και καθημερινότητα"},
                    {"name": "🤖・bot-εντολές", "type": 0, "topic": "Εντολές για bots, mini-games και μουσική"},
                ],
            },
            {
                "name": "🎬・TIKTOK & ΠΕΡΙΕΧΟΜΕΝΟ",
                "channels": [
                    {"name": "💡・ιδέες-για-tiktoks", "type": 0, "topic": "Προτάσεις και ιδέες για επόμενα TikToks & streams του PanosLIVE"},
                    {"name": "🌟・fan-art-edits", "type": 0, "topic": "Δικά σας edits, fan arts και clips από τα Lives!"},
                    {"name": "❓・ερωτήσεις-για-τα-live", "type": 0, "topic": "Κάντε ερωτήσεις για να απαντηθούν στα TikTok Lives"},
                ],
            },
            {
                "name": "🔊・VOICE LOUNGES",
                "channels": [
                    {"name": "🎙️・Live Lounge (Panos)", "type": 2},
                    {"name": "🔊・Παρεΐτσα 1", "type": 2},
                    {"name": "🔊・Παρεΐτσα 2", "type": 2},
                    {"name": "🎮・Gaming Voice", "type": 2},
                    {"name": "💤・AFK", "type": 2},
                ],
            },
            {
                "name": "🔒・STAFF ONLY",
                "channels": [
                    {"name": "🛡️・staff-chat", "type": 0, "topic": "Ιδιωτική συζήτηση ομάδας διαχείρισης"},
                    {"name": "🚨・mod-logs", "type": 0, "topic": "Καταγραφή συμβάντων moderation"},
                    {"name": "🔒・Staff Voice", "type": 2},
                ],
            },
        ]

        print("\n📁 Δημιουργία Κατηγοριών & Καναλιών...")
        rules_channel_id = None
        announcements_channel_id = None
        welcome_channel_id = None

        for cat_spec in structure:
            cat_resp = await client.post(
                f"{DISCORD_API_BASE}/guilds/{guild_id}/channels",
                headers=HEADERS,
                json={"name": cat_spec["name"], "type": 4},
            )
            if cat_resp.status_code not in (200, 201):
                print(f"  ❌ Σφάλμα στη κατηγορία {cat_spec['name']}: {cat_resp.text}")
                continue

            cat_data = cat_resp.json()
            cat_id = cat_data["id"]
            print(f"\n📂 Κατηγορία: {cat_spec['name']}")

            for ch_spec in cat_spec["channels"]:
                ch_payload = {
                    "name": ch_spec["name"],
                    "type": ch_spec["type"],
                    "parent_id": cat_id,
                }
                if "topic" in ch_spec:
                    ch_payload["topic"] = ch_spec["topic"]

                ch_resp = await client.post(
                    f"{DISCORD_API_BASE}/guilds/{guild_id}/channels",
                    headers=HEADERS,
                    json=ch_payload,
                )
                if ch_resp.status_code in (200, 201):
                    ch_data = ch_resp.json()
                    cid = ch_data["id"]
                    cname = ch_data["name"]
                    print(f"   ✅ Κανάλι: #{cname}")

                    if "κανόνες" in cname:
                        rules_channel_id = cid
                    elif "ανακοινώσεις" in cname:
                        announcements_channel_id = cid
                    elif "καλωσορίσματα" in cname:
                        welcome_channel_id = cid
                else:
                    print(f"   ❌ Σφάλμα στο κανάλι {ch_spec['name']}: {ch_resp.text}")

        # 4. Post Welcome & Rules Rich Embeds
        print("\n🎨 Αποστολή Επίσημων Embed Μηνυμάτων...")

        # Rules Embed
        if rules_channel_id:
            rules_embed = {
                "title": "📜 Κανόνες Κοινότητας PanosLIVE",
                "description": (
                    "Καλωσορίσατε στον επίσημο Discord server της κοινότητας **PanosLIVE** στο TikTok!\n"
                    "Για να περνάμε όλοι όμορφα, παρακαλούμε να τηρείτε τους παρακάτω βασικούς κανόνες:\n"
                ),
                "color": 0xED4245,  # Red
                "fields": [
                    {
                        "name": "1️⃣ Σεβασμός & Ευγένεια",
                        "value": "Σεβόμαστε όλα τα μέλη. Απαγορεύονται οι προσβολές, το hate speech, οι διακρίσεις και οι προσωπικές επιθέσεις.",
                        "inline": False,
                    },
                    {
                        "name": "2️⃣ Όχι Spam / Self-Promotion",
                        "value": "Απαγορεύεται η ανεπιθύμητη διαφήμιση άλλων servers, καναλιών ή πωλήσεων χωρίς άδεια από τον PanosLIVE ή τους Mods.",
                        "inline": False,
                    },
                    {
                        "name": "3️⃣ Κατάλληλο Περιεχόμενο (SFW)",
                        "value": "Απαγορεύεται αυστηρά ακατάλληλο, NSFW ή παράνομο περιεχόμενο.",
                        "inline": False,
                    },
                    {
                        "name": "4️⃣ Σωστή Χρήση Καναλιών",
                        "value": "Γράφουμε στο κατάλληλο κανάλι (memes στο #memes, ιδέες στο #ιδέες-για-tiktoks κλπ).",
                        "inline": False,
                    },
                    {
                        "name": "5️⃣ Ακούμε τους Moderators",
                        "value": "Οι οδηγίες των Moderators και του PanosLIVE είναι οριστικές. Αν υπάρξει θέμα, επικοινωνήστε ευγενικά.",
                        "inline": False,
                    },
                ],
                "footer": {"text": "PanosLIVE TikTok Community • Καλή διαμονή στην παρέα μας!"},
            }
            res = await client.post(
                f"{DISCORD_API_BASE}/channels/{rules_channel_id}/messages",
                headers=HEADERS,
                json={"embeds": [rules_embed]},
            )
            if res.status_code in (200, 201):
                msg_id = res.json()["id"]
                # Pin the message
                await client.put(f"{DISCORD_API_BASE}/channels/{rules_channel_id}/pins/{msg_id}", headers=HEADERS)
                print("  ✅ Κανόνες δημοσιεύτηκαν και καρφιτσώθηκαν στο #κανόνες!")

        # Announcements Embed
        if announcements_channel_id:
            announcement_embed = {
                "title": "🎉 Καλωσήρθατε στην Κοινότητα PanosLIVE!",
                "description": (
                    "🔥 **Ο επίσημος Discord Server του PanosLIVE είναι πλέον LIVE!**\n\n"
                    "Εδώ θα μπορείτε να:\n"
                    "• Ενημερώνεστε πρώτοι για τα **νέα TikTok Videos** και τα **TikTok Lives**!\n"
                    "• Μιλάτε καθημερινά με τον Πάνο και όλη την παρέα στο chat!\n"
                    "• Προτείνετε ιδέες για επόμενα βίντεο και challenges!\n"
                    "• Μπαίνετε σε voice rooms για παρέα και gaming!\n\n"
                    "👉 Ακολουθήστε το επίσημο κανάλι στο TikTok: **@PanosLIVE**\n"
                    "Περάστε από το <#{rules_channel_id}> για να διαβάσετε τους κανόνες και πείτε ένα 'Γεια' στο <#{welcome_channel_id}>!"
                ),
                "color": 0x5865F2,  # Blurple
                "footer": {"text": "PanosLIVE Official Community • Powered by Antigravity AI"},
            }
            res = await client.post(
                f"{DISCORD_API_BASE}/channels/{announcements_channel_id}/messages",
                headers=HEADERS,
                json={"embeds": [announcement_embed]},
            )
            if res.status_code in (200, 201):
                msg_id = res.json()["id"]
                await client.put(f"{DISCORD_API_BASE}/channels/{announcements_channel_id}/pins/{msg_id}", headers=HEADERS)
                print("  ✅ Ανακοίνωση δημοσιεύτηκε και καρφιτσώθηκε στο #ανακοινώσεις!")

        print("\n✨ ΟΛΟΚΛΗΡΩΘΗΚΕ ΕΠΙΤΥΧΩΣ! Το Greek TikTok Community του PanosLIVE είναι έτοιμο!")


if __name__ == "__main__":
    asyncio.run(main())
