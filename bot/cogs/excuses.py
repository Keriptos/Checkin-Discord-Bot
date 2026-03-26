# Discord Imports
import discord 
from discord import app_commands
from discord.ext import commands

# Google Sheets Related Imports
from bot.services.sheetService import sheetManager

# Other Imports
import bot.helpers.utils as utls
from bot.config_builder import ConfigDTO
import typing
import enum
import datetime; from datetime import timedelta
import time 

# Globals
CFG = ConfigDTO()

class LabelsMenu(discord.ui.Select):
    """ A menu to use other labels to fill in the activity days.
        THIS WILL FILL EVERY ACTIVITY DAY
    """
    def __init__(self, userID: str, activity: str):
        self.chosenActivity = activity
        self.userID: str = userID
        self.usersData: dict = utls.loadJSON(CFG.USERS_FILE)
        self.username: str = self.usersData[userID]['username']
        self.userFormat: str = self.usersData[userID]['format']
        self.registeredActivity: list = self.usersData[userID]['activities']



        options = []
        # Manual option appending because I want custom descriptions
        options.append(
            discord.SelectOption(
                label = "ADA URUSAN",
                description = f"You've done something else for your productive session"
            )
        )
        options.append(
            discord.SelectOption(
                label = "BREAK TIME",
                description= "A dedicated break day"
            )
        )
        options.append(
            discord.SelectOption(
                label = "EMERGENCY",
                description= "You had something urgent coming up"
            )            
        )
        options.append(
            discord.SelectOption(
                label = "MALAS",
                description= "The reason why you're inconsistent"
            )
        )
        options.append(
            discord.SelectOption(
                label = "SICK",
                description= "You've fallen ill"
            )
        )

        super().__init__(
            placeholder="Select your excuse",
            options = options,
            min_values= 1,
            max_values= 1
        )

    async def interaction_check(self, interaction: discord.Interaction):
        if (str(interaction.user.id) != self.userID): 
            print(f"{interaction.user.name} tried to check-in other user's menu and that's not allowed")
            await interaction.response.send_message(f"This menu is specifically for {self.username} only! Initiate the check-in command yourself", ephemeral= True)
            return False
        return True
    
    async def callback(self, interaction: discord.Interaction):
        commandStartTime = time.perf_counter()
        chosenExcuse: str = self.values[0] # User selected values will always be 1 element, which is a string        
        print(f"{self.username}'s excuse for {self.chosenActivity}: {chosenExcuse}")
        
        
        await interaction.response.defer()
        print("Going to Sheets")
        worksheet = sheetManager.get_worksheet(self.username)
        worksheetID = worksheet.id
        print(f"Got {self.username}'s worksheet")

        date = datetime.datetime.now()
        try:
            user = self.usersData[self.userID]
        except KeyError:
            print(f"{interaction.user} was not found in the local users file")
            await interaction.followup.send(f"An error has occured!")
            await interaction.followup.send(f"Your user profile was not found. If you had registered already, please DM the admin", ephemeral=True)
        yearCell: dict = sheetManager.get_year_cell(user, date)

        if self.userFormat == "Yearly":
            yearDivCell= None
            monthCell = sheetManager.get_month_cell(user, date, yearCell, yearDivCell)

            # Get rowToFind & columnToFind. Decrement by 1 afterwards so that it's 0-indexed
            rowToFind = (monthCell["row"] - 1) + date.day  # The first day is a row after monthRow. 
            columnToFind = monthCell["col"] - 1 # Since there's only 1 activity, columnToFind is just monthColumn
            
        else:
            yearDivCell= sheetManager.get_year_division_cell(yearCell, user, date)
            monthCell = sheetManager.get_month_cell(user, date, yearCell, yearDivCell)

            # Get rowTofind & columnToFind. There's no need to decrement by 1
            rowToFind = monthCell["row"] + date.day # The first day is 2 rows after monthRow. (0-indexed)                                           

            # Map the activity, offset columnToFind based on monthCell with baseIndex from the activity map
            try: 
                activityIndex = {}
                for index, activity in enumerate(self.registeredActivity):
                    activityIndex[activity] = index
                
                if self.chosenActivity in activityIndex:
                    baseIndex = activityIndex[self.chosenActivity]
                    offset = baseIndex + monthCell["col"] - 1       
                    columnToFind = offset
            
            except Exception as error:
                print(f"An error occured when getting rowToFind or columnToFind, {error}")
        
        # Request section
        compiledRequests = [] 
        ExcuseReq = { 
            "requests": [
                {
                    "updateCells": {
                        "rows": [ 
                            {"values": [{"userEnteredValue": {"stringValue": f"{chosenExcuse}"}}]}
                        ],
                        "fields": "userEnteredValue",
                        "range": {
                            "sheetId": worksheetID,
                            "startRowIndex": rowToFind, # First row
                            "endRowIndex": rowToFind + 1,
                            "startColumnIndex": columnToFind, # Column D
                            "endColumnIndex": columnToFind + 1,
                        }
                    }
                }
            ]
        }
        compiledRequests.extend(ExcuseReq["requests"])

        # Update to Sheets
        try:
            if compiledRequests:
                processStartTime = time.perf_counter()                             
                worksheet.spreadsheet.batch_update({"requests": compiledRequests}) 
                processEndTime = time.perf_counter()
                print(f"Sucessfully filled user's excuse in {processEndTime - processStartTime:.4f} seconds")            
        except Exception as error:
            print(f"An error has occured when batch-updatin, {error}\n") 

            # Debug
            print(f"User who failed to check-out: {interaction.user.name}, registered as {self.username} with ID: {self.userID}")
            print(f"Year cell: {yearCell}")
            if self.userFormat != "Yearly":
                print(f"YearDivision cell: {yearDivCell}")
            print(f"Month cell: {monthCell}")
            print(f"rowToFind: {rowToFind}")
            print(f"columnToFind: {columnToFind}\n")
            await interaction.followup.send(f"Failed to check-in to sheets!")
            await interaction.followup.send(f"Error: {error}", ephemeral=True)

        await interaction.followup.send(f"{interaction.user.mention}'s excuse for today: {chosenExcuse}")
        commandEndTime = time.perf_counter()
        print(f"Excuse command executed in {commandEndTime - commandStartTime:.4f} seconds\n")

