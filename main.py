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
from initialization import initialize_csv_files, initialize_globals

from timing_mode import timing_mode_impliment
from cv_mode import cv_mode_implement

# Initialize global variables and CSV files
initialize_globals()
initialize_csv_files()

# Global signal for threading
signal = threading.Event()


def main():

    while True:
        # When the receiver is in Timing Mode
        if Timing_mode and not CV_mode:
            timing_mode_impliment()

        # When the receiver is in Time transfer Mode
        elif CV_mode and not Timing_mode:
            cv_mode_implement()

    # Serial Communication and Rb Device Configuration
    serial_comm = SerialCommunication(port="COM10", baudrate=9600)
    serial_comm.open()

    rb_device = RbDevice(serial_comm)

    # Example usage of Rb Device
    curr_in_hz, current_value, current_value_bytes, check_sum_match = (
        rb_device.read_current()
    )
    if curr_in_hz is not None:
        print(f"Current frequency shift in Hz: {curr_in_hz}")

    # Example of sending command to Rb Device
    rb_device.send_command(apply_corr=0.5, lock_flag=0)

    # File Operations
    directory = "/path/to/directory"
    file_prefix = "IRNPLI60299"

    latest_file, mod_time, readable_time = latest_file_in_directory(
        directory, file_prefix
    )
    if latest_file:
        print(f"Latest file: {latest_file}")
        print(f"Modification time: {mod_time} (readable: {readable_time})")

        combined_data, unique_mjd, unique_sv, unique_frc = read_file_data(
            os.path.join(directory, latest_file)
        )
        print("Combined Data:")
        print(combined_data.head())
        print(f"Unique MJD values: {unique_mjd}")
        print(f"Unique SV IDs: {unique_sv}")
        print(f"Unique FRCs: {unique_frc}")

        # Assuming df1 and df2 are DataFrames you have
        df1 = combined_data  # Placeholder for actual DataFrame
        df2 = combined_data  # Placeholder for actual DataFrame
        unique_MJD_times = unique_mjd
        unique_SATs = unique_sv
        Freq_used = unique_frc

        # Process CV Data
        result, unique_mjd = process_CV(
            df1, df2, unique_MJD_times, unique_SATs, Freq_used
        )
        print("Processed CV Data:")
        print(result.head())

        # Apply CV Corrections
        CV_session = 1  # Example session
        Present_error = result["CV_avg_diff"].iloc[-1]
        Prev_error = result["CV_avg_diff"].iloc[-2] if len(result) > 1 else 0
        time_bw_errors = 60  # Example time between errors in seconds
        correction_delay = 60  # Example correction delay in seconds
        apply_CV_corrections(
            CV_session,
            Present_error,
            Prev_error,
            time_bw_errors,
            correction_delay,
            rb_device.send_command,
        )


if __name__ == "__main__":
    main()
