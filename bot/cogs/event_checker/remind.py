import discord
from discord.ext import tasks, commands

# Other Imports
import time
import random
from bot.config_builder import ConfigDTO 
import datetime

# Globals
CFG = ConfigDTO()

# Construct the time list to continously check. UTC +00:00
g_remind_time: list = [datetime.time(hour=i, tzinfo=datetime.timezone.utc) for i in range(0,24)] 
g_remind_time.extend([datetime.time(hour=i, minute=15, tzinfo= datetime.timezone.utc) for i in range (0,24)])
g_remind_time.extend([datetime.time(hour=i, minute=30, tzinfo= datetime.timezone.utc) for i in range (0,24)])
g_remind_time.sort()


class DailyRemind(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot        
        self.reminding.start()

    def cog_unload(self):
        self.reminding.cancel()


    @tasks.loop(time=g_remind_time)
    async def reminding(self):
        start = time.perf_counter()
        curr_time = datetime.datetime.now(tz=datetime.timezone.utc)
        curr_time_local = datetime.datetime.astimezone(curr_time) # Bot's local timezone
        print(f"Curr_time UTC = {curr_time}")
        print(f"Local time = {curr_time_local}")
        defaultMessages = [
            "GET YOUR SHIT DONEEEE 🔥🔥❗❗ ",
            "Don't forget to do your thing ❗",
            "You know what time it is? 👀",
            "Get yo ass up and GET YOUR SHIT DONE ❗❗",
            "'1 more match', that's what they all say...🙄",
            "Stop doomscrolling.",
            "You know you need to get a JOB later right❓",
            "LOCK IN TWINNN ❗❗❗",
            "Remember what you signed up for ❗",
            "Is it worth skipping today's work and double it to tomorrow ❓"
            "Your future self will thank you",
            "Let this be the push you need"
        ]
        guild = self.bot.get_guild(CFG.GUILD_ID)
        role_name = f"{'0' if curr_time.hour < 10 else ''}{curr_time.hour}:{curr_time.minute}{'0' if curr_time.minute == 0 else ''}"
        try:
            role_to_ping = discord.utils.get(guild.roles, name= role_name)
            if role_to_ping.members:
                checkin_channel = self.bot.get_channel(1393987877599445115) # replace the channel id later
                await checkin_channel.send(content=f"{role_to_ping.mention} {random.choice(defaultMessages)}")
                end = time.perf_counter()
                print(f"Reminder took {end-start:.8f} seconds\n")
            else:
                print(f"No one has this role, '{role_name}'\n")
        except Exception as error: # Could be triggered by the discord.utils.get() --> could return None or accessing members from a NoneType                    
            print(curr_time, curr_time_local, role_name)
            print(f"Role does not exist? | Error: {error}\n")
            
    @reminding.before_loop
    async def before_reminding(self):
        print("reminding task waiting...")
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):    
    GUILD_ID = discord.Object(id = CFG.GUILD_ID)
    await bot.add_cog(DailyRemind(bot), guild= GUILD_ID)