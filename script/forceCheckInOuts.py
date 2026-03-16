#Google Sheets Related Imports
from gspread import Worksheet
from gspread_formatting import *
from bot.services.sheetService import sheetManager

#Other Imports
import datetime
from datetime import timedelta
import bot.helpers.utils as utls
from bot.config_builder import ConfigDTO 
import time # To track how long commands take to execute

CFG = ConfigDTO()
SHEET = sheetManager.get_sheet_client()


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

Put month on enums, because monthColumn are basically constants. Just count the index and offset them by len of activities (DONE)
Save the check-in cell, so that check-out process doesn't need to fetch anything (DONE)


"""
class CheckInOutsDTO():
    def __init__(self, userID: int):
        self.userID = str(userID)
        usersData = utls.loadJSON(CFG.USERS_FILE)
        self.user = usersData[self.userID]
        self.username = self.user['username']
        self.userFormat = self.user['format']
        self.userActivities = self.user['activities']

# Update to sheets (Check-in)
def CheckIn(DTO: CheckInOutsDTO, chosen: list):        
    commandStartTime = time.perf_counter()
    
    # Local check-in
    start = time.perf_counter()
    timeCheckedIn = utls.loadJSON(CFG.CHECKIN_FILE)

    # If user has checked in, stop here
    if DTO.userID in timeCheckedIn:
        print("You've already checked in! Perhaps you wanted to check-out?")
        return
    
    # Set up the dict for the user
    timeCheckedIn[DTO.userID] = {}
    timeCheckedIn[DTO.userID]["username"] = DTO.username
    timeCheckedIn[DTO.userID]["activities"] = {}

    for activity in chosen:            
        # Username and activity = keys, time as the value into dictionary
        timeCheckedIn[DTO.userID]["activities"][activity] = datetime.datetime.now().isoformat()
    utls.saveJSON(timeCheckedIn, CFG.CHECKIN_FILE)
    end = time.perf_counter()
    print(f"Succesfully saved timestamp locally in {end - start:.8f} seconds")


    print("Going to sheets")    
    worksheet = sheetManager.get_worksheet(DTO.username)
    worksheetID = worksheet.id

    # Fetching rowToFind & colToFind for the activity cell that we want to know the location of
    date = datetime.datetime.now() 
    yearCell = sheetManager.get_year_cell(DTO.user, date)
    if DTO.user['format'] != 'Yearly':
        yearDivCell = sheetManager.get_year_division_cell(yearCell, DTO.user, date)
    else:
        yearDivCell = None
    monthCell = sheetManager.get_month_cell(DTO.user, date, yearCell, yearDivCell)

    # Set-up cache when checking in
    try:
        startCache = time.perf_counter()
        sheetCache = utls.loadJSON(CFG.SHEET_CACHE)
        if DTO.userID not in sheetCache:
            sheetCache[DTO.userID] = {}
            sheetCache[DTO.userID]['username'] = DTO.username
            sheetCache[DTO.userID]['activities'] = {}
            for activity in chosen:
                sheetCache[DTO.userID]['activities'][activity] = {}
                sheetCache[DTO.userID]['activities'][activity]['checkinCell'] = {}
        utls.saveJSON(sheetCache, CFG.SHEET_CACHE)
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
        columnToFind = [] # Made columnToFind a list, so that it's compatible with 2+ activity algorithm
        columnToFind.append(monthCell["col"] - 1) # Since there's only 1 activity, columnToFind is just monthColumn
        for activity in chosen:
            sheetCache[DTO.userID]['activities'][activity]['checkinCell']['row']= rowToFind 
            sheetCache[DTO.userID]['activities'][activity]['checkinCell']['col']= columnToFind[0]
        rowColEnd = time.perf_counter()
        utls.saveJSON(sheetCache, CFG.SHEET_CACHE)
        print(f"Sucessfully wrote {DTO.username}'s checkinCell into sheetCache in {rowColEnd - rowColStart:.8f} seconds")

    else: # 2+ algorithm
        """
        Year -> YearDiv -> Month -> Date
        """
        rowCol2Start = time.perf_counter()
        rowToFind = monthCell["row"] + date.day # The first day is 2 rows after monthRow. (0-indexed)
        sheetCache = utls.loadJSON(CFG.SHEET_CACHE)
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
        rowCol2End = time.perf_counter()
        print(f"Sucessfully wrote {DTO.username}'s multiple checkinCell into sheetCache in {rowCol2End - rowCol2Start:.8f} seconds")
        utls.saveJSON(sheetCache, CFG.SHEET_CACHE)
    

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

    timeCheckedIn = utls.loadJSON(CFG.CHECKIN_FILE)
    timeCheckedOut = datetime.datetime.now()
    if DTO.userID not in timeCheckedIn:
        print("You haven't checked in! You should check-in first!")
        return
    
    worksheet = sheetManager.get_worksheet(DTO.username)
    worksheetID = worksheet.id

    # Get rowToFind and columnToFind from sheetCache
    sheetCache: dict = utls.loadJSON(CFG.SHEET_CACHE)
    isSheetCacheBroken = False 
    if DTO.userID not in sheetCache: # If somehow check-in failed to write sheetCache, we check-out via old way
        isSheetCacheBroken = True
        print(f"{DTO.username}'s sheetCache was empty, fetching rowToFind & colToFind the old way")
        date = datetime.datetime.now()
        yearCell = sheetManager.get_year_cell(DTO.user, date)
        if DTO.user['format'] != 'Yearly':
            yearDivCell = sheetManager.get_year_division_cell(yearCell, DTO.user, date)
        else:
            yearDivCell = None
        monthCell = sheetManager.get_month_cell(DTO.user, date, yearCell, yearDivCell)

        rowToFind = monthCell["row"] + date.day # The first day is 2 rows after monthRow. (0-indexed)
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
            else:
                raise ValueError(f"Activity '{activity}' not found")
    else: # Use sheetCache from here
        isSheetCacheBroken = False
        for activity in chosen:
            rowToFind = sheetCache[DTO.userID]['activities'][activity]['checkinCell']['row']
            columnToFind = sheetCache[DTO.userID]['activities'][activity]['checkinCell']['col']

    compiledRequests = []
    for col in columnToFind:
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
                            "startRowIndex": rowToFind, 
                            "endRowIndex": rowToFind + 1,
                            "startColumnIndex": col,
                            "endColumnIndex": col + 1,
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


    # Response message
    for activity in chosen:
        userTimeCheckedIn = datetime.datetime.fromisoformat(timeCheckedIn[DTO.userID]["activities"][activity])
        elapsedTime: timedelta = timeCheckedOut - userTimeCheckedIn
        print(f"{DTO.username}'s {activity} elapsed time: {utls.lockedInTime(elapsedTime)}")

    # If user chooses to check out from all activities, remove the entire user's dict from the file
    checkedInActivities: list = timeCheckedIn[DTO.userID]["activities"]
    if len(chosen) == len(checkedInActivities):
        del timeCheckedIn[DTO.userID]    
    else: # Otherwise, remove the specific activity key from the user's dict
        for activity in chosen: 
            timeCheckedIn[DTO.userID]["activities"].pop(activity)
    utls.saveJSON(timeCheckedIn, CFG.CHECKIN_FILE) # Save the updated dictionary back to the JSON file
    print(f"{DTO.username} checked out locally for {chosen}")

    # Remove check-in cache
    if DTO.userID in sheetCache:
        try:             
            startCheckinCache = time.perf_counter()
            # Delete activty dict from user   
            if DTO.userFormat == 'Yearly':
                del sheetCache[DTO.userID]
            else: 
                for activity in chosen:
                    print(f"Activity: {activity} checkinCell: {sheetCache[DTO.userID]['activities'][activity]['checkinCell']}")
                    del sheetCache[DTO.userID]['activities'][activity]
            
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
            utls.saveJSON(sheetCache, CFG.SHEET_CACHE)
        except Exception as error:
            print(f"An error has occured when deleting user's dict from sheet_cache {error}")
        else:
            print(f"{DTO.username}'s sheet cache is already empty!")
    commandEndTime = time.perf_counter()
    print(f"Sucessfully executed check-out command in {commandEndTime - commandStartTime:.4f} seconds")   

# Fill in the MUST FILL section
def main():    
    """--------- MUST FILL!------------"""

    userID = 591939252061732900
    chosen: list = ["Coding"]

    """--------- MUST FILL!------------"""

    DTO = CheckInOutsDTO(userID)

    # Chosen activity validation
    for activity in chosen:
        if activity not in DTO.userActivities:
            raise LookupError (f"Your chosen list is not the same as your registered activity!")
    
    # Uncomment whichever you want to use    
    # CheckIn(DTO, chosen)
    CheckOut(DTO, chosen)


if __name__ == "__main__" :
    main()    

    
