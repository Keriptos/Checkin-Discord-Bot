#Discord Imports
import discord
from discord import app_commands
from discord.ext import commands

#Other Imports
import os
import asyncio
from dotenv import load_dotenv

load_dotenv(".env")
TOKEN: str = os.getenv("discordToken")


bot = commands.Bot(command_prefix = None,  intents = discord.Intents.all()) # command_prefix is not needed for app commands

@bot.event
async def on_ready():    
    print("Bot Ready!") 
    
    # Sync commands to the bot
    try :
        GUILD_ID = discord.Object(id = 1391372922219659435) #This is my server's ID, and I'm only gonna use it for my server
        syncedCommands = await bot.tree.sync(guild= GUILD_ID) #It'll return a list of commands that had been synced
        print(f"Synced {len(syncedCommands)} commands.\n")
        await bot.get_channel(1393987877599445115).send(f"@here Bot is online!") # Announce in the channel(check-ins-out) that bot is online
    except Exception as error:
        print("An error with syncing app commands has occured : ", error)
    


async def load():    
    print("Syncing cogs...")
    for filename in os.listdir("bot/cogs"):
        if filename.endswith(".py"):
            extensionName = f"cogs.{filename[:-3]}" # ":-3" removes 3 characters (.py) starting from behind the filename
            try: 
                await bot.load_extension(extensionName)
            except Exception as error:
                print(f"Failed to load {extensionName}: {error}")

    
async def main():
    async with bot:
        await load()
        await bot.start(TOKEN)


if __name__  == "__main__":
    asyncio.run(main())