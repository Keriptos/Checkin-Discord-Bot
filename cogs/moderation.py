#Discord Imports
import discord
from discord import app_commands
from discord.ext import commands

#Other Imports
import os
import time

GUILD_ID = discord.Object(id = 1391372922219659435) #This is my server's ID, and I'm only gonna use it for my server
class Moderation(commands.Cog) :
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")


    @app_commands.command(name = "clear", description= "(ADMIN ONLY) Purges a certain amount of text in a channel")    
    @app_commands.checks.has_role("Botministrator")
    @app_commands.describe(amount = "The amount of messages to delete")
    async def purgeMessages(self, interaction: discord.Interaction, amount: int):
        print(f"{interaction.user} is trying to purge {amount} messages")
        commandStartTime = time.perf_counter()
        
        if amount < 1 : # You can't really delete 0 messages or even negative messages can you?
            await interaction.response.send_message(f"{interaction.user.mention} You can't delete less than 1 message")
            return  #return blank so that the function won't run any further
        try :
            await interaction.response.send_message(f"{amount} messages are being deleted. Please wait...", ephemeral=True) # Without this, it'd send an error but it doesn't really matter.
            deletedMessages = await interaction.channel.purge(limit = amount) 
            await interaction.channel.send(f"{interaction.user.mention} has deleted {len(deletedMessages)} message(s).")
        except Exception as error:
            await interaction.response.send_message(f"An error has occured : {error}")
            return
        
        # I think it sent an error when deletedMessages was generating. Because this is asynchronus programming, it can run multiple things at once.
        # So when messages are getting deleted, program doesn't wait for it and line 22 runs. But it doesn't have deletedMessages yet. 
        # So it'd wouldn't run. Hence an error occurs.
        commandEndTime = time.perf_counter()
        print(f"Cleared {len(deletedMessages)} messages in {commandEndTime - commandStartTime:0.4f} seconds\n")

    @purgeMessages.error
    async def purgeError(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingRole) :
            await interaction.response.send_message("You don't have the required role to use this command❗", ephemeral=True)
        else :
            await interaction.response.send_message(f"An error has occured: {error}", ephemeral=True)
            print(f"An error has occured when a user tried to purge messages: {error}\n")


    @app_commands.command(name="sync", description="(ADMIN ONLY) Syncs the app commands")
    @app_commands.checks.has_role("Botministrator")
    async def syncCommands(self, interaction: discord.Interaction):
        commandStartTime = time.perf_counter()
        print(f"{interaction.user} is trying to sync commands")
        await interaction.response.defer() 
        try :
            syncedCommands = await self.bot.tree.sync(guild=GUILD_ID) # Syncs commands to the guild only
            await interaction.followup.send(f"{len(syncedCommands)} commands synced!", ephemeral=True)
        except Exception as error:
            print(f"An error with syncing app commands has occured: {error}\n")
            await interaction.followup.send(f"An error with syncing app commands has occured: {error}")
            return
        
        commandEndTime = time.perf_counter()
        print(f"Synced {len(syncedCommands)} commands in {commandEndTime - commandStartTime:0.4f} seconds\n")
    
    @syncCommands.error
    async def syncError(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingRole) :
            print(f"{interaction.user} tried to sync commands without the required role\n")
            await interaction.response.send_message("You don't have the required role to use this command❗", ephemeral=True)
        else :
            print(f"An error has occured when a user tried to sync commands: {error}\n")
            await interaction.response.send_message(f"An error has occured: {error}", ephemeral=True)

    
    async def cog_autocomplete(self, interaction: discord.Interaction, current: str):
        cogFiles = []
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                extensionName = f"cogs.{filename[:-3]}" # ":-3" removes 3 characters (.py) starting from behind the filename
                cogFiles.append(extensionName)

        return [ # This is the template from the discordpy doc. I only changed the variable name. Don't dare touch it
            app_commands.Choice(name = file, value = file)
            for file in cogFiles if current.lower() in file.lower()
        ][:25] # Discord only allows max of 25 items


    @app_commands.command(name = "load", description= "(ADMIN ONLY) Loads a cog file")
    @app_commands.autocomplete(cogfile = cog_autocomplete) 
    @app_commands.checks.has_role("Botministrator")
    async def load(self, interaction: discord.Interaction, cogfile: str):
        commandStartTime = time.perf_counter()
        print(f"{interaction.user.name} is trying to load a cog file")

        try:
            await self.bot.load_extension(f"{cogfile}")
            await interaction.response.send_message(f"loaded {cogfile} succesfully!", ephemeral=True)
        except Exception as error:
             await interaction.response.send_message(f"Failed to load {cogfile}, {error}!", ephemeral=True)

        commandEndTime = time.perf_counter()
        print(f"Load cogFile command executed in {commandEndTime - commandStartTime:0.4f} seconds\n")

    @load.error
    async def loadError(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingRole) :
            print(f"{interaction.user} tried to load a cog file without the required role\n")
            await interaction.response.send_message("You don't have the required role to use this command❗", ephemeral=True)
        else :
            print(f"An error has occured when a user tried to use the load command: {error}\n")
            await interaction.response.send_message(f"An error has occured: {error}", ephemeral=True)
    
    @app_commands.command(name = "reload", description= "(ADMIN ONLY) Reloads a cog file")
    @app_commands.autocomplete(cogfile = cog_autocomplete) 
    @app_commands.checks.has_role("Botministrator")
    async def reload(self, interaction: discord.Interaction, cogfile: str):
        commandStartTime = time.perf_counter()
        print(f"{interaction.user.name} is trying to reload a cog file")
        await interaction.response.defer()
        try:
            await self.bot.reload_extension(f"{cogfile}")
            await interaction.followup.send(f"Reloaded {cogfile} succesfully!", ephemeral=True)
        except Exception as error:
             await interaction.followup.send(f"Failed to reload {cogfile}, {error}!", ephemeral=True)

        commandEndTime = time.perf_counter()
        print(f"Ended cogReload command in {commandEndTime - commandStartTime:0.4f} seconds\n")

    @reload.error
    async def reloadError(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingRole) :
            print(f"{interaction.user} tried to reload a cog file without the required role\n")
            await interaction.response.send_message("You don't have the required role to use this command❗", ephemeral=True)
        else :
            print(f"An error has occured when a user tried to use the reload command: {error}\n")
            await interaction.response.send_message(f"An error has occured: {error}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot), guild=GUILD_ID)
