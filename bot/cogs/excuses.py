# Discord Imports
import discord 
from discord import app_commands
from discord.ext import commands

# Google Sheets Related Imports
from bot.services.sheetService import sheetManager

# Other Imports
import bot.helpers.utils as utls
from bot.config_builder import ConfigDTO
import datetime
import time 

# Globals
CFG = ConfigDTO()

class LabelsMenu(discord.ui.Select):
    """ A menu to use other labels to fill in the activity days.
        THIS WILL FILL EVERY ACTIVITY DAY
    """
    def __init__(self, userID: str, activities: list):
        self.chosenActivities: list = activities
        self.userID: str = userID
        self.usersData: dict = utls.loadJSON(CFG.USERS_FILE)
        try:
            self.user = self.usersData[self.userID]
            self.username: str = self.user['username']
            self.userFormat: str = self.user['format']
            self.registeredActivity: list = self.user['activities']
        except KeyError:
            raise KeyError(f"Local data lookup failed")
        
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
        print(f"{self.username}'s excuse for {self.chosenActivities}: {chosenExcuse}")
        
        try:
            user = self.usersData[self.userID]
        except KeyError:
            print(f"{interaction.user} was not found in the local users file")
            await interaction.followup.send(f"An error has occured!")
            await interaction.followup.send(f"Your user profile was not found. If you had registered already, please DM the admin", ephemeral=True)
            return 
        
        await interaction.response.defer()
        print("Going to Sheets")
        worksheet = sheetManager.get_worksheet(self.username)
        worksheetID = worksheet.id
        print(f"Got {self.username}'s worksheet")


        date = datetime.datetime.now()
        yearCell: dict = sheetManager.get_year_cell(user, date)
        if self.userFormat == "Yearly":
            yearDivCell= None
            monthCell = sheetManager.get_month_cell(self.user, date, yearCell, yearDivCell)

            # Values are decremeneted by 1, so that it's 0-indexed
            rowToFind = (monthCell["row"] - 1) + date.day  # The first day is a row after monthRow.
            columnToFind: list = [monthCell["col"] - 1] # Made into a list so that ExcuseReq could be consistent with 2+ activities
            
        else:
            yearDivCell= sheetManager.get_year_division_cell(yearCell, self.user, date)
            monthCell = sheetManager.get_month_cell(self.user, date, yearCell, yearDivCell)

            # There's no need to decrement by 1
            rowToFind = monthCell["row"] + date.day # The first day is 2 rows after monthRow. (0-indexed)                                           

            # Map the activity, offset columnToFind based on monthCell with baseIndex from the activity map
            try: 
                activityIndex = {}
                for index, activity in enumerate(self.registeredActivity):
                    activityIndex[activity] = index
                
                columnToFind: list = []
                for activity in self.chosenActivities:
                    if activity in activityIndex:
                        baseIndex = activityIndex[activity]
                        offset = baseIndex + monthCell["col"] - 1       
                        columnToFind.append(offset)
            
            except Exception as error:
                print(f"An error occured when getting rowToFind or columnToFind, {error}")
        
        # Request section
        compiledRequests = []
        for col in columnToFind:
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
                                "startRowIndex": rowToFind,
                                "endRowIndex": rowToFind + 1,
                                "startColumnIndex": col,
                                "endColumnIndex": col + 1
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
    def __init__(self, userID: str, activities: list):
        super().__init__(timeout=60) # Vanishes after 60s
        self.add_item(LabelsMenu(userID, activities))

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
    @app_commands.autocomplete(
        activity1 = excuse_autocomplete,
        activity2 = excuse_autocomplete,
        activity3 = excuse_autocomplete,
        activity4 = excuse_autocomplete,
        activity5 = excuse_autocomplete
    )
    async def test_excuse(
        self, 
        interaction: discord.Interaction, 
        activity1: str,
        activity2: str = None,
        activity3: str = None,
        activity4: str = None,
        activity5: str = None):

        userID = str(interaction.user.id)
        usersData = utls.loadJSON(CFG.USERS_FILE)
        try:
            user = usersData[userID]
        except KeyError:
            print(f"{interaction.user} was not found")
        userActivities: list = user['activities']

        await interaction.response.defer()
        # Filter the activities        
        groupedAct: tuple = (activity1, activity2, activity3, activity4, activity5)
        valid: list = []
        invalid: list = []
        for activity in groupedAct:
            if activity is None or activity in valid: # Skip duplicates or None
                continue
            if activity in userActivities:
                valid.append(activity)
            else:
                invalid.append(activity)
        print(f"{interaction.user} selected: {valid}")
        if invalid:
            await interaction.followup.send(f"{invalid} doesn't match with your registered activity!", ephemeral=True)

        # Activities validation
        if not valid:
            if len(groupedAct) == 1:
                await interaction.followup.send(f"The activity you've inputted doesn't match with your registered activity")
                return 
            else:
                await interaction.followup.send(f"The activities you've inputted doesn't match with your registered activities")
                return         

        await interaction.followup.send(f"Select your excuse for today's {valid}", view = LabelsMenuView(userID, valid))        

async def setup(bot: commands.Bot):
    _GUILD_ID = discord.Object(id = CFG.GUILD_ID)
    await bot.add_cog(Excuses(bot), guild = _GUILD_ID)
    