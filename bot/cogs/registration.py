# Discord Imports
import discord 
from discord import app_commands
from discord.ext import commands
from bot.services.sheet_service import sheetManager

# Other Imports
import bot.helpers.utils as utls
from bot.config_builder import ConfigDTO
import time
import datetime

# Globals
SHEET = sheetManager.get_sheet_client()
CFG = ConfigDTO()
VALID_UTC_OFFSET = {
    (-12,0), (-11,0),(-10,0),(-9,30),(-9,0),(-8,0),(-7,0),(-6,0),(-5,0), # 9 items
    (-4,0),(-3,30),(-3,0),(-2,0),(-1,0),(0,0),(1,0),(2,0),(3,0),(3,30), # 10 items
    (4,0),(4,30),(5,0),(5,30),(5,45),(6,0),(6,30),(7,0),(8,0),(8,45), # 10 items
    (9,0),(9,30),(10,0),(10,30),(11,0),(12,0),(12,45),(13,0),(14,0) # 9 items
}

def determine_activity_format(activities: list):
    total_act = len(activities)

    # Activities must be between 1 and 5
    if total_act < 1 or total_act > 5:
        raise ValueError("Invalid number of activities. Must be between 1 and 5.")
    
    # Determine the format based on the activities total
    match total_act:
        case 1: 
            return "Yearly"
        case 2:
            return "Semesterly_Standard"
        case 3: 
            return "Semesterly_Extended"
        case 4:
            return "Quarterly_Standard"
        case 5:
            return "Quarterly_Extended"

def convert_time_to_rolename(remind_time: int, utc_hours: int, utc_minutes: int) -> str:
    """Converts the remind time from the user into a UTC+00:00 rolename as string"""
    raw_time = datetime.datetime.strptime(f"{remind_time}:00", "%H:%M")
    local_user_remind_time = raw_time.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=utc_hours, minutes=utc_minutes)))
    user_remind_time = local_user_remind_time.astimezone(tz=datetime.timezone.utc)
    
    role_name = f"{'0' if user_remind_time.hour < 10 else ''}{user_remind_time.hour}:{user_remind_time.minute}{'0' if user_remind_time.minute == 0 else ''}"
    return role_name


