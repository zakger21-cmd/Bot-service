import os
import asyncio
import threading
import discord
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask

from config import GUILD_ID

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# ============================================================
# MINI SERVEUR WEB (nécessaire pour Render + UptimeRobot)
# ============================================================
web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Le bot est en ligne."


def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user} (ID: {bot.user.id})")
    try:
        guild = discord.Object(id=GUILD_ID)

        # 1. Copie les commandes vers ton serveur (instantané, pendant qu'elles existent encore)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"🔄 {len(synced)} commande(s) slash synchronisée(s) sur le serveur.")

        # 2. Nettoie les anciennes commandes globales (évite les doublons)
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
    except Exception as e:
        print(f"Erreur de synchronisation des commandes : {e}")


async def main():
    threading.Thread(target=run_web_server, daemon=True).start()
    async with bot:
        await bot.load_extension("cogs.common")
        await bot.load_extension("cogs.orders")
        await bot.load_extension("cogs.support")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
