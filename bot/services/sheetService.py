import time
import gspread
from gspread import Worksheet, Spreadsheet 
from google.oauth2.service_account import Credentials
from bot.config import GOOGLE_SHEET_ID, CREDS_PATH

class SheetService:
    def __init__(self):
        self.sheet: Spreadsheet | None = None        
        self.worksheets: dict[str, Worksheet] = {}
        
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
        if self.worksheets == {}:
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
        

sheetManager = SheetService()
    
