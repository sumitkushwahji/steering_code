import asyncio
import threading
import os
from datetime import datetime, timedelta
import pandas as pd
from serial_communication import SerialCommunication
from rb_device import RbDevice
from receiver import Receiver
from utils import mjd_to_utc, is_it_today, extract_time_from_filename, mjd_today
from file_operations import latest_file_in_directory, read_file_data
from cv_processing import process_CV, apply_CV_corrections

# from initialization import initialize_csv_files, initialize_globals
import initialization

from timing_mode import timing_mode_impliment
from cv_mode import cv_mode_implement

# Initialize global variables and CSV files
initialization.initialize_globals()
initialization.initialize_csv_files()

# Global signal for threading
signal = threading.Event()


def main():

    # Serial Communication and Rb Device Configuration
    serial_comm = SerialCommunication(port="COM10", baudrate=9600)
    serial_comm.open()

    while True:
        # When the receiver is in Timing Mode
        if initialization.Timing_mode and not initialization.CV_mode:
            timing_mode_impliment()

        # When the receiver is in Time transfer Mode
        elif initialization.CV_mode and not initialization.Timing_mode:
            cv_mode_implement()


if __name__ == "__main__":
    main()
