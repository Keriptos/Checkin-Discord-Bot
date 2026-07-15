import time
import datetime
import gspread
from gspread import Worksheet, Spreadsheet
from google.oauth2.service_account import Credentials
from bot.helpers.utils import loadJSON, saveJSON
from bot.config_builder import ConfigDTO

CFG = ConfigDTO()

class SheetService:
    def __init__(self):
        self.sheet: Spreadsheet | None = None        
        self.worksheets: dict[str, Worksheet] = {}
        self.year_column_cache: dict[str, list[int | str | float | None]] = {}
        
    def get_sheet_client(self) -> Spreadsheet:
        commandStartTime = time.perf_counter()
        if self.sheet is None:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_info(CFG.CREDS, scopes = scopes)            
            client = gspread.authorize(creds)
            self.sheet = client.open_by_key(CFG.GOOGLE_SHEET_ID)
            commandEndTime = time.perf_counter()
            print(f"Initialized sheet client in {commandEndTime - commandStartTime:.4f} seconds")
        return self.sheet
    
        
    def force_load_worksheets(self) -> dict[str, Worksheet]:
        self.sheet = self.get_sheet_client() # Load the sheet if it hasn't been loaded

        start = time.perf_counter()
        worksheets = self.sheet.worksheets()
        for worksheet in worksheets:
            self.worksheets[worksheet.title] = worksheet
        end = time.perf_counter()
        print(f"Loaded all worksheets in {end-start:.8f} seconds")
        return self.worksheets
    
    def get_worksheet(self, worksheet_name: str) -> Worksheet:
        if worksheet_name not in self.worksheets: # Fetch all the users before trying to return their worksheet
            self.worksheets = self.force_load_worksheets()
        
        # If it reached the exception, the user actually didn't register
        try:                    
            return self.worksheets[worksheet_name]
        except KeyError:
            raise gspread.WorksheetNotFound(f"{worksheet_name}'s worksheet not found. User should register first!")

    """Make a better dynamic label fetching. As of now, it's hard-coded"""  
    # def get_labels(self) -> list:
    #     commandStartTime = time.perf_counter()
    #     worksheet = self.get_worksheet("Template")
    #     labels: list = worksheet.col_values(1)
    #     try:
    #         for i in range(0,4):                
    #             labels.pop(0)
    #         labels.pop(len(labels) - 1)
    #         labels.pop(len(labels) - 1)
    #     except Exception:
    #         print("gk tau")
    #     labels.sort()
    #     commandEndTime = time.perf_counter()
    #     print(f"Succesfully fetched labels in {commandEndTime - commandStartTime:.4f} seconds")
    #     return labels

    
    def get_year_column(self, username: str) -> list[int | str | float | None]:
        if username not in self.year_column_cache:
            print(f"Didn't found {username} in year column cache. Setting up cache...")
            worksheet = self.get_worksheet(username)
            start = time.perf_counter()
            self.year_column_cache[username] = worksheet.col_values(4)
            end = time.perf_counter()
            print(f"Year column cache was set-up in {end - start:.4f} seconds\n")
        return self.year_column_cache[username]
    
    def get_year_cell(self, user: dict, date: datetime.datetime) -> dict[str, int]:
        processStartTime = time.perf_counter()
        
        user_format = user['format']
        username = user['username']

        if user_format == "Yearly": 
            year_cell = { # By default, it's D3 --> (0-indexed)
                "row": 2,
                "col": 3 
            }
        else:
            year_cell = { # By default, it's D1 --> (0-indexed)
                "row": 0,
                "col": 3 
            }

        time_column = self.get_year_column(username)

        year_row = year_cell["row"]
        found = False   
        while (year_row <= len(time_column)):        
            if (time_column[year_row] == str(date.year)):
                year_cell['row'] = year_row
                found = True
                break

            # Skip algorithm
            if (user_format == "Yearly"):
                year_row += 35
            else :
                year_row += 36

        if not found:
            raise ValueError(f"Year {date.year} not found")
        
        processEndTime = time.perf_counter()
        print(f"Found year_cell '{year_cell}' in {processEndTime - processStartTime:.8f} seconds")
        return year_cell
    
    
    def get_year_division_cell(self, user: dict, date: datetime.datetime) -> dict[str, int] | None:
        """Used for 2+ activity. Returns None for Yearly format (1 activity)"""        
        username = user['username']
        user_format = user['format']

        if user_format == "Yearly":            
            return None
        

        start = time.perf_counter()
        # Set the year division string 
        # Semester 1 --> 1 2 3 4 5 6 | Semester 2 --> 7 8 9 10 11 12 (Numbers are in months)
        if "Semesterly" in user_format:
            if date.month <= 6: 
                year_div_to_find = "Semester 1"
            else:
                year_div_to_find = "Semester 2"

        # Q1 --> 1 2 3 | Q2 --> 4 5 6 | Q3 --> 7 8 9 | Q4 --> 10 11 12        
        elif "Quarterly" in user_format:
            if date.month <= 3:
                year_div_to_find = "Q1"
            elif date.month <= 6:
                year_div_to_find = "Q2"
            elif date.month <= 9:
                year_div_to_find = "Q3"
            else:
                year_div_to_find = "Q4"

        
        time_column: list = self.get_year_column(username)
        year_cell = self.get_year_cell(user=user, date= date)
        year_division_cell = { # default values (0-indexed)
            "row": year_cell["row"] + 2, 
            "col": year_cell["col"]
        }

        # Search the row of year_division_cell
        found = False   
        year_div_row = year_division_cell["row"] 
        while (year_div_row <= len(time_column)):
            if (time_column[year_div_row] == year_div_to_find):
                year_division_cell['row'] = year_div_row
                found = True
                break

            # Skip algorithm
            year_div_row += 36
        
        end = time.perf_counter()
        if not found:
            raise ValueError(f"{year_div_to_find} not found")
        print(f"Found year_division_cell '{year_div_to_find}': {year_division_cell} in {end - start:.8f} seconds")
        return year_division_cell


    def get_month_cell(self, user: dict, date: datetime.datetime) -> dict[str, int]:
        # All values are 0 - indexed
        monthStart = time.perf_counter()
        user_format = user['format']
        
        year_cell: dict = self.get_year_cell(user, date)
        year_division_cell: dict | None = None if user_format == "Yearly" else self.get_year_division_cell(user, date)
        if user_format == "Yearly":
            month_cell = {
            "row": year_cell["row"],
            "col": 5 + (date.month -  1)
        }
        else:            
            userActivities = user['activities']            
            if "Semesterly" in user_format:
                month_cell = {
                "row": year_division_cell["row"] if year_division_cell is not None else year_cell["row"] + 2,
                "col": 5 + (len(userActivities) * ((date.month- 1) % 6))
            }
            else:
                month_cell = {
                "row": year_division_cell["row"] if year_division_cell is not None else year_cell["row"] + 2,
                "col": 5 + (len(userActivities) * ((date.month - 1) % 3))
        }
        monthEnd = time.perf_counter()
        print(f"Completed month_cell search '{month_cell}' in {monthEnd - monthStart:.8f} seconds")
        return month_cell


    def get_current_date_cell(self,date: datetime.datetime, user: dict, chosen: list) -> tuple[int, list[int]]:
        """Returns a tuple with the format (row, col) | 0-indexed"""
        user_format: str = user['format']
        user_activities: list = user['activities']

        # All values from these cells are (0-indexed)
        # The underlying process: Year -> YearDiv (If not yearly) -> Month -> Date
        month_cell: dict = self.get_month_cell(user= user, date= date)

        """Find row_to_find and col_to_find for the current date cell (0-indexed). Made col_to_find as a list so it's easier to manipulate"""
        # Basically do nothing if yearly, else increment by 1 because the format is different by 1 cell
        row_to_find: int = date.day + month_cell['row'] + (0 if user_format == "Yearly" else 1) 
        if user_format == "Yearly":
            col_to_find: list = [month_cell['col']]
        else:
            # Map the activity, offset it based on month_cell, and write rowToFind & offset to sheetCache
            activity_index = {}
            for index, activity in enumerate(user_activities):
                activity_index[activity] = index

            col_to_find: list = []
            for activity in chosen:            
                if activity in activity_index:
                    base_index = activity_index[activity]
                    offset = base_index + month_cell["col"]       
                    col_to_find.append(offset)                
                else:
                    raise ValueError(f"Activity '{activity}' not found")
        return row_to_find, col_to_find

# To prevent making another class instance in any of the logic files, 
# it's better to import the variable from this module
sheetManager = SheetService()
