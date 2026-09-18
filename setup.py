# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
Discord Bot & Antigravity MCP Setup Wizard
Automates:
1. Discord Bot Token verification
2. 1-Click Bot Invite link generation (with Admin permissions) and automatic browser launch
3. Saving .env credentials
4. Automatically configuring Antigravity's global mcp_config.json
"""

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path
import httpx

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_DIR = Path(__file__).parent.resolve()
ENV_FILE = PROJECT_DIR / ".env"
SERVER_SCRIPT = PROJECT_DIR / "server.py"
MCP_CONFIG_PATH = Path(os.path.expanduser("~")) / ".gemini" / "config" / "mcp_config.json"
DISCORD_API_BASE = "https://discord.com/api/v10"


def print_banner():
    print("=" * 65)
    print("   🤖 ANTIGRAVITY DISCORD BOT & MCP SERVER SETUP WIZARD   ")
    print("=" * 65)
    print("Αυτό το script ρυθμίζει αυτόματα το Discord Bot και συνδέει")
    print("το MCP Server με την εφαρμογή Antigravity!\n")


def verify_token(token: str):
    """Checks if the bot token is valid and returns the bot details."""
    headers = {
        "Authorization": f"Bot {token.strip()}",
        "User-Agent": "AntigravityDiscordSetup/1.0",
    }
    with httpx.Client() as client:
        resp = client.get(f"{DISCORD_API_BASE}/users/@me", headers=headers)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            return None
        else:
            raise RuntimeError(f"Discord API returned status {resp.status_code}: {resp.text}")


def update_mcp_config(token: str):
    """Adds the discord MCP server to Antigravity's global mcp_config.json."""
    MCP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    config = {}
    if MCP_CONFIG_PATH.exists():
        try:
            content = MCP_CONFIG_PATH.read_text(encoding="utf-8").strip()
            if content:
                config = json.loads(content)
        except Exception as e:
            print(f"⚠️  Warning reading existing mcp_config.json: {e}")
            config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    server_script_str = str(SERVER_SCRIPT)
    config["mcpServers"]["discord"] = {
        "command": "uv",
        "args": [
            "run",
            "--with", "mcp>=1.0.0",
            "--with", "httpx>=0.27.0",
            "--with", "python-dotenv>=1.0.0",
            server_script_str,
        ],
        "env": {
            "DISCORD_BOT_TOKEN": token,
        },
    }

    with open(MCP_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✅ Ενημερώθηκε επιτυχώς το MCP config: {MCP_CONFIG_PATH}")


def save_env_file(token: str):
    """Saves the bot token in .env."""
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(f"# Discord Bot Configuration\n")
        f.write(f"DISCORD_BOT_TOKEN={token}\n")
    print(f"✅ Αποθηκεύτηκε το token στο {ENV_FILE}")


def main():
    print_banner()

    parser = argparse.ArgumentParser(description="Discord Bot Setup for Antigravity")
    parser.add_argument("--token", help="Discord Bot Token", default=None)
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    token = args.token

    # Check if existing token is present in .env
    if not token and ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("DISCORD_BOT_TOKEN="):
                val = line.split("=", 1)[1].strip()
                if val:
                    print(f"ℹ️  Βρέθηκε υπάρχον token στο .env ({val[:8]}...{val[-4:]})")
                    reuse = input("Θέλεις να χρησιμοποιήσεις αυτό το token; (Y/n): ").strip().lower()
                    if reuse != "n":
                        token = val

    # If still no token, prompt user & offer to open developer portal
    if not token:
        print("\nΒήματα για να πάρεις το Discord Bot Token σου:")
        print(" 1. Θα ανοίξει το Discord Developer Portal στο browser σου.")
        print(" 2. Πάτα 'New Application', δώσε ένα όνομα (π.χ. Antigravity Bot).")
        print(" 3. Πήγαινε στην καρτέλα 'Bot' στα αριστερά.")
        print(" 4. Πάτα 'Reset Token' / 'Copy Token'.")
        print(" 5. (Προαιρετικό) Στο 'Privileged Gateway Intents' ενεργοποίησε: 'Server Members Intent' & 'Message Content Intent'.\n")

        if not args.no_browser:
            input("Πάτα ENTER για να ανοίξει το Discord Developer Portal στον browser...")
            webbrowser.open("https://discord.com/developers/applications")

        print("\nΕπικόλλησε το Discord Bot Token σου παρακάτω:")
        token = input("Bot Token: ").strip()

    if not token:
        print("❌ Σφάλμα: Δεν δόθηκε Bot Token. Η διαδικασία ακυρώθηκε.")
        sys.exit(1)

    print("\n🔍 Έλεγχος εγκυρότητας του Bot Token στο Discord API...")
    try:
        bot_data = verify_token(token)
    except Exception as e:
        print(f"❌ Σφάλμα επικοινωνίας με το Discord: {e}")
        sys.exit(1)

    if not bot_data:
        print("❌ Σφάλμα: Το Bot Token είναι άκυρο (401 Unauthorized)! Παρακαλώ έλεγξε ξανά το token σου.")
        sys.exit(1)

    bot_id = bot_data["id"]
    bot_tag = f"{bot_data['username']}#{bot_data.get('discriminator', '0')}"
    print(f"\n✨ ΕΠΙΤΥΧΙΑ! Συνδέθηκε στο Bot: {bot_tag} (ID: {bot_id})")

    # Generate Invite Link with Administrator permissions
    invite_url = f"https://discord.com/oauth2/authorize?client_id={bot_id}&permissions=8&scope=bot%20applications.commands"

    print("\n" + "=" * 65)
    print("🔗 ΣΥΝΔΕΣΜΟΣ ΠΡΟΣΚΛΗΣΗΣ ΤΟΥ BOT ΣΤΟ SERVER ΣΟΥ (1-Click Invite):")
    print(f"{invite_url}")
    print("=" * 65)

    if not args.no_browser:
        print("\n🌐 Ανοίγει ο σύνδεσμος πρόσκλησης στον browser για να προσθέσεις το bot στο server σου...")
        webbrowser.open(invite_url)

    # Save to .env and configure MCP
    save_env_file(token)
    update_mcp_config(token)

    print("\n🎉 ΟΛΑ ΕΤΟΙΜΑ!")
    print("1. Πρόσθεσε το bot στο Discord server σου μέσω του browser link.")
    print("2. Κάνε restart ή άνοιξε νέο chat στο Antigravity για να φορτώσει τα MCP tools.")
    print("3. Στο Antigravity μπορείς τώρα να πεις:")
    print("   'Φτιάξε μου ένα Community category με κανάλια welcome, rules, general, memes'")
    print("   'Φτιάξε έναν ρόλο VIP με χρυσό χρώμα'")
    print("   'Στείλε ανακοίνωση embed στο κανάλι announcements'")
    print("   'Φτιάξε όλο το Discord server από την αρχή για gaming κοινότητα'\n")


if __name__ == "__main__":
    main()
