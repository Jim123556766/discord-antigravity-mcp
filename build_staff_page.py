# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
Builds the Ultimate Staff Hub for PanosLIVE Discord Server:
1. Creates '🛡️ Staff Team' role with dedicated styling
2. Adds #📋・staff-οδηγίες, #🎯・tiktok-live-συντονισμός, #🚨・αναφορές-μελών
3. Configures strict private permissions
4. Posts 4 comprehensive, beautifully styled Staff Handbook & Protocol Embeds
5. Assigns role to server owner
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
    "User-Agent": "AntigravityStaffBuilder/1.0",
}

VIEW_CHANNEL = 1 << 10
SEND_MESSAGES = 1 << 11
READ_MESSAGE_HISTORY = 1 << 16
CONNECT = 1 << 20
SPEAK = 1 << 21
MANAGE_MESSAGES = 1 << 13
KICK_MEMBERS = 1 << 1
BAN_MEMBERS = 1 << 2
MUTE_MEMBERS = 1 << 22


async def set_perm(client: httpx.AsyncClient, channel_id: str, overwrite_id: str, allow: int, deny: int):
    payload = {"id": str(overwrite_id), "type": 0, "allow": str(allow), "deny": str(deny)}
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/permissions/{overwrite_id}"
    await client.put(url, headers=HEADERS, json=payload)


