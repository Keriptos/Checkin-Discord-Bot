#Discord Imports
import discord 
from discord import app_commands
from discord.ext import commands

#Google Sheets Imports
import gspread 
from gspread import Spreadsheet
from google.oauth2.service_account import Credentials

#Other Imports
import time
import datetime
from datetime import timedelta
import calendar
import json

def sheetInitialization():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("credentials.json", scopes = scopes)
    client = gspread.authorize(creds)

    sheetID = "1f77PidWRZtb2uaV5_QOLL6QBRhVlFx0tKiVodq9hwKE"
    sheet = client.open_by_key(sheetID)
    return sheet

def loadJSON(file_path):
    import os
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
        json.dump(data, file, indent=4)


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


def newUserSheetID(userID: str):
    newSheetID = int(userID) % 1_000_000_000
    return newSheetID


def templateSheetLayout(username: str, format: str): # All index are 0-based
    FORMATS = { # These are the static table locations that are in "Template" sheet, don't use this after copying once
        "Yearly": (0, 34, 3, 17),    # yearly | 3 -> D column | 17 -> Q column (exclusive)
        "Semesterly_Standard": (35, 70, 3, 17),   # semester
        "Semesterly_Extended": (35, 70, 18, 38),  # semester (alternate) | 18 -> S column | 38 is AL column (exclusive)
        "Quarterly_Standard": (71, 106, 3, 17),  # quarter
        "Quarterly_Extended": (71, 106, 18, 35), # quarter (alternate) | 18 -> S column | 35 is AI column (exclusive)
    }
    startRow, endRow, startCol, endCol = FORMATS[format]
    data = {
        username: {
            "startRowIndex": startRow,
            "endRowIndex": endRow,
            "startColumnIndex": startCol,
            "endColumnIndex": endCol,
        }
    }
    return data

