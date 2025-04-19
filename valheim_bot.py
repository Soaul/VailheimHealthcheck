import os
from dotenv import load_dotenv
import discord
from discord.ext import tasks, commands
import valve.source.a2s
import socket
from dotenv import load_dotenv

# Load env variables (optionnel sur Railway, mais utile en local)
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
SERVER_ADDRESS = "24.201.105.114"
SERVER_PORT = 2457

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
last_status = None

def check_valheim_server():
    try:
        result = subprocess.check_output([
            "gamedig",
            "--type", "valheim",
            "--host", SERVER_IP,
            "--port", SERVER_PORT
        ])
        data = json.loads(result)
        return {
            "online": True,
            "players": len(data.get("players", []))
        }
    except subprocess.CalledProcessError:
        return {"online": False}

@tasks.loop(seconds=60)
async def monitor_server():
    global last_status
    channel = bot.get_channel(CHANNEL_ID)

    status = check_valheim_server()
    if status["online"] and last_status != "online":
        await channel.send(f"🟢 Serveur Valheim en ligne avec **{status['players']} joueur(s)**.")
        last_status = "online"
    elif not status["online"] and last_status != "offline":
        await channel.send("🔴 Serveur Valheim **hors ligne** ou ne répond pas.")
        last_status = "offline"

@bot.event
async def on_ready():
    print(f"✅ Connecté à Discord en tant que {bot.user}")
    monitor_server.start()

bot.run(TOKEN)