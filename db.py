import pyodbc

def get_connection():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=sqlmisis-test.public.ca87cd4bc197.database.windows.net,3342;'
        'DATABASE=BELAJAR_SYNAPSE;'
        'UID=belajar_synapse_user;'
        'PWD=belajarsynapse123#'
    )
