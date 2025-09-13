import discord
from discord.ext import commands
from discord import app_commands
import random
from typing import List

class generalCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")
    
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):    
        channel = member.guild.system_channel
        if channel is not None: 
            await channel.send(f'Welcome {member.mention}.')

    @app_commands.command(name = "ping", description = "Latency test from you to the bot")
    async def ping(self, interaction: discord.Interaction):
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


    @app_commands.command(name = "remind", description = "Mention members with an optional message")
    @app_commands.describe(members = "Select one or more members to mention", message = "Custom reminder message (optional)")
    async def remind(
        self,
        interaction: discord.Interaction,
        members: discord.Member, 
        message : str = None
        ):
        
        if not members :
            await interaction.response.send_message("You must mention at least one member❗", ephemeral= True) #error mesage
            return  #returns nothing ~ as an error. Then the message above will appear only to you
        defaultMessages = [
            "GET YOUR SHIT DONEEEE 🔥🔥❗❗ ",
            "Don't forget to do your thing ❗",
            "You know what time it is? 👀"
        ]
        
        if message is None or message == "" :
            msg = random.choice(defaultMessages)
        else :
            msg = message # When user types something it saves into message, and uses that message.
        try :
            await interaction.response.send_message(f"{members.mention} {msg}") 
        except Exception as e:
            print(f"Failed to send message {e}")

    
async def setup(bot: commands.Bot):
    GUILD_ID = discord.Object(id = 1391372922219659435) #This is my server's ID, and I'm only gonna use it for my server
    await bot.add_cog(generalCommands(bot), guild = GUILD_ID)


   