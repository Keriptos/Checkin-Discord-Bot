#DO NOT PUT THIS IN COGS FOLDER, THIS IS MADE TO RUN LOCALLY

#Google Sheets Imports
import gspread 
from google.oauth2.service_account import Credentials
from gspread_formatting import *

#Other Imports
import calendar #To get month name
import datetime #To get time
import json # read, load, write into a JSON 
import time # To get record time for commands ~ To see how long a command takes to execute
import os

def lockedInTime(elapsedTime: datetime.timedelta):
    hours = elapsedTime.seconds // 3600
    minutes = (elapsedTime.seconds % 3600) // 60     
    seconds = elapsedTime.seconds % 60

    if hours != 0 and minutes != 0 and seconds != 0:
        return(f"{hours} hours {minutes} minutes {seconds} seconds")
    elif hours == 0 and minutes != 0 and seconds != 0:
        return (f"{minutes} minutes {seconds} seconds")
    elif hours == 0 and minutes == 0 and seconds != 0:
        return (f"{seconds} seconds")
    
def loadJSON(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            file.write('{}') # create empty file
    try:
        with open(file_path) as file: 
            return json.load(file)
    except json.JSONDecodeError:
        with open(file_path, 'w') as file:
            file.write('{}')  # Create an empty JSON file if it doesn't exist or is invalid
    return {}

def saveCheckins(checkinData):    
    with open('checkintimes.json', 'w') as file:
        json.dump(checkinData, file, indent=4)

# Used for finding activity row
def activityOffset(userID): # Alex only has 1 activity registered, no need for an offset. Offset is 1-indexed based. TEMP solution
    if userID == "880614022939041864": #Sam
        return 4
    elif userID == "582370335886802964": #Raf
        return 4
    elif userID == "461526727521206282": #TestUser
        return 4
    elif userID == "181760450273214464": #Chris
        return 40
    elif userID == "689028638544494621": #Nicholas
        return 40

# Used for finding the cell of date
def rowOffset(userID): #Row offset is calculated by row in sheet in 0-index format - 1; Ex = row 3 in sheet = 1 offset (2 -1 = 1)
     if userID == "591939252061732900": #Alex
         return 2
     elif userID == "582370335886802964": #Raf
        return 3
     elif userID == "880614022939041864": #Sam
         return 39
     elif userID == "181760450273214464": #Chris
         return 39
     elif userID == "689028638544494621": #Nicholas
        return 39
     elif userID == "461526727521206282": #TestUser
        return 3

def sheetInitialization():
    from dotenv import load_dotenv
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("credentials.json", scopes = scopes)
    client = gspread.authorize(creds)

    load_dotenv(".env")
    sheetID = os.getenv("googleSheetID")
    sheet = client.open_by_key(sheetID)
    return sheet


with open('users.json') as file:
    ID_to_name = json.load(file)


with open('checkintimes.json', 'r') as file:
    timeCheckedIn = json.load(file) # Set timeCheckedIn to the data from the JSON file


userID = "591939252061732900" # Replace with the actual user ID - Alex
username = ID_to_name[userID]

userActivities = loadJSON('userActivities.json')
chosen = ["Coding"] # Example activity, should be replaced with actual user input
chosen.sort()


class Checkin:
    def __init__(self):
        self.valid = []
        self.invalid = []

    def checkin(self):
        commandStartTime = time.perf_counter() # To record how long the command takes to execute

        sheet = sheetInitialization() # Initialize the sheet
        worksheet = sheet.worksheet(username) # Get the worksheet for the userID
        worksheetID = worksheet.id # Get the worksheetID for pasteLabels later on


        for activity in chosen:
            if activity in userActivities.get(username, []): #If valid
                self.valid.append(activity)
                if username not in timeCheckedIn:
                    timeCheckedIn[username] = {} # Creates a new dict for the user if they don't exist

                timeCheckedIn[username][activity] = datetime.datetime.now().isoformat() #userName and activity = keys, time as the value into dictionary
            else:
                self.invalid.append(activity)

        if len(self.valid) == 0:
            return (f"{username}'s chosen activities are all invalid: {self.invalid}")        
        saveCheckins(timeCheckedIn)
        print(timeCheckedIn[username])

        # I removed an unnecessary loop and it cleared 0.5 - 1 sec so thats good, remember to change that in sheetCommands file
        date = datetime.datetime.now() # Get date from right now, it's a check-in so date is whenever the user initiates the command

        #Only yearly table format(me) have different row and column algorithms, make a special case for them
        #Process to find row and column to update 
        rowToFind = date.day + rowOffset(userID) # 0-index based

        # Getting column is pretty hard since it needs month and activity, which is under the month. So have to get month first
        month = calendar.month_name[date.month] # Get the month name from the date

        #Get the month name row (1-index based), has None in the list
        monthRowList = []
        if userID != "591939252061732900": # Other than Alex
            monthRowList = worksheet.row_values(activityOffset(userID)- 1) #Offset is 1-index based, so -1 to move back onto month cell, instead of activity cell
        else: # Only for Alex
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
        if (username ==  'Alex'): # Only 1 activity algorithm
            columnToFind = monthColumn 
            
            compiledRequests = [] # To store all requests for batch update for later
            #Request section
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
            activityRow = worksheet.row_values(activityOffset(userID)) #Get the 4th row (1-index based), does have None in the list
            #Loops through the activityRow and stops until the first instance of activity is found, then set columnToFind as the index
            for i in range(monthColumn, len(userActivities[username]) + monthColumn): #Index must and will be 0-index based
                if activityRow[i] is not None and activityRow[i].lower() in [a.lower() for a in self.valid]: #Check if the activity matches
                    columnToFind.append(i)
            if columnToFind == []: #Checks in case activity is not found
                raise ValueError (f"Activity '{self.valid}' not found under month '{month}'")
        
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
            #print(rowToFind, columnToFind)
        #print(month, monthColumn, compiledRequests)

        if compiledRequests:
            worksheet.spreadsheet.batch_update({"requests": compiledRequests}) # Batch update all requests at once
            print ("Batch update successful.")

        commandEndTime = time.perf_counter()
        print(f"Checkin executed in {commandEndTime - commandStartTime:.4f} seconds")

# Check out
class Checkout: # Check-out
    def checkout():
        commandStartTime = time.perf_counter() # To record how long the command takes to execute

        sheet = sheetInitialization() # Initialize the sheet
        worksheet = sheet.worksheet(username) # Get the worksheet for the userID
        worksheetID = worksheet.id # Get the worksheetID for pasteLabels later on

        timeCheckedInDICT = loadJSON('checkintimes.json')

        # Make a list from the activities the user has checked in to
        user_activitiesCheckedIn = list(dict.fromkeys(timeCheckedInDICT[username].keys()))
        print(f"{username} selected {chosen}")

        for activity in chosen: #Iterate through the chosen activities, doesn't need to be sorted
            userTimeCheckedIn = datetime.datetime.fromisoformat(timeCheckedInDICT[username][activity])
            timeCheckedOut = datetime.datetime.now()

            elapsedTime :datetime.timedelta = timeCheckedOut - userTimeCheckedIn
            print(f"{username}'s {activity.lower()} elapsed time: {lockedInTime(elapsedTime)}")

            #Copy algorithm like check-in, but paste DONE instead of ON PROGRESS for the cell update
            #Process to find row and column to update
            rowToFind = userTimeCheckedIn.day + rowOffset(userID) # 0-index based

            # Getting column is pretty hard since it needs month and activity, which is under the month. So have to get month first
            month = calendar.month_name[userTimeCheckedIn.month] # Get the month name from the date

            #Get the month name row (1-index based), has None in the list
            monthRowList = []
            if userID != "591939252061732900": # Other than A_user 
                monthRowList = worksheet.row_values(activityOffset(userID)- 1) #Offset is 1-index based, so -1 to move back onto month cell, instead of activity cell
            else:
                monthRowList = worksheet.row_values(3) # A_user only has 1 activity, so month is always on row 3 (1-index based) ~ special case

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
            if (username ==  'Alex'): # Only 1 activity algorithm
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
                activityRow = worksheet.row_values(activityOffset(userID)) #Get the 4th row (1-index based), does have None in the list
                #Loops through the activityRow and stops until the first instance of activity is found, then set columnToFind as the index
                for i in range(monthColumn, len(userActivities[username]) + monthColumn): #Index must and will be 0-index based
                    if activityRow[i] is not None and activityRow[i].lower() in [a.lower() for a in user_activitiesCheckedIn]: #Check if the activity matches
                        columnToFind.append(i)
                if columnToFind == []: #Checks in case activity is not found
                    raise ValueError (f"Activity '{user_activitiesCheckedIn}' not found under month '{month}'")

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
                
        if len(chosen) == len(user_activitiesCheckedIn):
            timeCheckedInDICT.pop(username) 
        else : 
            for activity in chosen:
                timeCheckedInDICT[username].pop(activity)      
        saveCheckins(timeCheckedInDICT)
        commandEndTime = time.perf_counter()
        print(f"Checkout executed in {commandEndTime - commandStartTime:.4f} seconds")

#print(Checkin().checkin())
print(Checkout.checkout())
# Activate either check-in or check-out by uncommenting the above lines