async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Guild & Owner
        guild_resp = await client.get(f"{DISCORD_API_BASE}/users/@me/guilds", headers=HEADERS)
        guild_id = guild_resp.json()[0]["id"]
        everyone_id = guild_id

        g_info = await client.get(f"{DISCORD_API_BASE}/guilds/{guild_id}", headers=HEADERS)
        owner_id = g_info.json().get("owner_id")

        print(f"🚀 Συνδέθηκε στο Server ID: {guild_id}")

        # 2. Create '🛡️ Staff Team' Role
        # Permissions for Staff: Kick, Manage Messages, Mute, View Channel, Read History
        staff_perms = str(KICK_MEMBERS | MANAGE_MESSAGES | MUTE_MEMBERS | VIEW_CHANNEL | READ_MESSAGE_HISTORY | CONNECT | SPEAK)
        role_payload = {
            "name": "🛡️ Staff Team",
            "color": 0x00ADB5,  # Premium Teal/Cyan
            "hoist": True,
            "mentionable": True,
            "permissions": staff_perms,
        }
        r_resp = await client.post(f"{DISCORD_API_BASE}/guilds/{guild_id}/roles", headers=HEADERS, json=role_payload)
        staff_role_data = r_resp.json()
        staff_role_id = staff_role_data["id"]
        print(f"✅ Δημιουργήθηκε ο ρόλος: 🛡️ Staff Team (ID: {staff_role_id})")

        # Assign to owner
        if owner_id:
            await client.put(f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{owner_id}/roles/{staff_role_id}", headers=HEADERS)
            print(f"✅ Ο ρόλος Staff Team ανατέθηκε στον Owner ({owner_id})")

        # 3. Find '🔒・STAFF ONLY' Category
        ch_resp = await client.get(f"{DISCORD_API_BASE}/guilds/{guild_id}/channels", headers=HEADERS)
        channels = ch_resp.json()
        staff_cat = next((c for c in channels if c.get("type") == 4 and "STAFF ONLY" in c.get("name", "")), None)

        if not staff_cat:
            print("Creating Staff category...")
            cat_r = await client.post(f"{DISCORD_API_BASE}/guilds/{guild_id}/channels", headers=HEADERS, json={"name": "🔒・STAFF ONLY", "type": 4})
            staff_cat = cat_r.json()

        cat_id = staff_cat["id"]

        # Ensure Category has permissions for new Staff Team role
        await set_perm(client, cat_id, everyone_id, allow=0, deny=VIEW_CHANNEL)
        await set_perm(client, cat_id, staff_role_id, allow=VIEW_CHANNEL | SEND_MESSAGES | CONNECT | READ_MESSAGE_HISTORY, deny=0)

        # 4. Create new channels in Staff Category
        new_staff_channels = [
            {"name": "📋・staff-οδηγίες", "type": 0, "topic": "Επίσημο Εγχειρίδιο & Πρωτόκολλο Διαχείρισης της κοινότητας PanosLIVE"},
            {"name": "🎯・tiktok-live-συντονισμός", "type": 0, "topic": "Ζωντανός συντονισμός ομάδας κατά τη διάρκεια των TikTok Lives"},
            {"name": "🚨・αναφορές-μελών", "type": 0, "topic": "Καταγραφή και επίλυση αναφορών / προβλημάτων μελών"},
        ]

        created_channels = {}
        for sc in new_staff_channels:
            payload = {
                "name": sc["name"],
                "type": sc["type"],
                "parent_id": cat_id,
                "topic": sc["topic"],
            }
            c_res = await client.post(f"{DISCORD_API_BASE}/guilds/{guild_id}/channels", headers=HEADERS, json=payload)
            if c_res.status_code in (200, 201):
                cd = c_res.json()
                created_channels[sc["name"]] = cd["id"]
                # Lock channel: @everyone cannot see, Staff Team can
                await set_perm(client, cd["id"], everyone_id, allow=0, deny=VIEW_CHANNEL)
                await set_perm(client, cd["id"], staff_role_id, allow=VIEW_CHANNEL | SEND_MESSAGES | READ_MESSAGE_HISTORY, deny=0)
                print(f"✅ Δημιουργήθηκε το κανάλι: #{sc['name']}")

        guidelines_cid = created_channels.get("📋・staff-οδηγίες")
        live_coord_cid = created_channels.get("🎯・tiktok-live-συντονισμός")

        # 5. POST TELEIO STAFF HANDBOOK EMBEDS in #staff-οδηγίες
        if guidelines_cid:
            print("\n🎨 Αποστολή των Embeds στο #📋・staff-οδηγίες...")

            # Embed 1: Introduction & Principles
            embed1 = {
                "title": "🛡️ ΕΠΙΣΗΜΟ ΕΓΧΕΙΡΙΔΙΟ STAFF • PanosLIVE Community",
                "description": (
                    "Καλωσήρθατε στην επίσημη ομάδα διαχείρισης του **PanosLIVE**!\n\n"
                    "Ως μέλος του Staff, εκπροσωπείτε τον Πάνο και όλη την κοινότητα. "
                    "Στόχος μας είναι να διατηρούμε ένα φιλικό, ασφαλές και διασκεδαστικό περιβάλλον για όλους τους viewers και followers!\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                "color": 0x00ADB5,
                "fields": [
                    {
                        "name": "💎 Οι 3 Βασικές Αρχές του Staff",
                        "value": (
                            "**1. Ψυχραιμία & Ευγένεια:** Δεν απαντάμε ποτέ με ειρωνεία ή θυμό σε προκλήσεις.\n"
                            "**2. Δικαιοσύνη:** Όλοι οι κανόνες ισχύουν για όλους, χωρίς εξαιρέσεις.\n"
                            "**3. Συνεργασία:** Συνεννοούμαστε μεταξύ μας πριν από σοβαρές ποινές (Bans)."
                        ),
                        "inline": False,
                    }
                ],
                "footer": {"text": "PanosLIVE Staff Handbook • Μέρος 1/4"},
            }

            # Embed 2: Moderation Protocol & Punishment Escalation
            embed2 = {
                "title": "⚖️ ΠΡΩΤΟΚΟΛΛΟ ΠΟΙΝΩΝ & ΑΝΤΙΜΕΤΩΠΙΣΗΣ ΠΑΡΑΒΑΤΩΝ",
                "description": "Ακολουθούμε πάντα την κλίμακα ποινών βήμα-βήμα, εκτός αν πρόκειται για σοβαρή παραβίαση:",
                "color": 0xED4245,
                "fields": [
                    {
                        "name": "🟡 1ο Βήμα: Φιλική Προειδοποίηση (Warning)",
                        "value": "Για μικρά σφάλματα (caps lock, spam emoticons, λάθος κανάλι). Ενημερώνουμε ευγενικά.",
                        "inline": False,
                    },
                    {
                        "name": "🟠 2ο Βήμα: Time-out / Mute (10λ έως 1 ώρα)",
                        "value": "Αν ο χρήστης συνεχίζει να προκαλεί, να ειρωνεύεται ή να ανάβει φωτιές στο chat. Χρησιμοποιήστε το Timeout του Discord.",
                        "inline": False,
                    },
                    {
                        "name": "🔴 3ο Βήμα: Kick (Αποβολή)",
                        "value": "Αν επιστρέψει από timeout και συνεχίζει την ίδια συμπεριφορά. Μπορεί να ξαναμπεί αν καταλάβει το λάθος του.",
                        "inline": False,
                    },
                    {
                        "name": "⛔ 4ο Βήμα: Άμεσο Μόνιμο Ban (Zero Tolerance)",
                        "value": (
                            "Εφαρμόζεται **ΑΜΕΣΩΣ ΧΩΡΙΣ ΠΡΟΕΙΔΟΠΟΙΗΣΗ** για:\n"
                            "• Hate speech, ρατσισμό, bullying, απειλές\n"
                            "• Αποστολή NSFW ή ακατάλληλου περιεχομένου\n"
                            "• Ανεπιθύμητο scam / phishing links / server invites\n"
                            "• Raid accounts και bots"
                        ),
                        "inline": False,
                    },
                ],
                "footer": {"text": "PanosLIVE Staff Handbook • Μέρος 2/4"},
            }

            # Embed 3: TikTok Live Coordination Protocol
            embed3 = {
                "title": "📱 ΣΥΝΤΟΝΙΣΜΟΣ ΚΑΤΑ ΤΑ TIKTOK LIVES",
                "description": (
                    "Όταν ο **PanosLIVE** ξεκινάει Live stream στο TikTok, η ομάδα Staff μπαίνει σε κατάσταση ετοιμότητας!\n"
                    "Εδώ είναι τα καθήκοντα ανά τομέα:\n"
                ),
                "color": 0xFF007F,  # TikTok Rose/Magenta
                "fields": [
                    {
                        "name": "🎙️ 1. Voice Lounge",
                        "value": "Το κανάλι **`🎙️・Live Lounge (Panos)`** είναι σε **Listen-Only** mode για το κοινό. Μόνο ο Πάνος, το Staff και οι VIPs μπορούν να μιλάνε.",
                        "inline": False,
                    },
                    {
                        "name": "❓ 2. Συλλογή Ερωτήσεων",
                        "value": "Παρακολουθούμε το κανάλι **`#❓・ερωτήσεις-για-τα-live`** και σημειώνουμε τις καλύτερες ερωτήσεις για να τις μεταφέρουμε στον Πάνο.",
                        "inline": False,
                    },
                    {
                        "name": "⭐ 3. Ανάθεση Ρόλων VIP & Top Fans",
                        "value": "Όταν ένας ακόλουθος κάνει μεγάλο support στο TikTok Live (π.χ. Universe, Lion, Sub), του αποδίδουμε τον ρόλο **`⭐ TikTok VIP`** ή **`🔥 Top Fan`**!",
                        "inline": False,
                    },
                    {
                        "name": "🚨 4. Anti-Troll & Fast Moderation",
                        "value": "Σε περίπτωση troller ή διαφημιστή, δρούμε άμεσα ώστε το stream και το Discord chat να μένουν καθαρά.",
                        "inline": False,
                    },
                ],
                "footer": {"text": "PanosLIVE Staff Handbook • Μέρος 3/4"},
            }

            # Embed 4: Useful Commands & Staff Etiquette
            embed4 = {
                "title": "🛠️ ΕΡΓΑΛΕΙΑ & ΧΡΗΣΙΜΕΣ ΣΥΜΒΟΥΛΕΣ",
                "description": "Σύντομες εντολές και tips για καθημερινή χρήση:",
                "color": 0xF1C40F,  # Gold
                "fields": [
                    {
                        "name": "🤖 Bot Commands στο Server",
                        "value": (
                            "• `!status`: Εμφάνιση κατάστασης server & στατιστικών\n"
                            "• `!ping`: Έλεγχος ταχύτητας απόκρισης bot\n"
                            "• `!antigravity`: Πληροφορίες για το AI integration"
                        ),
                        "inline": False,
                    },
                    {
                        "name": "📝 Καταγραφή στο #mod-logs",
                        "value": "Όποτε δίνεται kick ή ban, γράψτε μια σύντομη αναφορά στο **`#🚨・mod-logs`** (π.χ. *@User - Ban για scam links*).",
                        "inline": False,
                    },
                    {
                        "name": "🤝 Επικοινωνία Ομάδας",
                        "value": "Όλες οι εσωτερικές συζητήσεις γίνονται στο **`#🛡️・staff-chat`** ή στο **`🔒・Staff Voice`**. Μην συζητάτε θέματα διαχείρισης στο δημόσιο chat!",
                        "inline": False,
                    },
                ],
                "footer": {"text": "PanosLIVE Staff Handbook • Μέρος 4/4 • Καλή δύναμη σε όλους!"},
            }

            # Send embeds in sequence
            res1 = await client.post(f"{DISCORD_API_BASE}/channels/{guidelines_cid}/messages", headers=HEADERS, json={"embeds": [embed1]})
            if res1.status_code in (200, 201):
                msg1_id = res1.json()["id"]
                # Pin the main handbook
                await client.put(f"{DISCORD_API_BASE}/channels/{guidelines_cid}/pins/{msg1_id}", headers=HEADERS)

            await client.post(f"{DISCORD_API_BASE}/channels/{guidelines_cid}/messages", headers=HEADERS, json={"embeds": [embed2]})
            await client.post(f"{DISCORD_API_BASE}/channels/{guidelines_cid}/messages", headers=HEADERS, json={"embeds": [embed3]})
            await client.post(f"{DISCORD_API_BASE}/channels/{guidelines_cid}/messages", headers=HEADERS, json={"embeds": [embed4]})
            print("  ✅ Και τα 4 Embeds δημοσιεύτηκαν στο #📋・staff-οδηγίες!")

        # Message in live coordination
        if live_coord_cid:
            live_msg = {
                "title": "🎯 Κέντρο Συντονισμού TikTok Lives",
                "description": (
                    "Αυτό το κανάλι χρησιμοποιείται **ΜΟΝΟ** κατά τη διάρκεια των TikTok Live streams του PanosLIVE!\n\n"
                    "📌 **Εδώ συντονίζουμε:**\n"
                    "• Ποιοι Mods είναι ενεργοί στο TikTok chat και ποιοι στο Discord\n"
                    "• Σημειώσεις για δώρα & VIP αναθέσεις\n"
                    "• Ερωτήσεις του κοινού που αξίζει να απαντήσει ο Πάνος\n"
                    "• Έκτακτα θέματα ή προβλήματα ήχου/εικόνας"
                ),
                "color": 0x5865F2,
                "footer": {"text": "PanosLIVE Live Ops • Ready for Stream!"},
            }
            await client.post(f"{DISCORD_API_BASE}/channels/{live_coord_cid}/messages", headers=HEADERS, json={"embeds": [live_msg]})
            print("  ✅ Μήνυμα συντονισμού αναρτήθηκε στο #🎯・tiktok-live-συντονισμός!")

        print("\n✨ ΟΛΟΚΛΗΡΩΘΗΚΕ! Το Staff Hub & Handbook του PanosLIVE είναι έτοιμο!")


if __name__ == "__main__":
    asyncio.run(main())
