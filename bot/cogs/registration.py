# Discord Imports
import discord 
from discord import app_commands
from discord.ext import commands
from bot.services.sheetService import sheetManager

# Other Imports
import bot.helpers.utils as utls
from bot.config_builder import ConfigDTO
import time
import datetime

# Globals
SHEET = sheetManager.get_sheet_client()
CFG = ConfigDTO()

def activityFormat(activities):
    amountOfActivities = len(activities)

    # Activities must be between 1 and 5
    if amountOfActivities < 1 or amountOfActivities > 5:
        raise ValueError("Invalid number of activities. Must be between 1 and 5.")
    
    # Determine the format based on the activities total
    match amountOfActivities:
        case 1: 
            return "Yearly"
        case 2:
            return "Semesterly_Standard"
        case 3: 
            return "Semesterly_Extended"
        case 4:
            return "Quarterly_Standard"
        case 5:
            return "Quarterly_Extended"



def logToParticipants(date: datetime.datetime, username: str, activityList: list):    
    worksheet = sheetManager.get_worksheet("Participants")
    participantSheet_id = worksheet.id

    nameColumn = worksheet.col_values(1) # 1-indexed
    emptyRow = len(nameColumn) # 0-indexed. A cell after the last name cell will always be empty
    
    formattedDate = date.strftime("%d %B %Y")
    rowUpdate = [username, formattedDate, ""] + activityList
    updateValuesReq = {
    "updateCells": {
        "rows": [
            {
                "values": [
                    {"userEnteredValue": {"stringValue": str(value)}} for value in rowUpdate
                ]
            }
        ],
        "start": {
            "sheetId": participantSheet_id,
            "rowIndex": emptyRow,
            "columnIndex": 0  # A column (0-indexed
        },
        "fields": "userEnteredValue"
    }}

    # Border format
    solidBorders = {
        "top" :{"style": "SOLID"},
        "bottom" :{"style": "SOLID"},
        "left" :{"style": "SOLID"},
        "right" :{"style": "SOLID"}
    }
    nameFormatReq = {
        "repeatCell": {
            "range": {
                "sheetId": participantSheet_id,
                "startRowIndex": emptyRow,
                "endRowIndex": emptyRow + 1,
                "startColumnIndex": 0,  # A
                "endColumnIndex": 2     # C (excluded)
            },
            "cell": {
                "userEnteredFormat": {
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "fontSize": 14,
                        "bold": True
                    },
                    "borders": solidBorders
                }
            },
            "fields": "userEnteredFormat"
        }
    }
    activityFormatReq = {
        "repeatCell": {
            "range": {
                "sheetId": participantSheet_id,
                "startRowIndex": emptyRow,
                "endRowIndex": emptyRow + 1,
                "startColumnIndex": 3,  # D column
                "endColumnIndex": 8    # I column
            },
            "cell": {
                "userEnteredFormat": {
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "fontSize": 12,
                        "bold": True
                    },
                    "borders": solidBorders
                }
            },
            "fields": "userEnteredFormat"
        }
    }
    worksheet.spreadsheet.batch_update({"requests": [updateValuesReq, nameFormatReq, activityFormatReq]})

