"""
Module that logs all trades including PNL in a text file.
"""

from datetime import datetime

from .config import LOG_FILE


def write_log(logline):
    timestamp = datetime.now().strftime("%d/%m %H:%M:%S")
    with open(LOG_FILE, 'a+') as f:
        print(timestamp, logline, file=f)
