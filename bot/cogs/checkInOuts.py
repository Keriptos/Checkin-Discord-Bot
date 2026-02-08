# Discord Imports
import discord 
from discord import app_commands
from discord.ext import commands

# Google Sheets Imports
from gspread import Worksheet, Spreadsheet
from bot.services.sheetService import sheetInitialization

# Other Imports
import os
import json
import datetime; from datetime import timedelta
import time 
from bot.config import CHECKIN_FILE, USERS_FILE, SHEET_CACHE

SHEET = sheetInitialization()

def lockedInTime(elapsedTime: datetime.timedelta):
    # Only handles the same day time difference. User is expected to check-out at the same day
    hours = elapsedTime.seconds // 3600
    minutes = (elapsedTime.seconds % 3600) // 60     
    seconds = elapsedTime.seconds % 60

    if hours != 0 and minutes != 0 and seconds != 0 : 
        return(f"{hours} hours {minutes} minutes {seconds} seconds") 
    elif hours == 0 and minutes != 0 and seconds != 0 :
        return (f"{minutes} minutes {seconds} seconds")
    elif hours == 0 and minutes == 0 and seconds != 0 :
        return (f"{seconds} seconds")

def loadJSON(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            file.write('{}') # create empty file with an empty dict
    try:
        with open(file_path) as file: 
            return json.load(file)
    except json.JSONDecodeError:
        with open(file_path, 'w') as file:
            file.write('{}')  # Create an empty JSON file if it doesn't exist or is invalid and write in an empty dict
    return {}

def saveJSON(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent = 4)

def setYearDivisionFormat(userFormat: str, date: datetime.datetime):
    # Semester 1 --> 1 2 3 4 5 6 | Semester 2 --> 7 8 9 10 11 12
    if "Semesterly" in userFormat:
        if date.month <= 6: 
            yearDivToFind = "Semester 1"
        else:
            yearDivToFind = "Semester 2"

    # Q1 --> 1 2 3 | Q2 --> 4 5 6 | Q3 --> 7 8 9 | Q4 --> 10 11 12        
    elif "Quarterly" in userFormat:
        if date.month <= 3:
            yearDivToFind = "Q1"
        elif date.month <= 6:
            yearDivToFind = "Q2"
        elif date.month <= 9:
            yearDivToFind = "Q3"
        else:
            yearDivToFind = "Q4"    
    return yearDivToFind

def getYearCell(userFormat: str, worksheet: Worksheet, date: datetime.datetime):
    processStartTime = time.perf_counter()
    if userFormat == "Yearly": 
        yearCell = { # By default, it's D3 --> (1-indexed)
            "row": 3,
            "col": 4 
        }
    else:
        yearCell = { # By default, it's D1 --> (1-indexed)
            "row": 1,
            "col": 4 
        }
    timeColumn = worksheet.col_values(4) # Year location is fixed, always at D column
    yearRow = yearCell["row"]
    
    found = False   
    while (yearRow <= len(timeColumn)):        
        if (timeColumn[yearRow - 1] == str(date.year)): # the index was decremented by 1 so it's 0-indexed
            yearCell['row'] = yearRow
            found = True
            break

        # Skip algorithm
        if (userFormat == "Yearly"):
            yearRow += 35
        else :
            yearRow += 36

    if not found:
        raise ValueError(f"Year {date.year} not found")
    
    processEndTime = time.perf_counter()
    print(f"Found yearCell '{yearCell}' in {processEndTime - processStartTime:.4f} seconds")

    return yearCell, timeColumn

class YearDivisionDTO():
    def __init__ (self, yearDivToFind: str, yearCell: dict, timeColumn: list):
        self.yearDivToFind = yearDivToFind
        self.yearCell = yearCell
        self.timeColumn = timeColumn

def getYearDivision(DTO: YearDivisionDTO):    
    start = time.perf_counter()    
    yearDivisionCell = { # default values (1-indexed)
        "row": DTO.yearCell["row"] + 2,
        "col": DTO.yearCell["col"]
    }

    # Search the row of yearDivisionCell
    found = False   
    yearDivRow = yearDivisionCell["row"] 
    while (yearDivRow <= len(DTO.timeColumn)):  
        if (DTO.timeColumn[yearDivRow - 1] == DTO.yearDivToFind): # The index is decremented by 1, so that it's 0-indexed
            yearDivisionCell['row'] = yearDivRow
            found = True
            break

        # Skip algorithm
        yearDivRow += 36
    
    end = time.perf_counter()
    if not found:
        raise ValueError(f"{DTO.yearDivToFind} not found")
    print(f"Found yearDivisionCell '{DTO.yearDivToFind}': {yearDivisionCell} in {end - start:.8f} seconds")

    return yearDivisionCell

def getMonthCell(userID: str, date: datetime.datetime, yearCell: dict, yearDivCell: dict | None):
    # All values are 1 - indexed
    monthStart = time.perf_counter()
    usersData = loadJSON(USERS_FILE)
    
    userFormat = usersData[userID]['format']
    if userFormat == "Yearly":
        monthCell = {
        "row": yearCell["row"],
        "col": 6 + (date.month - 1) 
    }
    else:         
        userActivities = usersData[userID]['activities']
        monthCell = {
        "row": yearDivCell["row"] if yearDivCell is not None else yearCell["row"] + 2,
        "col": 6 + (len(userActivities) * (date.month - 1)) 
    }
    monthEnd = time.perf_counter()
    print(f"Completed monthCell search '{monthCell}' in {monthEnd - monthStart:.8f} seconds")
    return monthCell

class CheckinMenu(discord.ui.Select):# A menu to select your activities up to 5 at once
    def __init__(self, userID: str):
        self.userID = userID
        self.usersData: dict = loadJSON(USERS_FILE)
        self.username: str = self.usersData[userID]['username']
        self.userFormat: str = self.usersData[userID]['format']    

        # Basically make a list of activities from user's registered activitiies
        self.userActivities = self.usersData[userID]['activities']

        activityOptions = [] #To store activities based on userID
        for activity in self.userActivities:
            activityOptions.append(
                discord.SelectOption(
                    label = activity,
                    description = f"Checks you in from the sheet for {activity}"
                )
            )
        
        super().__init__(
            placeholder = "Select your activity",
            options = activityOptions,
            min_values = 1,
            max_values = len(activityOptions) #Hard limit
        ) 
    

    async def interaction_check(self, interaction: discord.Interaction):
        if (str(interaction.user.id) != self.userID): 
            print(f"{interaction.user.name} tried to check-in other user's menu and that's not allowed")
            await interaction.response.send_message(f"This menu is specifically for {self.username} only! Initiate the check-in command yourself", ephemeral= True)
            return False
        return True


    async def callback(self, interaction: discord.Interaction):
        commandStartTime = time.perf_counter() # To record how long the command takes to execute

        # Menu related stuff
        chosen: list = self.values  # A list of selected activities by user
        chosen.sort() # Sort for consistency sake, it only affects how it looks. Chosen will always be the user's registered activities
        print(f"{interaction.user.name} selected: {chosen}")

            
        # Local check-in
        start = time.perf_counter()
        timeCheckedIn = loadJSON(CHECKIN_FILE)        
        await interaction.response.defer()

        # Duplicate activity check-in validation
        try:
            if self.userID in timeCheckedIn:            
                filtered = []
                activityKeys = timeCheckedIn[self.userID]['activities'].keys()
                for activity in chosen:
                    if activity in activityKeys: # Check if user has checked in for the same activity
                        print(f"{interaction.user.name} tried to re-checkin for {activity}")
                        await interaction.followup.send(f"You've already checked in for {activity}!", ephemeral=True)                    
                    else:
                        filtered.append(activity)
                chosen = filtered
                print(f"Filtered selection: {chosen}")
        except Exception as error:
            print(f"Something went terribly wrong with activity filtering, {error}")
    

        # Because of the check above, chosen can be empty
        if not chosen:
            print(f"{interaction.user.name} tried to re-checkin for duplicate activities\n")
            await interaction.followup.send(f"{interaction.user.mention}, you've already checked in for what you've chosen!")
            return


        # If user hasn't checked in, make an empty dict for user
        if self.userID not in timeCheckedIn:
            timeCheckedIn[self.userID] = {}
            timeCheckedIn[self.userID]['username'] = self.username # This is purely just for readability
            timeCheckedIn[self.userID]['activities'] = {}

        for activity in chosen:            
            # Username and activity = keys, time as the value into dictionary
            timeCheckedIn[self.userID]['activities'][activity] = datetime.datetime.now().isoformat()
        saveJSON(timeCheckedIn, CHECKIN_FILE)

        end = time.perf_counter()
        print(f"Succesfully saved timestamp locally in {end - start:.8f} seconds")        
        await interaction.followup.send(f"Syncing for {chosen}...", ephemeral= True)


        # Sync to sheets process (Check-in)
        print("Checking in to sheets")        
        worksheet = SHEET.worksheet(self.username) # Get the worksheet for the userID        
        worksheetID = worksheet.id

        # Get year, timeColumn is a column gotten by Sheet API to gather all values from the year and yearDivison column (D column) 
        date = datetime.datetime.now()
        yearCell, timeColumn = getYearCell(self.userFormat, worksheet, date)        

        # Set up check-in cache
        try:
            startCache = time.perf_counter()
            sheetCache = loadJSON(SHEET_CACHE)            
            if self.userID not in sheetCache:
                sheetCache[self.userID] = {}
                sheetCache[self.userID]['username'] = self.username
                sheetCache[self.userID]['activities'] = {}
            for activity in chosen:
                sheetCache[self.userID]['activities'][activity] = {}
                sheetCache[self.userID]['activities'][activity]['checkinCell'] = {}                    
            saveJSON(sheetCache, SHEET_CACHE)
            endCache = time.perf_counter()
            print(f"Sucessfully set up {interaction.user.name}'s check-in cache in {endCache - startCache:.8f} seconds")
        except Exception as error:
            print(f"An error has occured when setting up {interaction.user.name}'s sheetCache {error}")

        if self.userFormat == "Yearly":  # Only 1 activity algorithm
            """
            Year -> Month -> Date        
            """
            # Get month
            yearDivCell = None
            monthCell = getMonthCell(self.userID, date, yearCell, yearDivCell)


            # Get rowToFind & columnToFind. Decrement by 1 afterwards so that it's 0-indexed
            rowToFind = (monthCell["row"] - 1) + date.day  # The first day is a row after monthRow. 
            columnToFind = monthCell["col"] - 1 # Since there's only 1 activity, columnToFind is just monthColumn

            # Write it to sheetCache
            for activity in chosen:                                
                sheetCache[self.userID]['activities'][activity]['checkinCell']['row'] = rowToFind
                sheetCache[self.userID]['activities'][activity]['checkinCell']['col'] = columnToFind
            saveJSON(sheetCache, SHEET_CACHE)

            # Request section
            compiledRequests = [] 
            CheckInReq = { #Write ON PROGRESS to update cell (we used conditional formatting when making the table) | Check-in
                "requests": [
                    {
                        "updateCells": {
                            "rows": [ 
                                {"values": [{"userEnteredValue": {"stringValue": "ON PROGRESS"}}]}
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
            compiledRequests.extend(CheckInReq["requests"])

        else: # 2+ algorithm
            """
            Year -> YearDiv -> Month -> Date

            """
            # Get year divison cell
            yearDivToFind = setYearDivisionFormat(self.userFormat, date)
            DTO = YearDivisionDTO(yearDivToFind, yearCell, timeColumn)
            yearDivCell = getYearDivision(DTO)

            # Get month
            monthCell = getMonthCell(self.userID, date, yearCell, yearDivCell)

            try:
                # Get rowTofind & columnToFind. There's no need to decrement by 1
                rowToFind = monthCell["row"] + date.day # The first day is 2 rows after monthRow. (0-indexed)                                           

                # Map the activity, offset it based on monthCell, and write rowToFind & offset to sheetCache
                activityIndex = {}
                for index, activity in enumerate(self.userActivities):
                    activityIndex[activity] = index

                columnToFind = []
                for activity in chosen:
                    sheetCache[self.userID]['activities'][activity]['checkinCell']['row'] = rowToFind
                    if activity in activityIndex:
                        baseIndex = activityIndex[activity]
                        offset = baseIndex + monthCell["col"] - 1       
                        columnToFind.append(offset)
                        sheetCache[self.userID]['activities'][activity]['checkinCell']['col'] = offset
                    else:
                        raise ValueError(f"Activity '{activity}' not found")                             
                saveJSON(sheetCache, SHEET_CACHE)     
            except Exception as error:
                print(f"An error occured when getting rowToFind or columnToFind, {error}")

            # Request section
            compiledRequests = [] 
            for col in columnToFind:
                CheckInReq = { #Write ON PROGRESS to update cell (we used conditional formatting when making the table) | Check-in
                    "requests": [
                        {
                            "updateCells": {
                                "rows": [ 
                                    {"values": [{"userEnteredValue": {"stringValue": "ON PROGRESS"}}]}
                                ],
                                "fields": "userEnteredValue",
                                "range": {
                                    "sheetId": worksheetID,
                                    "startRowIndex": rowToFind, # First row
                                    "endRowIndex": rowToFind + 1,
                                    "startColumnIndex": col, # Column D
                                    "endColumnIndex": col + 1,
                                }
                            }
                        }
                    ]
                }
                compiledRequests.extend(CheckInReq["requests"])

        # Update to Sheets
        try:
            if compiledRequests:
                processStartTime = time.perf_counter()                             
                worksheet.spreadsheet.batch_update({"requests": compiledRequests}) 
                processEndTime = time.perf_counter()
                print(f"Sucessfully checked in user in {processEndTime - processStartTime:.4f} seconds")            
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
                        

        await interaction.followup.send(f"{interaction.user.mention} has checked in to the sheets for {chosen}")
        commandEndTime = time.perf_counter()
        print(f"Checkin executed in {commandEndTime - commandStartTime:.4f} seconds\n")
        
    async def on_timeout(self,interaction: discord.Interaction):
        await interaction.response.send_message("Check-in menu timed out")

class CheckinMenuView(discord.ui.View):
    def __init__(self, userID: str):
        super().__init__(timeout=60) #Vanishes after 60s
        self.add_item(CheckinMenu(userID))


class CheckoutMenu(discord.ui.Select):
    def __init__(self, userID: str):
        #Declarations to be locally used in the class
        self.userID = userID
        self.usersData: dict = loadJSON(USERS_FILE)
        self.username: str = self.usersData[userID]['username']
        self.userFormat: str = self.usersData[userID]['format']
        self.userActivities: list = self.usersData[userID]['activities']        


        # Basically make a list out of the activity keys from checkintimes.json UNDER their usernames
        checkinsFile = loadJSON(CHECKIN_FILE)
        self.checkedInActivities = list(dict.fromkeys(checkinsFile[self.userID]['activities'].keys()))

        options = []
        for activity in self.checkedInActivities:
            options.append(
                discord.SelectOption(
                    label = activity,
                    description = f"Checks you out from the sheet for {activity}"
                )
            )

        super().__init__(
            placeholder="Select your activity to check-out",
            options = options,
            min_values= 1,
            max_values= max(1, len(options))
         )       

    async def interaction_check(self, interaction: discord.Interaction):
        if (str(interaction.user.id) != self.userID):
            print(f"{interaction.user.name} tried to check-in other user's menu and that's not allowed\n")
            await interaction.response.send_message(f"This menu is specifically for {self.username} only! Initiate the check-out command yourself", ephemeral= True)
            return False
        return True
        
    async def callback(self, interaction: discord.Interaction):
        commandStartTime = time.perf_counter()

        chosen: list = self.values
        chosen.sort()  # Sort for consistency sake, it only affects how it looks
        print(f"{interaction.user.name} selected: {chosen}")

        # Chosen validation because user can use menu multiple times
        # Menu only updates when user initiates the command themselves
        timeCheckedIn: dict = loadJSON(CHECKIN_FILE)
        valid = []
        if self.userID not in timeCheckedIn:
            print(f"{interaction.user.name} tried to check-out when they've just literally checked out before")
            await interaction.response.send_message(f"You've just checked out from all your activities!")
            return
        
        
        activityKeys = timeCheckedIn[self.userID]['activities'].keys()
        for activity in chosen:
            if activity not in activityKeys:
                print(f"{interaction.user.name} tried to recheck-out for {activity}")
                await interaction.followup.send(f"You've already checked out for {activity}!", ephemeral=True)
            else: 
                valid.append(activity)
        chosen = valid
        print(f"Filtered selection: {chosen}")


        await interaction.response.defer()

        # Syncing to Sheets (Check-out)
        print("Checking out from sheets")        
        worksheet = SHEET.worksheet(self.username)
        worksheetID = worksheet.id 
        
        timeCheckedOut = datetime.datetime.now()                
        sheetCache = loadJSON(SHEET_CACHE)

        if self.userFormat == "Yearly":  # Only 1 activity algorithm
            # Get rowToFind and columnToFind from sheetCache
            try:
                processStartTime = time.perf_counter()
                for activity in chosen:
                    rowToFind = sheetCache[self.userID]['activities'][activity]['checkinCell']['row']
                    columnToFind = sheetCache[self.userID]['activities'][activity]['checkinCell']['col']
                processEndTime = time.perf_counter()
                print(f"Successfully gotten row and col from sheetCache in {processEndTime - processStartTime:.4f} seconds")
            except Exception as error:
                print(f"An error occured when trying to find row and col from sheetCache, {error}")

            # Request section
            compiledRequests = [] 
            CheckOutReq = { # Write DONE to update cell (we used conditional formatting when making the table) | Check-out
                "requests": [
                    {
                        "updateCells": {
                            "rows": [ 
                                {"values": [{"userEnteredValue": {"stringValue": "DONE"}}]}
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
            compiledRequests.extend(CheckOutReq["requests"])

        else: # 2+ algorithm
            # rowToFind & columnToFind fetching + request section 
            compiledRequests = []
            try:
                for activity in chosen:
                    rowToFind = sheetCache[self.userID]['activities'][activity]['checkinCell']['row']
                    columnToFind = sheetCache[self.userID]['activities'][activity]['checkinCell']['col']
                    CheckOutReq = { # Write DONE to update cell (we used conditional formatting when making the table) | Check - out
                        "requests": [
                            {
                                "updateCells": {
                                    "rows": [ 
                                        {"values": [{"userEnteredValue": {"stringValue": "DONE"}}]}
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
                    compiledRequests.extend(CheckOutReq["requests"])                    
            except Exception as error:
                print(f"An error occured when fetching rowToFind/columnToFind")

        # Update to Sheets
        try:
            if compiledRequests:
                processStartTime = time.perf_counter()
                worksheet.spreadsheet.batch_update({"requests": compiledRequests}) 
                processEndTime = time.perf_counter()
                print(f"Sucessfully checked out user from sheets in {processEndTime - processStartTime:.4f} seconds")

        except Exception as error:
            # Debug
            print(f"An error has occured when batch-updatin, {error}\n")
            print(f"User who failed to check-out: {interaction.user.name}, registered as {self.username} with ID: {self.userID}")                            
            print(f"rowToFind: {rowToFind}")
            print(f"columnToFind: {columnToFind}\n")

            await interaction.followup.send(f"Failed to check-out from sheets!")
            await interaction.followup.send(f"Error: {error}", ephemeral=True) 
                 
        # Response message
        for activity in chosen:
            userTimeCheckedIn = datetime.datetime.fromisoformat(timeCheckedIn[self.userID]['activities'][activity])
            elapsedTime: timedelta = timeCheckedOut - userTimeCheckedIn
            print(f"{interaction.user.name}'s {activity} elapsed time: {lockedInTime(elapsedTime)}")
            if len(chosen) == 1:
                await interaction.followup.send(f"{interaction.user.mention} has checked out from the sheet for {activity} activity! Locked in for {lockedInTime(elapsedTime)}")
            else:
                await interaction.followup.send(f"{interaction.user.mention} has checked out from the sheet for {activity} activities! Locked in for {lockedInTime(elapsedTime)}")
        
        # If user chooses to check out from all activities, remove the entire username dict from the file
        if len(chosen) == len(self.checkedInActivities): 
            timeCheckedIn.pop(self.userID)
        
        else: # Otherwise, remove the specific activity key from the user's dict
            for activity in chosen: 
                timeCheckedIn[self.userID]['activities'].pop(activity)            
        saveJSON(timeCheckedIn, CHECKIN_FILE) # Save the updated dictionary back to the JSON file
        print(f"{interaction.user.name} checked out locally for {chosen}")

        # Remove checkin cache
        try:             
            removeCheckinsStart = time.perf_counter()
            # Delete activty dict from user 
            if self.userFormat == 'Yearly':
                del sheetCache[self.userID]

            else: 
                for activity in chosen:
                    print(f"Activity: {activity} checkinCell: {sheetCache[self.userID]['activities'][activity]['checkinCell']}")
                    del sheetCache[self.userID]['activities'][activity]
            
                # Activity check in sheetCache to see if user have checked out from all their activities
                hasFullyCheckedOut = True
                for activity in self.userActivities:
                    if activity in sheetCache[self.userID]['activities'].keys():
                        hasFullyCheckedOut = False
                        break
                if hasFullyCheckedOut:
                    print(f"{interaction.user.name} has checked out from all their activities")
                    del sheetCache[self.userID]
                    removeCheckinsEnd = time.perf_counter()
                    print(f"Succesfully deleted {self.username}'s {chosen} check-in cache in {removeCheckinsEnd - removeCheckinsStart:8f} seconds")                
                else:
                    print(f"{self.username} is not fully checked-out yet")
            saveJSON(sheetCache, SHEET_CACHE)
        except Exception as error:
            print(f"An error has occured when deleting {interaction.user.name}'s dict from sheetCache {error}")

        commandEndTime = time.perf_counter()
        print(f"Checkout executed in {commandEndTime - commandStartTime:.4f} seconds\n")

    async def on_timeout(self,interaction: discord.Interaction):
        await interaction.response.send_message("Check-out menu timed out")

class CheckoutMenuView(discord.ui.View):
    def __init__(self, userID: str):
        super().__init__(timeout=60)
        self.add_item(CheckoutMenu(userID))

class CheckInOuts(commands.Cog):
    commandStartTime = time.perf_counter() # To record how long loading the cog takes
    def __init__(self, bot):
        self.bot = bot         

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")
    
    @app_commands.command(name = "checkinmenu", description = "Checks you in to the google sheet")
    async def checkinMenu(self, interaction: discord.Interaction):
        userID = str(interaction.user.id)        
        usersData = loadJSON(USERS_FILE)        
        

        print(f"{interaction.user.name} is trying to check in")
        if userID not in usersData: # Check if user is registered
            print(f"{interaction.user.name} is not registered\n")
            await interaction.response.send_message("You are not registered. Please register first!", ephemeral=True)
            return        
        
        try:
            await interaction.response.send_message("Please select your activity to check-in:", view=CheckinMenuView(userID))
        except Exception as error:
            print(f"Error in checkinMenu: {error}\n")
            await interaction.response.send_message(f"An error has occured: {error}", ephemeral=True)


    @app_commands.command(name="checkoutmenu", description="Checks you out from the google sheet")
    async def checkoutMenu(self, interaction: discord.Interaction):
        userID = str(interaction.user.id)
        usersData = loadJSON(USERS_FILE)        
        timeCheckedIn: dict = loadJSON(CHECKIN_FILE)

        print(f"{interaction.user.name} is trying to check out")        
        # Check if user is registered
        if userID not in usersData: 
            print(f"{interaction.user.name} is not registered\n")
            await interaction.response.send_message("You are not registered. Please register first!", ephemeral=True)
            return
        
        # Check if user hasn't checked in
        if userID not in timeCheckedIn: 
            print(f"{interaction.user.name} tried to check-out but hadn't checked in\n")
            await interaction.response.send_message("You haven't checked in! Please check-in first before you check-out!", ephemeral=True)
            return 
        try:
            await interaction.response.send_message("Please select your activity to check-out:", view=CheckoutMenuView(userID))
        except Exception as error:
            print(f"Error in checkoutMenu: {error}\n")
            await interaction.response.send_message(f"An error has occured: {error}", ephemeral=True)

    
async def setup(bot: commands.Bot):
    GUILD_ID = discord.Object(id = 1391372922219659435) # This is my server's ID, and I'm only gonna use it for my server
    await bot.add_cog(CheckInOuts(bot), guild = GUILD_ID)