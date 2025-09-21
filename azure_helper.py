# Helper for azure database scripts
import pyodbc
import json
import csv
import sys
import logging
from datetime import datetime
from dateutil import parser
import name_validator as nv
from blob_helper import *

# SECURITY NOTE:
# Usernames and passwords in the db_list below are intentionally replaced with
# EXAMPLEUSER and EXAMPLEPASSWORD to preserve confidential credentials that
# belong to the University of Maryland Athletics IT Department.

# NOTE: Most helper calls need the a login variable, which can be obtained by giving a database name to get_db
# New databases and their login information NEED to be added to the dictionary at the bottom of this script in the dictionary: db_list
# login var will be assumed to follow this format for all helper methods that need it
    # login = {
    #     "server": 'xxx.database.windows.net',
    #     "database": 'training_db',
    #     "username": 'yyy',
    #     "password": 'zzz',
    #     "driver": '{SQL Server}',
    #     "table": '[dbo].[main]'
    # }
# 

today = str(datetime.today()) 
curr_date = datetime.today().strftime("%Y-%m-%d") 
logging.basicConfig(filename="Azure_Helper_Logs.log", level=logging.INFO) 

# Establishes a database connection
def establish_connection(login):
    return pyodbc.connect('DRIVER='+login['driver']+';SERVER=tcp:'+login['server']+';PORT=1433;DATABASE='+login['database']+';UID='+login['username']+';PWD='+ login['password'])
def close_connection(connection):
    connection.close()