class LabelsMenuView(discord.ui.View):
    def __init__(self, userID: str, activity: str):
        super().__init__(timeout=60) # Vanishes after 60s
        self.add_item(LabelsMenu(userID, activity))

class Excuses(commands.Cog):
    def __init__(self, bot):
        self.bot = bot         

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")


    async def excuse_autocomplete(self, interaction: discord.Interaction, current: str):
        userID = str(interaction.user.id)
        usersData = utls.loadJSON(CFG.USERS_FILE)
        try:
            user = usersData[userID]
        except KeyError:
            print(f"{interaction.user} was not found")
        userActivities = user['activities']

        return [
            app_commands.Choice(name=activity, value=activity)
            for activity in userActivities if current.lower() in activity.lower()
        ]

    # TODO: FIX EXCUSE CONFLICT WITH CHECKIN. Excuse could overwrite a cell, when the user is supposed to be done for that day.
    @app_commands.command(name="test_excusesmenu", description="Fills in today's cell with the selected excuse")
    @app_commands.autocomplete(activity = excuse_autocomplete)
    async def test_excuse(self, interaction: discord.Interaction, activity: str):
        userID = str(interaction.user.id)
        usersData = utls.loadJSON(CFG.USERS_FILE)
        try:
            user = usersData[userID]
        except KeyError:
            print(f"{interaction.user} was not found")
        userActivities: list = user['activities']

        if activity not in userActivities:
            message = "The activity you've inputted doesn't match with your registered activit"
            localMessage = f"{interaction.user} inputted: ({activity}) and it doesn't match with their registered activit"
            if len(userActivities) == 1:
                newLocalMessage = localMessage + 'y'
                newMessage = message + 'y'
            else:
                newLocalMessage = localMessage + 'ies'
                newMessage = message + 'ies'
            print(newLocalMessage)
            await interaction.response.send_message(newMessage)

        
        await interaction.response.send_message(f"Select your excuse for today's {activity}", view = LabelsMenuView(userID, activity))
async def setup(bot: commands.Bot):
    _GUILD_ID = discord.Object(id = CFG.GUILD_ID)
    await bot.add_cog(Excuses(bot), guild = _GUILD_ID)

    