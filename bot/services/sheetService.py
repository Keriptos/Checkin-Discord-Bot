import time
import gspread
from gspread import Worksheet, Spreadsheet 
from google.oauth2.service_account import Credentials
from bot.config_builder import GOOGLE_SHEET_ID, CREDS_PATH

class SheetService:
    def __init__(self):
        self.sheet: Spreadsheet | None = None        
        self.worksheets: dict[str, Worksheet] = {}
        self.year_column_cache: dict[str, list[int | str | float | None]] = {}
        
    def get_sheet_client(self) -> Spreadsheet:
        commandStartTime = time.perf_counter()
        if self.sheet is None:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file(CREDS_PATH, scopes = scopes)
            client = gspread.authorize(creds)
            self.sheet = client.open_by_key(GOOGLE_SHEET_ID)
            commandEndTime = time.perf_counter()
            print(f"Initialized sheet client in {commandEndTime - commandStartTime:.4f} seconds")
        return self.sheet

    def load_worksheets(self) -> dict[str, Worksheet]:
        if not self.worksheets:
            start = time.perf_counter()
            self.sheet = self.get_sheet_client()
            worksheets = self.sheet.worksheets()            
            for worksheet in worksheets:
                self.worksheets[worksheet.title] = worksheet
            end = time.perf_counter()
            print(f"Loaded all worksheets in {end-start:.8f} seconds")
        return self.worksheets

    def get_worksheet(self, username) -> Worksheet:
        self.load_worksheets()
        try:
            return self.worksheets[username]
        except KeyError:
            raise gspread.WorksheetNotFound(f"{username}'s worksheet not found. User should register first!")
        
    def load_year_columns(self, username) -> list[int | str | float | None]:
        if not self.year_column_cache:                
            worksheet = self.get_worksheet(username)              
            start = time.perf_counter()
            self.year_column_cache[username] = worksheet.col_values(4)
            end = time.perf_counter()
            print(f"Year column cache was set-up in {end - start:.4f} seconds")
        return self.year_column_cache[username]
    
    def get_year_column(self, username: str):
        if username not in self.year_column_cache:
            print(f"Didn't found {username} in year column cache. Setting up cache...")
            self.load_year_columns(username)
        return self.year_column_cache[username]