def tableGeneration(date: datetime.datetime, userID: int, user: dict):
    registrationRequest = [] # A list to place all the request later on    
    worksheet = sheetManager.get_worksheet("Template")
    templateSheetID = worksheet.id

    
    username: str = user.get("username", "Unknown User")
    userActivities: list = user.get("activities", [])
    userFormat: str = user.get("format", "Format not found")


    newSheetID = utls.newUserSheetID(userID)
    templateUserLayout = utls.templateSheetLayout(username, userFormat) 
    # All indexes from here are 0-indexed. startIndex are inclusive, endIndex are exclusive
    tableSetup = [ # This list is for sheet setup
        {
            "addSheet": { # Make a new sheet for the new user
                "properties": {
                    "title": username,
                    "sheetId": newSheetID # Customized ID from 6 digits of their userID
                }
            },
        },
        {
            "copyPaste": { # Copas label table from template
                "source": {
                    "sheetId": templateSheetID, 
                    "startRowIndex": 0,
                    "endRowIndex": 11, 
                    "startColumnIndex": 0, 
                    "endColumnIndex": 2,
                },
                "destination": {
                    "sheetId": newSheetID,  
                    "startRowIndex": 0,
                    "endRowIndex": 11, 
                    "startColumnIndex": 0, 
                    "endColumnIndex": 2,
                },
                "pasteType": "PASTE_NORMAL",
                "pasteOrientation": "NORMAL"
            }
        },
        {
            "copyPaste": { # Copas table from template
                "source": {
                    "sheetId": templateSheetID,
                    "startRowIndex": templateUserLayout[username]["startRowIndex"],
                    "endRowIndex": templateUserLayout[username]["endRowIndex"], 
                    "startColumnIndex": templateUserLayout[username]["startColumnIndex"], 
                    "endColumnIndex": templateUserLayout[username]["endColumnIndex"],
                },
                "destination": {
                    "sheetId": newSheetID,
                    "startRowIndex": 0,
                    "endRowIndex": 35, 
                    "startColumnIndex": 3, # D column
                    "endColumnIndex": 23, # W column (it's actually X column but it's excluded so it's W column)
                },
                "pasteType": "PASTE_NORMAL",
                "pasteOrientation": "NORMAL"
            }
        }
    ]

    common_replacements = [] # A list to rewrite common placeholders    
    if userFormat == "Yearly":
        common_replacements.extend([
            {
                "updateCells": { #Rewrite the username placeholder to the user's username (D1)
                    "rows": [ 
                        {"values": [{"userEnteredValue": {"stringValue": f"{username} - {userActivities[0]}"}}]}  
                    ],
                    "fields": "userEnteredValue",
                    "range": {
                        "sheetId": newSheetID,
                        "startRowIndex": 0, # First row
                        "endRowIndex": 1,
                        "startColumnIndex": 3, # Column D
                        "endColumnIndex": 4,
                    }
                }
            },
            {
                "updateCells": { #Rewrite the year placeholder as today's year (D3)
                    "rows": [
                        {"values": [{"userEnteredValue": {"numberValue": date.year}}]} 
                    ],
                    "fields": "userEnteredValue",
                    "range": {
                        "sheetId": newSheetID,
                        "startRowIndex": 2, # Third row
                        "endRowIndex": 3,
                        "startColumnIndex": 3, # Column D
                        "endColumnIndex": 4,
                    }
                },
            }
            
        ])
    else:
        # Rewrite the common placeholders
        common_replacements.extend([
            {
                "updateCells": { # Rewrite the year placeholder as today's year (D3)
                    "rows": [
                        {"values": [{"userEnteredValue": {"numberValue": date.year}}]}
                    ],
                    "fields": "userEnteredValue",
                    "range": {
                        "sheetId": newSheetID,
                        "startRowIndex": 0, # First row
                        "endRowIndex": 1,
                        "startColumnIndex": 3, # Column D
                        "endColumnIndex": 4,
                    }
                },
            },
            {
                "updateCells": { # Rewrite the username placeholder as user's username (E1)
                    "rows": [
                        {"values": [{"userEnteredValue": {"stringValue": f"{username}"}}]} 
                    ],
                    "fields": "userEnteredValue",
                    "range": {
                        "sheetId": newSheetID,
                        "startRowIndex": 0, # First row
                        "endRowIndex": 1,
                        "startColumnIndex": 4, # Column E
                        "endColumnIndex": 5,
                    }
                },
            }
        ])
        
        # Rewrite the activity placeholders
        activityRow = 3
        activityRewrites: list = utls.activity_rewrites(
            newSheetID, 
            user, 
            utls.col_range_selector(user['format']), 
            activityRow)        
        common_replacements.extend(activityRewrites)

        # Time related rewrites
        time_related_rewrites: list = []
        fullYear = (
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September","October", "November", "December"
        )
        
        fullYearDivision = (
            "Semester 1", "Semester 2",
            "Q1", "Q2", "Q3", "Q4"
        )

        startMonth = 0 # Default value. If this stays 0, the loop for rewriting month won't execute
        if "Semesterly" in userFormat:            
            if date.month < 6:
                yearDivSelector = 0
            else :
                yearDivSelector = 1
                startMonth = countEnder = 6                
        elif "Quarterly" in userFormat:
            countEnder = 3

            if date.month <= 3:
                startMonth = 0
                yearDivSelector = 2
            elif date.month <= 6:
                startMonth = 3
                yearDivSelector = 3
            elif date.month <= 9:         
                startMonth = 6
                yearDivSelector = 4
            else :
                yearDivSelector = 5

        # Rewrite month
        if startMonth != 0:
            for month in range(startMonth, startMonth + countEnder):
                if "Semesterly" in userFormat:
                    monthIndex = 6 + (len(userActivities) * (month % 6)) - 1
                else: 
                    monthIndex = 6 + (len(userActivities) * (month % 3)) - 1
                time_related_rewrites.extend([
                    {
                        "updateCells": {
                            "rows": [
                                {"values": [{"userEnteredValue": {"stringValue": f"{fullYear[month]}"}}]} 
                            ],
                            "fields": "userEnteredValue",
                            "range": {
                                "sheetId": newSheetID,
                                "startRowIndex": 2, # Third row
                                "endRowIndex": 3,
                                "startColumnIndex": monthIndex, # Column D
                                "endColumnIndex": monthIndex + 1,
                            }
                        }                    
                    }
                ])
        # Rewrite year division (semester/quarter)
        time_related_rewrites.extend([            
            {
                "updateCells": {
                    "rows": [
                        {"values": [{"userEnteredValue": {"stringValue": f"{fullYearDivision[yearDivSelector]}"}}]} 
                    ],
                    "fields": "userEnteredValue",
                    "range": {
                        "sheetId": newSheetID,
                        "startRowIndex": 2, # Third row
                        "endRowIndex": 3,
                        "startColumnIndex": 3, # Column D
                        "endColumnIndex": 4,
                    }
                }
            }
        ])


    tableSetup.extend(common_replacements)
    if userFormat != "Yearly": tableSetup.extend(time_related_rewrites)
    registrationRequest.extend(tableSetup)
    return registrationRequest


