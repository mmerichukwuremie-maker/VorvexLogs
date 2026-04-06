import discord
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta
import os

from keep_alive import keep_alive
keep_alive()

# --- CONFIG ---
BOT_TOKEN = os.getenv("TOKEN")
LOG_CHANNEL_ID = 1479806557050110146
ALLOWED_CHANNEL_ID = 1479806557050110146
GUILD_ID = 1479805335463268425

# --- DB ---
conn = sqlite3.connect('transactions.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    amount REAL,
    currency TEXT,
    mode TEXT,
    sender TEXT,
    receiver TEXT,
    timestamp TEXT,
    status TEXT,
    notes TEXT
)
''')
conn.commit()

# --- BOT ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
guild = discord.Object(id=GUILD_ID)

# --- HELPERS ---
def is_allowed(interaction):
    return interaction.channel_id == ALLOWED_CHANNEL_ID

def add_transaction(t_type, amount, currency, mode, sender, receiver, notes=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO transactions (type, amount, currency, mode, sender, receiver, timestamp, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (t_type, amount, currency, mode, sender, receiver, timestamp, "Completed", notes))
    conn.commit()
    return c.lastrowid, timestamp

async def send_log(embed):
    try:
        channel = bot.get_channel(LOG_CHANNEL_ID) or await bot.fetch_channel(LOG_CHANNEL_ID)
        await channel.send(embed=embed)
    except Exception as e:
        print("Log error:", e)

# --- READY ---
@bot.event
async def on_ready():
    await bot.tree.sync(guild=guild)
    print(f"Logged in as {bot.user}")

# --- ERROR HANDLER ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    print("Error:", error)
    if interaction.response.is_done():
        await interaction.followup.send("An error occurred.", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred.", ephemeral=True)

# ======================
# 💰 DEPOSIT
# ======================
@bot.tree.command(guild=guild)
async def deposit(interaction: discord.Interaction, amount: float, mode: str, client: discord.Member, developer: discord.Member, notes: str = ""):
    await interaction.response.defer()

    if not is_allowed(interaction):
        await interaction.followup.send("Use in financial channel.", ephemeral=True)
        return

    currency = "Money" if mode.lower() == "real money" else "Robux"

    tid, timestamp = add_transaction("Deposit", amount, currency, mode, client.name, developer.name, notes)

    embed = discord.Embed(title="Deposit Recorded", color=discord.Color.green())
    embed.add_field(name="ID", value=tid)
    embed.add_field(name="From → To", value=f"{client.mention} → {developer.mention}")
    embed.add_field(name="Amount", value=f"{amount} {currency}")
    embed.add_field(name="Time", value=timestamp)

    await interaction.followup.send(embed=embed)
    await send_log(embed)

# ======================
# 🔄 TRANSFER
# ======================
@bot.tree.command(guild=guild)
async def transfer(interaction: discord.Interaction, amount: float, mode: str, sender: discord.Member, receiver: discord.Member, notes: str = ""):
    await interaction.response.defer()

    if not is_allowed(interaction):
        await interaction.followup.send("Use in financial channel.", ephemeral=True)
        return

    currency = "Money" if mode.lower() == "real money" else "Robux"

    tid, timestamp = add_transaction("Transfer", amount, currency, mode, sender.name, receiver.name, notes)

    embed = discord.Embed(title="Transfer Recorded", color=discord.Color.blue())
    embed.add_field(name="ID", value=tid)
    embed.add_field(name="From → To", value=f"{sender.mention} → {receiver.mention}")
    embed.add_field(name="Amount", value=f"{amount} {currency}")
    embed.add_field(name="Time", value=timestamp)

    await interaction.followup.send(embed=embed)
    await send_log(embed)

# ======================
# 🏦 PAYOUT
# ======================
@bot.tree.command(guild=guild)
async def payout(interaction: discord.Interaction, amount: float, mode: str, developer: discord.Member, notes: str = ""):
    await interaction.response.defer()

    if not is_allowed(interaction):
        await interaction.followup.send("Use in financial channel.", ephemeral=True)
        return

    currency = "Money" if mode.lower() == "real money" else "Robux"

    tid, timestamp = add_transaction("Payout", amount, currency, mode, "Vornex Corp", developer.name, notes)

    embed = discord.Embed(title="Payout Recorded", color=discord.Color.gold())
    embed.add_field(name="ID", value=tid)
    embed.add_field(name="From → To", value=f"Vornex Corp → {developer.mention}")
    embed.add_field(name="Amount", value=f"{amount} {currency}")
    embed.add_field(name="Time", value=timestamp)

    await interaction.followup.send(embed=embed)
    await send_log(embed)

# ======================
# 📊 SUMMARY
# ======================
@bot.tree.command(guild=guild)
async def summary(interaction: discord.Interaction):
    await interaction.response.defer()

    if not is_allowed(interaction):
        await interaction.followup.send("Wrong channel.", ephemeral=True)
        return

    c.execute("SELECT SUM(amount) FROM transactions WHERE type='Deposit'")
    deposits = c.fetchone()[0] or 0

    c.execute("SELECT SUM(amount) FROM transactions WHERE type='Payout'")
    payouts = c.fetchone()[0] or 0

    profit = deposits - payouts

    embed = discord.Embed(title="Financial Summary", color=discord.Color.dark_green())
    embed.add_field(name="Deposits", value=deposits)
    embed.add_field(name="Payouts", value=payouts)
    embed.add_field(name="Net", value=profit)

    await interaction.followup.send(embed=embed)

# --- RUN ---
bot.run(BOT_TOKEN)
