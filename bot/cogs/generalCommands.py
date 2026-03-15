#Discord Imports
import discord
from discord.ext import commands
from discord import app_commands

#Other Imports
from bot.helpers.utils import loadJSON
from bot.config_builder import ConfigDTO
import time
import random

CFG = ConfigDTO()
class generalCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")
            
    @app_commands.command(name = "ping", description = "Latency test from you to the bot")
    async def ping(self, interaction: discord.Interaction):
        commandStartTime = time.perf_counter()

        pingEmbed = discord.Embed(title = "Latency Test", color = discord.Color.blue())
        pingEmbed.add_field (
            name = f"{self.bot.user.name}'s Latency (ms) : ",
            value = f"{round(self.bot.latency * 1000)} ms", 
            inline = True
        )
        pingEmbed.set_footer(
            text = f"Requested by {interaction.user.name}",
            icon_url= interaction.user.avatar
        )

        await interaction.response.send_message(embed = pingEmbed)
        commandEndTime = time.perf_counter()
        print(f"Ping command executed in {commandEndTime - commandStartTime:0.4f} seconds\n") #Track how long the command takes to execute


    @app_commands.command(name = "test_remind", description = "Mention members with an optional message")
    @app_commands.describe(members = "Select one or more members to mention", message = "Custom reminder message (optional)")
    async def test_remind(
        self,
        interaction: discord.Interaction,
        members: discord.Member, 
        message : str = None
        ):

        print(f"{interaction.user} is trying to remind {members} with message: {message}")

        commandStartTime = time.perf_counter() 
        time_checkedin = loadJSON(CFG.CHECKIN_FILE)

        if not members :
            await interaction.response.send_message("You must mention at least one member❗", ephemeral= True) #error mesage
            return  #returns nothing ~ as an error. Then the message above will appear only to you
        defaultMessages = [
            "GET YOUR SHIT DONEEEE 🔥🔥❗❗ ",
            "Don't forget to do your thing ❗",
            "You know what time it is? 👀",
            "Get yo ass up an GET YOUR SHIT DONE ❗❗"

        ]
        
        checkin_messages = [
            "Don't forget to CHECKOUT ❗"        
        ]
        if message is None or message == "":
            # If user that was reminded has checked in, print checked-in messages.
            # Else, print default messages
            if members.id in time_checkedin: 
                msg = random.choice(checkin_messages)
            else:
                msg = random.choice(defaultMessages)
        else:
            msg = message # When user types something it saves into message, and uses that message.
        try:
            await interaction.response.send_message(f"{members.mention} {msg}") 
        except Exception as e:
            print(f"Failed to send message {e}\n")

        commandEndTime = time.perf_counter()
        print(f"Remind command executed in {commandEndTime - commandStartTime:0.4f} seconds\n") #Track how long the command takes to execute

    
async def setup(bot: commands.Bot):
    _GUILD_ID = discord.Object(id = CFG.GUILD_ID)
    await bot.add_cog(generalCommands(bot), guild = _GUILD_ID)


   