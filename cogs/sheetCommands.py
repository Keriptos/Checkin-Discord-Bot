#Discord Imports
import discord 
from discord import app_commands
from discord.ext import commands

#Google Sheets Imports
import gspread 
from google.oauth2.service_account import Credentials

#Other Imports
import time 
import datetime
from datetime import timedelta
import calendar #To get month name
import json
import os


def lockedInTime(elapsedTime:datetime.timedelta):
    hours = elapsedTime.seconds // 3600
    minutes = (elapsedTime.seconds % 3600) // 60     
    seconds = elapsedTime.seconds % 60

    if hours != 0 and minutes != 0 and seconds != 0 : 
        return(f"{hours} hours {minutes} minutes {seconds} seconds") 
    elif hours == 0 and minutes != 0 and seconds != 0 :
        return (f"{minutes} minutes {seconds} seconds")
    elif hours == 0 and minutes == 0 and seconds != 0 :
        return (f"{seconds} seconds")

def sheetInitialization():
    from dotenv import load_dotenv
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("credentials.json", scopes = scopes)
    client = gspread.authorize(creds)

    load_dotenv(".env")
    sheetID = os.getenv("googleSheetID")
    sheet = client.open_by_key(sheetID)
    return sheet

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

def saveTimeCheckins(checkinData):    
    with open('checkintimes.json', 'w') as file:
        json.dump(checkinData, file, indent=4)

# Used for finding activity row, month row is always above activity row
def activityOffset(userID): # Alex only has 1 activity registered, no need for an offset. Offset is 1-indexed based. TEMP solution
    if userID == "880614022939041864": #Sam
        return 40
    elif userID == "582370335886802964": #Raf
        return 4
    elif userID == "461526727521206282": #TestUser
        return 4
    elif userID == "181760450273214464": #Chris
        return 40
    elif userID == "689028638544494621": #Nicholas
        return 40

"""
Row offset is calculated by row in sheet in 0-index format - 1 (day) 
Ex = Day 1 in at row 3 in sheet --> rowOffset = 1, 2 - 1 ~~~ (3rd row in 0-index format) - (day 1)
"""
# Used for finding the cell of date
def rowOffset(userID): #Row offset is 0-index based. TEMP solution
     if userID == "591939252061732900": #Alex
         return 2
     elif userID == "880614022939041864": #Sam
         return 39
     elif userID == "181760450273214464": #Chris
         return 39
     elif userID == "689028638544494621": #Nicholas
        return 75
     elif userID == "582370335886802964": #Raf
        return 3
     elif userID == "461526727521206282": #TestUser
        return 3

