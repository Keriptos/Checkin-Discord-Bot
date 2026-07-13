# Discord Imports
import discord
from discord.ext import tasks, commands

# Other Imports
import bot.helpers.utils as utls
from bot.config_builder import ConfigDTO
from bot.services.sheetService import sheetManager
import datetime
import time

# Globals
CFG = ConfigDTO()
SHEET = sheetManager.get_sheet_client()
"""
    This file will generate a new table when the current date is Dec 31
"""

def find_empty_cell_row(date: datetime.datetime, user: dict):
    
    username: str = user['username']    
    userFormat: str = user['format']
        

    # 2 approaches,
    # Approach 1: Delete existing table, remake a new one. (Users can't see past years anymore)
    # Approach 2: Use existing tables, their sheet will become a long one. 
    # (Gotta scroll for the current year if they've done this for a long time)


    # Using approach 2, search for an empty cell after existing table
    timeColumn = sheetManager.get_year_column(username)
    foundYear = False
    yearRow: int = 0 # 0-indexed. Row index of the first year. (Default value will be used for non-yearly format)
    
    start = time.perf_counter()
    if userFormat == "Yearly":
        yearRow: int = 2 # 0-indexed. Only yearly format has a different location
        while (yearRow <= len(timeColumn)):
            if (timeColumn[yearRow] == str(date.year)):
                empty_cell_row = yearRow + 33
                foundYear = True
                break

            # Skip algorithm
            yearRow += 35
        if not foundYear:
            raise ValueError(f"Year {date.year} not found")
    else:
        # Search for year
        while (yearRow <= len(timeColumn)):
            if (timeColumn[yearRow] == str(date.year)):
                foundYear = True
                break
            
            yearRow += 36
        if not foundYear:
            raise ValueError(f"Year {date.year} not found")


        # Search for yearDivisionCell
        if "Semesterly" in userFormat:
            yearDivision = "Semester 2"
        else:
            yearDivision = "Q4"    
        yearDivRow = yearRow + 2
        foundYearDiv = False
        while (yearDivRow <= len(timeColumn)):
            if (timeColumn[yearDivRow] == yearDivision):                
                empty_cell_row = yearDivRow + 34
                foundYearDiv = True
                break

            # Skip algorithm
            yearDivRow += 36   
        if not foundYearDiv:
            raise ValueError(f"Year division {yearDivision} not found")
    end = time.perf_counter()
    print(f"Found an empty cell for {username} (row: {empty_cell_row}) after existing table in {end - start:.8f} seconds")
    return empty_cell_row

    
def copiesNeeded(userFormat: str) -> int | None:
    """ It's the start of the year, so no need for dynamic selection based on months"""    
    if "Quarterly" in userFormat:        
        copiesNeeded = 4        
    elif "Semesterly" in userFormat: # Semesterly
        copiesNeeded = 2    
    elif userFormat == "Yearly": # Early exit because Yearly doesn't need a loop
        return 
    else:
        raise ValueError(f"User's format is unrecognized! {userFormat}")
    return copiesNeeded


