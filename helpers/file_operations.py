# dont want name to be logging. 
from datetime import datetime
from json import dump, dumps, load



def write_log(logline, LOG_FILE):
    timestamp = datetime.now().strftime("%d/%m %H:%M:%S")
    with open(LOG_FILE,'a+') as f:
        f.write(timestamp + ' ' + logline + '\n')


#! TODO: Define a better way to update coins_bought.json
def update_coins_json(file_path, items, op):
    """Updates coins json depending on items and op

    Args:
        file_path (str): path to file
        items (str): data
        op (str): python open operation
    """
    with open(file_path, op) as file:
        dump(items, file, indent=4)

def load_json_file(file_path):
    """returns loaded json file"""

    # FileNotFound Error returned if cant open
    with open(file_path) as f:
        file_content = load(f)
    
    return file_content



    