class CheckinMenu(discord.ui.Select):# A menu to select your activities up to 5 at once
    def __init__(self, userID: str):
        self.userID = userID
        self.ID_to_name = loadJSON('users.json')
        self.username = self.ID_to_name[userID]
        self.userActivities = loadJSON('userActivities.json') 

        # Basically make a list out of the activity keys from checkintimes.json UNDER their usernames
        self.validUserActivities = list(dict.fromkeys(self.userActivities.get(self.username))) 

        activityOptions = [] #To store activities based on userID
        for activity in self.validUserActivities:
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
        chosen = self.values  # A list of selected activities by user
        chosen.sort() # Sort for consistency sake, it only affects how it looks. Chosen will always be the user's registered activities
        print(f"{self.username} selected: {chosen}")
        
        # Starts to handle checking in
        timeCheckedIn = loadJSON('checkintimes.json')

        await interaction.response.defer()

        #Check-in user's time locally
        for activity in chosen:
            if activity in self.userActivities.get(self.ID_to_name[self.userID], []):
                if self.username not in timeCheckedIn:
                    timeCheckedIn[self.username] = {}

                #Username and activity = keys, time as the value into dictionary
                timeCheckedIn[self.username][activity] = datetime.datetime.now().isoformat() 
        saveTimeCheckins(timeCheckedIn) # Saves once after processing all the check-in times (avoid multiple writes in loop)


        #Update to sheets (Check-in)
        print("Syncing to sheets")
        sheet = sheetInitialization() 
        worksheet = sheet.worksheet(self.username) # Get the worksheet for the userID
        worksheetID = worksheet.id

        date = datetime.datetime.now() # Get the value from userID, which is the time checked in for that specific user

        #Only yearly table format(me) have different row and column algorithms, make a special case for them
        #Process to find row and column to update 
        rowToFind = date.day + rowOffset(self.userID) # 0-index based

        # Getting column is pretty hard since it needs month and activity, which is under the month. So have to get month first
        month = calendar.month_name[date.month] # Get the month name from the date

        #Get the month name row (1-index based), has None in the list
        monthRowList = []
        if self.userID not in ["591939252061732900", "650679555740401677"]: #Alex and Kendrick only have 1 activity registered, no need for an offset
            monthRowList = worksheet.row_values(activityOffset(self.userID)- 1) #Offset is 1-index based, so -1 to move back onto month cell, instead of activity cell
        else:
            monthRowList = worksheet.row_values(3) # Alex and Kendrick only has 1 activity, so month is always on row 3 (1-index based)

        monthColumn = None
        #Loops through the monthRowList and stops until the month is found, should return the index of it
        for i, value in enumerate(monthRowList): #Index must and will be 0-index based
            if value is not None and value.strip().lower() == month.lower():
                monthColumn :int = i
                break
        #Checks in case month is not found
        if monthColumn is None:
            raise ValueError (f"Month '{month}' not found") 
        

        #Get the column of the activity under the month found
        if (self.username ==  'Alex' or self.username == 'Kendrick'): # Only 1 activity algorithm
            columnToFind = monthColumn 

            #Request section
            compiledRequests = [] # To store all requests for batch update for later
            pre_pasteLabels = { #ON PROGRESS to update cell | Check-in
                "requests": [
                    {
                        "copyPaste": {
                            "source": {
                                # 0-index based
                                "sheetId": worksheetID,
                                "startRowIndex": 3,  # Copies "ON PROGRESS" Cell
                                "startColumnIndex": 0,
                                "endRowIndex": 4,
                                "endColumnIndex": 1
                            },
                            "destination": {
                                # 0-index based
                                "sheetId": worksheetID,
                                "startRowIndex": rowToFind,
                                "startColumnIndex": columnToFind,
                                "endRowIndex": rowToFind + 1,
                                "endColumnIndex": columnToFind + 1
                            },
                            "pasteType": "PASTE_NORMAL",
                            "pasteOrientation": "NORMAL"
                        }
                    }
                ]
            }
            compiledRequests.extend(pre_pasteLabels["requests"]) # Add the requests to the compiled list

        else:  # 2+ activity algorithm
            columnToFind = []
            activityRow = worksheet.row_values(activityOffset(self.userID)) #Get the 4th row (1-index based), does have None in the list
            #Loops through the activityRow and stops until the first instance of activity is found, then set columnToFind as the index
            for i in range(monthColumn, len(self.userActivities[self.username]) + monthColumn): #Index must and will be 0-index based
                if activityRow[i] is not None and activityRow[i].lower() in [a.lower() for a in chosen]: #Check if the activity matches
                    columnToFind.append(i)
            if columnToFind == []: #Checks in case activity is not found
                raise ValueError (f"Activity '{chosen}' not found under month '{month}'")
        
            #Request section
            compiledRequests = [] # To store all requests for batch update
            for i in columnToFind:
                pre_pasteLabels = { #ON PROGRESS to update cell | Check-in
                    "requests": [
                        {
                            "copyPaste": {
                                "source": {
                                    # 0-index based
                                    "sheetId": worksheetID,
                                    "startRowIndex": 3,  # Copies "ON PROGRESS" Cell
                                    "startColumnIndex": 0,
                                    "endRowIndex": 4,
                                    "endColumnIndex": 1
                                },
                                "destination": {
                                    # 0-index based
                                    "sheetId": worksheetID,
                                    "startRowIndex": rowToFind,
                                    "startColumnIndex": i,
                                    "endRowIndex": rowToFind + 1,
                                    "endColumnIndex": i + 1
                                },
                                "pasteType": "PASTE_NORMAL",
                                "pasteOrientation": "NORMAL"
                            }
                        }
                    ]
                }
                compiledRequests.extend(pre_pasteLabels["requests"]) # Add the requests to the compiled list
    

        if compiledRequests is not []:
            worksheet.spreadsheet.batch_update({"requests": compiledRequests}) # Batch update all requests at once
            print("Batch update successful.")

        
        # Tell user that they've checked into the sheet after all the processes
        if chosen:
            print(f"User checked in for {chosen} activities")
            await interaction.followup.send(f"{interaction.user.mention} has checked in to the sheets for {chosen} activities")

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
        self.ID_to_name = loadJSON('users.json')
        self.username = self.ID_to_name[userID]
        self.userActivities = loadJSON('userActivities.json') 

        # Basically make a list out of the activity keys from checkintimes.json UNDER their usernames
        self.validUserActivities = list(dict.fromkeys(loadJSON('checkintimes.json').get(self.username).keys())) 

        options = []
        for activity in self.validUserActivities:
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
            print(f"{interaction.user.name} tried to check-in other user's menu and that's not allowed")
            await interaction.response.send_message(f"This menu is specifically for {self.username} only! Initiate the check-out command yourself", ephemeral= True)
            return False
        return True
        
    async def callback(self, interaction: discord.Interaction):
        commandStartTime = time.perf_counter() # To record how long the command takes to execute

        chosen = self.values # A list of selected activities by user
        chosen.sort()  # Sort for consistency sake, it only affects how it looks
        print(f"{self.username} selected: {chosen}")
        timeCheckedInDICT = loadJSON('checkintimes.json')

        await interaction.response.defer()

        #Syncing to Sheets (Check-out)
        print("Syncing to sheets")
        sheet = sheetInitialization() # Initialize the sheet
        worksheet = sheet.worksheet(self.username) # Get the worksheet for the userID
        worksheetID = worksheet.id # Get the worksheetID for pasteLabels later on


        for activity in chosen:
            userTimeCheckedIn = datetime.datetime.fromisoformat(timeCheckedInDICT[self.username][activity])
            timeCheckedOut = datetime.datetime.now()
            elapsedTime :timedelta = timeCheckedOut - userTimeCheckedIn

            print(f"{interaction.user.name}'s {activity} elapsed time: {lockedInTime(elapsedTime)}")
            if len(chosen) == 1:
                await interaction.followup.send(f"{interaction.user.mention} has checked out from the sheet for {activity} activity! Locked in for {lockedInTime(elapsedTime)}")
            else:
                await interaction.followup.send(f"{interaction.user.mention} has checked out from the sheet for {activity} activities! Locked in for {lockedInTime(elapsedTime)}")

            #Copy algorithm like check-in, but paste DONE instead of ON PROGRESS for the cell update
            #Process to find row and column to update
            
            rowToFind = userTimeCheckedIn.day + rowOffset(self.userID) # 0-index based

            # Getting column is pretty hard since it needs month and activity, which is under the month. So have to get month first
            month = calendar.month_name[userTimeCheckedIn.month] # Get the month name from the date

            #Get the month name row (1-index based), has None in the list
            monthRowList = []
            if self.userID != "591939252061732900":
                monthRowList = worksheet.row_values(activityOffset(self.userID)- 1) #Offset is 1-index based, so -1 to move back onto month cell, instead of activity cell
            else:
                monthRowList = worksheet.row_values(3) # Alex only has 1 activity, so month is always on row 3 (1-index based)

            monthColumn = None
            #Loops through the monthRowList and stops until the month is found, should return the index of it
            for i, value in enumerate(monthRowList): #Index must and will be 0-index based
                if value is not None and value.strip().lower() == month.lower():
                    monthColumn :int = i
                    break
            #Checks in case month is not found
            if monthColumn is None:
                raise ValueError (f"Month '{month}' not found") 

            compiledRequests = [] # To store all requests for batch update for later

            #Get the column of the activity under the month found
            if (self.username ==  'Alex'): # Only 1 activity algorithm
                columnToFind = monthColumn 
                
                #Request section
                post_pasteLabels = { #DONE to update cell | Check-out
                        "requests": [
                            {
                                "copyPaste": {
                                    "source": {
                                        # 0-index based
                                        "sheetId": worksheetID,
                                        "startRowIndex": 2,  # Copies "DONE" Cell
                                        "startColumnIndex": 0,
                                        "endRowIndex": 3,
                                        "endColumnIndex": 1
                                    },
                                    "destination": {
                                        # 0-index based
                                        "sheetId": worksheetID,
                                        "startRowIndex": rowToFind,
                                        "startColumnIndex": i,
                                        "endRowIndex": rowToFind + 1,
                                        "endColumnIndex": i + 1
                                    },
                                    "pasteType": "PASTE_NORMAL",
                                    "pasteOrientation": "NORMAL"
                                }
                            }
                        ]
                    }
                compiledRequests.extend(post_pasteLabels["requests"]) # Add the requests to the compiled list

            else:  # 2+ activity algorithm
                columnToFind = []
                activityRow = worksheet.row_values(activityOffset(self.userID)) #Get the 4th row (1-index based), does have None in the list
                #Loops through the activityRow and stops until the first instance of activity is found, then set columnToFind as the index
                for i in range(monthColumn, len(self.userActivities[self.username]) + monthColumn): #Index must and will be 0-index based
                    if activityRow[i] is not None and activityRow[i].lower() in [a.lower() for a in self.validUserActivities]: #Check if the activity matches
                        columnToFind.append(i)
                if columnToFind == []: #Checks in case activity is not found
                    raise ValueError (f"Activity '{self.validUserActivities}' not found under month '{month}'")

                #Request section
                for i in columnToFind:
                    post_pasteLabels = { #DONE to update cell | Check-out
                        "requests": [
                            {
                                "copyPaste": {
                                    "source": {
                                        # 0-index based
                                        "sheetId": worksheetID,
                                        "startRowIndex": 2,  # Copies "DONE" Cell
                                        "startColumnIndex": 0,
                                        "endRowIndex": 3,
                                        "endColumnIndex": 1
                                    },
                                    "destination": {
                                        # 0-index based
                                        "sheetId": worksheetID,
                                        "startRowIndex": rowToFind,
                                        "startColumnIndex": i,
                                        "endRowIndex": rowToFind + 1,
                                        "endColumnIndex": i + 1
                                    },
                                    "pasteType": "PASTE_NORMAL",
                                    "pasteOrientation": "NORMAL"
                                }
                            }
                        ]
                    }
                    
                    compiledRequests.extend(post_pasteLabels["requests"]) # Add the requests to the compiled list

        if compiledRequests:
            print("Batch update successful.")
            worksheet.spreadsheet.batch_update({"requests": compiledRequests}) # Batch update all requests at once
                
        if len(chosen) == len(self.validUserActivities): # If user checked out from all activities, remove the entire username key from the dictionary
            timeCheckedInDICT.pop(self.username)
            print(f"{interaction.user.name} checked out from all of their activities")

        else : # Else, just remove the specific activity key from the dictionary
            for activity in chosen: 
                timeCheckedInDICT[self.username].pop(activity)      
            print(f"{interaction.user.name} checked out from {chosen} activity")

        saveTimeCheckins(timeCheckedInDICT) # Save the updated dictionary back to the JSON file
        
        commandEndTime = time.perf_counter()
        print(f"Checkout executed in {commandEndTime - commandStartTime:.4f} seconds\n")

    async def on_timeout(self,interaction: discord.Interaction):
        await interaction.response.send_message("Check-out menu timed out")

