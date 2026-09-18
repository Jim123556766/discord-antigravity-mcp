# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "discord.py>=2.3.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
Live Discord Bot runner for Antigravity AI
Keeps the bot online 24/7 with custom status and chat commands.
Includes automatic fallback if Privileged Gateway Intents are not enabled.
"""

import os
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import discord
from discord.ext import commands
from dotenv import load_dotenv
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
if not TOKEN:
    print("❌ Error: DISCORD_BOT_TOKEN is missing in .env! Run 'setup.bat' first.")
    sys.exit(1)


# -------------------------------------------------------------
# 24/7 Cloud Hosting Keep-Alive Server
# -------------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"online","service":"PanosLIVE-Discord-Bot","24_7":true}')

    def log_message(self, format, *args):
        return  # Suppress noisy keep-alive access logs


def start_keep_alive_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        print(f"🌐 24/7 Cloud Keep-Alive Server active on port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"⚠️ Keep-alive server notice: {e}")


def register_handlers(bot: commands.Bot):
    @bot.event
    async def on_ready():
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="Antigravity AI | !antigravity",
        )
        await bot.change_presence(status=discord.Status.online, activity=activity)
        print("=" * 60)
        print(f"🤖 Bot is ONLINE as {bot.user.name}#{bot.user.discriminator} (ID: {bot.user.id})")
        print(f"📡 Connected to {len(bot.guilds)} servers:")
        for g in bot.guilds:
            print(f"   - {g.name} (ID: {g.id})")
        print("=" * 60)
        print("💡 The Antigravity MCP Server can now manage this server directly!")

    @bot.event
    async def on_member_join(member: discord.Member):
        print(f"👋 Νέο μέλος: {member.name}#{member.discriminator} (ID: {member.id})")
        # Find TikTok Community role
        role = discord.utils.get(member.guild.roles, name="👥 TikTok Community")
        if not role:
            role = next((r for r in member.guild.roles if "Community" in r.name), None)

        if role:
            try:
                await member.add_roles(role)
                print(f"✅ Ο ρόλος '{role.name}' ανατέθηκε αυτόματα στον {member.name}")
            except Exception as e:
                print(f"❌ Αποτυχία ανάθεσης ρόλου στον {member.name}: {e}")

        # Send greeting in #καλωσορίσματα
        welcome_ch = next((c for c in member.guild.text_channels if "καλωσορίσματα" in c.name), None)
        if welcome_ch:
            embed = discord.Embed(
                title="🎉 Νέο Μέλος στην Κοινότητα!",
                description=(
                    f"Καλωσήρθες στην επίσημη κοινότητα του **PanosLIVE**, {member.mention}! 👋\n\n"
                    f"Έλαβες αυτόματα τον ρόλο **{role.name if role else 'TikTok Community'}**!\n"
                    f"👉 Δες τους κανόνες στο κανάλι των κανόνων και έλα να πεις ένα γεια στο chat! 🚀"
                ),
                color=discord.Color.green(),
            )
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            await welcome_ch.send(embed=embed)

    @bot.command(name="ping")
    async def ping_cmd(ctx):
        """Checks the bot latency."""
        latency = round(bot.latency * 1000)
        await ctx.send(f"🏓 **Pong!** Latency: `{latency}ms`")

    @bot.command(name="antigravity", aliases=["agy", "ai"])
    async def antigravity_cmd(ctx):
        """Displays information about the Antigravity MCP integration."""
        embed = discord.Embed(
            title="🚀 Antigravity Discord Integration",
            description=(
                "Αυτό το Discord server είναι συνδεδεμένο με το **Antigravity AI** μέσω **Model Context Protocol (MCP)**!\n\n"
                "Μπορείς να ζητήσεις από το Antigravity στο chat του να δημιουργήσει ή να τροποποιήσει οτιδήποτε στο server σου αυτόματα!"
            ),
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="🛠️ Δυνατότητες Antigravity MCP",
            value=(
                "• Δημιουργία καναλιών (Text, Voice, Announcements, Forums)\n"
                "• Οργάνωση Categories και ιεραρχίας\n"
                "• Δημιουργία και ανάθεση Roles με χρώματα και δικαιώματα\n"
                "• Αποστολή Embed ανακοινώσεων & καρφίτσωμα μηνυμάτων\n"
                "• Batch Server Builder (φτιάχνει ολόκληρο server layout σε 1 εντολή!)\n"
                "• Raw Discord API endpoint execution"
            ),
            inline=False,
        )
        embed.add_field(
            name="💬 Παραδείγματα εντολών στο Antigravity",
            value=(
                "1. *'Φτιάξε μου ένα Category GAMING με 3 voice channels και ένα text chat'*\n"
                "2. *'Φτιάξε έναν ρόλο Moderator με μπλε χρώμα και δικαιώματα διαχείρισης'*\n"
                "3. *'Στείλε ένα όμορφο embed με τους κανόνες του server στο #rules'*"
            ),
            inline=False,
        )
        server_name = ctx.guild.name if ctx.guild else "Direct Message"
        embed.set_footer(text=f"Server: {server_name} • Powered by Google Antigravity & MCP")
        await ctx.send(embed=embed)

    @bot.command(name="status")
    async def status_cmd(ctx):
        """Shows server status and metrics."""
        guild = ctx.guild
        if not guild:
            await ctx.send("This command can only be used inside a server.")
            return

        embed = discord.Embed(
            title=f"📊 Server Status: {guild.name}",
            color=discord.Color.green(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="💬 Κανάλια", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="🎭 Ρόλοι", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="👑 Owner ID", value=str(guild.owner_id), inline=True)
        embed.add_field(name="⚡ Bot Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
        await ctx.send(embed=embed)

    @bot.command(name="help")
    async def help_cmd(ctx):
        """Displays bot commands."""
        embed = discord.Embed(
            title="📖 Discord Bot Commands",
            description="Εντολές που μπορείς να τρέξεις στο Discord chat (με `!` ή mention `@Bot`):",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="!antigravity", value="Πληροφορίες για το Antigravity MCP", inline=False)
        embed.add_field(name="!status", value="Στατιστικά για το server", inline=False)
        embed.add_field(name="!ping", value="Έλεγχος απόκρισης του bot", inline=False)
        embed.add_field(name="!help", value="Εμφάνιση αυτού του μενού", inline=False)
        await ctx.send(embed=embed)


def create_bot(use_privileged: bool = False) -> commands.Bot:
    intents = discord.Intents.default()
    if use_privileged:
        intents.message_content = True
        intents.members = True

    bot = commands.Bot(
        command_prefix=commands.when_mentioned_or("!"),
        intents=intents,
        help_command=None,
    )
    register_handlers(bot)
    return bot


def main():
    try:
        # First attempt: Try with privileged intents if enabled
        bot = create_bot(use_privileged=True)
        bot.run(TOKEN)
    except discord.errors.PrivilegedIntentsRequired:
        print("\n" + "=" * 60)
        print("ℹ️  Privileged Intents δεν είναι ενεργοποιημένα στο Developer Portal.")
        print("🔄 Αυτόματη εκκίνηση με Standard Intents (δεν απαιτείται καμία αλλαγή)...")
        print("=" * 60 + "\n")
        bot = create_bot(use_privileged=False)
        bot.run(TOKEN)


if __name__ == "__main__":
    main()
