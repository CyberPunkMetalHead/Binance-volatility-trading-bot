# Module that logs all trades including PNL in a text file

from datetime import  datetime

# We need the LOG_FILE for this
from config import LOG_FILE


def write_log(logline):
    timestamp = datetime.now().strftime("%d/%m %H:%M:%S")
    with open(LOG_FILE,'a+') as f:
        f.write(timestamp + ' ' + logline + '\n')
