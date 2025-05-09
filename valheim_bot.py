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

        # Send A2S_INFO request
        request = b'\xFF\xFF\xFF\xFF\x54Source Engine Query\x00'
        sock.sendto(request, (ip, port))
        data, _ = sock.recvfrom(4096)

        # Handle challenge response
        if data[4] == 0x41:
            challenge_token = data[5:9]
            print(f"🔐 Challenge token reçu : {challenge_token.hex()}")

            # Rebuild request with challenge
            request = b'\xFF\xFF\xFF\xFF\x54Source Engine Query\x00' + challenge_token
            sock.sendto(request, (ip, port))
            data, _ = sock.recvfrom(4096)

        if data[4] != 0x49:
            print(f"⚠️ Mauvais type de réponse : {data[4]}")
            return {"online": False}

        # Parse A2S_INFO packet
        offset = 5  # skip header and type

        def read_string():
            nonlocal offset
            end = data.index(b'\x00', offset)
            s = data[offset:end].decode('utf-8', errors='ignore')
            offset = end + 1
            return s

        protocol = data[offset]
        offset += 1
        name = read_string()
        map_name = read_string()
        folder = read_string()
        game = read_string()
        offset += 2  # game ID (ushort)

        players = data[offset]
        max_players = data[offset + 1]

        print(f"✅ {players}/{max_players} joueur(s) — {name} sur {map_name}")
        return {
            "online": True,
            "players": players,
            "max_players": max_players,
            "name": name,
            "map": map_name
        }

    except socket.timeout:
        print("⏱️ Timeout — pas de réponse à la requête finale avec challenge")
        return {"online": False}
    except Exception as e:
        print(f"💥 Erreur fatale : {e}")
        return {"online": False}
    finally:
        sock.close()

@tasks.loop(seconds=60)
async def monitor_server():
    global last_status
    channel = bot.get_channel(CHANNEL_ID)
    status = query_valheim_server(SERVER_IP, SERVER_PORT)

    if status["online"]:
        new_status = f"🟢 Serveur UP — {status['players']} joueur(s)"
        if last_status != "online":
            await channel.send(f"🟢 Serveur Valheim en ligne avec **{status['players']} joueur(s)**.")
        await bot.change_presence(activity=discord.Game(new_status))
        last_status = "online"
    else:
        if last_status != "offline":
            await channel.send("🔴 Serveur Valheim **hors ligne** ou ne répond pas.")
        await bot.change_presence(activity=discord.Game("🔴 Serveur DOWN"))
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