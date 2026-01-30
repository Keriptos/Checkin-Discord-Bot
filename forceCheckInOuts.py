#Google Sheets Imports
import gspread 
from gspread import Worksheet, Spreadsheet
from google.oauth2.service_account import Credentials
from gspread_formatting import *

#Other Imports
import json
import os
import datetime
from datetime import timedelta
from enum import Enum # For defining labels
import time # To track how long commands take to execute

sheet = None

def lockedInTime(elapsedTime: timedelta):
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
            json.dump({}, file) # create an empty file
    try:
        with open(file_path) as file: 
            return json.load(file)
    except json.decoder.JSONDecodeError:
        with open(file_path, 'w') as file:
            json.dump({}, file)  # Create an empty JSON file if it doesn't exist or is invalid
    return {}

def saveJSON(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent = 4)

def sheetInitialization():
    start = time.perf_counter()
    global sheet
    if sheet is None:
        from dotenv import load_dotenv
        load_dotenv(".env")
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file("credentials.json", scopes = scopes)
        client = gspread.authorize(creds)

        googlesheetID = os.getenv("googleSheetID")
        sheet = client.open_by_key(googlesheetID)
        end = time.perf_counter()
        print(f"Succesfully opened sheet client in {end - start:4f} seconds")
    return sheet



    
    


"""
Check-In Process 
----------------------------------------------------------
(1 Activity)
Year --> Month --> Date
1. Get timestamp right now (YY:MM:DD, the format doesn't matter)
2. Get yearCell (0 by default). If not found, jump by (put number here) cells. Repeat until found
3. When yearCell is found, get the monthRowList (it's 2 rows below yearCell). monthRowLocation = yearCell + 2
4. Get rowToFind (the first ever day is a row after monthRowList, so rowToFind = monthRowLocation + current day)
5. Get month name from the monthRowList, that value (aka the index) will be monthColumn.
6. If monthColumn is found, set colToFind as monthColumn
---------------------------------------------------------- 
(2+ Activities)
Year --> Year Division (Semester or Quarter) --> Month --> Activity --> Date
1. Get timestamp right now (YY:MM:DD, the format doesn't matter)
2. Get yearCell. If not found, jump by (put number here) cells. Repeat until found
3. When yearCell is found, get the monthRowList (it's 2 rows below yearCell). monthRowLocation = yearCell + 2

(Search rowToFind)
4. Get activityRowList (it's a row after monthRowList). activityRowLocation = monthRowLocation + 1
5. Get rowToFind (the first ever day is a row after activityRow, so rowToFind = activityRowLocation + date.day)

{Search colToFind (list), since checked in for mulitple activities }
6. Get month name from the monthRow, that value (aka the index) will be monthColumn.
7. If monthColumn is found, loop through the merged cells (the length of the merge cells is the index of month + activites count from user)
8. If the activity header matches with the activity the user has checked in for, append colToFind as the iterator from the loop
"""


"""
OPTIMIZATIONS?

Put month on enums, because monthColumn are basically constants. Just count the index and offset them by len of activities
Save the check-in cell, so that check-out process doesn't need to fetch anything


"""

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
    print(f"Found yearCell in {processEndTime - processStartTime:.4f} seconds")

    return yearCell, timeColumn


class YearDivisionDTO():
    def __init__ (self, yearDivToFind: str, yearCell: dict, timeColumn: list):
        self.yearDivToFind = yearDivToFind
        self.yearCell = yearCell
        self.timeColumn = timeColumn

# Search for year division like Semester 1, Q2, etc
def getYearDivision(DTO: YearDivisionDTO):    
    start = time.perf_counter()    

    # Default values are 1-indexed)
    yearDivisionCell = { 
        "row": DTO.yearCell["row"] + 2,
        "col": DTO.yearCell["col"]
    }

    # Search the yearDivRow
    found = False   
    yearDivRow = yearDivisionCell["row"] 
    while (yearDivRow <= len(DTO.timeColumn)):  
        if (DTO.timeColumn[yearDivRow - 1] == DTO.yearDivToFind): # the index was decremented by 1 so it's 0-indexed
            yearDivisionCell['row'] = yearDivRow
            found = True
            break

        # Skip algorithm
        yearDivRow += 36
    
    end = time.perf_counter()
    print(f"Found yearDivisionCell '{DTO.yearDivToFind}' in {end - start:.8f} seconds")
    if not found:
        raise ValueError(f"{DTO.yearDivToFind} not found")

    return yearDivisionCell