def copiesNeeded(date: datetime.datetime, userFormat: str) -> int:
    if "Quarterly" in userFormat:
        if date.month <= 3:
            copiesNeeded = 3
        elif date.month <= 6:
            copiesNeeded = 2
        elif date.month <= 9:
            copiesNeeded = 1
        else:
            copiesNeeded = 0
    elif "Semesterly" in userFormat:
        if date.month <= 6:
            copiesNeeded = 1
        else:
            copiesNeeded = 0
    return copiesNeeded


def tableDuplication(date: datetime.datetime, userID: int, user: dict):
    """ Duplicate table for non yearly table formats. Only used for registration"""

    userFormat = user['format']
    if userFormat == "Yearly": # Early exit, tableDuplication is not designed for Yearly as it is not needed
        return ValueError(f"Not supported for {userFormat} format!")
    
    sheetID = utls.newUserSheetID(userID)
    userActivities = user['activities']
    totalCopies = copiesNeeded(date, userFormat)

    if totalCopies == 0:
        print("No duplication needed!")
        return

    # Default values, all values here are 0-indexed
    fullYear = (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September","October", "November", "December"
    )
    fullYearDivision = (
        "Semester 1", "Semester 2",
        "Q1", "Q2", "Q3", "Q4"
    )  

    if "Semesterly" in userFormat:
        startMonth = countEnder = 6 # Duplication continues after the 1st semester.        
        yearDivSelector = 1 # Semester 1 is not needed

        if userFormat == "Semesterly_Standard":
            endCol = 17
        elif userFormat == "Semesterly_Extended":
            endCol = 23

    elif "Quarterly" in userFormat:
        starDestRow = 36
        endDestRow = 71
        countEnder = 3

        if userFormat == "Quarterly_Standard":
            endCol = 17
        elif userFormat == "Quarterly_Extended":
            endCol = 20
                
        # Determine the month name rewrites
        if date.month <= 3: # 3 copies
            yearDivSelector = 3
            startMonth = 3 # April
        elif date.month <= 6: # 2 copies
            yearDivSelector = 4 
            startMonth = 6 # July
        elif date.month <= 9: # 1 copy
            yearDivSelector = 5
            startMonth = 9 # October        
                
                
    duplicationReq: list = []
    while(totalCopies >= 1):
        duplicationReq.extend([
            {
                "copyPaste": { # Copas table from current sheet
                    "source": {
                        "sheetId": sheetID,
                        "startRowIndex": 0,
                        "endRowIndex": 35,
                        "startColumnIndex": 3,
                        "endColumnIndex": endCol # Dynamic column, (it really doesn't matter but prevents a bad copy)
                    },
                    "destination": {
                        "sheetId": sheetID,
                        "startRowIndex": starDestRow,
                        "endRowIndex": endDestRow, 
                        "startColumnIndex": 3, 
                        "endColumnIndex": endCol
                    },
                    "pasteType": "PASTE_NORMAL",
                    "pasteOrientation": "NORMAL"
                }
            }
        ])
              
        duplicationReq.extend([
            {
                "updateCells": { # Rewrite the month for duplication
                    "rows": [
                        {"values": [{"userEnteredValue": {"stringValue": fullYearDivision[yearDivSelector]}}]}
                    ],
                    "fields": "userEnteredValue",
                    "range": {
                        "sheetId": sheetID,
                        "startRowIndex": starDestRow + 2, # Third row
                        "endRowIndex": starDestRow + 3,
                        "startColumnIndex": 3, # Column D
                        "endColumnIndex": 4,
                    }
                }                    
            }
        ])
                
        for month in range(startMonth, startMonth + countEnder):
            if "Semesterly" in userFormat:
                monthIndex = 6 + (len(userActivities) * (month % 6)) - 1
            else: 
                monthIndex = 6 + (len(userActivities) * (month % 3)) - 1
            duplicationReq.extend([
                {
                    "updateCells": { # Rewrite the month for duplication
                        "rows": [
                            {"values": [{"userEnteredValue": {"stringValue": f"{fullYear[month]}"}}]} 
                        ],
                        "fields": "userEnteredValue",
                        "range": {
                            "sheetId": sheetID,
                            "startRowIndex": starDestRow + 2, # Third row
                            "endRowIndex": starDestRow + 3,
                            "startColumnIndex": monthIndex, # Column D
                            "endColumnIndex": monthIndex + 1,
                        }
                    }                    
                }
            ])

        # Incrementation
        totalCopies -= 1        
        if userFormat == "Yearly":
            starDestRow += 35 
            endDestRow += 35
        else:
            starDestRow += 36
            endDestRow += 36

            yearDivSelector += 1
            if "Quarterly" in userFormat:
                startMonth += 3
        
    return duplicationReq    

