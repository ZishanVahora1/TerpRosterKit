import csv

__author__ = "Josh Lobo"
__credits__ = ["Josh Lobo", "Timothy Santosa"]
__maintainer__ = "Josh Lobo"
__email__ = "jlobo11@umd.edu"
__status__ = "Testing"

def activeDict(fileLocation=r'C:\Users\Administrator\Documents\GitHub\Integrations\DataSources\CleaningScripts\Student_Athlete_Active_Roster.csv'):
    sis_data_file = csv.DictReader(open(fileLocation))
    returnDict = {}
    for row in sis_data_file:
        returnDict[row["U_ID"]] = row
    return returnDict
#Checks if there is an active roster file
#If this does not exist, then you create one
# if not os.path.isfile(r'C:\Users\Administrator\Documents\GitHub\Integrations\DataSources\CleaningScripts\Student_Athlete_Active_Roster.csv'):
#     fields = list(sis_data_list[0].keys())
#     with open((r'C:\Users\Administrator\Documents\GitHub\Integrations\DataSources\CleaningScripts\Student_Athlete_Active_Roster.csv'), 'w') as csvfile:
#         active_academic_profiles_file = csv.DictWriter(csvfile, fieldnames=fields)
#         active_academic_profiles_file.writeheader()
