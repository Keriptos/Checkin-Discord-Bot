import discord
from discord.ext import commands
from discord import app_commands

class Moderation(commands.Cog) :
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener() 
    async def on_ready(self) : 
        print(f"{__name__} is ready!")


    @app_commands.command(name = "clear", description= "Purges a certain amount of text in a channel")    
    @app_commands.checks.has_permissions(manage_messages = True)
    @app_commands.describe(amount = "The amount of messages to delete")
    async def purgeMessages(self, interaction: discord.Interaction, amount: int):
        if amount < 1 : # You can't really delete 0 messages or even negative messages can you?
            await interaction.response.send_message(f"{interaction.user.mention} You can't delete less than 1 message")
            return  #return blank so that the function won't run any further
        await interaction.response.send_message(f"{amount} messages are being deleted. Please wait...", ephemeral=True) # Without this, it'd send an error but it doesn't really matter.
        deletedMessages = await interaction.channel.purge(limit = amount) 
        await interaction.channel.send(f"{interaction.user.mention} has deleted {len(deletedMessages)} message(s).")
        # I think it sent an error when deletedMessages was generating. Because this is asynchronus programming, it can run multiple things at once.
        # So when messages are getting deleted, program doesn't wait for it and line 22 runs. But it doesn't have deletedMessages yet. 
        # So it'd wouldn't run. Hence an error occurs.


async def setup(bot: commands.Bot):
    GUILD_ID = discord.Object(id = 1391372922219659435) #This is my server's ID, and I'm only gonna use it for my server
    await bot.add_cog(Moderation(bot), guild = GUILD_ID)
