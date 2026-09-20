import asyncio
import gspread_asyncio
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError

from bot.config_builder import ConfigDTO as CFG
from bot.helpers import utils as utls
import time
import logging
import datetime


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SheetService:
    _cm: gspread_asyncio.ClientManager | None = None
    _year_column_cache: dict[str, list[int | str | float | None]] = {}

        
    @staticmethod
    def _get_creds() -> Credentials:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(CFG.CREDS, scopes = scopes)
        return creds

    @classmethod
    def _init_cm(cls):
        "Initialize an internal client manager"
        if cls._cm is None:
            cls._cm = gspread_asyncio.ClientManager(cls._get_creds)

    @classmethod
    async def get_spreadsheet_client(cls):
        start = time.perf_counter()
        cls._init_cm()
        client = await cls._cm.authorize()
        sheet_client = await client.open_by_key(CFG.GOOGLE_SHEET_ID)
        end = time.perf_counter()
        logger.info(f" Fetched spreadsheet_client in {end-start:.8f} seconds")
        return sheet_client

    @classmethod
    async def _get_year_column(cls, username: str) -> list[int | str | float | None]:
        if username not in cls._year_column_cache:
            logger.info(f" Didn't found {username} in year column cache. Setting up cache...")
            worksheet = await (await cls.get_spreadsheet_client()).worksheet(username)    
            start = time.perf_counter()
            cls._year_column_cache[username] = await worksheet.col_values(4) # col_values is 1-indexed, 4th col is D column
            end = time.perf_counter()
            logger.info(f" {username}'s year column cache was set-up in {end - start:.4f} seconds\n")
        return cls._year_column_cache[username]

    @classmethod
    async def _refresh_year_column(cls, username: str) -> list[int | str | float | None]:
        worksheet = await (await cls.get_spreadsheet_client()).worksheet(username)
        start = time.perf_counter()
        cls._year_column_cache[username] = await worksheet.col_values(4)
        end = time.perf_counter()
        print(f"Year column cache was refreshed in {end - start:.4f} seconds\n")
        return cls._year_column_cache[username]
        
    @staticmethod
    def _find_target_row_in_col(start_row: int, time_col: list, target: str, skip: int):
        for row in range(start_row, len(time_col), skip):
            if time_col[row] == target:
                return row
        raise ValueError(f"'{target}' not found")

    @classmethod
    async def _get_year_cell(cls, user: dict, date: datetime.datetime) -> dict[str, int]:
        start = time.perf_counter()

        username = user['username']
        user_format = user['format']

        # (Yearly) Year cell starts at row 2  | (Non-Yearly) Year cell starts at row 0. Both are 0-indexed
        targetted_row = cls._find_target_row_in_col(
            start_row= 2 if user_format == "Yearly" else 0, 
            time_col= await cls._get_year_column(username),
            target= str(date.year),
            skip= 35 if user_format == "Yearly" else 36)

        year_cell: dict = {"row": targetted_row, "col": 3}
        end = time.perf_counter()
        logger.info(f" Found year_cell '{year_cell}' in {end - start:.8f} seconds")
        return year_cell

    @classmethod
    async def _get_year_division_cell(cls, user: dict, year_cell: dict, date: datetime.datetime) -> dict[str, int] | None:
        start = time.perf_counter()

        username = user['username']
        user_format = user['format']
        if user_format == "Yearly":
            logger.info(f" {username}'s format is Yearly. Terminating year_division search...")
            return None 


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

        targetted_row = cls._find_target_row_in_col(
            start_row= year_cell['row'] + 2, # year_division cell is 2 rows after the year_cell.
            time_col= await cls._get_year_column(username),
            target= selector,
            skip= 36
        )
        year_division_cell: dict = {"row": targetted_row, "col": 3}
        end = time.perf_counter()
        logger.info(f" Found year_division_cell '{year_division_cell}' in {end - start:.8f} seconds")
        return year_division_cell

    @classmethod
    async def _get_month_cell(cls, user: dict, date: datetime.datetime) -> dict[str, int]:
        start = time.perf_counter()
        user_format = user['format']
        year_cell = await cls._get_year_cell(user, date)
        year_division_cell = await cls._get_year_division_cell(user, year_cell, date)
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
            logger.error(f" Year_division_cell is None | Error: {e}")
        end = time.perf_counter()
        logger.info(f" Found month_cell '{month_cell}' in {end - start:.8f} seconds")
        return month_cell

    @classmethod    
    async def get_current_date_cell(cls, date: datetime.datetime, user: dict, chosen: list) -> tuple[int, list[int]]:
        """Returns a tuple with the format (row, col) | 0-indexed"""
        user_format: str = user['format']
        user_activities: list = user['activities']

        # All values from these cells are (0-indexed)
        # The underlying process: Year -> YearDiv (If not yearly) -> Month -> Date
        month_cell: dict = await cls._get_month_cell(user= user, date= date)

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

    @classmethod
    async def log_participants(cls, user: dict):
        """Logs the user onto the Participants sheet"""
        worksheet = await (await cls.get_spreadsheet_client()).worksheet("Participants")

        start = time.perf_counter()
        try:
            username = user['username']
            activities: list = user['activities']
            date: str = user['registered_at']
        except KeyError as e:
            logger.exception(f"Missing key in user dictionary: {e}")
            return
        
        participant_sheet_id = worksheet.id
        name_col = await worksheet.col_values(1) # 1-indexed argument
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
            await (await cls.get_spreadsheet_client()).batch_update({"requests": compiledReq})
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