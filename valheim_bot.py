import os
from dotenv import load_dotenv
import discord
from discord.ext import tasks, commands
import valve.source.a2s
import socket

# Load env variables (optionnel sur Railway, mais utile en local)
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
SERVER_ADDRESS = ("24.201.105.114", 2456)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

last_status = None

@tasks.loop(seconds=60)
async def check_server():
    global last_status
    channel = bot.get_channel(CHANNEL_ID)

    try:
        with valve.source.a2s.ServerQuerier(SERVER_ADDRESS, timeout=3) as server:
            info = server.info()
            players = info["player_count"]
            if last_status != "online":
                await channel.send(f"🟢 Serveur Valheim en ligne avec **{players} joueur(s)**.")
                last_status = "online"
    except (valve.source.a2s.NoResponseError, socket.timeout):
        if last_status != "offline":
            await channel.send("🔴 Serveur Valheim **hors ligne** ou ne répond pas.")
            last_status = "offline"

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    check_server.start()

bot.run(TOKEN)