def logToParticipants(sheet: Spreadsheet, date: datetime.datetime, username: str, activityList: list):
    worksheet = sheet.worksheet("Participants")
    participantSheet_id = worksheet.id

    nameColumn = worksheet.col_values(4) # 1-indexed
    emptyRow = len(nameColumn) # 0-indexed. A cell after the last name cell will always be empty
    
    formattedDate = date.strftime("%d %B %Y")
    rowUpdate = [username, formattedDate, ""] + activityList
    updateValuesReq = {
    "updateCells": {
        "rows": [
            {
                "values": [
                    {"userEnteredValue": {"stringValue": str(value)}}
                    for value in rowUpdate
                ]
            }
        ],
        "start": {
            "sheetId": participantSheet_id,
            "rowIndex": emptyRow,
            "columnIndex": 3  # D column (0-indexed)
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
                "startColumnIndex": 3,  # D
                "endColumnIndex": 6     # F
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
                "startColumnIndex": 6,  # G
                "endColumnIndex": 12    # L
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
    sheet.batch_update({"requests": [updateValuesReq, nameFormatReq, activityFormatReq]})

def tableGeneration(sheet: Spreadsheet, date: datetime, userID: int, users: dict):
    registrationRequest = [] # A list to place all the request later on
    worksheet = sheet.worksheet("Template")
    templateSheetID = worksheet.id

    
    username = users.get("username", "Unknown User")
    userActivities = users.get("activities", [])
    userFormat = users.get("format", "Format not found")


    newSheetID = newUserSheetID(userID)
    templateUserLayout = templateSheetLayout(username, userFormat) 
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
            "copyPaste": { #Copas label table from template
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
                    "endRowIndex": 36, 
                    "startColumnIndex": 3, # D column
                    "endColumnIndex": 23, # W column (it's actually X column but it's excluded so it's W column)
                },
                "pasteType": "PASTE_NORMAL",
                "pasteOrientation": "NORMAL"
            }
        }
    ]

    replacements = [] # A list to rewrite common placeholders
    activityRewrites  = [] # A list to rewrite activity placeholders
    if userFormat == "Yearly":
        replacements.extend([
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
    elif userFormat != "Yearly":
        # Rewrite the common placeholders
        replacements.extend([
            {
                "updateCells": { #Rewrite the year placeholder as today's year (D3)
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
                "updateCells": { #Rewrite the username placeholder as user's username (E1)
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
    
        # Rewrite semester/quarter
        if "Semesterly" in userFormat:
            semesterTuple = ("Semester 1", "Semester 2")
            if date.month < 6:
                semesterSelector = 0
            else :
                semesterSelector = 1
            replacements.extend([
                {
                    "updateCells": { #Rewrite the quarter placeholder as current semester (D3)
                        "rows": [
                            {"values": [{"userEnteredValue": {"stringValue": f"{semesterTuple[semesterSelector]}"}}]} 
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
        elif "Quarterly" in userFormat:
            quarterTuple = ("Q1", "Q2", "Q3", "Q4")
            if date.month <= 3:
                quarterSelector = 0
            elif date.month > 3 and date.month <= 6:
                quarterSelector = 1
            elif date.month > 6 and date.month <= 9:                
                quarterSelector = 2
            else :
                quarterSelector = 3
            replacements.extend([
                    {
                        "updateCells": { #Rewrite the quarter placeholder as current semester (D3)
                            "rows": [
                                {"values": [{"userEnteredValue": {"stringValue": f"{quarterTuple[quarterSelector]}"}}]} 
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
        
        # Since this is registration, it'd be fixed
        # Rewrite the activity placeholders
        activityRow = 3        
        if userFormat == "Semesterly_Standard":
            for col in range(5, 17): # Starts from column F, ends at column Q (col 16)          
                if col % 2 == 1:
                    selector = 0
                else:
                    selector = 1
                activityRewrites.extend([{
                    "updateCells": { 
                        "rows": [
                            {"values": [{"userEnteredValue": {"stringValue": f"{userActivities[selector]}"}}]} 
                        ],
                        "fields": "userEnteredValue",
                        "range": {
                            "sheetId": newSheetID,
                            "startRowIndex": activityRow, 
                            "endRowIndex": activityRow + 1,
                            "startColumnIndex": col, 
                            "endColumnIndex": col + 1,
                        }
                    }   
                }])                
        elif userFormat == "Semesterly_Extended":
            for col in range(5, 23): # Starts from column F, ends at column W (col 22)       
                if col % 3 == 2:
                    selector = 0
                elif col % 3 == 0:
                    selector = 1
                else :
                    selector = 2
                activityRewrites.extend([{
                    "updateCells": { #Rewrite the activity placeholders
                        "rows": [
                            {"values": [{"userEnteredValue": {"stringValue": f"{userActivities[selector]}"}}]} 
                        ],
                        "fields": "userEnteredValue",
                        "range": {
                            "sheetId": newSheetID,
                            "startRowIndex": activityRow, 
                            "endRowIndex": activityRow + 1,
                            "startColumnIndex": col, 
                            "endColumnIndex": col + 1,
                        }
                    }   
                }])
        elif userFormat == "Quarterly_Standard":
            for col in range(5, 17): # Starts from column F, ends at column Q (col 16)           
                if col % 4 == 1:
                    selector = 0
                elif col % 4 == 2:
                    selector = 1
                elif col % 4 == 3: 
                    selector = 2
                else:
                    selector = 3
                activityRewrites.extend([{
                    "updateCells": { #Rewrite the activity placeholders
                        "rows": [
                            {"values": [{"userEnteredValue": {"stringValue": f"{userActivities[selector]}"}}]} 
                        ],
                        "fields": "userEnteredValue",
                        "range": {
                            "sheetId": newSheetID,
                            "startRowIndex": activityRow, 
                            "endRowIndex": activityRow + 1,
                            "startColumnIndex": col, 
                            "endColumnIndex": col + 1,
                        }
                    }   
                }])
        elif userFormat == "Quarterly_Extended":
            for col in range(5, 20): # Starts from column F, ends at column T (col 19)
                if col % 5 == 0:
                    selector = 0
                elif col % 5 == 1:
                    selector = 1
                elif col % 5 == 2:
                    selector = 2
                elif col % 5 == 3: 
                    selector = 3
                elif col % 5 == 4:
                    selector = 4
                else:
                    selector = 5
                activityRewrites.extend([{
                    "updateCells": { #Rewrite the activity placeholders
                        "rows": [
                            {"values": [{"userEnteredValue": {"stringValue": f"{userActivities[selector]}"}}]} 
                        ],
                        "fields": "userEnteredValue",
                        "range": {
                            "sheetId": newSheetID,
                            "startRowIndex": activityRow, 
                            "endRowIndex": activityRow + 1,
                            "startColumnIndex": col, 
                            "endColumnIndex": col + 1,
                        }
                    }   
                }])
        replacements.extend(activityRewrites)


    tableSetup.extend(replacements)
    registrationRequest.extend(tableSetup)
    return registrationRequest

class Registration (commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")

    @app_commands.command(name = "demo_register", description = "Registers a new user onto the sheet")
    @app_commands.describe(name = "A username to register with. Defaulted to your discord name", activities = "Comma-separated list of a maximum five activities")
    async def register(self, interaction: discord.Interaction, activities: str, name: str = None):
        print(f"{interaction.user.name} is trying to register")
        commandStartTime = time.perf_counter() # To record how long the command takes to execute
        STR_userID = str(interaction.user.id)

        usersData = loadJSON('demo.json')

        #Checks if name is none
        if name is None or name == "":
            name = interaction.user.global_name
            await interaction.response.send_message("Your username will be your discord username", ephemeral=True)

        #Checks if activity is valid
        if activities is None:
            await interaction.response.send_message("Please provide at least one activity to register with.", ephemeral=True)
            return
        else:
            # Get the activities from the command, seperate them and insert them into the list
            activityList = [activity.strip() for activity in activities.split(",")]
            activityList.sort() # Sort for consistency sake
            if len(activityList) > 5:
                await interaction.response.send_message("Please provide a maximum of five activities to register with.", ephemeral=True)
                return 
         
        # Check if userID is already registered. If not, save user's details locally
        if STR_userID in usersData: 
            print(f"{name} has already registered! Stopping registration process.")
            await interaction.response.send_message(f"{interaction.user.mention}, you are already registered as {name}!", ephemeral=True)
            return 
        else : 
            usersData[STR_userID] = {} # Make a new dict for the user
            usersData[STR_userID]['username'] = name # Add username in the user's dict
            usersData[STR_userID]['activities'] = activityList # Add activities in the user's dict
            usersData[STR_userID]['format'] = activityFormat(activityList) # Add format in the user's dict

        # Save the data to local
        processStartTime = time.perf_counter()
        saveJSON(usersData, 'demo.json')
        processEndTime = time.perf_counter()
        print(f"Added {name} into the local logs in {processEndTime - processStartTime:.4f} seconds")


        await interaction.response.defer()
        # Try to write to Google Sheet (Slow Process)
        try: 
            sheet = sheetInitialization()   

            # Write the user onto the Participants worksheet
            processStartTime = time.perf_counter()
            logToParticipants(sheet, date = datetime.datetime.now(), username = name, activityList = activityList)
            processEndTime = time.perf_counter()
            print(f"Succesfully logged {name} to participants sheet in {processEndTime - processStartTime:.4f} seconds")


            #Make new sheet and table for the user 
            processStartTime = time.perf_counter()
            sheet.batch_update({"requests": tableGeneration(
                sheet = sheet, 
                date = datetime.datetime.now(), 
                userID = int(STR_userID),
                users= usersData.get(STR_userID))})
            processEndTime = time.perf_counter()
            print(f"Added {name}'s sheet in {processEndTime - processStartTime:.4f} seconds")

        except Exception as error:
            print(f"An error has occured, {error}")
            await interaction.followup.send(f"An error has occurred, {error}", ephemeral=True)
            return 
        
        # Print success logs
        await interaction.followup.send(f"{interaction.user.mention} successfully registered as {name} with activities: {", ".join(activityList)}.")
        print(f"{interaction.user.name} successfully registered as {name} with activities: {', '.join(activityList)}.")
        commandEndTime = time.perf_counter()
        print(f"Registration command finish executed in {commandEndTime - commandStartTime:.4f} seconds\n")

async def setup(bot: commands.Bot):
    GUILD_ID = discord.Object(id = 1391372922219659435) #This is my server's ID, and I'm only gonna use it for my server
    await bot.add_cog(Registration(bot), guild = GUILD_ID)