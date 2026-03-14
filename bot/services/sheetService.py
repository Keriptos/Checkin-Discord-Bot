import time
import datetime
import gspread
from gspread import Worksheet, Spreadsheet 
from google.oauth2.service_account import Credentials
from bot.helpers.utils import loadJSON, saveJSON
from bot.config_builder import USERS_FILE, GOOGLE_SHEET_ID, CREDS

class SheetService:
    def __init__(self):
        self.sheet: Spreadsheet | None = None        
        self.worksheets: dict[str, Worksheet] = {}
        self.year_column_cache: dict[str, list[int | str | float | None]] = {}
        
    def get_sheet_client(self) -> Spreadsheet:
        commandStartTime = time.perf_counter()
        if self.sheet is None:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_info(CREDS, scopes = scopes)            
            client = gspread.authorize(creds)
            self.sheet = client.open_by_key(GOOGLE_SHEET_ID)
            commandEndTime = time.perf_counter()
            print(f"Initialized sheet client in {commandEndTime - commandStartTime:.4f} seconds")
        return self.sheet
    
    
    def force_load_worksheets(self) -> dict[str, Worksheet]:
        start = time.perf_counter()
        self.sheet = self.get_sheet_client()
        worksheets = self.sheet.worksheets()
        for worksheet in worksheets:
            self.worksheets[worksheet.title] = worksheet
        end = time.perf_counter()
        print(f"Loaded all worksheets in {end-start:.8f} seconds")
        return self.worksheets
    
    def get_worksheet(self, username) -> Worksheet:
        if username not in self.worksheets: # Fetch all the users before trying to return their worksheet
            self.worksheets = self.force_load_worksheets()
        
        # If it reached the exception, the user actually didn't register
        try:            
            return self.worksheets[username]
        except KeyError:
            raise gspread.WorksheetNotFound(f"{username}'s worksheet not found. User should register first!")
        
    
    def get_year_column(self, username: str) -> list[int | str | float | None]:
        if username not in self.year_column_cache:
            print(f"Didn't found {username} in year column cache. Setting up cache...")
            worksheet = self.get_worksheet(username)
            start = time.perf_counter()
            self.year_column_cache[username] = worksheet.col_values(4)
            end = time.perf_counter()
            print(f"Year column cache was set-up in {end - start:.4f} seconds")
        return self.year_column_cache[username]
    
    def get_year_cell(self, user: dict, date: datetime.datetime):
        processStartTime = time.perf_counter()
        
        userFormat = user['format']
        username = user['username']

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

        timeColumn = self.get_year_column(username)

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
        print(f"Found yearCell '{yearCell}' in {processEndTime - processStartTime:.8f} seconds")
        return yearCell
    
    
    def get_year_division_cell(self, yearCell: dict, user: dict, date: datetime.datetime): # Only used for 2+ activity
        start = time.perf_counter()
        
        # Set the year division string 
        username = user['username']
        userFormat = user['format']
        # Semester 1 --> 1 2 3 4 5 6 | Semester 2 --> 7 8 9 10 11 12 (Numbers are in months)
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

        
        timeColumn: list = self.get_year_column(username)
        yearDivisionCell = { # default values (1-indexed)
            "row": yearCell["row"] + 2, 
            "col": yearCell["col"]
        }

        # Search the row of yearDivisionCell
        found = False   
        yearDivRow = yearDivisionCell["row"] 
        while (yearDivRow <= len(timeColumn)):
            if (timeColumn[yearDivRow - 1] == yearDivToFind): # The index is decremented by 1, so that it's 0-indexed
                yearDivisionCell['row'] = yearDivRow
                found = True
                break

            # Skip algorithm
            yearDivRow += 36
        
        end = time.perf_counter()
        if not found:
            raise ValueError(f"{yearDivToFind} not found")
        print(f"Found yearDivisionCell '{yearDivToFind}': {yearDivisionCell} in {end - start:.8f} seconds")
        return yearDivisionCell


# To prevent making another class instance in any of the logic files, 
# it's better to import the variable from this module
sheetManager = SheetService()

if __name__ == "__main__":
    print(sheetManager.get_year_column('imon06'))
    
    usersData: dict = loadJSON(USERS_FILE)
    userID = str(582370335886802964)
    user = usersData[userID]
    
    yearCell = sheetManager.get_year_cell(user, datetime.datetime.now())
    print(yearCell)
    print(sheetManager.get_year_division_cell(yearCell, user, datetime.datetime.now()))
