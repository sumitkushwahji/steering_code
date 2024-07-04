# import asyncio
# import threading
# import os
# from datetime import datetime, timedelta
# import pandas as pd
# from serial_communication import SerialCommunication
# from rb_device import RbDevice
# from receiver import Receiver
# from utils import mjd_to_utc, is_it_today, extract_time_from_filename, mjd_today
# from file_operations import latest_file_in_directory, read_file_data
# from cv_processing import process_CV, apply_CV_corrections

# # from initialization import initialize_csv_files, initialize_globals
# import initialization

# from timing_mode import timing_mode_impliment
# from cv_mode import cv_mode_implement

# # Initialize global variables and CSV files
# initialization.initialize_globals()
# initialization.initialize_csv_files()

# # Global signal for threading
# signal = threading.Event()


# def main():

#     # Serial Communication and Rb Device Configuration
#     serial_comm = SerialCommunication(port="COM10", baudrate=9600)
#     serial_comm.open()

#     while True:
#         # When the receiver is in Timing Mode
#         if initialization.Timing_mode and not initialization.CV_mode:
#             timing_mode_impliment()

#         # When the receiver is in Time transfer Mode
#         elif initialization.CV_mode and not initialization.Timing_mode:
#             cv_mode_implement()


# if __name__ == "__main__":
#     main()




import os
import threading
from data_transfer_manager import DataTransferManager
from cv_processing import process_CV, apply_CV_corrections
import initialization
from timing_mode import timing_mode_impliment
from cv_mode import cv_mode_implement
from serial_communication import SerialCommunication  # Assuming you have this module

# Initialize global variables and CSV files
initialization.initialize_globals()
initialization.initialize_csv_files()

# Global signal for threading
signal = threading.Event()

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to CggttsFtpClient.exe
exe_path = os.path.join(current_dir, 'CggttsFtpClient.exe')

# Paths for the first DataTransferManager
parent_directory_do = os.path.join(current_dir, 'Data_Log_DO')
file_history_do = "sent_files_do.txt"
ip_address_do = '172.16.26.42'
source_do = "RRSL-FARIDABAD-NAVIC-DO-01"

# Paths for the second DataTransferManager
parent_directory_ref = os.path.join(current_dir, 'Data_Log_REF')
file_history_ref = "sent_files_ref.txt"
ip_address_ref = '172.16.26.41'
source_ref = "npli"

# Initialize both DataTransferManager instances
data_transfer_manager_do = DataTransferManager(exe_path, ip_address_do, parent_directory_do, file_history_do, source_do)
data_transfer_manager_ref = DataTransferManager(exe_path, ip_address_ref, parent_directory_ref, file_history_ref, source_ref)

# Function to handle data transfer
def run_data_transfer():
    data_transfer_manager_thread_do = threading.Thread(target=data_transfer_manager_do.run_data_transfer)
    data_transfer_manager_thread_ref = threading.Thread(target=data_transfer_manager_ref.run_data_transfer)

    data_transfer_manager_thread_do.start()
    data_transfer_manager_thread_ref.start()

    # Optionally, join threads if you want to wait for their completion
    # data_transfer_manager_thread_do.join()
    # data_transfer_manager_thread_ref.join()


# Function to handle timing and CV modes
def handle_modes():
    serial_comm = SerialCommunication(port="COM10", baudrate=9600)
    serial_comm.open()

    while True:
        if initialization.Timing_mode and not initialization.CV_mode:
            timing_mode_impliment()

        elif initialization.CV_mode and not initialization.Timing_mode:
            cv_mode_implement()

# Create and start threads for data transfer, additional logic, and mode handling
data_transfer_thread = threading.Thread(target=run_data_transfer)

mode_handling_thread = threading.Thread(target=handle_modes)

data_transfer_thread.start()

mode_handling_thread.start()

# Optionally, join threads if you want to wait for their completion
# data_transfer_thread.join()
# additional_logic_thread.join()
# mode_handling_thread.join()

