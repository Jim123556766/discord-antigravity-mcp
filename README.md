# 🤖 Antigravity Discord MCP Bot

Μία ολοκληρωμένη λύση που συνδέει το **Antigravity AI** με το **Discord Server** σου μέσω **Model Context Protocol (MCP)**.
Με αυτό το σύστημα, μπορείς να ζητήσεις από το Antigravity στο chat του να δημιουργήσει ή να τροποποιήσει **οτιδήποτε** στο Discord!

---

## 🌟 1. Ο Νέος Animated Installer (Προτεινόμενο!)

Κάνε απλά **διπλό κλικ** στο αρχείο:
👉 [`installer.bat`](file:///C:/Users/nikel/.gemini/antigravity/scratch/discord-antigravity-mcp/installer.bat)

Θα ανοίξει αυτόματα στον browser σου ένα **πανέμορφο γραφικό περιβάλλον με animations (particle effects, live bot card, terminal log & confetti)**!
Από εκεί μπορείς:
1. Να δεις τα system diagnostics σου.
2. Να πληκτρολογήσεις το Bot Token σου και να δεις **ζωντανά το προφίλ και το avatar του bot σου**!
3. Να πατήσεις **1-Click Invite** για να μπει το bot στο server.
4. Να πατήσεις **Κατέβασμα ZIP** για να πάρεις ένα έτοιμο πακέτο εγκατάστασης (`Antigravity-Discord-Bot.zip`) να το στείλεις σε οποιονδήποτε άλλο!
5. Να ξεκινήσεις το Live Bot με ένα κλικ!

---

## 📦 2. Έτοιμο Πακέτο για Φίλους (ZIP Download)
Στο φάκελο έχει ήδη δημιουργηθεί το αρχείο:
📁 [`Antigravity-Discord-Bot.zip`](file:///C:/Users/nikel/.gemini/antigravity/scratch/discord-antigravity-mcp/Antigravity-Discord-Bot.zip)
Μπορείς να στείλεις αυτό το `.zip` σε οποιονδήποτε θέλει το bot: απλά το κάνει αποσυμπίεση και πατάει `installer.bat`!

---

## ⚡ 3. Εναλλακτικά: Terminal Setup (Setup.bat)

2. Το script θα:
   - **Ανοίξει αυτόματα** το [Discord Developer Portal](https://discord.com/developers/applications) στο browser σου.
   - Σου ζητήσει να αντιγράψεις το **Bot Token**.
   - Κάνει αυτόματα **verify** το token στο Discord API.
   - Σου δημιουργήσει και ανοίξει αυτόματα στο browser το **1-Click Invite Link** (με Administrator permissions) για να προσθέσεις το bot στο server σου αμέσως!
   - Ρυθμίσει αυτόματα το `~/.gemini/config/mcp_config.json` του Antigravity.

---

## ⚡ Πώς να φτιάξεις το Bot στο Discord Portal (αν δεν έχεις ήδη):

1. Στο [Discord Developer Portal](https://discord.com/developers/applications):
   - Πάτα **"New Application"** και δώσε ένα όνομα (π.χ. `Antigravity Assistant`).
2. Στο αριστερό μενού πάτα **"Bot"**:
   - Πάτα **"Reset Token"** και κάνε **Copy**.
   - Στην ίδια σελίδα, κύλησε προς τα κάτω στο **"Privileged Gateway Intents"** και ενεργοποίησε:
     - ✅ **Presence Intent**
     - ✅ **Server Members Intent**
     - ✅ **Message Content Intent**
   - Πάτα **Save Changes**.
3. Επικόλλησε το Token στο setup script!

---

## 🛠️ Τι μπορείς να ζητήσεις από το Antigravity;

Μόλις ρυθμιστεί, μπορείς απλά να γράψεις στο chat του Antigravity στα Ελληνικά ή Αγγλικά:

### 1. Δημιουργία Ολόκληρου Server Layout
> *"Φτιάξε μου ένα πλήρες Discord server layout για gaming κοινότητα με categories Welcome, Text Chats, Voice Lounges, και ρόλους Admin, Moderator, Member."*

### 2. Δημιουργία & Διαχείριση Καναλιών & Κατηγοριών
> *"Φτιάξε μια νέα κατηγορία 'PROJECTS' και μέσα βάλε 2 κανάλια: #general-ideas και #code-reviews."*
> *"Φτιάξε ένα voice channel 'Conference Room' κάτω από το Meeting category."*

### 3. Δημιουργία & Ανάθεση Ρόλων
> *"Φτιάξε έναν ρόλο 'VIP Gold' με χρυσό χρώμα (#FFD700) που να φαίνεται ξεχωριστά στη λίστα μελών."*
> *"Δώσε το ρόλο Moderator στον χρήστη @User."*

### 4. Αποστολή Ανακοινώσεων & Rich Embeds
> *"Στείλε ένα όμορφο embed μήνυμα στο #announcements με τίτλο 'Καλωσορίσατε στο Server!', μπλε χρώμα και τους 5 βασικούς κανόνες."*
> *"Καρφίτσωσε (pin) το μήνυμα των κανόνων στο #rules."*

### 5. Εκτέλεση Οποιουδήποτε Discord API Endpoint
> Μέσω του `discord_raw_api` tool, το Antigravity μπορεί να εκτελέσει **οποιοδήποτε** Discord API endpoint (π.χ. custom emojis, soundboards, auto-moderation rules, webhooks).

---

## 🎮 Προαιρετικό: Live Bot Runner

Αν θέλεις το bot να φαίνεται **Online 24/7** στο server σου με custom status (*"Watching: Antigravity AI"*) και εντολές στο chat (`!antigravity`, `!status`, `!ping`), κάνε διπλό κλικ στο:
```cmd
run_bot.bat
```

---

## 📂 Αρχεία Project
- [`server.py`](file:///C:/Users/nikel/.gemini/antigravity/scratch/discord-antigravity-mcp/server.py): Ο FastMCP server με όλα τα 18 Discord management tools.
- [`setup.py`](file:///C:/Users/nikel/.gemini/antigravity/scratch/discord-antigravity-mcp/setup.py): Το αυτοματοποιημένο wizard εγκατάστασης.
- [`bot_runner.py`](file:///C:/Users/nikel/.gemini/antigravity/scratch/discord-antigravity-mcp/bot_runner.py): Live bot process με presence & εντολές.
- [`setup.ps1`](file:///C:/Users/nikel/.gemini/antigravity/scratch/discord-antigravity-mcp/setup.ps1): PowerShell script για 1-click εκτέλεση setup.
- [`run_bot.ps1`](file:///C:/Users/nikel/.gemini/antigravity/scratch/discord-antigravity-mcp/run_bot.ps1): PowerShell launcher για το live bot.