class CheckoutMenuView(discord.ui.View):
    def __init__(self, userID: str):
        super().__init__(timeout=60)
        self.add_item(CheckoutMenu(userID))

class sheetCommands(commands.Cog):
    commandStartTime = time.perf_counter() # To record how long loading the cog takes
    def __init__(self, bot):
        self.bot = bot 

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")
    
    
    @app_commands.command(name = "register", description = "Registers a new user onto the sheet")
    @app_commands.describe(name = "Your name to register with", activities = "Comma-separated list of a maximum five activities")
    async def register(self, interaction: discord.Interaction, name: str, activities: str):
        print(f"{interaction.user.name} is trying to register")
        commandStartTime = time.perf_counter() # To record how long the command takes to execute
        userID = str(interaction.user.id)

       #Try to load JSON file 
        ID_to_name = loadJSON('users.json')
        userActivities = loadJSON('userActivities.json')

        #Checks if user has registered already
        if userID in ID_to_name:
            await interaction.response.send_message(f"{interaction.user.mention}, you are already registered as {name}!", ephemeral=True)
            return 

        #Checks if name is valid
        if name is None or name == "":
            await interaction.response.send_message("Please provide a name to register with.", ephemeral=True)
            return
        #Checks if activity is valid
        if activities is None:
            await interaction.response.send_message("Please provide at least one activity to register with.", ephemeral=True)
            return
        else:
            activitiesList = [activity.strip() for activity in activities.split(",")]  # Split the activities string into a list
            activitiesList.sort() # Sort for consistency sake
            if len(activitiesList) > 5:
                await interaction.response.send_message("Please provide a maximum of five activities to register with.", ephemeral=True)
                return 
            
        ID_to_name[userID] = name # Adds userID and name into the dictionary
        with open('users.json', 'w') as file:
            json.dump(ID_to_name, file, indent=4) # Writes into the JSON file
        
        userActivities[name] = activitiesList # Adds name and activitiesList into the dictionary
        with open('userActivities.json', 'w') as file:
            json.dump(userActivities, file, indent=4) # Writes into the JSON file
            

        await interaction.response.defer()
        # Try to write to Google Sheet (Slow Process)
        try:
            sheet = sheetInitialization() 
            worksheet = sheet.worksheet("Participants")  

            nameColumn = worksheet.col_values(4) #Column D ~ 1 index based
            emptyRow = len(nameColumn) + 1 # Always is empty because its beneath the table

            #Update to the sheet 
            rowUpdate = [name,"",""] + activitiesList # Fills in the name, then 2 empty cells, then activities
            worksheet.update(range_name = f"D{emptyRow}:L{emptyRow}", values=[rowUpdate])
            
            #Efficient formatting 
            solidBorders = {
                "top" :{"style": "SOLID"},
                "bottom" :{"style": "SOLID"},
                "left" :{"style": "SOLID"},
                "right" :{"style": "SOLID"}
            }
            
            formats = [
                (f"D{emptyRow}:F{emptyRow}", 14),
                (f"G{emptyRow}:L{emptyRow}", 12)
            ]

            for cell_range, font_size in formats:
                worksheet.format(cell_range,
                {
                    "horizontalAlignment": "CENTER",
                    "textFormat": {"fontSize": font_size,"bold": True},
                    "borders": solidBorders
                })                
        except Exception as error:
            await interaction.followup.send(f"Error on writing to Google Sheet: {error}", ephemeral=True)
            return 
        
        print(f"{interaction.user.name} successfully registered as {name} with activities: {', '.join(activitiesList)}.")
        commandsEndTime = time.perf_counter()
        print(f"Registration executed in {commandsEndTime - commandStartTime:.4f} seconds\n")
        
        await interaction.followup.send(f"{interaction.user.mention} successfully registered as {name} with activities: {", ".join(activitiesList)}.")

    @app_commands.command(name = "checkinmenu", description = "Checks you in to the google sheet")
    async def checkinMenu(self, interaction: discord.Interaction):
        userID = str(interaction.user.id)
        ID_to_name = loadJSON('users.json')
        username = ID_to_name[userID]

        print(f"{username} is trying to check in")
        if userID not in ID_to_name: # Check if user is registered
            print(f"{username} is not registered")
            await interaction.response.send_message("You are not registered. Please register first.", ephemeral=True)
            return
        
        try:
            await interaction.response.send_message("Please select your activity to check-in:", view=CheckinMenuView(userID))
        except Exception as error:
            print(f"Error in checkinMenu: {error}\n")
            await interaction.response.send_message(f"An error has occured: {error}", ephemeral=True)


    @app_commands.command(name="checkoutmenu", description="Checks you out from the google sheet")
    async def checkoutMenu(self, interaction: discord.Interaction):
        userID = str(interaction.user.id)
        ID_to_name = loadJSON('users.json')
        username = ID_to_name[userID]
        print(f"{username} is trying to checkout")

        if userID not in ID_to_name: # Check if user is registered
            print(f"{username} is not registered")
            await interaction.response.send_message("You are not registered. Please register first.", ephemeral=True)
            return
        
        try:
            await interaction.response.send_message("Please select your activity to check-out:", view=CheckoutMenuView(userID))
        except Exception as error:
            print(f"Error in checkoutMenu: {error}\n")
            await interaction.response.send_message(f"An error has occured: {error}", ephemeral=True)

    
async def setup(bot: commands.Bot):
    GUILD_ID = discord.Object(id = 1391372922219659435) #This is my server's ID, and I'm only gonna use it for my server
    await bot.add_cog(sheetCommands(bot), guild = GUILD_ID)

  


   