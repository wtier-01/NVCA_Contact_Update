# logger.py

import csv
import os

LOG_FILE = os.path.join("logs", "master_summary.csv")

def init_logger():
    """Creates the logs directory and initializes the summary log."""
    os.makedirs("logs", exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Firm Name", "Status", "Notes"])

def log_result(firm_name, status, note=""):
    """Logs the result of processing a firm."""
    with open(LOG_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([firm_name, status, note])
