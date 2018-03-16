import time
import inspect

# CONSTANTS
# ===================================================
LOG_FILE = 'log.txt'


# FUNCTIONS
# ===================================================

# String -> Write to file, Int
# takes a string and writes it to a predefined file and returns 1 if succesful
def log(message):
    # create file if it doesn't already exist
    try:
        f = open(LOG_FILE, 'a') #opens file with append mode
        current_time = time.ctime()
        function_caller = inspect.stack()[1][3]
        f.write(current_time + ' ' + function_caller + '() ' + message + "\n")  # add details to log file imestamped with file name
        return 1
    except:
        return 0
