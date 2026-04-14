import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime
import os

from keep_alive import keep_alive
keep_alive()

BOT_TOKEN = os.environ.get("TOKEN")
LOG_CHANNEL_ID = 1493250315858743326  # #financial-logs

if not BOT_TOKEN:
    raise ValueError("TOKEN missing")

# ---------------- DATABASE ----------------
conn = sqlite3.connect('transactions.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    amount REAL,
    currency TEXT,
    sender TEXT,
    receiver TEXT,
    timestamp TEXT,
    status TEXT,
    notes TEXT
)
''')
conn.commit()

# ---------------- BOT ----------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- HELPERS ----------------
def add_transaction(t_type, amount, currency, sender, receiver, notes="", status="Pending"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    c.execute('''
        INSERT INTO transactions (type, amount, currency, sender, receiver, timestamp, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (t_type, amount, currency, sender, receiver, timestamp, status, notes))

    conn.commit()
    return c.lastrowid, timestamp

async def send_log(embed, view=None):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        channel = await bot.fetch_channel(LOG_CHANNEL_ID)

    await channel.send(embed=embed, view=view)

# ---------------- APPROVAL VIEW ----------------
class ApprovalView(discord.ui.View):
    def __init__(self, tid):
        super().__init__(timeout=None)
        self.tid = tid

    async def update_message(self, interaction, status, color):
        c.execute("UPDATE transactions SET status=? WHERE id=?", (status, self.tid))
        conn.commit()

        embed = interaction.message.embeds[0]
        embed.color = color
        embed.title = embed.title.replace("(Pending)", f"({status})")

        # disable buttons after action
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only", ephemeral=True)
            return

        await self.update_message(interaction, "Approved", discord.Color.green())

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only", ephemeral=True)
            return

        await self.update_message(interaction, "Denied", discord.Color.red())

# ---------------- READY ----------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print("Sync error:", e)

# ---------------- MODE CHOICES ----------------
mode_choices = [
    app_commands.Choice(name="$", value="$"),
    app_commands.Choice(name="Robux", value="Robux")
]

# ---------------- DEPOSIT ----------------
@bot.tree.command(name="deposit")
@app_commands.choices(mode=mode_choices)
async def deposit(interaction: discord.Interaction, amount: float, mode: app_commands.Choice[str], client: discord.Member, developer: discord.Member, notes: str = ""):

    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be > 0", ephemeral=True)
        return

    currency = mode.value

    tid, timestamp = add_transaction("Deposit", amount, currency, client.name, developer.name, notes)

    embed = discord.Embed(title="📥 Deposit (Pending)", color=discord.Color.orange(), timestamp=datetime.now())
    embed.add_field(name="ID", value=tid)
    embed.add_field(name="From → To", value=f"{client.mention} → {developer.mention}")
    embed.add_field(name="Amount", value=f"{amount} {currency}")
    embed.add_field(name="Notes", value=notes or "None")

    await interaction.response.send_message(embed=embed)
    await send_log(embed, ApprovalView(tid))

# ---------------- PAYOUT ----------------
@bot.tree.command(name="payout")
@app_commands.choices(mode=mode_choices)
async def payout(interaction: discord.Interaction, amount: float, mode: app_commands.Choice[str], developer: discord.Member, notes: str = ""):

    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be > 0", ephemeral=True)
        return

    currency = mode.value

    tid, timestamp = add_transaction("Payout", amount, currency, "Company", developer.name, notes)

    embed = discord.Embed(title="💸 Payout (Pending)", color=discord.Color.gold(), timestamp=datetime.now())
    embed.add_field(name="ID", value=tid)
    embed.add_field(name="To", value=developer.mention)
    embed.add_field(name="Amount", value=f"{amount} {currency}")
    embed.add_field(name="Notes", value=notes or "None")

    await interaction.response.send_message(embed=embed)
    await send_log(embed, ApprovalView(tid))

# ---------------- TRANSFER ----------------
@bot.tree.command(name="transfer")
@app_commands.choices(mode=mode_choices)
async def transfer(interaction: discord.Interaction, amount: float, mode: app_commands.Choice[str], sender: discord.Member, receiver: discord.Member, notes: str = ""):

    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be > 0", ephemeral=True)
        return

    currency = mode.value

    tid, timestamp = add_transaction("Transfer", amount, currency, sender.name, receiver.name, notes)

    embed = discord.Embed(title="🔁 Transfer (Pending)", color=discord.Color.blue(), timestamp=datetime.now())
    embed.add_field(name="ID", value=tid)
    embed.add_field(name="From → To", value=f"{sender.mention} → {receiver.mention}")
    embed.add_field(name="Amount", value=f"{amount} {currency}")
    embed.add_field(name="Notes", value=notes or "None")

    await interaction.response.send_message("✅ Transaction sent to #financial-logs", ephemeral=True)
    await send_log(embed, ApprovalView(tid))

# ---------------- TOTALS ----------------
@bot.tree.command(name="totals")
async def totals(interaction: discord.Interaction):
    c.execute("SELECT receiver, SUM(amount) FROM transactions WHERE type='Payout' AND status='Approved' GROUP BY receiver")
    rows = c.fetchall()

    msg = "No data." if not rows else "\n".join([f"{r[0]}: {round(r[1],2)}" for r in rows])

    embed = discord.Embed(title="📊 Total Earnings", description=msg, color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

# ---------------- RUN ----------------
bot.run(BOT_TOKEN)
