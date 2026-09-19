# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "discord.py>=2.3.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
PanosLIVE Community Super-Bot & Live Runner
Provides 24/7 online presence, Greek Ticket System with Discord UI buttons,
Automated Greek Welcome & Auto-Role, Live Stream & Video Alerts, and Greek Moderation.
"""

import asyncio
import io
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import discord
from discord.ext import commands
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
if not TOKEN:
    print("❌ Error: DISCORD_BOT_TOKEN is missing in .env!")
    sys.exit(1)


# -------------------------------------------------------------
# 24/7 Cloud Hosting Keep-Alive Server
# -------------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"online","service":"PanosLIVE-Super-Bot","ticket_handler":"active","24_7":true}')

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


# -------------------------------------------------------------
# DISCORD UI: Interactive Greek Ticket System
# -------------------------------------------------------------
class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Κλείσιμο Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_close_persistent_btn",
        emoji="🔐",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Confirmation & delete
        await interaction.response.send_message(
            "⚠️ **Το ticket θα αρχειοθετηθεί και θα διαγραφεί σε 5 δευτερόλεπτα...**",
            ephemeral=False,
        )

        guild = interaction.guild
        if guild:
            mod_log = discord.utils.get(guild.text_channels, name="🚨・mod-logs")
            if not mod_log:
                mod_log = next((c for c in guild.text_channels if "mod-log" in c.name), None)
            if mod_log:
                embed = discord.Embed(
                    title="🔒 Ticket Έκλεισε",
                    description=(
                        f"• **Κανάλι:** `{interaction.channel.name}`\n"
                        f"• **Έκλεισε από:** {interaction.user.mention} (`{interaction.user.name}`)\n"
                        f"• **Ημερομηνία:** <t:{int(discord.utils.utcnow().timestamp())}:F>"
                    ),
                    color=discord.Color.red(),
                )
                try:
                    await mod_log.send(embed=embed)
                except Exception:
                    pass

        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user.name}")
        except Exception as e:
            print(f"Failed to delete ticket channel: {e}")


class TicketOpenButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📩 Άνοιγμα Ticket Υποστήριξης",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_open_persistent_btn",
        emoji="🎫",
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Αυτή η ενέργεια υποστηρίζεται μόνο σε server.", ephemeral=True)
            return

        user = interaction.user
        channel_name = f"ticket-{user.name.lower()[:15]}"

        # Prevent duplicate ticket channels
        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            await interaction.response.send_message(
                f"⚠️ Έχετε ήδη ένα ανοιχτό ticket εδώ: {existing.mention}!", ephemeral=True
            )
            return

        # Find or use Tickets category
        category = discord.utils.get(guild.categories, name="🎫・ΥΠΟΣΤΗΡΙΞΗ & TICKETS")
        if not category:
            category = next((c for c in guild.categories if "TICKET" in c.name.upper()), None)

        # Set permissions for the private ticket channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
                read_message_history=True,
            ),
        }

        # Grant access to staff roles
        for r in guild.roles:
            r_name = r.name.lower()
            if any(k in r_name for k in ["staff", "moderator", "creator", "admin"]):
                overwrites[r] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                    read_message_history=True,
                )

        try:
            ticket_ch = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ιδιωτικό Ticket Υποστήριξης για τον χρήστη {user.name} ({user.id})",
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Σφάλμα κατά τη δημιουργία του ticket: {e}", ephemeral=True
            )
            return

        # Send welcome message inside the new ticket
        embed = discord.Embed(
            title=f"🎫 Ticket Υποστήριξης • {user.name}",
            description=(
                f"Γεια σου {user.mention}! 👋\n\n"
                "Ευχαριστούμε που επικοινώνησες με την ομάδα του **PanosLIVE**.\n"
                "Ένα μέλος του **Staff Team** θα σε εξυπηρετήσει άμεσα!\n\n"
                "📌 **Παρακαλούμε εξήγησε αναλυτικά:**\n"
                "1. Ποιο είναι το θέμα ή το πρόβλημα που αντιμετωπίζεις;\n"
                "2. Αν πρόκειται για αναφορά μέλους, στείλε σχετικά αποδεικτικά (screenshots).\n"
                "3. Αν πρόκειται για συνεργασία, ανάφερε λεπτομέρειες.\n\n"
                "🔒 *Όταν ολοκληρωθεί η εξυπηρέτηση, πατήστε το παρακάτω κόκκινο κουμπί για κλείσιμο.*"
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="PanosLIVE Community Support • Πατήστε Κλείσιμο Ticket όταν τελειώσετε")

        view = TicketCloseView()
        await ticket_ch.send(
            content=f"{user.mention} | <@&1550609066848690246> (Staff Team)",
            embed=embed,
            view=view,
        )

        await interaction.response.send_message(
            f"✅ Το ticket σου δημιουργήθηκε επιτυχώς! Μετάβαση: {ticket_ch.mention}",
            ephemeral=True,
        )


# -------------------------------------------------------------
# HANDLERS & BOT COMMANDS
# -------------------------------------------------------------
def register_handlers(bot: commands.Bot):
    @bot.event
    async def on_ready():
        # Register persistent UI views so buttons work across restarts
        bot.add_view(TicketOpenButton())
        bot.add_view(TicketCloseView())

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="PanosLIVE | !help",
        )
        await bot.change_presence(status=discord.Status.online, activity=activity)
        print("=" * 60)
        print(f"🤖 Bot is ONLINE as {bot.user.name}#{bot.user.discriminator} (ID: {bot.user.id})")
        print(f"📡 Connected to {len(bot.guilds)} servers:")
        for g in bot.guilds:
            print(f"   - {g.name} (ID: {g.id})")
        print("🎫 Greek Ticket System & Live Alerts active!")
        print("=" * 60)

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
                    f"👉 Δες τους κανόνες στο κανάλι των κανόνων και έλα να πεις ένα γεια στο chat! 🚀\n"
                    f"🎫 Χρειάζεσαι βοήθεια; Άνοιξε ticket στο κανάλι <#1550773354259157072>!"
                ),
                color=discord.Color.green(),
            )
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            try:
                await welcome_ch.send(embed=embed)
            except Exception as e:
                print(f"Welcome send error: {e}")

    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return

        # Auto-mod: Block unauthorized discord invites from non-staff members
        if "discord.gg/" in message.content.lower() or "discord.com/invite/" in message.content.lower():
            is_staff = False
            if isinstance(message.author, discord.Member):
                is_staff = any(
                    any(k in r.name.lower() for k in ["staff", "moderator", "creator", "admin"])
                    for r in message.author.roles
                )
            if not is_staff:
                try:
                    await message.delete()
                    await message.channel.send(
                        f"⚠️ {message.author.mention}, η κοινοποίηση Discord invite links δεν επιτρέπεται!",
                        delete_after=6,
                    )
                    # Log to mod-logs
                    if message.guild:
                        mod_log = next((c for c in message.guild.text_channels if "mod-log" in c.name), None)
                        if mod_log:
                            log_embed = discord.Embed(
                                title="🚨 Auto-Mod: Διαγραφή Discord Link",
                                description=f"Ο χρήστης {message.author.mention} έστειλε invite link στο {message.channel.mention}.",
                                color=discord.Color.red(),
                            )
                            await mod_log.send(embed=log_embed)
                    return
                except Exception:
                    pass

        await bot.process_commands(message)

    # -------------------------------------------------------------
    # COMMAND: Send/Refresh Ticket Panel
    # -------------------------------------------------------------
    @bot.command(name="ticket_panel", aliases=["post_ticket_panel"])
    @commands.has_permissions(administrator=True)
    async def ticket_panel_cmd(ctx):
        """Sends the interactive Greek Ticket Panel with click-to-open button."""
        embed = discord.Embed(
            title="📩 ΚΕΝΤΡΟ ΕΞΥΠΗΡΕΤΗΣΗΣ & TICKETS",
            description=(
                "Καλωσήρθατε στο επίσημο σύστημα εξυπηρέτησης του **PanosLIVE Community**!\n\n"
                "Χρειάζεστε βοήθεια; Έχετε ερωτήσεις για τα streams; Θέλετε να αναφέρετε κάποιο μέλος "
                "ή προτείνετε κάποια συνεργασία;\n\n"
                "👇 **Πατήστε το παρακάτω μπλε κουμπί για να ανοίξετε άμεσα ένα ιδιωτικό Ticket!**"
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="📋 Επιλογές Υποστήριξης",
            value=(
                "• ❓ **Γενικές Ερωτήσεις & Βοήθεια**\n"
                "• 🔴 **Ερωτήσεις για TikTok Lives**\n"
                "• 🚨 **Αναφορά Παραβίασης / Report** (Εμπιστευτικό)\n"
                "• 🤝 **Συνεργασίες / Collabs**"
            ),
            inline=False,
        )
        embed.set_footer(text="PanosLIVE Support Bot • Πατήστε το κουμπί παρακάτω")
        view = TicketOpenButton()
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()

    # -------------------------------------------------------------
    # COMMAND: Manual Ticket for members (!ticket [θέμα])
    # -------------------------------------------------------------
    @bot.command(name="ticket")
    async def ticket_cmd(ctx, *, reason: str = "Γενική Υποστήριξη"):
        """Opens a private support ticket."""
        guild = ctx.guild
        user = ctx.author
        channel_name = f"ticket-{user.name.lower()[:15]}"

        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            await ctx.send(f"⚠️ {user.mention}, έχετε ήδη ανοιχτό ticket στο {existing.mention}!", delete_after=10)
            return

        category = discord.utils.get(guild.categories, name="🎫・ΥΠΟΣΤΗΡΙΞΗ & TICKETS")
        if not category:
            category = next((c for c in guild.categories if "TICKET" in c.name.upper()), None)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
                read_message_history=True,
            ),
        }

        for r in guild.roles:
            r_name = r.name.lower()
            if any(k in r_name for k in ["staff", "moderator", "creator", "admin"]):
                overwrites[r] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                    read_message_history=True,
                )

        ticket_ch = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket: {reason} | User: {user.name} ({user.id})",
        )

        embed = discord.Embed(
            title=f"🎫 Ticket Υποστήριξης • {user.name}",
            description=(
                f"Γεια σου {user.mention}!\n\n"
                f"**Θέμα:** `{reason}`\n\n"
                "Ένα μέλος του **Staff Team** θα σε εξυπηρετήσει άμεσα!\n"
                "Παρακαλούμε παράθεσε όσες περισσότερες λεπτομέρειες μπορείς."
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Πατήστε Κλείσιμο Ticket όταν ολοκληρωθεί το αίτημά σας.")

        view = TicketCloseView()
        await ticket_ch.send(
            content=f"{user.mention} | <@&1550609066848690246> (Staff Team)",
            embed=embed,
            view=view,
        )
        await ctx.send(f"✅ {user.mention}, το ticket σου άνοιξε εδώ: {ticket_ch.mention}", delete_after=10)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    # -------------------------------------------------------------
    # COMMANDS: Live Stream & Video Announcements
    # -------------------------------------------------------------
    @bot.command(name="live", aliases=["stream"])
    @commands.has_permissions(manage_messages=True)
    async def live_announcement_cmd(ctx, *, details: str):
        """Broadcasts a live stream announcement to #live-alerts.
        Usage: !live https://tiktok.com/@panoslive Τρέχουμε live τώρα!
        """
        guild = ctx.guild
        alerts_ch = discord.utils.get(guild.text_channels, name="🔴・live-alerts")
        if not alerts_ch:
            alerts_ch = next((c for c in guild.text_channels if "live-alert" in c.name or "tiktok-feed" in c.name), ctx.channel)

        embed = discord.Embed(
            title="🔴 Ο PANOSLIVE ΕΙΝΑΙ ΤΩΡΑ LIVE!",
            description=(
                f"📢 **Ελάτε όλοι στο stream!**\n\n"
                f"{details}\n\n"
                f"👉 Μπείτε τώρα για να μη χάσετε τίποτα! 🔥"
            ),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text="PanosLIVE Official Streams • Ειδοποίηση Ζωντανής Μετάδοσης")
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await alerts_ch.send(content="@everyone 🔴 **LIVE ALERT!**", embed=embed)
        await ctx.send(f"✅ Η ανακοίνωση Live στάλθηκε επιτυχώς στο {alerts_ch.mention}!", delete_after=5)

    @bot.command(name="video", aliases=["tiktok", "newvideo"])
    @commands.has_permissions(manage_messages=True)
    async def video_announcement_cmd(ctx, *, details: str):
        """Broadcasts a new video announcement to #tiktok-feed and #live-alerts.
        Usage: !video https://tiktok.com/... Νέο βίντεο μόλις ανέβηκε!
        """
        guild = ctx.guild
        feed_ch = discord.utils.get(guild.text_channels, name="📱・tiktok-feed")
        if not feed_ch:
            feed_ch = next((c for c in guild.text_channels if "tiktok" in c.name), ctx.channel)

        embed = discord.Embed(
            title="🎬 ΝΕΟ ΒΙΝΤΕΟ ΣΤΟ TIKTOK!",
            description=(
                f"🔥 **Μόλις ανέβηκε νέο βίντεο από τον PanosLIVE!**\n\n"
                f"{details}\n\n"
                f"👉 Δείτε το, αφήστε like και σχόλιο για υποστήριξη! 🚀"
            ),
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text="PanosLIVE Community • Νέο Περιεχόμενο")
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await feed_ch.send(content="🔔 @everyone **Νέο Βίντεο!**", embed=embed)
        await ctx.send(f"✅ Η ανακοίνωση βίντεο στάλθηκε στο {feed_ch.mention}!", delete_after=5)

    @bot.command(name="announce")
    @commands.has_permissions(administrator=True)
    async def general_announce_cmd(ctx, *, message: str):
        """Sends a formatted announcement into #ανακοινώσεις."""
        guild = ctx.guild
        ann_ch = discord.utils.get(guild.text_channels, name="📢・ανακοινώσεις")
        if not ann_ch:
            ann_ch = next((c for c in guild.text_channels if "ανακοιν" in c.name), ctx.channel)

        embed = discord.Embed(
            title="📢 ΕΠΙΣΗΜΗ ΑΝΑΚΟΙΝΩΣΗ",
            description=message,
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text=f"Ανακοινώθηκε από {ctx.author.name} • PanosLIVE Team")
        await ann_ch.send(content="@everyone", embed=embed)
        await ctx.send(f"✅ Η ανακοίνωση δημοσιεύτηκε στο {ann_ch.mention}!", delete_after=5)

    # -------------------------------------------------------------
    # UTILITY & STATUS COMMANDS
    # -------------------------------------------------------------
    @bot.command(name="ping")
    async def ping_cmd(ctx):
        """Checks bot response latency."""
        latency = round(bot.latency * 1000)
        await ctx.send(f"🏓 **Pong!** Latency: `{latency}ms`")

    @bot.command(name="status")
    async def status_cmd(ctx):
        """Displays live server health and statistics."""
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
        embed.add_field(name="👥 Μέλη", value=str(guild.member_count), inline=True)
        embed.add_field(name="⚡ Bot Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="🎫 Ticket System", value="🟢 Ενεργό (Greek UI)", inline=True)
        embed.add_field(name="🔴 Live Alerts", value="🟢 Ενεργό", inline=True)
        await ctx.send(embed=embed)

    @bot.command(name="help")
    async def help_cmd(ctx):
        """Displays available bot commands."""
        embed = discord.Embed(
            title="📖 Εντολές PanosLIVE Community Bot",
            description="Όλες οι διαθέσιμες εντολές του server (πρόθεμα: `!` ή mention):",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="🎫 Υποστήριξη & Tickets",
            value=(
                "`!ticket [θέμα]` : Άνοιγμα ιδιωτικού ticket υποστήριξης\n"
                "`!ticket_panel` : (Admin) Δημοσίευση διαδραστικού πάνελ με κουμπί"
            ),
            inline=False,
        )
        embed.add_field(
            name="🔴 Ειδοποιήσεις & Ανακοινώσεις (Staff)",
            value=(
                "`!live <link/θέμα>` : Ανακοίνωση TikTok Live στο #live-alerts\n"
                "`!video <link>` : Ανακοίνωση νέου βίντεο στο #tiktok-feed\n"
                "`!announce <κείμενο>` : Επίσημη ανακοίνωση στο #ανακοινώσεις"
            ),
            inline=False,
        )
        embed.add_field(
            name="⚙️ Γενικές Εντολές",
            value=(
                "`!status` : Στατιστικά και κατάσταση του server\n"
                "`!ping` : Έλεγχος απόκρισης του bot\n"
                "`!antigravity` : Πληροφορίες για το AI integration\n"
                "`!help` : Εμφάνιση αυτού του μενού"
            ),
            inline=False,
        )
        await ctx.send(embed=embed)

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
        server_name = ctx.guild.name if ctx.guild else "Direct Message"
        embed.set_footer(text=f"Server: {server_name} • Powered by Google Antigravity & MCP")
        await ctx.send(embed=embed)


def create_bot(use_privileged: bool = True) -> commands.Bot:
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
    # Start web keep-alive server for cloud deployment
    keep_alive_thread = threading.Thread(target=start_keep_alive_server, daemon=True)
    keep_alive_thread.start()

    try:
        bot = create_bot(use_privileged=True)
        bot.run(TOKEN)
    except discord.errors.PrivilegedIntentsRequired:
        print("\n" + "=" * 60)
        print("ℹ️  Privileged Intents δεν είναι ενεργοποιημένα στο Developer Portal.")
        print("🔄 Αυτόματη εκκίνηση με Standard Intents...")
        print("=" * 60 + "\n")
        bot = create_bot(use_privileged=False)
        bot.run(TOKEN)


if __name__ == "__main__":
    main()