def getMonthCell(userID: str, date: datetime.datetime, yearCell: dict, yearDivCell: dict | None):
    # All values are 1 - indexed
    monthStart = time.perf_counter()
    usersData = loadJSON('users.json')
    
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
    print(f"Completed month search in {monthEnd - monthStart:.8f} seconds")
    return monthCell

class CheckInOutsDTO():
    def __init__(self, userID: int):
        self.userID = str(userID)
        self.usersData = loadJSON('users.json')
        user = self.usersData[self.userID]
        self.username = user['username']
        self.userFormat = user['format']
        self.userActivities = user['activities']

# Update to sheets (Check-in)
def CheckIn(DTO: CheckInOutsDTO, chosen: list):
    commandStartTime = time.perf_counter()
    print("Going to sheets")
    sheet = sheetInitialization()
    worksheet = sheet.worksheet(DTO.username) # Get the worksheet for the userID
    worksheetID = worksheet.id

    date = datetime.datetime.now() # Get the value from userID, which is the time checked in for that specific user
    
    # Get year, timeColumn is a column gotten by Sheet API to gather all values from the year and yearDivison column (D column) 
    yearCell, timeColumn = getYearCell(DTO.userFormat, worksheet, date) 
        
    # Get year divison (semester or quarter) - Only for non-yearly formats
    yearDivCell = None
    monthCell = getMonthCell(DTO.userID, date, yearCell, yearDivCell)


    # Set-up cache when checking in
    try:
        startCache = time.perf_counter()
        sheetCache = loadJSON('sheetCache.json')
        if DTO.userID not in sheetCache:
            sheetCache[DTO.userID] = {}
            sheetCache[DTO.userID]['username'] = DTO.username
            sheetCache[DTO.userID]['activities'] = {}
            for activity in chosen:
                sheetCache[DTO.userID]['activities'][activity] = {}
                sheetCache[DTO.userID]['activities'][activity]['checkinCell'] = {}
        saveJSON(sheetCache, 'sheetCache.json')
        endCache = time.perf_counter()
        print(f"Sucessfully set up {DTO.username}'s check-in cache in {endCache - startCache:.8f} seconds")
    except Exception as error:
        print(f"An error has occured when setting up to sheet_cache {error}")


    if DTO.userFormat == 'Yearly':
        """
        Year -> Month -> Date
        """
        # Get rowToFind and columnToFind. Decrement by 1 so that it's 0-indexed
        rowColStart = time.perf_counter()
        rowToFind = (monthCell["row"] - 1) + date.day  # The first day is a row after monthRow. 
        columnToFind = monthCell["col"] - 1 # Since there's only 1 activity, columnToFind is just monthColumn
        for activity in chosen:
            sheetCache[DTO.userID]['activities'][activity]['checkinCell']['row']= rowToFind 
            sheetCache[DTO.userID]['activities'][activity]['checkinCell']['col']= columnToFind
        rowColEnd = time.perf_counter()
        saveJSON(sheetCache, 'sheetCache.json')
        print(f"Sucessfully wrote {DTO.username}'s checkinCell into sheetCache in {rowColEnd - rowColStart:.8f} seconds")

        # Request section
        compiledRequests = [] 
        CheckInReq = { #Write 'ON PROGRESS' or 'DONE' to update cell (we used conditional formatting when making the table) 
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
        
        yearDivToFind = setYearDivisionFormat(DTO.userFormat, date)
        DTO = YearDivisionDTO(yearDivToFind, yearCell, timeColumn)
        yearDivCell = getYearDivision(DTO)
        monthCell = getMonthCell(DTO.userFormat, date, yearCell, yearDivCell)


        rowToFind = monthCell["row"] + date.day # The first day is 2 rows after monthRow. (0-indexed)
        sheetCache = loadJSON('sheetCache.json')
        sheetCache[DTO.userID]['activities'][activity]['checkinCell']['row'] = rowToFind

        # Map the activities, offset it based on monthCell, and save it to sheetCache
        activityIndex = {}
        for index, activity in enumerate(DTO.userActivities):
            activityIndex[activity] = index

        columnToFind = []
        for activity in chosen:
            if activity in activityIndex:
                baseIndex = activityIndex[activity]
                offset = baseIndex + monthCell["col"] - 1         
                columnToFind.append(offset)
                sheetCache[DTO.userID]['activities'][activity]['checkinCell']['col'] = offset
            else:
                raise ValueError(f"Activity '{activity}' not found")
        saveJSON(sheetCache, 'sheetCache.json')
            
        # Request section        
        compiledRequests = [] # To store all requests for batch update for later
        for col in columnToFind:
            CheckInOutsReq = { # Write 'ON PROGRESS' or 'DONE' to update cell (we used conditional formatting when making the table)
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
            compiledRequests.extend(CheckInOutsReq["requests"])


    if compiledRequests is not None:
        processStartTime = time.perf_counter()
        worksheet.spreadsheet.batch_update({"requests": compiledRequests})
        print("Batch update successful.")
        processEndTime = time.perf_counter()        
        print(f"Sucessfully checked in user in {processEndTime - processStartTime:.4f} seconds")        
    else:
        print("PANIC")

    commandEndTime = time.perf_counter()
    print(f"Sucessfully executed check-in command in {commandEndTime - commandStartTime:.4f} seconds")   
    
        
def CheckOut(DTO: CheckInOutsDTO, chosen: list):
    commandStartTime = time.perf_counter()
    sheet = sheetInitialization()
    worksheet = sheet.worksheet(DTO.username)
    worksheetID = worksheet.id

    # Get rowToFind and columnToFind from sheetCache
    sheetCache: dict = loadJSON('sheetCache.json')
    compiledRequests = []
    for activity in chosen:
        rowToFind = sheetCache[DTO.userID]['activities'][activity]['checkinCell']['row']
        columnToFind = sheetCache[DTO.userID]['activities'][activity]['checkinCell']['col']

        # Request section
        CheckOutReq = { #Write 'ON PROGRESS' or 'DONE' to update cell (we used conditional formatting when making the table) 
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

    if compiledRequests is not None:
        processStartTime = time.perf_counter()
        worksheet.spreadsheet.batch_update({"requests": compiledRequests})
        print("Batch update successful.")
        processEndTime = time.perf_counter()   
        print(f"Sucessfully checked out user in {processEndTime - processStartTime:.4f} seconds")
    else :
        print("PANIC")

    try:             
        startCheckinCache = time.perf_counter()
        # Delete activty dict from user   
        if DTO.userFormat == 'Yearly':
            del sheetCache[DTO.userID]

        else: 
            for activity in chosen:
                print(f"Activity: {activity} checkinCell: {sheetCache[DTO.userID]['activities'][activity]['checkinCell']}")
                del sheetCache[DTO.userID][activity]
        
            # Activity check in sheetCache to see if user have checked out from all their activities
            hasFullyCheckedOut = True
            for activity in DTO.userActivities:
                if activity in sheetCache[DTO.userID]['activities'].keys():
                    hasFullyCheckedOut = False
                    break
            if hasFullyCheckedOut:
                print(f"{DTO.username} with ID: {DTO.userID} has checked out from all their activities")
                del sheetCache[DTO.userID]
                endCheckinCache = time.perf_counter()
                print(f"Succesfully deleted {DTO.username}'s {chosen} check-in cache in {endCheckinCache - startCheckinCache:8f} seconds")                
            else:
                print(f"{DTO.username} is not fully checked-out yet")


        saveJSON(sheetCache, 'sheetCache.json')
        
    except Exception as error:
        print(f"An error has occured when deleting user's dict from sheet_cache {error}")
    commandEndTime = time.perf_counter()
    print(f"Sucessfully executed check-out command in {commandEndTime - commandStartTime:.4f} seconds")   

# Fill in the MUST FILL section
def main():    
    """--------- MUST FILL!------------"""

    userID = 591939252061732900
    chosen = ['Coding']

    """--------- MUST FILL!------------"""

    DTO = CheckInOutsDTO(userID)

    # Chosen activity validation
    for activity in chosen:
        if activity not in DTO.userActivities:
            raise LookupError (f"Your chosen list is not the same as your registered activity!")
    
    # Uncomment whichever you want to use    
    # CheckIn(DTO, chosen)
    # CheckOut(DTO, chosen)


if __name__ == "__main__" :
    main()


    