def tableGeneration(date: datetime.datetime, userID: int, user: dict):
    registrationRequest = [] # A list to place all the request later on    
    worksheet = sheetManager.get_worksheet("Template")
    templateSheetID = worksheet.id

    
    username: str = user.get("username", "Unknown User")
    userActivities: list = user.get("activities", [])
    userFormat: str = user.get("format", "Format not found")


    newSheetID = utls.newUserSheetID(userID)
    templateUserLayout = utls.templateSheetLayout(username, userFormat) 
    # All indexes from here are 0-indexed. startIndex are inclusive, endIndex are exclusive
    tableSetup = [ # This list is for sheet setup
        {
            "addSheet": { # Make a new sheet for the new user
                "properties": {
                    "title": username,
                    "sheetId": newSheetID # Customized ID from 6 digits of their userID
                }
            },
        },
        utls.make_copy_paste_req( # Copas label table from template
            source_sheet_id=templateSheetID,
            origin_start_row=0,
            origin_end_row=11,
            origin_start_col=0,
            origin_end_col=2,
            dest_sheet_id=newSheetID,
            dest_start_row=0,
            dest_end_row=11,
            dest_start_col=0,
            dest_end_col=2),

        utls.make_copy_paste_req( # Copas table from template
            source_sheet_id=templateSheetID,
            origin_start_row=templateUserLayout[username]["startRowIndex"],
            origin_end_row=templateUserLayout[username]["endRowIndex"],
            origin_start_col=templateUserLayout[username]["startColumnIndex"],
            origin_end_col=templateUserLayout[username]["endColumnIndex"],
            dest_sheet_id=newSheetID,
            dest_start_row=0,
            dest_end_row=35,
            dest_start_col=3, # D column
            dest_end_col=23 # W column (it's actually X column but it's excluded so it's W column)
            ),        
    ]

    common_replacements = [] # A list to rewrite common placeholders    
    if userFormat == "Yearly":
        common_replacements.extend([
            utls.make_update_cells__str_req( # Rewrite the username placeholder to the user's username (D1)
                source_sheet_id=newSheetID,
                start_row= 0,
                end_row= 1,
                start_col= 3,
                end_col= 4,
                value= f"{username} - {userActivities[0]}"
            ),
            utls.make_update_cells__str_req( # Rewrite the year placeholder as today's year (D3)
                source_sheet_id=newSheetID,
                start_row= 2,
                end_row= 3,
                start_col= 3,
                end_col= 4,
                value= f"{date.year}"
            )                        
        ])
    else:
        # Rewrite the common placeholders
        common_replacements.extend([
            utls.make_update_cells__str_req( # Rewrite the year placeholder as today's year (D3)
                source_sheet_id=newSheetID,
                start_row= 0,
                end_row= 1,
                start_col= 3,
                end_col= 4,
                value= f"{date.year}"
            ),
            utls.make_update_cells__str_req( # Rewrite the username placeholder as user's username (E1)
                source_sheet_id=newSheetID,
                start_row= 0,
                end_row= 1,
                start_col= 4,
                end_col= 5,
                value= f"{username}"
            )           
        ])
        
        # Rewrite the activity placeholders
        activityRow = 3
        activityRewrites: list = utls.activity_rewrites(
            newSheetID, 
            user, 
            utls.col_range_selector(user['format']), 
            activityRow)        
        common_replacements.extend(activityRewrites)

        # Time related rewrites
        time_related_rewrites: list = []
        fullYear = (
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September","October", "November", "December"
        )
        
        fullYearDivision = (
            "Semester 1", "Semester 2",
            "Q1", "Q2", "Q3", "Q4"
        )

        start_month = 0 # Default value. If this stays 0, the loop for rewriting month won't execute
        if "Semesterly" in userFormat:            
            if date.month < 6:
                year_div_selector = 0
            else :
                year_div_selector = 1
                start_month = count_ender = 6                
        elif "Quarterly" in userFormat:
            count_ender = 3

            if date.month <= 3:
                start_month = 0
                year_div_selector = 2
            elif date.month <= 6:
                start_month = 3
                year_div_selector = 3
            elif date.month <= 9:         
                start_month = 6
                year_div_selector = 4
            else :
                year_div_selector = 5

        # Rewrite month
        if start_month != 0:
            for month in range(start_month, start_month + count_ender):
                if "Semesterly" in userFormat:
                    month_index = 6 + (len(userActivities) * (month % 6)) - 1
                else: 
                    month_index = 6 + (len(userActivities) * (month % 3)) - 1
                time_related_rewrites.extend([
                    utls.make_update_cells__str_req(
                        source_sheet_id=newSheetID,
                        start_row= 2,
                        end_row= 3,
                        start_col= month_index,
                        end_col= month_index + 1,
                        value= f"{fullYear[month]}"
                    )                   
                ])
        # Rewrite year division (semester/quarter)
        time_related_rewrites.extend([
            utls.make_update_cells__str_req(
                source_sheet_id=newSheetID,
                start_row= 2,
                end_row= 3,
                start_col= 3,
                end_col= 4,
                value= f"{fullYearDivision[year_div_selector]}"
            )           
        ])


    tableSetup.extend(common_replacements)
    if userFormat != "Yearly": tableSetup.extend(time_related_rewrites)
    registrationRequest.extend(tableSetup)
    return registrationRequest


def copiesNeeded(date: datetime.datetime, userFormat: str) -> int:
    copiesNeeded = 0
    if "Quarterly" in userFormat:
        if date.month <= 3:
            copiesNeeded = 3
        elif date.month <= 6:
            copiesNeeded = 2
        elif date.month <= 9:
            copiesNeeded = 1
        else:
            copiesNeeded = 0
    elif "Semesterly" in userFormat:
        if date.month <= 6:
            copiesNeeded = 1
        else:
            copiesNeeded = 0
    return copiesNeeded


