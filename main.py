import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta
import os

from keep_alive import keep_alive
keep_alive()

# ---------------- TOKEN SAFETY ----------------
BOT_TOKEN = os.environ.get("TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ TOKEN is missing in Render environment variables!")

LOG_CHANNEL_ID = 1479806557050110146

print("Starting bot...")
print("Token loaded:", bool(BOT_TOKEN))

# ---------------- DATABASE ----------------
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

# ---------------- BOT ----------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- HELPERS ----------------
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
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel is None:
            channel = await bot.fetch_channel(LOG_CHANNEL_ID)

        await channel.send(embed=embed)

    except Exception as e:
        print("Log error:", e)

# ---------------- READY ----------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ---------------- SAFE SYNC COMMAND ----------------
@bot.command()
@commands.is_owner()
async def sync(ctx):
    try:
        if not ctx.guild:
            await ctx.send("❌ Use this in a server, not DMs.")
            return

        guild = discord.Object(id=ctx.guild.id)
        synced = await bot.tree.sync(guild=guild)

        await ctx.send(f"✅ Synced {len(synced)} commands")

    except Exception as e:
        await ctx.send(f"❌ Sync error: {e}")

# ---------------- COMMANDS ----------------
@bot.tree.command(name="deposit")
async def deposit(interaction: discord.Interaction, amount: float, mode: str, client: discord.Member, developer: discord.Member, notes: str = ""):

    currency = "Money" if mode.lower() == "real" else "Robux"
    tid, timestamp = add_transaction("Deposit", amount, currency, mode, client.name, developer.name, notes)

    embed = discord.Embed(title="Deposit Recorded", color=discord.Color.green())
    embed.add_field(name="ID", value=tid)
    embed.add_field(name="From → To", value=f"{client.mention} → {developer.mention}")
    embed.add_field(name="Amount", value=f"{amount} {currency}")
    embed.add_field(name="Time", value=timestamp)

    await interaction.response.send_message(embed=embed)
    await send_log(embed)

@bot.tree.command(name="transfer")
async def transfer(interaction: discord.Interaction, amount: float, mode: str, sender: discord.Member, receiver: discord.Member, notes: str = ""):

    currency = "Money" if mode.lower() == "real" else "Robux"
    tid, timestamp = add_transaction("Transfer", amount, currency, mode, sender.name, receiver.name, notes)

    embed = discord.Embed(title="Transfer Recorded", color=discord.Color.blue())
    embed.add_field(name="ID", value=tid)
    embed.add_field(name="From → To", value=f"{sender.mention} → {receiver.mention}")
    embed.add_field(name="Amount", value=f"{amount} {currency}")
    embed.add_field(name="Time", value=timestamp)

    await interaction.response.send_message(embed=embed)
    await send_log(embed)

@bot.tree.command(name="payout")
async def payout(interaction: discord.Interaction, amount: float, mode: str, developer: discord.Member, notes: str = ""):

    currency = "Money" if mode.lower() == "real" else "Robux"
    tid, timestamp = add_transaction("Payout", amount, currency, mode, "Company", developer.name, notes)

    embed = discord.Embed(title="Payout Recorded", color=discord.Color.gold())
    embed.add_field(name="ID", value=tid)
    embed.add_field(name="To", value=developer.mention)
    embed.add_field(name="Amount", value=f"{amount} {currency}")
    embed.add_field(name="Time", value=timestamp)

    await interaction.response.send_message(embed=embed)
    await send_log(embed)

@bot.tree.command(name="totals")
async def totals(interaction: discord.Interaction):

    c.execute("SELECT receiver, SUM(amount) FROM transactions WHERE type='Payout' GROUP BY receiver")
    rows = c.fetchall()

    msg = "No data." if not rows else "\n".join([f"{r[0]}: {round(r[1],2)}" for r in rows])

    embed = discord.Embed(title="Total Earnings", description=msg, color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="summary")
@app_commands.describe(range="weekly, monthly, 6months, year")
async def summary(interaction: discord.Interaction, range: str = None):

    now = datetime.now()

    if range == "weekly":
        time_filter = now - timedelta(days=7)
    elif range == "monthly":
        time_filter = now - timedelta(days=30)
    elif range == "6months":
        time_filter = now - timedelta(days=180)
    elif range == "year":
        time_filter = now - timedelta(days=365)
    else:
        time_filter = None

    if time_filter:
        c.execute("SELECT SUM(amount) FROM transactions WHERE type='Deposit' AND timestamp >= ?", (time_filter,))
        deposits = c.fetchone()[0] or 0

        c.execute("SELECT SUM(amount) FROM transactions WHERE type='Payout' AND timestamp >= ?", (time_filter,))
        payouts = c.fetchone()[0] or 0
    else:
        c.execute("SELECT SUM(amount) FROM transactions WHERE type='Deposit'")
        deposits = c.fetchone()[0] or 0

        c.execute("SELECT SUM(amount) FROM transactions WHERE type='Payout'")
        payouts = c.fetchone()[0] or 0

    profit = deposits - payouts

    embed = discord.Embed(title="Financial Summary", color=discord.Color.dark_green())
    embed.add_field(name="Deposits", value=round(deposits, 2))
    embed.add_field(name="Payouts", value=round(payouts, 2))
    embed.add_field(name="Net", value=round(profit, 2))

    await interaction.response.send_message(embed=embed)

# ---------------- RUN ----------------
bot.run(BOT_TOKEN)