def tableYearDupeReq(startCell: int, userID: int, user: dict):    
    userFormat = user['format']
    sheetID = utls.newUserSheetID(userID)
    userActivities = user['activities']
    totalCopies = copiesNeeded(userFormat)
    
    duplicationReq: list = []
    if userFormat == "Yearly":
        # Pre-requisites of the cell locations
        templateSheetID = sheetManager.get_worksheet(worksheet_name="Template").id
        startDestRow = startCell
        endDestRow = startCell + 34

        # Request section        
        duplicationReq.extend([
            {
                "copyPaste": { # Copas table from template sheet
                    "source": {
                        "sheetId": templateSheetID,
                        "startRowIndex": 0,
                        "endRowIndex": 34,
                        "startColumnIndex": 3,
                        "endColumnIndex": 17
                    },
                    "destination": {
                        "sheetId": sheetID,
                        "startRowIndex": startDestRow,
                        "endRowIndex": endDestRow, 
                        "startColumnIndex": 3, 
                        "endColumnIndex": 17
                    },
                    "pasteType": "PASTE_NORMAL",
                    "pasteOrientation": "NORMAL"
                }
            }        
        ])
        duplicationReq.extend([
            { # TODO: Add a delete prevention so that this won't run if the table's actually empty. It'd run faster
                "updateCells": { # Delete inner table contents
                    "rows": [
                        {"values": [{"userEnteredValue": {"stringValue": ""}}]}
                    ],
                    "fields": "userEnteredValue",
                    "range": {
                        "sheetId": sheetID,
                        "startRowIndex": startDestRow + 3,
                        "endRowIndex": startDestRow + 34,
                        "startColumnIndex": 5,
                        "endColumnIndex": 17,
                    }
                }                    
            },
            {
                "updateCells": { # Rewrite the name & activity
                    "rows": [
                        {"values": [{"userEnteredValue": {"stringValue": f"{user['username']} - {', '.join(userActivities)}"}}]}
                    ],
                    "fields": "userEnteredValue",
                    "range": {
                        "sheetId": sheetID,
                        "startRowIndex": startDestRow,
                        "endRowIndex": startDestRow + 1,
                        "startColumnIndex": 3, # Column D
                        "endColumnIndex": 4,
                    }
                }                    
            },
            {
                "updateCells": { # Rewrite the year
                    "rows": [
                        {"values": [{"userEnteredValue": {"stringValue": f"{datetime.datetime.now().year + 1}"}}]}
                    ],
                    "fields": "userEnteredValue",
                    "range": {
                        "sheetId": sheetID,
                        "startRowIndex": startDestRow + 2,
                        "endRowIndex": startDestRow + 3,
                        "startColumnIndex": 3, # Column D
                        "endColumnIndex": 4,
                    }
                }                    
            }
        ])        
        return duplicationReq
    

    # Default values, all values here are 0-indexed
    fullYear = (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September","October", "November", "December"
    )
    fullYearDivision = (
        "Semester 1", "Semester 2",
        "Q1", "Q2", "Q3", "Q4"
    )  

    # Pre-requisites of the cell positions
    startDestRow = startCell
    endDestRow = startCell + 35
    if "Semesterly" in userFormat:
        startMonth = 0
        countEnder = 6 # Dynamic loop ender offset (Each semester has 6 months)
        yearDivSelector = 0

        if userFormat == "Semesterly_Standard":
            endCol = 17
        elif userFormat == "Semesterly_Extended":
            endCol = 23

    else: # Quarterly
        yearDivSelector = 2 # Q1
        startMonth = 0 # January
        countEnder = 3 # Dynamic loop ender offset (Each quarter has 3 months)

        if userFormat == "Quarterly_Standard":
            endCol = 17
        elif userFormat == "Quarterly_Extended":
            endCol = 20
    
    # Request Section     
    while(totalCopies):
        duplicationReq.extend([
            {
                "copyPaste": { # Copas table from current sheet
                    "source": {
                        "sheetId": sheetID,
                        "startRowIndex": 0,
                        "endRowIndex": 36,
                        "startColumnIndex": 3,
                        "endColumnIndex": endCol # Dynamic column, (it really doesn't matter but prevents a bad copy)
                    },
                    "destination": {
                        "sheetId": sheetID,
                        "startRowIndex": startDestRow,
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
                "updateCells": { # Delete inner table contents
                    "rows": [
                        {"values": [{"userEnteredValue": {"stringValue": ""}}]}
                    ],
                    "fields": "userEnteredValue",
                    "range": {
                        "sheetId": sheetID,
                        "startRowIndex": startDestRow + 4,
                        "endRowIndex": startDestRow + 35,
                        "startColumnIndex": 5,
                        "endColumnIndex": endCol,
                    }
                }                    
            },
            {
                "updateCells": { # Rewrite the year
                    "rows": [
                        {"values": [{"userEnteredValue": {"stringValue": f"{datetime.datetime.now().year + 1}"}}]}
                    ],
                    "fields": "userEnteredValue",
                    "range": {
                        "sheetId": sheetID,
                        "startRowIndex": startDestRow,
                        "endRowIndex": startDestRow + 1,
                        "startColumnIndex": 3, # Column D
                        "endColumnIndex": 4,
                    }
                }                    
            },
            {
                "updateCells": { # Rewrite the yearDivision for duplication
                    "rows": [
                        {"values": [{"userEnteredValue": {"stringValue": fullYearDivision[yearDivSelector]}}]}
                    ],
                    "fields": "userEnteredValue",
                    "range": {
                        "sheetId": sheetID,
                        "startRowIndex": startDestRow + 2, # Third row
                        "endRowIndex": startDestRow + 3,
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
                            "startRowIndex": startDestRow + 2, # Third row
                            "endRowIndex": startDestRow + 3,
                            "startColumnIndex": monthIndex, # Column D
                            "endColumnIndex": monthIndex + 1,
                        }
                    }                    
                }
            ])
        
        # Incrementation
        totalCopies -= 1        
        startDestRow += 36
        endDestRow += 36
        yearDivSelector += 1
        if "Quarterly" in userFormat:
            startMonth += 3
        
    return duplicationReq


utc = datetime.timezone.utc
g_timeCheck = datetime.time(hour=0, minute=1, tzinfo= utc)


class YearCheck(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.is_end_of_year_check.start()        

    def cog_unload(self):
        self.is_end_of_year_check.cancel()        

    @tasks.loop(time = g_timeCheck)
    async def is_end_of_year_check(self):
        now = datetime.datetime.now()
        if now.month == 12 and now.day == 31: # Check for end of year (31 Dec)
            print("It's end of the year!!!")
            users = utls.loadJSON(CFG.USERS_FILE)
            for target_user_id in users.keys():
                start = time.perf_counter()
                SHEET.batch_update({"requests": tableYearDupeReq(
                    startCell = find_empty_cell_row(date = datetime.datetime.now(), user= users[target_user_id]),
                    userID = int(target_user_id),
                    user = users[target_user_id]
                )})
                end = time.perf_counter()
                print(f"Duplicated table for {users[target_user_id]['username']} in {end - start:.4f} seconds\n")
        elif now.month != 12 and now.day == 1:
            print(f"table_year_dupe: {12 - now.month} months left")
        
    @is_end_of_year_check.before_loop
    async def before_is_end_of_year_check(self):
        print('waiting...')
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    GUILD_ID = discord.Object(id = CFG.GUILD_ID)
    await bot.add_cog(YearCheck(bot), guild= GUILD_ID)

if __name__ == "__main__":
    now = datetime.datetime.fromisoformat("2027-01-31 12:05:23.283")
    if now.month == 12 and now.day == 31: # Check for end of year (31 Dec)
        print("TRUE")
    else:
        print("FALSE")
        print(f"Today's date: {now}")