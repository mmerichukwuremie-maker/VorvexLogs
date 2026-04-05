import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime
import os

# --- KEEP ALIVE ---
from keep_alive import keep_alive
keep_alive()

# --- CONFIG ---
BOT_TOKEN = os.getenv("TOKEN")

# --- Database Setup ---
conn = sqlite3.connect('transactions.db')
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    mode TEXT NOT NULL,
    sender TEXT NOT NULL,
    receiver TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'Yes',
    notes TEXT
)
''')
conn.commit()

# --- Bot Setup ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Helper ---
def add_transaction(t_type, amount, currency, mode, sender, receiver, notes=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO transactions (type, amount, currency, mode, sender, receiver, timestamp, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (t_type, amount, currency, mode, sender, receiver, timestamp, notes))
    conn.commit()
    return c.lastrowid, timestamp

# --- Ready ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# --- Commands ---

# Deposit
@bot.tree.command(name="deposit", description="Log a deposit")
@app_commands.describe(amount="Amount", mode="Robux or Real Money", client="Client", developer="Developer", notes="Notes")
@app_commands.choices(mode=[
    app_commands.Choice(name="Robux", value="Robux"),
    app_commands.Choice(name="Real Money", value="Real Money"),
])
async def deposit(interaction: discord.Interaction, amount: float, mode: app_commands.Choice[str], client: discord.Member, developer: discord.Member, notes: str = ""):
    
    currency = "Money" if mode.value == "Real Money" else "Robux"

    tid, timestamp = add_transaction("Deposit", amount, currency, mode.value, client.name, developer.name, notes)

    embed = discord.Embed(title="💰 Deposit Logged", color=discord.Color.green())
    embed.add_field(name="ID", value=str(tid))
    embed.add_field(name="Client → Dev", value=f"{client.mention} → {developer.mention}")
    embed.add_field(name="Amount", value=f"{amount} {currency} ({mode.value})")
    embed.add_field(name="Time", value=timestamp)
    if notes:
        embed.add_field(name="Notes", value=notes, inline=False)

    await interaction.response.send_message(embed=embed)

# Transfer
@bot.tree.command(name="transfer", description="Log a transfer")
@app_commands.describe(amount="Amount", mode="Robux or Real Money", sender="Sender", receiver="Receiver", notes="Notes")
@app_commands.choices(mode=[
    app_commands.Choice(name="Robux", value="Robux"),
    app_commands.Choice(name="Real Money", value="Real Money"),
])
async def transfer(interaction: discord.Interaction, amount: float, mode: app_commands.Choice[str], sender: discord.Member, receiver: discord.Member, notes: str = ""):

    currency = "Money" if mode.value == "Real Money" else "Robux"

    tid, timestamp = add_transaction("Transfer", amount, currency, mode.value, sender.name, receiver.name, notes)

    embed = discord.Embed(title="🔄 Transfer Logged", color=discord.Color.blue())
    embed.add_field(name="ID", value=str(tid))
    embed.add_field(name="Sender → Receiver", value=f"{sender.mention} → {receiver.mention}")
    embed.add_field(name="Amount", value=f"{amount} {currency} ({mode.value})")
    embed.add_field(name="Time", value=timestamp)
    if notes:
        embed.add_field(name="Notes", value=notes, inline=False)

    await interaction.response.send_message(embed=embed)

# Payout
@bot.tree.command(name="payout", description="Log a payout")
@app_commands.describe(amount="Amount", mode="Robux or Real Money", developer="Developer", notes="Notes")
@app_commands.choices(mode=[
    app_commands.Choice(name="Robux", value="Robux"),
    app_commands.Choice(name="Real Money", value="Real Money"),
])
async def payout(interaction: discord.Interaction, amount: float, mode: app_commands.Choice[str], developer: discord.Member, notes: str = ""):

    currency = "Money" if mode.value == "Real Money" else "Robux"

    tid, timestamp = add_transaction("Payout", amount, currency, mode.value, "Vornex Corp", developer.name, notes)

    embed = discord.Embed(title="🏦 Payout Logged", color=discord.Color.gold())
    embed.add_field(name="ID", value=str(tid))
    embed.add_field(name="Corp → Dev", value=f"Vornex Corp → {developer.mention}")
    embed.add_field(name="Amount", value=f"{amount} {currency} ({mode.value})")
    embed.add_field(name="Time", value=timestamp)
    if notes:
        embed.add_field(name="Notes", value=notes, inline=False)

    await interaction.response.send_message(embed=embed)

# View
@bot.tree.command(name="view", description="View last 10 transactions")
async def view(interaction: discord.Interaction):

    c.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 10")
    rows = c.fetchall()

    if rows:
        msg = ""
        for r in rows:
            msg += f"ID:{r[0]} | {r[1]} | {r[2]} {r[3]} | {r[5]} → {r[6]} | {r[7]}\n"
        embed = discord.Embed(title="📋 Transactions", description=msg, color=discord.Color.purple())
    else:
        embed = discord.Embed(title="📋 Transactions", description="No data.", color=discord.Color.red())

    await interaction.response.send_message(embed=embed)

# --- Run Bot ---
bot.run(BOT_TOKEN)