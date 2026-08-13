import time; import logging
import datetime
import gspread
from googleapiclient.errors import HttpError
from gspread import Worksheet, Spreadsheet
from google.oauth2.service_account import Credentials
import bot.helpers.utils as utls
from bot.config_builder import ConfigDTO

CFG = ConfigDTO()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SheetService:
    def __init__(self):
        self._sheet: Spreadsheet | None = None        
        self._worksheets_cache: dict[str, Worksheet] = {}
        self._year_column_cache: dict[str, list[int | str | float | None]] = {}


    def get_sheet_client(self) -> Spreadsheet:
        commandStartTime = time.perf_counter()
        if self._sheet is None:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_info(CFG.CREDS, scopes = scopes)            
            client = gspread.authorize(creds)
            self._sheet = client.open_by_key(CFG.GOOGLE_SHEET_ID)
            commandEndTime = time.perf_counter()
            print(f"Initialized sheet client in {commandEndTime - commandStartTime:.4f} seconds")
        return self._sheet
    
        
    def force_load_worksheets(self) -> dict[str, Worksheet]:
        self._sheet = self.get_sheet_client() # Load the sheet if it hasn't been loaded

        start = time.perf_counter()
        worksheets = self._sheet.worksheets()
        for worksheet in worksheets:
            self._worksheets_cache[worksheet.title] = worksheet # Worksheet title are the registered usernames
        end = time.perf_counter()
        print(f"Loaded all worksheets in {end-start:.8f} seconds")
        return self._worksheets_cache
    
    def update_worksheets_cache(self, username: str) -> None:
        """Updates the worksheet cache. Returns nothing"""
        start = time.perf_counter()        
        
        self._worksheets_cache.update({username: self.get_worksheet(username)})
        end = time.perf_counter()
        print(f"Updated worksheets cache in {end - start:.8f} seconds\n")

    def remove_user_from_worksheets_cache(self, username: str) -> None:
        start = time.perf_counter()
        try:
            del self._worksheets_cache[username]
        except KeyError as e:
            logger.exception(f"User is not on cache! | {e}")
        else:
            logger.info(f"Removed {username} from worksheets cache in {time.perf_counter() - start:.8f} seconds")
    
    def get_worksheet(self, worksheet_name: str) -> Worksheet:
        "Gets a worksheet by the worksheet's name"
        if worksheet_name not in self._worksheets_cache: # Fetch all the users before trying to return their worksheet
            self._worksheets_cache = self.force_load_worksheets()
        
        # If it reached the exception, the user actually didn't register
        try:                    
            return self._worksheets_cache[worksheet_name]
        except KeyError:
            raise gspread.WorksheetNotFound(f"{worksheet_name}'s worksheet not found. User should register first!")


    def log_participants(self, user: dict) -> None:
        """Logs the user onto the Participants sheet"""
        worksheet = self.get_worksheet("Participants")

        start = time.perf_counter()
        try:
            username = user['username']
            activities: list = user['activities']
            date: str = user['registered_at']
        except KeyError as e:
            logger.exception(f"Missing key in user dictionary: {e}")
            return
        
        participant_sheet_id = worksheet.id
        name_col = worksheet.col_values(1) # 1-indexed argument
        empty_row = len(name_col) # 0-indexed. A cell after the last name cell will always be empty

        formatted_date: str = datetime.date.fromisoformat(date).strftime("%d %B %Y")
        row_update: list = [username, formatted_date] + activities # !! REMEMBER TO ADJUST THE SHEET LATER. SIGNOUT IS NO LONGER SHOWN ON SHEET. BUT WILL BE SAVED IN DATABASE

        compiledReq: list = []
        compiledReq.extend([{
            "updateCells": { # Writes the username, registration date, activities, and reminder time
                "rows": [
                    {
                        "values": [
                            {"userEnteredValue": {"stringValue": str(value)}} for value in row_update
                        ]
                    }
                ],
                "start": {
                    "sheetId": participant_sheet_id,
                    "rowIndex": empty_row,
                    "columnIndex": 0  # A column (0-indexed
                },
                "fields": "userEnteredValue"
            }},
            utls.make_update_cells__str_req(
                source_sheet_id= participant_sheet_id,
                start_row= empty_row,
                end_row= empty_row + 1,
                start_col= 7,
                end_col= 8,
                value= f"{user["remind_at"]}:00:{'+' if user["utc_offset"][0] >= 0 else ''}{str(user["utc_offset"][0]).zfill(3 if user["utc_offset"][0] < 0 else 2)}:{user["utc_offset"][1]:02d}"
            ) # user["remind_at"] is an hour in 24-hour format. user["utc_offset"] is a list that consists of the hour (index 0) and minute (index 1)
        ])

        # Border format
        solid_borders = {
            "top" :{"style": "SOLID"},
            "bottom" :{"style": "SOLID"},
            "left" :{"style": "SOLID"},
            "right" :{"style": "SOLID"}
        }
        compiledReq.extend([{
            "repeatCell": { # The format for the name and registration date column
                "range": {
                    "sheetId": participant_sheet_id,
                    "startRowIndex": empty_row,
                    "endRowIndex": empty_row + 1,
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
                        "borders": solid_borders
                    }
                },
                "fields": "userEnteredFormat"
            }
        }])
        
        compiledReq.extend([{
            "repeatCell": { # The format for activity and reminder column
                "range": {
                    "sheetId": participant_sheet_id,
                    "startRowIndex": empty_row,
                    "endRowIndex": empty_row + 1,
                    "startColumnIndex": 2,  # C column
                    "endColumnIndex": 8    # J column (excluded)
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER",
                        "textFormat": {
                            "fontSize": 12,
                            "bold": True
                        },
                        "borders": solid_borders
                    }
                },
                "fields": "userEnteredFormat"
        }}])               
        try:
            worksheet.spreadsheet.batch_update({"requests": compiledReq})
        except HttpError as err:
            if err.resp.status == 400:
                logger.error("Invalid Request: Check your JSON structure or cell ranges. Details: %s", err.content)
            elif err.resp.status == 403:
                logger.warning("Permission Denied: Ensure your credentials have write access.")
            elif err.resp.status == 429:
                logger.warning("Rate Limit Exceeded: The script is sending requests too quickly.")
            else:
                logger.error(f"An unexpected API error occurred: {err}")
        except Exception:        
            logger.exception("A non-API error occurred during the batchUpdate process.")
        else:
            end = time.perf_counter()
            logger.info(f"Succesfully logged {username} to participants sheet in {end - start:.8f} seconds")

        

    def get_year_column(self, username: str) -> list[int | str | float | None]:
        if username not in self._year_column_cache:
            print(f"Didn't found {username} in year column cache. Setting up cache...")
            worksheet = self.get_worksheet(username)
            start = time.perf_counter()
            self._year_column_cache[username] = worksheet.col_values(4)
            end = time.perf_counter()
            print(f"Year column cache was set-up in {end - start:.4f} seconds\n")
        return self._year_column_cache[username]

    def refresh_year_column(self, username: str) -> list[int | str | float | None]:
        worksheet = self.get_worksheet(username)
        start = time.perf_counter()
        self._year_column_cache[username] = worksheet.col_values(4)
        end = time.perf_counter()
        print(f"Year column cache was refreshed in {end - start:.4f} seconds\n")
        return self._year_column_cache[username]

    @staticmethod    
    def _determine_skip(user_format: str) -> int:
        if user_format == "Yearly":
            return 35
        else: return 36
    
    @staticmethod
    def _find_target_row_in_col(start_row: int, time_col: list, target: str, skip: int):        
        for row in range(start_row, len(time_col), skip):            
            if time_col[row] == target:                
                return row
        raise ValueError(f"'{target}' not found")

    def test_year_cell(self, user: dict, date: datetime.datetime) -> dict[str, int]:
        start = time.perf_counter()

        username = user['username']
        user_format = user['format']        
        
        # Year column is always at index 3 (0 indexed) --> D column
        targetted_row = self._find_target_row_in_col(
            start_row= 2 if user_format == "Yearly" else 0,
            time_col= self.get_year_column(username), 
            target= str(date.year), 
            skip= 35 if user_format == "Yearly" else 36)

        year_cell: dict = {"row": targetted_row, "col": 3}
        end = time.perf_counter()
        logger.info(f"Found year_cell '{year_cell}' in {end - start:.8f} seconds")
        return year_cell
        
    
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
    
    def test_year_division_cell(self, user: dict, date: datetime.datetime) -> dict[str, int]:
        start = time.perf_counter()

        username = user['username']
        user_format = user['format']        

        selector = "Semester 1"
        if "Semesterly" in user_format:
            if date.month <= 6: 
                selector = "Semester 1"
            else:
                selector = "Semester 2"

        # Q1 --> 1 2 3 | Q2 --> 4 5 6 | Q3 --> 7 8 9 | Q4 --> 10 11 12        
        elif "Quarterly" in user_format:
            if date.month <= 3:
                selector = "Q1"
            elif date.month <= 6:
                selector = "Q2"
            elif date.month <= 9:
                selector = "Q3"
            else:
                selector = "Q4"

        targetted_row = self._find_target_row_in_col(
            start_row= 2,
            time_col=self.get_year_column(username),
            target= selector,
            skip= 36
        )
        year_division_cell: dict = {"row": targetted_row, "col": 3}
        end = time.perf_counter()
        logger.info(f"Found year_division_cell '{year_division_cell}' in {end - start:.8f} seconds")
        return year_division_cell

    
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

    def test_get_month_cell(self, user: dict, date: datetime.datetime, year_cell: dict, year_division_cell: dict | None) -> dict[str, int]:        
        start = time.perf_counter()
        user_format = user['format']
        try:   
            if user_format == "Yearly":
                month_cell = {
                "row": year_cell["row"],
                "col": 5 + (date.month -  1)}
            else:
                user_activities = user['activities']
                month_cell = {
                    "row": year_division_cell["row"],
                    "col": 5 + (len(user_activities) * ((date.month- 1) % (6 if user_format == "Semesterly" else 3)))}
        except TypeError as e:
            logger.error(f"Year_cell or year_division_cell is None | Error: {e}")
        end = time.perf_counter()
        logger.info(f"Found month_cell '{month_cell}' in {end - start:.8f} seconds")
        return month_cell

        
    def get_month_cell(self, user: dict, date: datetime.datetime) -> dict[str, int]:
        # All values are 0 - indexed
        start = time.perf_counter()
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
            month_cell = {
                "row": year_division_cell["row"] if year_division_cell is not None else year_cell["row"] + 2,
                "col": 5 + (len(userActivities) * ((date.month- 1) % (6 if user_format == "Semesterly" else 3)))
            }
        end = time.perf_counter()
        print(f"Completed month_cell search '{month_cell}' in {end - start:.8f} seconds")
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