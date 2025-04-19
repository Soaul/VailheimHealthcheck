import os
import socket
import struct
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Load env variables (optionnel sur Railway, mais utile en local)
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
SERVER_IP = "24.201.105.114"
SERVER_PORT = 2457

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
last_status = None

def query_valheim_server(ip, port, timeout=3):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)

        # A2S_INFO request
        request_data = b'\xFF\xFF\xFF\xFF\x54Source Engine Query\x00'
        sock.sendto(request_data, (ip, port))

        data, _ = sock.recvfrom(4096)
        if data[4] != 0x49:
            return {"online": False}

        # Parse number of players (Byte 6 = protocol, Byte 7+ = name etc.)
        # We skip to the player count which is the last byte before the last null bytes
        # This is fragile parsing; better than nothing
        players = data.count(b'\x00')  # crude fallback
        return {"online": True, "players": max(players - 3, 0)}

    except socket.timeout:
        return {"online": False}
    except Exception as e:
        print(f"Erreur: {e}")
        return {"online": False}
    finally:
        sock.close()

@tasks.loop(seconds=60)
async def monitor_server():
    global last_status
    channel = bot.get_channel(CHANNEL_ID)
    status = query_valheim_server(SERVER_IP, SERVER_PORT)

    if status["online"] and last_status != "online":
        await channel.send(f"🟢 Serveur Valheim en ligne avec environ **{status['players']} joueur(s)**.")
        last_status = "online"
    elif not status["online"] and last_status != "offline":
        await channel.send("🔴 Serveur Valheim **hors ligne** ou ne répond pas.")
        last_status = "offline"

@bot.command()
async def status(ctx):
    """Commande pour vérifier le serveur Valheim."""
    status = query_valheim_server(SERVER_IP, SERVER_PORT)
    if status["online"]:
        await ctx.send(f"🟢 Serveur Valheim en ligne avec environ **{status['players']} joueur(s)**.")
    else:
        await ctx.send("🔴 Serveur Valheim **hors ligne** ou ne répond pas.")

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")
    monitor_server.start()

bot.run(TOKEN)