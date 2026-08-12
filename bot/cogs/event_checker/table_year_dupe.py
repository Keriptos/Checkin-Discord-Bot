# Discord Imports
import discord
from discord.ext import tasks, commands

# Other Imports
import bot.helpers.utils as utls
from bot.config_builder import ConfigDTO
from bot.services.sheet_service import sheetManager
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
    user_format: str = user['format']
        

    # 2 approaches,
    # Approach 1: Delete existing table, remake a new one. (Users can't see past years anymore)
    # Approach 2: Use existing tables, their sheet will become a long one. 
    # (Gotta scroll for the current year if they've done this for a long time)


    # Using approach 2, search for an empty cell after existing table
    timeColumn = sheetManager.get_year_column(username)
    foundYear = False
    yearRow: int = 0 # 0-indexed. Row index of the first year. (Default value will be used for non-yearly format)
    
    start = time.perf_counter()
    if user_format == "Yearly":
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
        if "Semesterly" in user_format:
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

    
def copiesNeeded(user_format: str) -> int | None:
    """ It's the start of the year, so no need for dynamic selection based on months"""    
    if "Quarterly" in user_format:        
        copiesNeeded = 4        
    elif "Semesterly" in user_format: # Semesterly
        copiesNeeded = 2    
    elif user_format == "Yearly": # Early exit because Yearly doesn't need a loop
        return 
    else:
        raise ValueError(f"User's format is unrecognized! {user_format}")
    return copiesNeeded


def tableYearDupeReq(start_cell: int, userID: int, user: dict):    
    user_format = user['format']
    sheetID = utls.newUserSheetID(userID)
    userActivities = user['activities']
    total_copies = copiesNeeded(user_format)
    
    duplication_req: list = []
    if user_format == "Yearly":
        # Pre-requisites of the cell locations
        templateSheetID = sheetManager.get_worksheet(worksheet_name="Template").id
        start_dest_row = start_cell
        end_dest_row = start_cell + 34

        # Request section        
        duplication_req.extend([
            utls.make_copy_paste_req( # Copas table from template sheet
                source_sheet_id= templateSheetID,
                source_start_row= 0,
                source_end_row= 34,
                source_start_col= 3,
                source_end_col= 17,
                dest_sheet_id= sheetID, 
                dest_start_row= start_dest_row,
                dest_end_row= end_dest_row,
                dest_start_col= 3,
                dest_end_col= 17                
            )                    
        ])

        duplication_req.extend([ 
            # TODO: Add a delete prevention so that this won't run if the table's actually empty. It'd run faster
            utls.make_update_cells__str_req( # Delete inner table contents
                source_sheet_id= sheetID,
                start_row= start_dest_row + 2,
                end_row= start_dest_row + 3,
                start_col= 5,
                end_col= 17,
                value = ""),                        
            utls.make_update_cells__str_req( # Rewrite the name & activity
                source_sheet_id= sheetID,
                start_row= start_dest_row,
                end_row= start_dest_row + 1,
                start_col= 3, # Column D
                end_col= 4,
                value= f"{user['username']} - {', '.join(userActivities)}"),
            utls.make_update_cells__str_req( # Rewrite the year
                source_sheet_id= sheetID,
                start_row= start_dest_row + 1,
                end_row= start_dest_row + 2,
                start_col= 3, # Column D
                end_col= 4,
                value= f"{datetime.datetime.now().year + 1}")            
        ])        
        return duplication_req
    

    # Default values, all values here are 0-indexed
    full_year = (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September","October", "November", "December"
    )
    full_year_division = (
        "Semester 1", "Semester 2",
        "Q1", "Q2", "Q3", "Q4"
    )  

    # Pre-requisites of the cell positions
    start_dest_row = start_cell
    end_dest_row = start_cell + 35
    if "Semesterly" in user_format:
        start_month = 0
        count_ender = 6 # Dynamic loop ender offset (Each semester has 6 months)
        year_div_selector = 0

        if user_format == "Semesterly_Standard":
            end_col = 17
        elif user_format == "Semesterly_Extended":
            end_col = 23

    else: # Quarterly
        year_div_selector = 2 # Q1
        start_month = 0 # January
        count_ender = 3 # Dynamic loop ender offset (Each quarter has 3 months)

        if user_format == "Quarterly_Standard":
            end_col = 17
        elif user_format == "Quarterly_Extended":
            end_col = 20
    
    # Request Section     
    while(total_copies):
        duplication_req.extend([
            utls.make_copy_paste_req( # Copas table from current sheet
                source_sheet_id= sheetID,
                source_start_row= 0,
                source_end_row= 36,
                source_start_col= 3,
                source_end_col= end_col, # Dynamic column, (it really doesn't matter but prevents a bad copy)
                dest_sheet_id= sheetID,
                dest_start_row= start_dest_row,
                dest_end_row= end_dest_row,
                dest_start_col= 3,
                dest_end_col= end_col)                      
        ])
        
        duplication_req.extend([
            utls.make_update_cells__str_req( # Delete inner table contents
                source_sheet_id= sheetID,
                start_row= start_dest_row + 4,
                end_row= start_dest_row + 35,
                start_col= 5,
                end_col= end_col,
                value = ""),
            utls.make_update_cells__str_req( # Rewrite the year
                source_sheet_id= sheetID,
                start_row= start_dest_row,                    
                end_row= start_dest_row + 1,
                start_col= 3, # Column D
                end_col= 4,
                value= f"{datetime.datetime.now().year + 1}"),
            utls.make_update_cells__str_req( # Rewrite the yearDivision for duplication
                source_sheet_id= sheetID,
                start_row= start_dest_row + 1,
                end_row= start_dest_row + 2,
                start_col= 3, # Column D
                end_col= 4,
                value= f"{full_year_division[year_div_selector]}")            
        ])
        
        for month in range(start_month, start_month + count_ender):
            if "Semesterly" in user_format:
                month_index = 6 + (len(userActivities) * (month % 6)) - 1
            else: 
                month_index = 6 + (len(userActivities) * (month % 3)) - 1
            duplication_req.extend([
                utls.make_update_cells__str_req( # Rewrite the month for duplication
                    source_sheet_id= sheetID,
                    start_row= start_dest_row + 2,
                    end_row= start_dest_row + 3,
                    start_col= month_index, # Column D
                    end_col= month_index + 1,
                    value= f"{full_year[month]}"
                )])
        
        # Incrementation
        total_copies -= 1
        start_dest_row += 36
        end_dest_row += 36
        year_div_selector += 1
        if "Quarterly" in user_format:
            start_month += 3
        
    return duplication_req


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
                    start_cell = find_empty_cell_row(date = datetime.datetime.now(), user= users[target_user_id]),
                    userID = int(target_user_id),
                    user = users[target_user_id]
                )})
                end = time.perf_counter()
                print(f"Duplicated table for {users[target_user_id]['username']} in {end - start:.4f} seconds\n")
        elif now.month != 12 and now.day == 1:
            print(f"table_year_dupe: {12 - now.month} months left")
        
    @is_end_of_year_check.before_loop
    async def before_is_end_of_year_check(self):
        print('table_year_dupe background task is waiting...')
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    GUILD_ID = discord.Object(id = CFG.GUILD_ID)
    await bot.add_cog(YearCheck(bot), guild= GUILD_ID)