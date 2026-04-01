"""
Alpha Edge — Cron Job Setup Script
Sets up a daily cron job (Linux/Mac) or Task Scheduler hint (Windows).

Usage:
    python scripts/setup_cron.py
"""

import os
import sys
import platform

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_PATH = sys.executable
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, "main.py")
LOG_FILE = os.path.join(PROJECT_ROOT, "output", "cron.log")


def setup():
    system = platform.system()

    if system in ("Linux", "Darwin"):
        cron_line = f'0 7 * * 1-5 cd {PROJECT_ROOT} && {PYTHON_PATH} {MAIN_SCRIPT} >> {LOG_FILE} 2>&1'
        print("Add this line to your crontab (crontab -e):\n")
        print(f"  {cron_line}\n")
        print("This runs at 07:00 IST every weekday (Mon-Fri).")

    elif system == "Windows":
        print("Windows Task Scheduler setup:\n")
        print(f"  Program: {PYTHON_PATH}")
        print(f"  Arguments: {MAIN_SCRIPT}")
        print(f"  Start in: {PROJECT_ROOT}")
        print(f"  Trigger: Daily at 07:00 AM, weekdays only\n")
        print("Create via: Task Scheduler > Create Basic Task > Daily > 07:00")

    else:
        print(f"Unknown OS: {system}. Set up a daily job manually to run:")
        print(f"  cd {PROJECT_ROOT} && {PYTHON_PATH} {MAIN_SCRIPT}")


if __name__ == "__main__":
    setup()