def tableDuplication(date: datetime.datetime, userID: int, user: dict):
    """ Duplicate table for non yearly table formats. Only used for registration"""

    userFormat = user['format']
    if userFormat == "Yearly": # Early exit, tableDuplication is not designed for Yearly as it is not needed
        return ValueError(f"Not supported for {userFormat} format!")
    
    sheetID = utls.newUserSheetID(userID)
    userActivities = user['activities']
    totalCopies = copiesNeeded(date, userFormat)

    if totalCopies == 0:
        print("No duplication needed!")
        return

    # Default values, all values here are 0-indexed
    fullYear = (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September","October", "November", "December"
    )
    fullYearDivision = (
        "Semester 1", "Semester 2",
        "Q1", "Q2", "Q3", "Q4"
    )  

    if "Semesterly" in userFormat:
        start_month = count_ender = 6 # Duplication continues after the 1st semester.        
        year_div_selector = 1 # Semester 1 is not needed

        if userFormat == "Semesterly_Standard":
            end_col = 17
        elif userFormat == "Semesterly_Extended":
            end_col = 23

    elif "Quarterly" in userFormat:
        start_dest_row = 36
        end_dest_row = 71
        count_ender = 3

        if userFormat == "Quarterly_Standard":
            end_col = 17
        elif userFormat == "Quarterly_Extended":
            end_col = 20
                
        # Determine the month name rewrites
        if date.month <= 3: # 3 copies
            year_div_selector = 3
            start_month = 3 # April
        elif date.month <= 6: # 2 copies
            year_div_selector = 4 
            start_month = 6 # July
        elif date.month <= 9: # 1 copy
            year_div_selector = 5
            start_month = 9 # October        
                
                
    duplication_req: list = []
    while(totalCopies >= 1):
        duplication_req.extend([
            utls.make_copy_paste_req( # Copas table from current sheet
                source_sheet_id=sheetID,
                origin_start_row=0,
                origin_end_row=35,
                origin_start_col=3,
                origin_end_col=end_col, # Dynamic column, (it really doesn't matter but prevents a bad copy)
                dest_sheet_id=sheetID,
                dest_start_row=start_dest_row,
                dest_end_row=end_dest_row,
                dest_start_col=3,
                dest_end_col=end_col
            )])
              
        duplication_req.extend([
            utls.make_update_cells__str_req( # Rewrite the month for duplication
                source_sheet_id=sheetID,
                start_row= start_dest_row + 2,
                end_row= start_dest_row + 3,
                start_col= 3,
                end_col= 4,
                value= fullYearDivision[year_div_selector]
            )])
                
        for month in range(start_month, start_month + count_ender):
            if "Semesterly" in userFormat:
                month_index = 6 + (len(userActivities) * (month % 6)) - 1
            else: 
                month_index = 6 + (len(userActivities) * (month % 3)) - 1
            duplication_req.extend([
                utls.make_update_cells__str_req( # Rewrite the month for duplication
                    source_sheet_id=sheetID,
                    start_row= start_dest_row + 2,
                    end_row= start_dest_row + 3,
                    start_col= month_index,
                    end_col= month_index + 1,
                    value= fullYear[month]
                )])

        # Incrementation
        totalCopies -= 1        
        if userFormat == "Yearly":
            start_dest_row += 35 
            end_dest_row += 35
        else:
            start_dest_row += 36
            end_dest_row += 36

            year_div_selector += 1
            if "Quarterly" in userFormat:
                start_month += 3
        
    return duplication_req    

