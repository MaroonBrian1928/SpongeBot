import json
import os
import random
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def load_data():
    with open("spongebob_content.json", "r", encoding="utf-8") as f:
        return json.load(f)

DATA = load_data()

def pick_quote() -> str:
    return random.choice(DATA["quotes"])

def pick_meme_url() -> str:
    return random.choice(DATA["memes"])

@client.event
async def on_ready():
    # Sync commands to one guild for fast iteration
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
        print(f"Synced to guild {GUILD_ID}")
    else:
        await tree.sync()
        print("Synced globally")

    print(f"Logged in as {client.user} (id={client.user.id})")

@tree.command(name="spongebob", description="Send a SpongeBob meme and/or quote.")
@app_commands.describe(kind="What to send: both, meme, or quote")
@app_commands.choices(kind=[
    app_commands.Choice(name="both", value="both"),
    app_commands.Choice(name="meme", value="meme"),
    app_commands.Choice(name="quote", value="quote"),
])
async def spongebob(interaction: discord.Interaction, kind: app_commands.Choice[str]):
    kind_val = kind.value if kind else "both"

    if kind_val == "quote":
        await interaction.response.send_message(pick_quote())
        return

    if kind_val == "meme":
        await interaction.response.send_message(pick_meme_url())
        return

    # both
    quote = pick_quote()
    meme = pick_meme_url()
    await interaction.response.send_message(f"{quote}\n{meme}")

if not TOKEN:
    raise SystemExit("Missing DISCORD_TOKEN in .env")

client.run(TOKEN)