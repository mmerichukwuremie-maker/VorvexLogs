import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta
import os

# --- KEEP ALIVE ---
from keep_alive import keep_alive
keep_alive()

# --- CONFIG ---
BOT_TOKEN = os.getenv("TOKEN")
LOG_CHANNEL_ID = 1479806557050110146  # PUT YOUR CHANNEL ID

# --- DATABASE ---
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

# --- HELPERS ---
def add_transaction(t_type, amount, currency, mode, sender, receiver, notes=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO transactions (type, amount, currency, mode, sender, receiver, timestamp, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (t_type, amount, currency, mode, sender, receiver, timestamp, "Completed", notes))
    conn.commit()
    return c.lastrowid, timestamp

async def send_log(embed):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(LOG_CHANNEL_ID)
    await channel.send(embed=embed)

# --- READY ---
@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} commands")
    print(f"Logged in as {bot.user}")

# ======================
# 💰 DEPOSIT
# ======================
@bot.tree.command(name="deposit", description="Log a deposit")
@app_commands.describe(amount="Amount", mode="Robux or Real Money", client="Client", developer="Developer", notes="Notes")
async def deposit(interaction: discord.Interaction, amount: float, mode: str, client: discord.Member, developer: discord.Member, notes: str = ""):

    currency = "Money" if mode == "Real Money" else "Robux"
    tid, timestamp = add_transaction("Deposit", amount, currency, mode, client.name, developer.name, notes)

    embed = discord.Embed(title="Deposit Recorded", color=discord.Color.green())
    embed.add_field(name="ID", value=tid)
    embed.add_field(name="From → To", value=f"{client.mention} → {developer.mention}")
    embed.add_field(name="Amount", value=f"{amount} {currency}")
    embed.add_field(name="Time", value=timestamp)

    await interaction.response.send_message(embed=embed)
    await send_log(embed)

# ======================
# 🔄 TRANSFER
# ======================
@bot.tree.command(name="transfer", description="Log a transfer")
@app_commands.describe(amount="Amount", mode="Robux or Real Money", sender="Sender", receiver="Receiver", notes="Notes")
async def transfer(interaction: discord.Interaction, amount: float, mode: str, sender: discord.Member, receiver: discord.Member, notes: str = ""):

    currency = "Money" if mode == "Real Money" else "Robux"
    tid, timestamp = add_transaction("Transfer", amount, currency, mode, sender.name, receiver.name, notes)

    embed = discord.Embed(title="Transfer Recorded", color=discord.Color.blue())
    embed.add_field(name="ID", value=tid)
    embed.add_field(name="From → To", value=f"{sender.mention} → {receiver.mention}")
    embed.add_field(name="Amount", value=f"{amount} {currency}")
    embed.add_field(name="Time", value=timestamp)

    await interaction.response.send_message(embed=embed)
    await send_log(embed)

# ======================
# 🏦 PAYOUT
# ======================
@bot.tree.command(name="payout", description="Log a payout")
@app_commands.describe(amount="Amount", mode="Robux or Real Money", developer="Developer", notes="Notes")
async def payout(interaction: discord.Interaction, amount: float, mode: str, developer: discord.Member, notes: str = ""):

    currency = "Money" if mode == "Real Money" else "Robux"
    tid, timestamp = add_transaction("Payout", amount, currency, mode, "Vornex Corp", developer.name, notes)

    embed = discord.Embed(title="Payout Recorded", color=discord.Color.gold())
    embed.add_field(name="ID", value=tid)
    embed.add_field(name="To", value=developer.mention)
    embed.add_field(name="Amount", value=f"{amount} {currency}")
    embed.add_field(name="Time", value=timestamp)

    await interaction.response.send_message(embed=embed)
    await send_log(embed)

# ======================
# 📊 TOTALS
# ======================
@bot.tree.command(name="totals", description="View earnings")
@app_commands.describe(developer="Optional developer")
async def totals(interaction: discord.Interaction, developer: discord.Member = None):

    if developer:
        c.execute("SELECT SUM(amount) FROM transactions WHERE receiver=? AND type='Payout'", (developer.name,))
        total = c.fetchone()[0] or 0
        msg = f"{developer.mention}: {total}"
    else:
        c.execute("SELECT receiver, SUM(amount) FROM transactions WHERE type='Payout' GROUP BY receiver")
        rows = c.fetchall()
        msg = "\n".join([f"{r[0]}: {r[1]}" for r in rows]) or "No data"

    embed = discord.Embed(title="Total Earnings", description=msg, color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

# ======================
# 📊 SUMMARY
# ======================
@bot.tree.command(name="summary", description="Financial summary")
async def summary(interaction: discord.Interaction):

    c.execute("SELECT SUM(amount) FROM transactions WHERE type='Deposit'")
    deposits = c.fetchone()[0] or 0

    c.execute("SELECT SUM(amount) FROM transactions WHERE type='Payout'")
    payouts = c.fetchone()[0] or 0

    profit = deposits - payouts

    embed = discord.Embed(title="Financial Summary", color=discord.Color.dark_green())
    embed.add_field(name="Deposits", value=deposits)
    embed.add_field(name="Payouts", value=payouts)
    embed.add_field(name="Net", value=profit)

    await interaction.response.send_message(embed=embed)

# --- RUN ---
bot.run(BOT_TOKEN)