class Registration(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")
    

    @app_commands.command(name = "register", description = "Registers a new user onto the sheet")    
    @app_commands.describe(
        name = "A username to register with. Defaulted to your discord name",
        activity1 = "Your required first activity",
        activity2 = "Your second activity",
        activity3 = "Your third activity",
        activity4 = "Your fourth activity",
        activity5 = "Your fifth activity",
        remind_time = "A reminder time. Type in the hour for you to be pinged at. (24-hour format)",
        utc_hours = "UTC hour offset, Ranges from -12 to 14. If positive, omit the '+' sign.",
        utc_minutes = "UTC minute offset. Only has 0, 30, and 45")
    
    async def register(
        self, 
        interaction: discord.Interaction,        
        remind_time: int,
        utc_hours: int,
        utc_minutes: int,
        activity1: str,
        activity2: str = None,
        activity3: str = None,
        activity4: str = None,
        activity5: str = None,
        name: str = None
        ):
        print(f"{interaction.user.name} is trying to register")
        commandStartTime = time.perf_counter()
        userID = str(interaction.user.id)
        usersData = utls.loadJSON(CFG.USERS_FILE)

        # Validations
        if userID in usersData:
            print(f"{interaction.user.name} has already registered! Stopping registration process.\n")
            username = usersData[userID]['username']
            await interaction.response.send_message(f"{interaction.user.mention}, you are already registered as {username}!", ephemeral=True)
            return

        if activity1 is None:
            await interaction.response.send_message("Please provide at least one activity to register with.", ephemeral=True)
            return
                
        if remind_time < 0 or remind_time > 23:
            await interaction.response.send_message("Invalid hour! Please enter a valid hour.", ephemeral=True)
            return
        
        user_utc_offset: tuple = (utc_hours, utc_minutes)
        if user_utc_offset not in VALID_UTC_OFFSET:
            await interaction.response.send_message("Invalid UTC offset! Please enter a valid UTC offset.", ephemeral= True)
            return
        
        
        await interaction.response.defer(thinking=True)
        if name is None:
            name = interaction.user.name
            await interaction.followup.send("Your username will be your discord username. Syncing...", ephemeral=True)

        
        try:
            temp: list = [activity1, activity2, activity3, activity4, activity5]
            activityList: list = sorted([activity.strip().capitalize() for activity in temp if activity is not None])
            
            # Write the data to local file
            processStartTime = time.perf_counter()
            usersData[userID] = {} # Make a new dict for the user
            usersData[userID]['username'] = name
            usersData[userID]['activities'] = activityList
            usersData[userID]['format'] = determine_activity_format(activityList)
            usersData[userID]['remind_at'] = remind_time
            usersData[userID]['registered_at'] = datetime.date.isoformat(datetime.datetime.now())
            usersData[userID]['utc_offset'] = user_utc_offset
            utls.saveJSON(usersData, CFG.USERS_FILE)
            processEndTime = time.perf_counter()
            print(f"Registered as {name} into the local logs in {processEndTime - processStartTime:.4f} seconds")
        except Exception as error:
            print(f"An error has occured when registering locally! {error}")

        
        # Try to write to Google Sheet (Slow Process)
        try:
            # Write the user onto the Participants worksheet
            processStartTime = time.perf_counter()
            sheetManager.log_participants(usersData[userID])
            processEndTime = time.perf_counter()
            print(f"Succesfully logged {name} to participants sheet in {processEndTime - processStartTime:.4f} seconds")


            # Make new sheet and table for the user 
            processStartTime = time.perf_counter()
            SHEET.batch_update({"requests": tableGeneration(                
                date = datetime.datetime.now(),
                userID = int(userID),
                user= usersData.get(userID))})
            processEndTime = time.perf_counter()
            print(f"Added {name}'s sheet in {processEndTime - processStartTime:.4f} seconds")

            # Update the bot worksheet cache
            sheetManager.update_worksheets_cache(usersData[userID]['username'])


        except Exception as error:
            print(f"An error has occured, {error}")
            await interaction.followup.send(f"An error has occurred, {error}", ephemeral=True)
            return

        # Assign the user their time role
        try:
            role_name = convert_time_to_rolename(usersData[userID]['remind_at'], utc_hours, utc_minutes)        
            time_role = discord.utils.get(interaction.guild.roles, name=role_name)
            await interaction.user.add_roles(time_role)
            print(f"Successfully assigned {role_name} role to {interaction.user.name}")
        except Exception as error:
            print(f"An error occured when assigning roles | {error}")
            await interaction.followup.send(f"An error occured when assigning roles, {error}", ephemeral=True)
            return
                    
        
        # Print success logs
        print(f"{interaction.user.name} successfully registered as {name} with activities: {', '.join(activityList)} with a reminder at {remind_time}:00 UTC {'+' if utc_hours >= 0 else ''}{str(utc_hours).zfill(3 if utc_hours < 0 else 2)}:{utc_minutes:02d}")
        await interaction.followup.send(f"{interaction.user.mention} successfully registered as {name} with activities: {", ".join(activityList)} with a reminder at {remind_time}:00 UTC {'+' if utc_hours >= 0 else ''}{utc_hours}:{utc_minutes}")
        commandEndTime = time.perf_counter()
        print(f"Registration executed in {commandEndTime - commandStartTime:.4f} seconds\n")

    @app_commands.command(name="signout", description="Signs out from the sheet. Will delete your sheet data upon initiating")
    async def signout(self, interaction: discord.Interaction):
        command_start_time = time.perf_counter()
        print(f"{interaction.user.name} is trying to sign-out")

        userID = str(interaction.user.id)
        usersData: dict = utls.loadJSON(CFG.USERS_FILE)
        # Validations
        if userID not in usersData:
            print(f"{interaction.user.name} tried to sign-out but hasn't registered")
            await interaction.response.send_message(f"Can't sign out if you haven't registered!", ephemeral=True)
            return
        
        await interaction.response.defer()
        try:
            # Erase user from participant sheet
            registered_name: str = usersData[userID]["username"]
            participant_sheet = sheetManager.get_worksheet("Participants")
            user_cell = participant_sheet.find(registered_name) # The row and column of this cell is 1-indexed
            remove_user_req = [
                utls.make_update_cells__str_req( # Delete the user's row 
                    source_sheet_id=participant_sheet.id,
                    start_row= user_cell.row - 1,
                    end_row= user_cell.row,
                    start_col= user_cell.col - 1,
                    end_col= user_cell.col + 7,
                    value=""
                ),
                {
                    "deleteSheet": {
                        "sheetId": sheetManager.get_worksheet(registered_name).id
                    }
                }
            ]
            
            sheet_deletion_start = time.perf_counter()  
            SHEET.batch_update({"requests": remove_user_req})
            sheet_deletion_end = time.perf_counter()
            print(f"Sheet deletion finished in {sheet_deletion_end - sheet_deletion_start:.8f} seconds")

            # Role deletion
            role_start = time.perf_counter()
            role_name = convert_time_to_rolename(usersData[userID]['remind_at'], utc_hours= usersData[userID]["utc_offset"][0], utc_minutes=usersData[userID]["utc_offset"][1])
            time_role = discord.utils.get(interaction.guild.roles, name=role_name)            
            await interaction.user.remove_roles(time_role)
            print(f"Succesfully removed {interaction.user.name}'s time role in {time.perf_counter() - role_start:.8f} seconds!")

            # Local deletion
            local_deletion_start = time.perf_counter()            
            del usersData[userID]
            utls.saveJSON(usersData, CFG.USERS_FILE)
            local_deletion_end = time.perf_counter()
            print(f"Local deletion finished in {local_deletion_end - local_deletion_start:.8f} seconds")        
        except Exception as e:
            print(f"Error: {e}")
            await interaction.followup.send(f"Something went wrong! {e}\n", ephemeral=True)
            return
        command_end_time = time.perf_counter()
        print(f"Signing out {registered_name} took {command_end_time - command_start_time:4f} seconds\n")
        await interaction.followup.send(f"You've been signed out!")

async def setup(bot: commands.Bot):    
    _GUILD_ID = discord.Object(id = CFG.GUILD_ID)    
    await bot.add_cog(Registration(bot), guild = _GUILD_ID)