#Inserts activity list into Catapult Table
def insert_table_batch(conn,table_name, activity_list):
    with conn.cursor() as cursor:
        #Find the columns using the 1st recod in the data list
        columns = str(activity_list[0].keys()).strip("dict_keys([").strip("])").replace("'","")
        exec_str = "INSERT INTO "+ str(table_name) + " (" + columns + ") VALUES "

        #Iterate through all the records and append them to a single string for the SQL insert statement
        for index in range(len(activity_list)):
            dict_data = activity_list[index]
            if index == len(activity_list)-1:
                exec_str += "(" + str(dict_data.values()).strip("dict_values([").strip("])") + ")"
            else:
                exec_str += "(" + str(dict_data.values()).strip("dict_values([").strip("])") + "),"    

        print(today + " : Attemping query \"" + exec_str + "\"")

        try:
            cursor.execute(exec_str)
            print("Insert Activity Success: " + str(cursor.rowcount) + " row(s) affected. Intended rows affected is " + str(len(activity_list)))

        except pyodbc.Error as error:
            print("Insert Activity Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
            logging.info("Insert Activity Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
            blob_output("azure_helper.log", "logs", "Insert Activity Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
            raise error



# Example usage
""" connection = establish_connection(login)

insert_table_batch(connection, "Table1", related_activity_list_1)
insert_table_batch(connection, "Table2", related_activity_list_2)
insert_table_batch(connection, "Table3", related_activity_list_3)

connection.close() """

#Inserts activity list into Catapult Table
def delete_table_batch(conn, table_name, delete_key, delete_value):
    with conn.cursor() as cursor:
        #Find the columns using the 1st recod in the data list
        exec_str = "DELETE FROM "+ str(table_name) + " WHERE " + delete_key + " = \'" + delete_value + "\'"

        print(today + " : Attemping query \"" + exec_str + "\"")

        try:
            cursor.execute(exec_str)
            print("Delete Data Success: " + str(cursor.rowcount) + " row(s) affected." )

        except pyodbc.Error as error:
            print("Delete Data Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
            raise error

# with pyodbc.connect('DRIVER='+driver+';SERVER=tcp:'+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+ password) as conn:
#     with conn.cursor() as cursor:
#         cursor.execute(" ... ")

# Inserts dictionary of data into the database specified in login 
# This method works for tables where UID is the only primary key
def insert_athlete(conn, login, dict_data_list):
    with conn.cursor() as cursor:

        columns = str(dict_data_list[0].keys()).strip("dict_keys([").strip("])").replace("'","")

        exec_str = "INSERT INTO "+ str(login['tables']['athletes']) + " (" + columns + ") VALUES "
        for index in range(len(dict_data_list)):
            dict_data = dict_data_list[index]
            if index == len(dict_data_list)-1:
                exec_str += "(" + str(dict_data.values()).strip("dict_values([").strip("])") + ")"
            else:
                exec_str += "(" + str(dict_data.values()).strip("dict_values([").strip("])") + ")," 

        logging.info(today + " : Attemping query \"" + exec_str + "\"")
        blob_output("azure_helper.log", "logs", today + " : Attemping query \"" + exec_str + "\"")

        if get_athlete(conn, login, dict_data['uid']):
            logging.info(today + " : Insert Error: User already exists")
            blob_output("azure_helper.log", "logs", today + " : Insert Error: User already exists")
            
        else:
            try:
                cursor.execute(exec_str)
                logging.info("Insert Athlete Success: " + str(cursor.rowcount) + " row(s) affected. Intended rows affected is " + str(len(dict_data_list)))
                blob_output("azure_helper.log", "logs", "Insert Athlete Success: " + str(cursor.rowcount) + " row(s) affected. Intended rows affected is " + str(len(dict_data_list)))

            except pyodbc.Error as error:
                logging.info("Insert Athlete Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
                blob_output("azure_helper.log", "logs", "Insert Athlete Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))


# Returns dictionary of athlete information 
def get_athlete(conn, login, uid):
    with conn.cursor() as cursor:

        exec_str = f"SELECT * FROM {login['tables']['athletes']} WHERE UID = {str(uid)}"
        cursor.execute(exec_str)
        
        iterator = cursor.fetchone()
        if iterator:
            columns = [column[0] for column in cursor.description]
            return dict(zip(columns, iterator))
        else:
            return None

    
# Updates the athlete with the specified UID with the values specified in the new dict OR inserts them if they don't exist
def update_athlete(conn, login, uid, new_dict):
    with conn.cursor() as cursor:
        
        exec_str = "UPDATE " + login['tables']['athletes'] + " set "

        for pair in new_dict:
            if type(new_dict[pair]) == int:
                exec_str += (str(pair) + " = " + str(new_dict[pair]) + ", ")
            else:
                exec_str += (str(pair) + " = '" + str(new_dict[pair]) + "', ")

        exec_str = exec_str[:-2]
        exec_str += " where uid = " + str(uid)

        logging.info(today + " : Attemping query \"" + exec_str + "\"")
        blob_output("azure_helper.log", "logs", today + " : Attemping query \"" + exec_str + "\"")

        if get_athlete(conn, login, uid):
            try:
                cursor.execute(exec_str)
                logging.info("Update Athlete Success: " + str(cursor.rowcount) + " row(s) affected. Intended rows affected is 1")
                blob_output("azure_helper.log", "logs", "Update Athlete Success: " + str(cursor.rowcount) + " row(s) affected. Intended rows affected is 1")

            except pyodbc.Error as error:
                logging.info("Update Athlete Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
                blob_output("azure_helper.log", "logs", "Update Athlete Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
                
        else:
            logging.info("Update Athlete calling Insert Athlete function instead since athlete does NOT exist")
            blob_output("azure_helper.log", "logs", "Update Athlete calling Insert Athlete function instead since athlete does NOT exist")
            insert_athlete(conn, login, [new_dict])

# Inserts dictionary of data into the database specified in login 
# This method is meant to interact with the AthleteSports table where UID and Sport ID are composite keys
def insert_athlete_sport(conn, login, dict_data_list):
    with conn.cursor() as cursor:
        #Find the columns using the 1st recod in the data list
        columns = str(dict_data_list[0].keys()).strip("dict_keys([").strip("])").replace("'","")
        exec_str = "INSERT INTO "+ str(login['tables']['athlete_sports']) + " (" + columns + ") VALUES "

        #Iterate through all the records and append them to a single string for the SQL insert statement
        for index in range(len(dict_data_list)):
            dict_data = dict_data_list[index]
            if index == len(dict_data_list)-1:
                exec_str += "(" + str(dict_data.values()).strip("dict_values([").strip("])") + ")"
            else:
                exec_str += "(" + str(dict_data.values()).strip("dict_values([").strip("])") + "),"    

        logging.info(today + " : Attemping query \"" + exec_str + "\"")
        blob_output("azure_helper.log", "logs", today + " : Attemping query \"" + exec_str + "\"")

        try:
            cursor.execute(exec_str)
            logging.info("Insert Athlete Sport Success: " + str(cursor.rowcount) + " row(s) affected. Intended rows affected is " + str(len(dict_data_list)))
            blob_output("azure_helper.log", "logs", "Insert Athlete Sport Success: " + str(cursor.rowcount) + " row(s) affected. Intended rows affected is " + str(len(dict_data_list)))

        except pyodbc.Error as error:
            logging.info("Insert Athlete Sport Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
            blob_output("azure_helper.log", "logs", "Insert Athlete Sport Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))

# Returns dictionary of athlete information 
def get_athlete_sport(conn, login, uid, sport_id):
    with conn.cursor() as cursor:

        cursor.execute(f"SELECT * FROM {login['tables']['athlete_sports']} WHERE UID = {str(uid)} AND SPORT_ID = {str(sport_id)}")
        
        iterator = cursor.fetchone()
        if iterator:
            columns = [column[0] for column in cursor.description]
            return dict(zip(columns, iterator))
        else:
            # print("Get Athlete Error: User does NOT exist.")
            return None

# Updates the athlete's sport with the specified UID and Sport ID with the values specified in the new dict OR inserts them if they don't exist
def update_athlete_sport(conn, login, uid, new_dict):
    with conn.cursor() as cursor:
        sport_id = new_dict["sport_id"] 
        athlete = get_athlete_sport(conn, login, uid, sport_id)

        if athlete:
            exec_str = "UPDATE " + login['tables']['athlete_sports'] + " set "

            for pair in new_dict:
                if type(new_dict[pair]) == int:
                    exec_str += (str(pair) + " = " + str(new_dict[pair]) + ", ")
                else:
                    exec_str += (str(pair) + " = '" + str(new_dict[pair]) + "', ")

            exec_str = exec_str[:-2]
            exec_str += " where uid = " + str(uid) + " and sport_id = " + str(sport_id)

            logging.info(today + " : Attemping query \"" + exec_str + "\"")
            blob_output("azure_helper.log", "logs", today + " : Attemping query \"" + exec_str + "\"")
            try:

                cursor.execute(exec_str)
                logging.info("Update Athlete Sport Success: " + str(cursor.rowcount) + " row(s) affected. Intended rows affected is 1")
                blob_output("azure_helper.log", "logs", "Update Athlete Sport Success: " + str(cursor.rowcount) + " row(s) affected. Intended rows affected is 1")

            except pyodbc.Error as error:
                logging.info("Update Athlete Sport Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
                blob_output("azure_helper.log", "logs", "Update Athlete Sport Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
        else:
            logging.info("Update Athlete Sport calling Insert Athlete Sport since Athlete does NOT exist")
            blob_output("azure_helper.log", "logs", "Update Athlete Sport calling Insert Athlete Sport since Athlete does NOT exist")
            insert_athlete_sport(conn, login, [new_dict])
            # print("Update Athlete Error: User does NOT exist.")

# Sets the active status of an athlete to 'Inactive'
def deactivate_athlete(conn,login, uid, sport_id):
    with conn.cursor() as cursor:
        exec_str = "UPDATE " + login['tables']['athlete_sports'] + " set status_id = 2 where uid = " + str(uid) + " and sport_id = " + str(sport_id)

        logging.info(today + " : Attemping query \"" + exec_str + "\"")
        blob_output("azure_helper.log", "logs", today + " : Attemping query \"" + exec_str + "\"")
        try:
            cursor.execute(exec_str)
            logging.info("Deactivate Athlete Success: " + str(cursor.rowcount) + " row(s) affected")
            blob_output("azure_helper.log", "logs", "Deactivate Athlete Success: " + str(cursor.rowcount) + " row(s) affected")
        
        except pyodbc.Error as error:
            logging.info("Deactive Athlete Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
            blob_output("azure_helper.log", "logs", "Deactive Athlete Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
               

# Will be finalized when real table is given
# Returns a dictionary of all the UIDs mapped to the athlete's dictionary for all athletes in the specified team 
def get_roster(conn, login, team_str_name):
    with conn.cursor() as cursor:

        roster_data = {}
        cursor.execute(f"SELECT * FROM [dbo].[Athletes] \
                        JOIN [dbo].[AthleteSports] on [dbo].[Athletes].uid = [dbo].[AthleteSports].uid \
                        JOIN [dbo].[Sports] on [dbo].[AthleteSports].sport_id = [dbo].[Sports].sport_id \
                        WHERE sport_name = {team_str_name}")

        iterator = cursor.fetchone()
        while iterator:
            columns = [column[0] for column in cursor.description]
            curr_athlete = dict(zip(columns, iterator))
            roster_data.update({curr_athlete['uid']: curr_athlete})
            iterator = cursor.fetchone()
            
        return roster_data

# Returns all athlete info in this table mapped to a specific key (typically will map all records associated with an athlete to their uid)
# {UID:[{
#    Athlete info}]}
def get_all_athletes(conn, login, map_key, table):
    with conn.cursor() as cursor:

        roster_data = {}
        cursor.execute(f"SELECT * FROM {login['tables'][table]}")

        iterator = cursor.fetchone()
        while iterator:
            columns = [column[0] for column in cursor.description]
            curr_athlete = dict(zip(columns, iterator))
            uid = curr_athlete[map_key]

            if uid in roster_data.keys():
                roster_data[uid].append(curr_athlete)
            else:
                roster_data[uid] = [curr_athlete]
            iterator = cursor.fetchone()
            
        return roster_data

# similar to the previous get_all_athletes() method above, but it includes the tw team id 
# takes in athletesport login
def get_all_athlete_sports_tw(conn, login, dev_or_prod):
    with conn.cursor() as cursor:

        tw_ids = get_tw_team_id_dict(conn,get_db("spfdata"), dev_or_prod)
        roster_data = {}
        cursor.execute(f"SELECT * FROM {login['table']['sports']}")

        iterator = cursor.fetchone()
        while iterator:
            columns = [column[0] for column in cursor.description]
            curr_athlete = dict(zip(columns, iterator))
            uid = curr_athlete["uid"]

            if uid in roster_data.keys():
                tw_team_id = tw_ids[curr_athlete['sport_id']]
                curr_athlete['tw_team_id'] = tw_team_id
                roster_data[uid].append(curr_athlete)
            else:
                tw_team_id = tw_ids[curr_athlete['sport_id']]
                curr_athlete['tw_team_id'] = tw_team_id
                roster_data[uid] = [curr_athlete]
            iterator = cursor.fetchone()
            
        return roster_data

# takes in sport login
def get_tw_team_id_dict(conn,login, dev_or_prod):
    with conn.cursor() as cursor:
        teams_map = {}
        cursor.execute(f"SELECT * FROM {login['tables']['sports']}")

        iterator = cursor.fetchone()
        if dev_or_prod == "dev":
            while iterator:
                teams_map.update({iterator.sport_id: iterator.teamworks_id_dev})
                
                iterator = cursor.fetchone()
        elif dev_or_prod == "prod":
            while iterator:
                teams_map.update({iterator.sport_id: iterator.teamworks_id_prod})
                
                iterator = cursor.fetchone()
        else:
            print("Error: Type in searching for dev or prod parameter")
            
        return teams_map

# Returns a dictionary of all the team IDs mapped to their team name
def get_teams(conn,login):
    with conn.cursor() as cursor:
        teams_map = {}
        cursor.execute(f"SELECT * FROM {login['tables']['sports']}")

        iterator = cursor.fetchone()
        while iterator:
            teams_map.update({iterator.sport_name: iterator.sport_id})
            
            iterator = cursor.fetchone()
            
        return teams_map
    
# Returns dict of sis team names mapped to prod teamworks team ids
def get_sis_teams_tw(conn,login):
    with conn.cursor() as cursor:
        teams_map = {}
        cursor.execute(f"SELECT * FROM {login['tables']['sports']}")

        iterator = cursor.fetchone()
        while iterator:
            teams_map.update({iterator.sis_sport_name: iterator.teamworks_id_prod})
            
            iterator = cursor.fetchone()
            
        return teams_map
    
# Returns dict of sis names mapped to sport ids
def get_sis_teams_id(conn,login):
    with conn.cursor() as cursor:
        teams_map = {}
        cursor.execute(f"SELECT * FROM {login['tables']['sports']}")

        iterator = cursor.fetchone()
        while iterator:
            teams_map.update({iterator.sis_sport_name: iterator.sport_id})
            
            iterator = cursor.fetchone()
            
        return teams_map

# Same as get_teams but it returns tw team ids instead of the azure ones
def get_tw_teams(conn, login, dev_or_prod):
    with conn.cursor() as cursor:
        teams_map = {}
        cursor.execute(f"SELECT * FROM {login['tables']['sports']}")

        iterator = cursor.fetchone()
        if dev_or_prod == "dev":
            while iterator:
                teams_map.update({iterator.sport_name: iterator.teamworks_id_dev})
                
                iterator = cursor.fetchone()
                
            return teams_map
        elif dev_or_prod == "prod":
            while iterator:
                teams_map.update({iterator.sport_name: iterator.teamworks_id_prod})
                
                iterator = cursor.fetchone()
                
            return teams_map
        return None

# Returns a dictionary of all the status IDs with their status name
def get_statuses(conn, login):
    with conn.cursor() as cursor:
        teams_map = {}
        cursor.execute(f"SELECT * FROM {login['tables']['status']}")

        iterator = cursor.fetchone()
        while iterator:
            teams_map.update({iterator.status_description: iterator.status_id})
            
            iterator = cursor.fetchone()
            
        return teams_map

# Returns a dictionary of all the team IDs mapped to their team name
def get_inactive_reasons(conn,login):
    with conn.cursor() as cursor:
        teams_map = {}
        cursor.execute(f"SELECT * FROM {login['tables']['inactive_reasons']}")


        iterator = cursor.fetchone()
        while iterator:
            teams_map.update({iterator.reason_description: iterator.reason_id})
            
            iterator = cursor.fetchone()
            
        return teams_map
    
# Returns a dictionary of all the team IDs mapped to their team name
def get_inactive_reasons_sis(conn,login):
    with conn.cursor() as cursor:
        teams_map = {}
        cursor.execute(f"SELECT * FROM {login['tables']['inactive_reasons']}")


        iterator = cursor.fetchone()
        while iterator:
            teams_map.update({iterator.SIS_reason_desc: iterator.reason_id})
            
            iterator = cursor.fetchone()
            
        return teams_map



# Takes in the name of the database and gives the login dictionary needed for the other helper calls
def get_db(db_name):
    return db_list[db_name]

# Gets all information in the table
def get_table(conn, login, table):
    with conn.cursor() as cursor:

        table_data = []
        cursor.execute(f"SELECT * FROM {login['tables'][table]}")

        iterator = cursor.fetchone()
        while iterator:
            columns = [column[0] for column in cursor.description]
            curr_athlete = dict(zip(columns, iterator))
            table_data.append(curr_athlete)
            iterator = cursor.fetchone()
            
        return table_data
        
# Returns a list of all the data in the specified column of that table
def get_rows_for_col(conn, login, column, table):
    with conn.cursor() as cursor:

        table_data = []
        cursor.execute(f"SELECT [{column}] FROM {login['tables'][table]}")

        iterator = cursor.fetchone()
        while iterator:
            table_data.append(iterator[0])
            iterator = cursor.fetchone()
            
        return table_data
        
# Returns a list of the rows where the specified column is null
def get_null_rows(conn, login, column, table):
    with conn.cursor() as cursor:

        table_data = []
        cursor.execute(f"SELECT * FROM {login['tables'][table]} WHERE {column} IS NULL")

        iterator = cursor.fetchone()
        while iterator:
            columns = [column[0] for column in cursor.description]
            curr_athlete = dict(zip(columns, iterator))
            table_data.append(curr_athlete)
            iterator = cursor.fetchone()
            
        return table_data    

#Inserts activity list into Catapult Table
""" def insert_catapult(conn, login,activity_list):
    with conn.cursor() as cursor:
        #Find the columns using the 1st recod in the data list
        columns = str(activity_list[0].keys()).strip("dict_keys([").strip("])").replace("'","")
        exec_str = "INSERT INTO "+ str(login['table']) + " (" + columns + ") VALUES "

        #Iterate through all the records and append them to a single string for the SQL insert statement
        for index in range(len(activity_list)):
            dict_data = activity_list[index]
            if index == len(activity_list)-1:
                exec_str += "(" + str(dict_data.values()).strip("dict_values([").strip("])") + ")"
            else:
                exec_str += "(" + str(dict_data.values()).strip("dict_values([").strip("])") + "),"    

        print(today + " : Attemping query \"" + exec_str + "\"")

        try:
            cursor.execute(exec_str)
            print("Insert Activity Success: " + str(cursor.rowcount) + " row(s) affected. Intended rows affected is " + str(len(activity_list)))

        except pyodbc.Error as error:
            print("Insert Activity Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]"))) """

def insert_log(conn, login, uid, message, system, outcome):
    with conn.cursor() as cursor:
        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        print(date)
        # print(date)
        if type(uid) != int and uid.isnumeric():
            uid = int(uid)
        elif uid == "" or not uid.isnumeric():
            uid = None
        exec_str = f"INSERT INTO {str(login['tables']['logging'])} (date, uid, message, system, outcome) VALUES ('{date}', {uid}, '{message}', '{system}', '{outcome}')"

        logging.info(today + " : Attemping to log \"" + exec_str + "\"")
        blob_output("azure_helper.log", "logs", today + " : Attemping to log \"" + exec_str + "\"")
        try:
            cursor.execute(exec_str)
            logging.info("Log Success: " + str(cursor.rowcount) + " row(s) affected")
            blob_output("azure_helper.log", "logs", "Log Success: " + str(cursor.rowcount) + " row(s) affected")
        
        except pyodbc.Error as error:
            logging.info("Log Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
            blob_output("azure_helper.log", "logs", "Log Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))


def insert_call(conn, login, call_type, endpoint, payload):
    with conn.cursor() as cursor:
        uid = payload['orgID']
        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        if type(uid) != int and uid.isnumeric():
            uid = int(uid)
        elif uid == "" or not uid.isnumeric():
            uid = None
        exec_str = f"INSERT INTO {str(login['tables']['external_calls'])} (call_type, endpoint, payload, date) VALUES ('{call_type}', {endpoint}, '{payload}', '{date}')"

        logging.info(today + " : Attemping to log \"" + exec_str + "\"")
        blob_output("azure_helper.log", "logs", today + " : Attemping to log \"" + exec_str + "\"")
        try:
            cursor.execute(exec_str)
            logging.info("Log Success: " + str(cursor.rowcount) + " row(s) affected")
            blob_output("azure_helper.log", "logs", "Log Success: " + str(cursor.rowcount) + " row(s) affected")
        
        except pyodbc.Error as error:
            logging.info("Log Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))
            blob_output("azure_helper.log", "logs", "Log Error: " + str(error.args[1].partition('Server]')[2].strip("[SQL Server]")))


def process_roster_athsp(uid, athsp_db, source_aths, curr_tw_ath, ath_sport_inserts, ath_sport_updates, fr_team_dict, tw_team_dict, change, statuses, test_run):
    source_ath_teams = source_aths.keys()
    as_login = get_db("spfdata")
    conn = establish_connection(as_login)

    for teamname in source_ath_teams:
        curr = source_aths[teamname]
        if curr["Inactive Reason"]:
            inactive = ((curr["Inactive Reason"].replace("(","")).replace(")","")).split(" ")
            date_index = len(inactive)-1
            date = datetime.strptime(inactive[date_index], '%m/%d/%Y').date()
            reason = ""
            for x in range(date_index):
                reason += (inactive[x] + " ")
            reason = reason.strip()
        else:
            reason = None
            date = None

        if reason:
            reason_id = change[reason]
        else:
            reason_id = None

        sport_id = fr_team_dict[teamname]
        tw_team_id = tw_team_dict[teamname]
        if curr_tw_ath and tw_team_id in curr_tw_ath.keys() and 'athleteStatus' in curr_tw_ath[tw_team_id].keys():
            tw_status = curr_tw_ath[tw_team_id]['athleteStatus']
            
        else:
            tw_status = None

        if curr['Status Change Reason'] != "":
            ch_reason = curr['Status Change Reason']
        else:
            ch_reason = None

        ath_sport_local = {
                    "uid": int(uid),
                    "sport_id": sport_id,
                    "status_id": statuses[curr["Roster Status"]],
                    "reason_id": reason_id,
                    "change_date": date,
                    "change_reason": ch_reason,
                    "teamworks_status": tw_status
                }
        
        # if current athlete in this sport is not in the athsp table, add them 
        if (test_run == False and get_athlete_sport(conn, as_login, int(uid), ath_sport_local['sport_id']) == None) or (test_run and not any((d for d in [item for sublist in athsp_db.values() for item in sublist] if (d.get('uid') == int(uid) and d.get('sport_id') == ath_sport_local['sport_id'])))): 
            print(f"db: Athsp insert will include {curr['Full Name']} ({uid}) on {list(fr_team_dict.keys())[list(fr_team_dict.values()).index(ath_sport_local['sport_id'])]} {ath_sport_local['sport_id']}")
            blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"db: Athsp insert will include {curr['Full Name']} ({uid}) on {list(fr_team_dict.keys())[list(fr_team_dict.values()).index(ath_sport_local['sport_id'])]} {ath_sport_local['sport_id']}")
            ath_sport_inserts.append(ath_sport_local)
            curr_athsp_user = None
            
        # if curr doesn't match any of the current athsp data, update it
        else:
            
            # getting athsp user in db currently
            if test_run:
                curr_athsp_user = next((d for d in [item for sublist in athsp_db.values() for item in sublist] if d.get('uid') == int(uid) and d.get('sport_id') == ath_sport_local['sport_id']), None)
            else:
                curr_athsp_user = get_athlete_sport(conn, as_login, int(uid), ath_sport_local['sport_id']) 
            # if db athsp user and local athsp user dont match, update them
            if ath_sport_local != curr_athsp_user:
                print(f"db: Athsp update will include {curr['Full Name']} ({uid}) on {list(fr_team_dict.keys())[list(fr_team_dict.values()).index(ath_sport_local['sport_id'])]} {ath_sport_local['sport_id']}")
                blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"db: Athsp update will include {curr['Full Name']} ({uid}) on {list(fr_team_dict.keys())[list(fr_team_dict.values()).index(ath_sport_local['sport_id'])]} {ath_sport_local['sport_id']}")
                # update them in the athlete sport table 
                ath_sport_updates.append(ath_sport_local) 

        # checking if they got inserted into wo/men's track, which means i need to add/update them into normal track in spfdata
        if 17 <= ath_sport_local['sport_id'] <= 20:
            track_athsp_local = ath_sport_local.copy()
            track_athsp_local['sport_id'] = 21
            if (test_run == False and get_athlete_sport(conn, as_login, int(uid), 21) == None) or (test_run and not any((d for d in [item for sublist in athsp_db.values() for item in sublist] if (d.get('uid') == int(uid) and d.get('sport_id') == 21)))): 
                if not any(dictionary.get("uid") == int(uid) and dictionary.get("sport_id") == 21 for dictionary in ath_sport_inserts):
                    ath_sport_inserts.append(track_athsp_local)
                    print(f"db: Athsp insert will include {curr['Full Name']} ({uid}) on Track 21")
                    blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"db: Athsp insert will include {curr['Full Name']} ({uid}) on Track 21")
                curr_athsp_user = None
            else:
                if test_run:
                    curr_athsp_user = next((d for d in [item for sublist in athsp_db.values() for item in sublist] if d.get('uid') == int(uid) and d.get('sport_id') == 21), None)
                else: 
                    curr_athsp_user = get_athlete_sport(conn, as_login, int(uid), 21) 
                if track_athsp_local != curr_athsp_user and track_athsp_local not in ath_sport_updates: 
                    ath_sport_updates.append(track_athsp_local) 
                    print(f"db: Athsp update will include {curr['Full Name']} ({uid}) on Track 21")
                    blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"db: Athsp update will include {curr['Full Name']} ({uid}) on Track 21")
                elif track_athsp_local['status_id'] == 1 and any(dictionary.get("uid") == int(uid) and dictionary.get("sport_id") == 21 and dictionary.get("status_id") != 1 for dictionary in ath_sport_updates):
                    # ath_sport_updates.append(track_athsp_local) 
                    print(f"db: Remove prev athsp update for {curr['Full Name']} ({uid}) on Track 21")
                    blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"db: Remove prev athsp update for {curr['Full Name']} ({uid}) on Track 21")
                    del ath_sport_updates[ath_sport_updates.index(next((d for d in [item for item in ath_sport_updates] if d.get('uid') == int(uid) and d.get('sport_id') == 21 and d.get('status_id') != 1), None))]

    close_connection(conn)

def process_roster_ath(uid, ath_db, source_aths, curr_tw_ath, cat_aths, ath_inserts, ath_updates):
    source_ath = source_aths[next(iter(set(source_aths.keys())))]
    
    if curr_tw_ath and len(curr_tw_ath) > 0:
        tw_id = curr_tw_ath[next(iter(set(curr_tw_ath.keys())))]['id']
    else:
        tw_id = None

    cat_id = None
    for name in cat_aths.keys():
        full_name = name.split(" ")
        if nv.name_validator(source_ath['NAME_FIRST'], source_ath['NAME_LAST'], full_name[0], full_name[1]):
            cat_id = cat_aths[name][0]['id']    
            break

    if source_ath['dob'] == '':
        dob = None
    else:
        # dob = datetime.strptime(source_ath['dob'], "%Y-%m-%d").date()
        dob = source_ath['dob']

    max_sem = max([int(item['ATH_NUM_TERMS']) for item in source_aths.values() if 'ATH_NUM_TERMS' in item])
    
    athlete_local = {
                "uid": int(uid),
                "last_name": source_ath["NAME_LAST"].replace("'",""),
                "first_name": source_ath["NAME_FIRST"].replace("'",""),
                "dir_id": source_ath["DIR_ID"].lower(),
                "email_address": source_ath["DIR_ID"].lower() + "@terpmail.umd.edu",
                "phone_num": source_ath["Cell Phone"].replace("-","").replace("(","").replace(")","").replace("+","").replace(".","").replace(" ",""),
                "full_name": source_ath["Full Name"].replace("'",""),
                "teamworks_id": tw_id,
                "catapult_id": cat_id, 
                "gender": source_ath['gender'],
                "birth_date": dob,
                "semester": max_sem,
                "vald_id": None
    }

    if int(uid) not in ath_db.keys():
        print(f"db: Ath insert will include {source_ath['Full Name']} ({uid})")
        blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"db: Ath insert will include {source_ath['Full Name']} ({uid})")
        # They're not in the db, so insert them into the the athlete table
        ath_inserts.append(athlete_local)
    elif int(uid) in ath_db.keys():
        curr_ath_db = ath_db[int(uid)]
        if curr_ath_db[0]['birth_date']:
            curr_ath_db[0]['birth_date'] = curr_ath_db[0]['birth_date'].strftime('%Y-%m-%d')
        if curr_ath_db[0] != athlete_local:
            # If their current profile in the db doesnt match the one in the CSVs, update it
            ath_updates.append(athlete_local) 
            print("db: Athlete data in the spfdata database doesn't match what's in FR and SIS")
            blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", "db: Athlete data in the spfdata database doesn't match what's in FR and SIS")
            print(f"ICA Roster db:    {str(curr_ath_db[0])}")
            blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"ICA Roster db:    {str(curr_ath_db[0])}")
            print(f"FR & SIS sources: {str(athlete_local)}")
            blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"FR & SIS sources: {str(athlete_local)}")

def process_roster_athsp_sis(uid, athsp_db, source_aths, curr_tw_ath, ath_sport_inserts, ath_sport_updates, sis_team_dict, tw_team_dict, change, test_run):
    source_ath_teams = source_aths.keys()
    as_login = get_db("spfdata")
    conn = establish_connection(as_login)

    for teamname in source_ath_teams:
        curr = source_aths[teamname]
        if curr["ATH_SPORT_ACTIVE"]:
            reason = curr["ATH_SPORT_ACTIVE"].strip()
            if reason == "Active":
                status_id = 1
            else:
                status_id = 2
 
            if reason in change.keys():
                reason_id = change[reason]
            else:
                reason_id = 8
        else:
            reason = None
            reason_id = None

        sport_id = sis_team_dict[teamname]
        tw_team_id = tw_team_dict[teamname]
        if curr_tw_ath and tw_team_id in curr_tw_ath.keys() and 'athleteStatus' in curr_tw_ath[tw_team_id].keys():
            tw_status = curr_tw_ath[tw_team_id]['athleteStatus']
        else:
            tw_status = None

        fullname = curr['NAME_FIRST'] + " " + curr['NAME_LAST']
        
        ath_sport_local = {
                    "uid": int(uid),
                    "sport_id": sport_id,
                    "status_id": status_id,
                    "reason_id": reason_id,
                    "change_date": None,
                    "change_reason": reason,
                    "teamworks_status": tw_status
                }
        # if current athlete in this sport is not in the athsp table, add them 
        if (test_run == False and get_athlete_sport(conn, as_login, int(uid), ath_sport_local['sport_id']) == None) or (test_run and not any((d for d in [item for sublist in athsp_db.values() for item in sublist] if (d.get('uid') == int(uid) and d.get('sport_id') == ath_sport_local['sport_id'])))): 
            print(f"db: Athsp insert will include {fullname} ({uid}) on {list(sis_team_dict.keys())[list(sis_team_dict.values()).index(ath_sport_local['sport_id'])]} {ath_sport_local['sport_id']}")
            blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"db: Athsp insert will include {fullname} ({uid}) on {list(sis_team_dict.keys())[list(sis_team_dict.values()).index(ath_sport_local['sport_id'])]} {ath_sport_local['sport_id']}")
            ath_sport_inserts.append(ath_sport_local)
            curr_athsp_user = None
            
        # if curr doesn't match any of the current athsp data, update it
        else:
            
            # getting athsp user in db currently
            if test_run:
                curr_athsp_user = next((d for d in [item for sublist in athsp_db.values() for item in sublist] if d.get('uid') == int(uid) and d.get('sport_id') == ath_sport_local['sport_id']), None)
            else:
                curr_athsp_user = get_athlete_sport(conn, as_login, int(uid), ath_sport_local['sport_id']) 
            # if db athsp user and local athsp user dont match, update them
            if ath_sport_local != curr_athsp_user:
                print(f"db: Athsp update will include {fullname} ({uid}) on {list(sis_team_dict.keys())[list(sis_team_dict.values()).index(ath_sport_local['sport_id'])]} {ath_sport_local['sport_id']}")
                blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"db: Athsp update will include {fullname} ({uid}) on {list(sis_team_dict.keys())[list(sis_team_dict.values()).index(ath_sport_local['sport_id'])]} {ath_sport_local['sport_id']}")
                # update them in the athlete sport table 
                ath_sport_updates.append(ath_sport_local) 

        # checking if they got inserted into wo/men's track, which means i need to add/update them into normal track in spfdata
        if 17 <= ath_sport_local['sport_id'] <= 20:
            track_athsp_local = ath_sport_local.copy()
            track_athsp_local['sport_id'] = 21
            if (test_run == False and get_athlete_sport(conn, as_login, int(uid), 21) == None) or (test_run and not any((d for d in [item for sublist in athsp_db.values() for item in sublist] if (d.get('uid') == int(uid) and d.get('sport_id') == 21)))): 
                if not any(dictionary.get("uid") == int(uid) and dictionary.get("sport_id") == 21 for dictionary in ath_sport_inserts):
                    ath_sport_inserts.append(track_athsp_local)
                    print(f"db: Athsp insert will include {fullname} ({uid}) on Track 21")
                    blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"db: Athsp insert will include {fullname} ({uid}) on Track 21")
                curr_athsp_user = None
            else:
                if test_run:
                    curr_athsp_user = next((d for d in [item for sublist in athsp_db.values() for item in sublist] if d.get('uid') == int(uid) and d.get('sport_id') == 21), None)
                else: 
                    curr_athsp_user = get_athlete_sport(conn, as_login, int(uid), 21) 
                if track_athsp_local != curr_athsp_user and track_athsp_local not in ath_sport_updates: 
                    ath_sport_updates.append(track_athsp_local) 
                    print(f"db: Athsp update will include {fullname} ({uid}) on Track 21")
                    blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"db: Athsp update will include {fullname} ({uid}) on Track 21")
                elif track_athsp_local['status_id'] == 1 and any(dictionary.get("uid") == int(uid) and dictionary.get("sport_id") == 21 and dictionary.get("status_id") != 1 for dictionary in ath_sport_updates):
                    # ath_sport_updates.append(track_athsp_local) 
                    print(f"db: Remove prev athsp update for {fullname} ({uid}) on Track 21")
                    blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"db: Remove prev athsp update for {fullname} ({uid}) on Track 21")
                    del ath_sport_updates[ath_sport_updates.index(next((d for d in [item for item in ath_sport_updates] if d.get('uid') == int(uid) and d.get('sport_id') == 21 and d.get('status_id') != 1), None))]

    close_connection(conn)

def process_roster_ath_sis(uid, ath_db, sis_aths, curr_tw_ath, cat_aths, ath_inserts, ath_updates):
    sis_ath = sis_aths[next(iter(set(sis_aths.keys())))]
    
    if curr_tw_ath and len(curr_tw_ath) > 0:
        tw_id = curr_tw_ath[next(iter(set(curr_tw_ath.keys())))]['id']
    else:
        tw_id = None

    cat_id = None
    for name in cat_aths.keys():
        full_name = name.split(" ")
        if nv.name_validator(sis_ath['NAME_FIRST'], sis_ath['NAME_LAST'], full_name[0], full_name[1]):
            cat_id = cat_aths[name][0]['id']    
            break

    if sis_ath['ATH_SPORT'][0] == 'M':
        gender = 'M'
    elif sis_ath['ATH_SPORT'][0] == 'W':
        gender = 'F'
    else:
        gender = None

    fullname = sis_ath["NAME_FIRST"].replace("'","") + " " + sis_ath["NAME_LAST"].replace("'","")

    max_sem = max([int(item['ATH_NUM_TERMS']) for item in sis_aths.values() if 'ATH_NUM_TERMS' in item])

    athlete_local = {
                "uid": int(uid),
                "last_name": sis_ath["NAME_LAST"].replace("'",""),
                "first_name": sis_ath["NAME_FIRST"].replace("'",""),
                "dir_id": sis_ath["DIR_ID"].lower(),
                "email_address": sis_ath["DIR_ID"].lower() + "@terpmail.umd.edu",
                "phone_num": None,
                "full_name": fullname,
                "teamworks_id": tw_id,
                "catapult_id": cat_id, 
                "gender": gender,
                "birth_date": None,
                "semester": max_sem,
                "vald_id": None
    }

    if int(uid) not in ath_db.keys():
        print(f"db: Ath insert will include {fullname} ({uid})")
        blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"db: Ath insert will include {fullname} ({uid})")
        # They're not in the db, so insert them into the the athlete table
        ath_inserts.append(athlete_local)
    elif int(uid) in ath_db.keys():
        curr_ath_db = ath_db[int(uid)]
        if curr_ath_db[0]['birth_date']:
            curr_ath_db[0]['birth_date'] = curr_ath_db[0]['birth_date'].strftime('%Y-%m-%d')
        if curr_ath_db[0] != athlete_local:
            # If their current profile in the db doesnt match the one in the CSVs, update it
            ath_updates.append(athlete_local) 
            print("db: Athlete data in the spfdata database doesn't match what's in FR and SIS")
            blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", "db: Athlete data in the spfdata database doesn't match what's in FR and SIS")
            print(f"ICA Roster db:    {str(curr_ath_db[0])}")
            blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"ICA Roster db:    {str(curr_ath_db[0])}")
            print(f"FR & SIS sources: {str(athlete_local)}")
            blob_output(f"db_comp_output/{curr_date}_db_comp_output.log", "logs", f"FR & SIS sources: {str(athlete_local)}")


def db_comp_athsp_insert(ath_sport_inserts):
    ath_sport_final_inserts = {}
    # Loop for doing inserts on ath sp db
    for index in range(len(ath_sport_inserts)):
        # Removing all the keys with empty values so we don't cause any errors
        # key_str will be used to sort the dictionaries so we can run one insert statement for all records with the same keys
        delete = []
        data = ath_sport_inserts[index]
        key_str = ""
        for key in data.keys():
            #If no data in the key,value pair then drop it from the dict
            #elif the key is change_date then we need to convert the datetime object into a string 
            if data[key] == None:
                delete.append(key)
            elif key == "change_date":
                data[key] = data[key].strftime('%m/%d/%Y')
                key_str += key
            else:
                key_str += key
        for key in delete:
            data.pop(key)

        if key_str not in ath_sport_final_inserts.keys():
            ath_sport_final_inserts[key_str] = [data]
        else:
            ath_sport_final_inserts[key_str].append(data)

    #Call the SQL statement
    # print("ATH SP INSERT")
    database = get_db("spfdata")
    connection = establish_connection(database)
    for key in ath_sport_final_inserts:
        as_insert_list = ath_sport_final_inserts[key]
        insert_athlete_sport(connection, database,as_insert_list)
        # print(as_insert_list)
    close_connection(connection)

def db_comp_athsp_updates(ath_sport_updates):
    ath_sport_final_updates = {}
    # Loop for doing updates in ath sp db
    for index in range(len(ath_sport_updates)):
        # Removing all the keys with empty values so we don't cause any errors
        #key_str will be used to sort the dictionaries so we can run one insert statement for all records with the same keys 
        delete = []
        data = ath_sport_updates[index]
        key_str = ""
        for key in data.keys():
            #If no data in the key,value pair then drop it from the dict
            #elif the key is change_date then we need to convert the datetime object into a string 
            if data[key] == None:
                delete.append(key)
            elif key == "change_date":
                data[key] = data[key].strftime('%m/%d/%Y')
                key_str += key
            else:
                key_str += key
        for key in delete:
            data.pop(key)

        if key_str not in ath_sport_final_updates.keys():
            ath_sport_final_updates[key_str] = [data]
        else:
            ath_sport_final_updates[key_str].append(data)

    #Call the SQL statement
    # print("ATH SP UPDATE")
    database = get_db("spfdata")
    conn = establish_connection(database)
    for key in ath_sport_final_updates:
        as_update_list = ath_sport_final_updates[key]
        for ath_sp in as_update_list:
            update_athlete_sport(conn,database,ath_sp["uid"],ath_sp)
            # print(ath_sp)
            # continue
    close_connection(conn)

def db_comp_ath_inserts(ath_inserts):
    ath_final_inserts = {}
    for index in range(len(ath_inserts)):
        # Removing all the keys with empty values
        delete = []
        data = ath_inserts[index]
        key_str = ""
        for key in data.keys():
            if data[key] == None:
                delete.append(key)
            else:
                key_str += key
        for key in delete:
            data.pop(key)

        if key_str not in ath_final_inserts.keys():
            ath_final_inserts[key_str] = [data]
        else:
            ath_final_inserts[key_str].append(data)
        #print(data)
        #Call the SQL Statement
    # print("ATH INSERT")
    database = get_db("spfdata")
    conn = establish_connection(database)
    for key in ath_final_inserts:
        a_insert_list = ath_final_inserts[key]
        insert_athlete(conn, database ,a_insert_list)
        # print(a_insert_list)
    close_connection(conn)

def db_comp_ath_updates(ath_updates):
    ath_final_updates = {}
    for index in range(len(ath_updates)):
        # Removing all the keys with empty values
        delete = []
        data = ath_updates[index]
        key_str = ""
        for key in data.keys():
            if data[key] == None:
                delete.append(key)
            else:
                key_str += key
        for key in delete:
            data.pop(key)

        if key_str not in ath_final_updates.keys():
            ath_final_updates[key_str] = [data]
        else:
            ath_final_updates[key_str].append(data)
        #print(data)
        #Call the SQL Statement
    # print("ATH UPDATES")
    database = get_db("spfdata")
    conn = establish_connection(database)
    for key in ath_final_updates:
        a_update_list = ath_final_updates[key]
        for ath in a_update_list:
            # print(ath)
            update_athlete(conn, database ,ath["uid"],ath)
            # continue
    close_connection(conn)

# # Specifically for the spfdata db to combine both Athlete and AthleteSports into a dict mapped as {UID: {combined athlete and athletesports dict fields}, UID: {...}, ...}
# # NOTE : Takes in the spf-athletes login db
# def get_comb_aths(login):
#     all_athletes = get_all_athletes(db_list["spfdata-athletes"],"UID")

#     with login['conn'] as conn:
#         with conn.cursor() as cursor:

#             roster_data = {}
#             # cursor.execute(f"SELECT * FROM {login['table']}")
#             # finalize below later
#             cursor.execute(f"SELECT * FROM [dbo].[AthleteSports]")

#             iterator = cursor.fetchone()
#             while iterator:
#                 columns = [column[0] for column in cursor.description]
#                 curr_athlete = dict(zip(columns, iterator))
#                 #{
#                 #    "UID": 123456
#                 #}
#                 uid = curr_athlete["UID"]
#                 #Get UID from curr_athlete

#                 #Get value using curr_athlete uid as the key
                
#                 curr_combine = all_athletes[uid]
#                 curr_athlete.update(curr_combine)

#                 if curr_athlete['UID'] in roster_data.keys():
#                     roster_data.update({curr_athlete['UID']: [curr_athlete]})
#                 else:
#                     roster_data[curr_athlete['UID']].append(curr_athlete)
#                 iterator = cursor.fetchone()
                
#             return roster_data

# 17 for server computer, 18 for local
# NOTE: ALL USERS AND PASSWORDS HAVE BEEN CHANGED TO PROTECT CONFIDENTIAL CREDENTIALS 
# IMPORTANT: MUST CHANGE SERVER & DATABASE TO YOUR OWN ENVIORMENT!

db_list = {
    "spfdata":{
        "server": 'icaumd.database.windows.net',
        "database": 'spfdata',
        "username": 'EXAMPLEUSER', 
        "password": 'EXAMPLEPASSWORD',
        "driver": '{ODBC Driver 18 for SQL Server}',
        "tables": {
            "sports":'[dbo].[Sports]',
            "status":'[dbo].[Status]',
            "inactive_reasons": '[dbo].[InactiveReasons]',
            "athletes": '[dbo].[Athletes]',
            "athlete_sports":'[dbo].[AthleteSports]',
            "logging": '[dbo].[Logging]',
            "external_calls": '[dbo].[ExternalCalls]'
        }
    },
    "catapult_mlx":{
        "server": 'icaumd.database.windows.net',
        "database": 'catapult_db_mlax',
        "username": 'EXAMPLEUSER',
        "password": 'EXAMPLEPASSWORD',
        "driver": '{ODBC Driver 18 for SQL Server}',
        "tables": {
            "activities": '[dbo].[Activities]',
            "athlete_activities": '[dbo].[AthleteActivities]',
            "period_data": '[dbo].[PeriodData]',
            "periods": '[dbo].[Periods]',
            "athletes": '[dbo].[Athletes]'
        }
    },
    "catapult_mfb":{
        "server": 'icaumd.database.windows.net',
        "database": 'catapult_db_football',
        "username": 'EXAMPLEUSER',
        "password": 'EXAMPLEPASSWORD',
        "driver": '{ODBC Driver 18 for SQL Server}',
        "tables": {
            "activities": '[dbo].[Activities]',
            "athlete_activities": '[dbo].[AthleteActivities]',
            "period_data": '[dbo].[PeriodData]',
            "periods": '[dbo].[Periods]',
            "athletes": '[dbo].[Athletes]',
            "empty_activities": '[dbo].[EmptyActivities]'
        }
    },
    "catapult_wfh":{
        "server": 'icaumd.database.windows.net',
        "database": 'catapult_db_wfh',
        "username": 'EXAMPLEUSER',
        "password": 'EXAMPLEPASSWORD',
        "driver": '{ODBC Driver 18 for SQL Server}',
        "tables": {
            "activities": '[dbo].[Activities]',
            "athlete_activities": '[dbo].[AthleteActivities]',
            "period_data": '[dbo].[PeriodData]',
            "periods": '[dbo].[Periods]',
            "athletes": '[dbo].[Athletes]',
            "empty_activities": '[dbo].[EmptyActivities]'
        }
    },
    "dexa":{
        "server": 'icaumd.database.windows.net',
        "database": 'DEXA_db',
        "username": 'EXAMPLEUSER',
        "password": 'EXAMPLEPASSWORD',
        "driver": '{ODBC Driver 18 for SQL Server}',
        "table": {
            "athletes":'[dbo].[Athletes]',
            "measures": '[dbo].[Measures]'
        }
    }
    # add more here
}
