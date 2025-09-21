import requests
import json
import sys
import os
sys.path.insert(1, f"{os.path.expanduser('~')}/Users/hd/Documents/GitHub/Integrations/Helpers")

from catapult_mlax_helper import *
from catapult_user_helper import *
'''
test = get_all_users()

for i in test:
    print(i.text)


athleteinfo = {
  "first_name": "Test",
  "last_name": "Test",
  "gender": "Male",
  "jersey": "T00",
  "date_of_birth": 180000,
  "date_of_birth_date": "2000-1-1",
  "team_id": "75054b55-9900-11e3-b9b6-22000af8166b",
  "position_id": "bb38b276-d2b1-11e4-b293-22000afc007c",
  
}

ath = {
    "team_id": "75054b55-9900-11e3-b9b6-22000af8166b",
    "position_id": "bb50873a-d2b1-11e4-b293-22000afc007c",
    "jersey": "123",
    "gender": "Female",
    "first_name": "Leah",
    "last_name": "Orozco",
    "date_of_birth_date": "2022-10-17"
}
'''
#test =get_userId("116230728",  "football")
#test = getTeamRoster("mlax").text

#test = createAthlete(ath, "mlax").text

test = get_position_id("football").text
print(test)