class Registration (commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")


    @app_commands.command(name = "register", description = "Registers a new user onto the sheet")
    @app_commands.describe(
        name = "A username to register with. Defaulted to your discord name",
        activity1 = "Your required first activity",
        activity2 = "Your second activity",
        activity3 = "Your third activity",
        activity4 = "Your fourth activity",
        activity5 = "Your fifth activity")
    
    async def register(
        self, 
        interaction: discord.Interaction,        
        activity1: str,
        activity2: str = None,
        activity3: str = None,
        activity4: str = None,
        activity5: str = None,
        name: str = None
        ):
        print(f"{interaction.user.name} is trying to register")
        commandStartTime = time.perf_counter()
        userID = str(interaction.user.id)
        usersData = utls.loadJSON(CFG.USERS_FILE)
        
        # Validations
        if userID in usersData:
            print(f"{interaction.user.name} has already registered! Stopping registration process.\n")
            username = usersData[userID]['username']
            await interaction.response.send_message(f"{interaction.user.mention}, you are already registered as {username}!", ephemeral=True)
            return 

        # Checks if activity is valid
        if activity1 is None:
            await interaction.response.send_message("Please provide at least one activity to register with.", ephemeral=True)
            return    
        
        await interaction.response.defer()
        if name is None:
            name = interaction.user.name
            await interaction.followup.send("Your username will be your discord username. Syncing...", ephemeral=True)


        try:       
            temp: list = [activity1, activity2, activity3, activity4, activity5]
            activityList: list = sorted([activity.strip().capitalize() for activity in temp if activity is not None])            

            # Write the data to local file
            processStartTime = time.perf_counter()
            usersData[userID] = {} # Make a new dict for the user
            usersData[userID]['username'] = name 
            usersData[userID]['activities'] = activityList 
            usersData[userID]['format'] = activityFormat(activityList) 
            utls.saveJSON(usersData, CFG.USERS_FILE)
            processEndTime = time.perf_counter()
            print(f"Registered as {name} into the local logs in {processEndTime - processStartTime:.4f} seconds")
        except Exception as error:
            print(f"An error has occured when registering locally! {error}")

        
        # Try to write to Google Sheet (Slow Process)
        try:             
            # Write the user onto the Participants worksheet
            processStartTime = time.perf_counter()
            logToParticipants(datetime.datetime.now(), name, activityList)
            processEndTime = time.perf_counter()
            print(f"Succesfully logged {name} to participants sheet in {processEndTime - processStartTime:.4f} seconds")


            # Make new sheet and table for the user 
            processStartTime = time.perf_counter()
            SHEET.batch_update({"requests": tableGeneration(                
                date = datetime.datetime.now(),
                userID = int(userID),
                user= usersData.get(userID))})
            processEndTime = time.perf_counter()
            print(f"Added {name}'s sheet in {processEndTime - processStartTime:.4f} seconds")

        except Exception as error:
            print(f"An error has occured, {error}")
            await interaction.followup.send(f"An error has occurred, {error}", ephemeral=True)
            return 
        
        # Print success logs
        print(f"{interaction.user.name} successfully registered as {name} with activities: {', '.join(activityList)}.")
        await interaction.followup.send(f"{interaction.user.mention} successfully registered as {name} with activities: {", ".join(activityList)}.")
        commandEndTime = time.perf_counter()
        print(f"Registration executed in {commandEndTime - commandStartTime:.4f} seconds\n")

    @app_commands.command(name="signout", description="Signs out from the sheet. Will delete your sheet data upon initiating")
    async def signout(self, interaction: discord.Interaction):
        command_start_time = time.perf_counter()
        print(f"{interaction.user.name} is trying to sign-out")

        userID = str(interaction.user.id)
        usersData: dict = utls.loadJSON(CFG.USERS_FILE)
        # Validations
        if userID not in usersData:
            print(f"{interaction.user.name} tried to sign-out but hasn't registered")
            await interaction.response.send_message(f"Can't sign out if you haven't registered!", ephemeral=True)
            return
        
        await interaction.response.defer()
        try:            
            local_deletion_start = time.perf_counter()
            registered_name: str = usersData[userID]["username"]
            del usersData[userID]
            utls.saveJSON(usersData, CFG.USERS_FILE)
            local_deletion_end = time.perf_counter()
            print(f"Local deletion finished in {local_deletion_end - local_deletion_start:.8f} seconds")

            sheet_deletion_start = time.perf_counter()
            SHEET.del_worksheet(sheetManager.get_worksheet(registered_name))
            sheet_deletion_end = time.perf_counter()
            print(f"Sheet deletion finished in {sheet_deletion_end - sheet_deletion_start:.4f} seconds")
            

        except Exception as error:
            print(f"{interaction.user.name}'s ID was not found: {error}")            
            await interaction.followup.send(f"Your data lookup went wrong {error}\n", ephemeral=True)
            return
        command_end_time = time.perf_counter()
        print(f"Signing out {registered_name} took {command_end_time - command_start_time:4f} seconds\n")
        await interaction.followup.send(f"You've been signed out!")

async def setup(bot: commands.Bot):    
    _GUILD_ID = discord.Object(id = CFG.GUILD_ID)
    await bot.add_cog(Registration(bot), guild = _GUILD_ID)