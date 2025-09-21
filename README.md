# TerpRosterKit

Helpers for UMD Athletics to load rosters from CSV, compare and sync athlete data, and interact with Azure SQL tables (Athletes, AthleteSports, Activities, etc.). Includes name comparison utilities and example scripts that integrate with external Catapult/Teamworks helpers.

> **Security note:** All database usernames and passwords in the sample config are intentionally set to `EXAMPLEUSER` and `EXAMPLEPASSWORD` to preserve confidential credentials that belong to the University of Maryland Athletics IT Department. Replace them locally via environment variables or your own secure mechanism before use.

---

## 📦 What’s inside

- **`azure_helper.py`** – Azure SQL connection + CRUD utilities, plus higher-level roster sync helpers (insert/update athletes, athlete-sport records, logging, etc.).
- **`name_validator.py`** – Minimal helper to check if two `(first, last)` names match after normalization (case, spaces, apostrophes, simple suffixes).
- **`roster_helper.py`** – Loads a Student Athlete Active Roster CSV into a Python dict keyed by `U_ID`.
- **`test.py`** – Example scratch file showing how local Catapult helpers (not included) can be imported and used.

---

## ✅ Requirements

- Python 3.9+
- Install packages:
  ```bash
  pip install pyodbc python-dateutil requests
ODBC Driver for SQL Server (e.g., ODBC Driver 18 for SQL Server)
Network access to your Azure SQL server(s)
(Optional) Local Catapult/Teamworks helper modules if you run test.py

## ⚙️ Configuration

azure_helper.py contains a db_list mapping with connection profiles like:
 ```bash
 db_list = {
  "spfdata": {
    "server": "icaumd.database.windows.net",
    "database": "spfdata",
    "username": "EXAMPLEUSER",
    "password": "EXAMPLEPASSWORD",
    "driver": "{ODBC Driver 18 for SQL Server}",
    "tables": {
      "sports": "[dbo].[Sports]",
      "status": "[dbo].[Status]",
      "inactive_reasons": "[dbo].[InactiveReasons]",
      "athletes": "[dbo].[Athletes]",
      "athlete_sports": "[dbo].[AthleteSports]",
      "logging": "[dbo].[Logging]",
      "external_calls": "[dbo].[ExternalCalls]"
    }
  } 
```
Replace EXAMPLEUSER / EXAMPLEPASSWORD with real credentials outside of source control (e.g., environment variables).
  
Hostnames like icaumd.database.windows.net are safe to publish; credentials are not.

## 🚀 Quick Start
# 1) Connect to a database
from azure_helper import get_db, establish_connection, close_connection

login = get_db("spfdata")        # or "catapult_mlx", "catapult_mfb", "catapult_wfh", "dexa"
conn = establish_connection(login)
try:
    # Do work with `conn`
    pass
finally:
    close_connection(conn)

# 2) Insert multiple rows into a table

```from azure_helper import insert_table_batch, get_db, establish_connection, close_connection

login = get_db("catapult_wfh")
conn = establish_connection(login)
try:
    rows = [
        {"ActivityID": 1, "AthleteID": 101, "StartTime": "2025-08-20T12:00:00"},
        {"ActivityID": 2, "AthleteID": 102, "StartTime": "2025-08-21T14:30:00"},
    ]
    insert_table_batch(conn, login["tables"]["activities"], rows)
finally:
    close_connection(conn)
```

# 3) Load the active roster CSV
```from roster_helper import activeDict

roster = activeDict("path/to/Student_Athlete_Active_Roster.csv")
print("Loaded", len(roster), "rows")
print(roster.get("116230728"))
```
# 4) Compare names (normalized)
```
from name_validator import name_validator
print(name_validator("Robert", "Smith Jr.", "robert", "smith"))  # True

```

