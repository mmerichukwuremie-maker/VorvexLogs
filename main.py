import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta
import os

from keep_alive import keep_alive
keep_alive()

BOT_TOKEN = os.getenv("TOKEN")
LOG_CHANNEL_ID = 1479806557050110146

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


def get_time_filter(range):
    now = datetime.now()

    if range == "weekly":
        return now - timedelta(days=7)
    elif range == "monthly":
        return now - timedelta(days=30)
    elif range == "6months":
        return now - timedelta(days=180)
    elif range == "year":
        return now - timedelta(days=365)
    else:
        return None


async def send_log(embed):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(LOG_CHANNEL_ID)

    await channel.send(embed=embed)


# --- READY ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


# ======================
# MANUAL SYNC (IMPORTANT FIX)
# ======================
@bot.command()
@commands.is_owner()
async def sync(ctx):
    """Manually sync slash commands (run only when needed)"""
    guild = discord.Object(id=ctx.guild.id)
    synced = await bot.tree.sync(guild=guild)
    await ctx.send(f"✅ Synced {len(synced)} commands (guild only)")


# ======================
# DEPOSIT
# ======================
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


# ======================
# TRANSFER
# ======================
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


# ======================
# PAYOUT
# ======================
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


# ======================
# DELETE
# ======================
@bot.tree.command(name="delete")
async def delete(interaction: discord.Interaction, transaction_id: int, user: discord.Member):

    c.execute("SELECT receiver FROM transactions WHERE id=?", (transaction_id,))
    result = c.fetchone()

    if not result:
        await interaction.response.send_message("Transaction not found.", ephemeral=True)
        return

    if result[0] != user.name:
        await interaction.response.send_message("User mismatch. Cannot delete.", ephemeral=True)
        return

    c.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
    conn.commit()

    await interaction.response.send_message(f"Transaction {transaction_id} deleted.")


# ======================
# TOTALS
# ======================
@bot.tree.command(name="totals")
async def totals(interaction: discord.Interaction):

    c.execute("SELECT receiver, SUM(amount) FROM transactions WHERE type='Payout' GROUP BY receiver")
    rows = c.fetchall()

    if not rows:
        msg = "No data."
    else:
        msg = "\n".join([f"{r[0]}: {round(r[1],2)}" for r in rows])

    embed = discord.Embed(title="Total Earnings", description=msg, color=discord.Color.green())
    await interaction.response.send_message(embed=embed)


# ======================
# SUMMARY
# ======================
@bot.tree.command(name="summary")
@app_commands.describe(range="weekly, monthly, 6months, year")
async def summary(interaction: discord.Interaction, range: str = None):

    time_filter = get_time_filter(range)

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

    if range:
        embed.set_footer(text=f"Range: {range}")

    await interaction.response.send_message(embed=embed)


# --- RUN ---
bot.run(BOT_TOKEN)
