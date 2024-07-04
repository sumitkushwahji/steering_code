
import serial
from datetime import datetime, timedelta
import time
import csv
import os
import struct
import threading
import serial.tools.list_ports
import numpy as np
from serial import serialutil
import telnetlib3
import pandas as pd
import asyncio
import math

Rb_ser = None

Fst =0


try:
    if(Rb_ser is None):
        Rb_ser = serial.Serial(port ='COM10',baudrate= 9600,bytesize = serial.EIGHTBITS, stopbits= serial.STOPBITS_ONE,timeout=1)
    print("Rb port is open now: ", Rb_ser.isOpen())
except serial.serialutil.SerialException as w:
    print(f"Could not open the port Restart the program : {w}")

# Open the TIC serial port 
# TIC_ser = serial.Serial(port = 'COM12',baudrate = 115200 )


# Funtion defined to send command to Rb serial port 

def compute_checksum(PID_out_hex_CS):
    byte_arr = bytes.fromhex(PID_out_hex_CS)
    checksum =0
    for byte in byte_arr:
        checksum^= byte
    checksum = '{:#04x}'.format(checksum & 0xFF)
    return checksum
    #checksum &= 0xFF
    #return '{:02X}'.format(checksum ^ 0xFF ^ 0xFF ^ 0xFF)
    #checksum = .format(checksum & 0xFF)


def read_current_Rb():   
    Read_RAM = "2D 04 00 29"
    print("Reading the current shift from Rb")

    try:
        Rb_ser.write(bytes.fromhex(Read_RAM))
    except serial.serialutil.PortNotOpenError as e:
        print(f"Port not open error: {e}")
        try:
            Rb_ser.open()
            Rb_ser.write(bytes.fromhex(Read_RAM))
        except serial.serialutil.SerialException as n:
            print(f"Port could not open error: {n}")
            return (None, None, None, None)
    
    except serial.serialutil.SerialException as e:
        print(f"Serial error: {e}")
        return (None, None, None, None)  # Additional catch for general serial errors

            # Rb_ser.close()
            # Rb_ser.open()
            # Rb_ser.write(bytes.fromhex(Read_RAM))
    time.sleep(0.1)  # Wait for the device to process the write command

    # data_read = Rb_ser.readline()
    data_read = Rb_ser.read(9)
    # print(f"Data Read : {data_read}")
     # Check if the received data is of the expected length
    if len(data_read) != 9:
        print(f"Warning: Received {len(data_read)} bytes, expected 9.")
        return (None, None, None, None)
    
    # Extract the data bytes (4-7) and convert directly to a signed integer
    current_value_bytes = data_read[4:8]
    current_value = int.from_bytes(current_value_bytes, byteorder='big', signed=True)
    
    
    # Convert the current value to Hz using the given formula
    curr_in_Hz = current_value * 3.725 * 1E-9
    # print("Current shift in Hz:", curr_in_Hz)
    check_sum_match = 1
    # Checksum validation (optional, but recommended)
    received_checksum = data_read[8]
    calculated_checksum = compute_checksum(data_read[4:8].hex())
       # Convert the calculated_checksum from hexadecimal string to integer
    calculated_checksum_int = int(calculated_checksum, 16)

    if received_checksum != calculated_checksum_int:
        print(f"Checksum mismatch: received {received_checksum}, calculated {calculated_checksum_int}")
        check_sum_match = 0
        return None  # or some error handling
    
    # print(f"Curr_in_Hz: {curr_in_Hz}")
    # print(f"current_value: {current_value}")
    # print(f"current_value_bytes: {current_value_bytes.hex()}")
    # print(f"check_sum_match: {check_sum_match}")
    
    # Flush any stale data from the serial buffer
    Rb_ser.flushInput()
    
    return curr_in_Hz, current_value, current_value_bytes.hex(), check_sum_match

# Method to send the command to the Rb device
def send_cmd_Rb(apply_corr, lock_flag):
    signal.wait()
    
    if lock_flag == 0: # PID is not in lock mode
        New_shift = apply_corr
    else:
        curr_value, hex_before, bytes_before, matching_check_sum = read_current_Rb() # Get the current frequency offset value from the Rb
        New_shift = apply_corr + curr_value

    # Convert the shift to the unit expected by the device and round it
    # Check if New_shift is NaN
    if math.isnan(New_shift):
        print("Error: New_shift is NaN. Cannot proceed with the operation.")
        signal.clear()
        return  # Exit the function early or handle accordingly

    # If New_shift is not NaN, proceed with the calculation
    try:
        shift_in_device_units = round(New_shift / 3.725 * 1e9)
        # Continue with the rest of the function to send the command...
    except ValueError as e:
        print(f"ValueError occurred: {e}")
    finally:
        signal.clear()

    # Clamp shift_in_device_units to the 32-bit signed integer range
    shift_in_device_units_clamped = max(min(shift_in_device_units, max_int32), min_int32)

    # Convert to bytes as signed 32-bit integer (two's complement for negative numbers)
    shift_bytes = shift_in_device_units.to_bytes(4, byteorder='big', signed=True)
    bytes_applied = shift_bytes
    # Convert bytes to hexadecimal string
    shift_hex = shift_bytes.hex()
    hex_applied = " ".join(shift_hex[i:i+2] for i in range(0, len(shift_hex), 2)) 
    # Prepare command string
    cmnd = "2e 09 00 27 " + " ".join(shift_hex[i:i+2] for i in range(0, len(shift_hex), 2)) + compute_checksum(shift_hex).replace("0x", "")
    
    try:
        Rb_ser.write(bytes.fromhex(cmnd))
        print("Command Sent")
    except serial.serialutil.SerialException as e:
        print(f"An error occurred: {e}")
        Rb_ser.close()
        try:
            Rb_ser.open()
            Rb_ser.write(bytes.fromhex(cmnd))
        except serial.serialutil.SerialException as e:
            print(f"Failed to reopen the port and send the command: {e}")
    
    # save the observations to the file 
    if lock_flag == 1:
        curr_new_value, hex_after, bytes_after, matching_check_sum = read_current_Rb() # Get the current frequency offset value from the Rb
        Correction_info = {'Time stamp': datetime.now(),'Before_correction': curr_value,'After_correction': curr_new_value, 'Hex_before': hex_before, 'Bytes_before':bytes_before, 'Bytes_applied': bytes_applied, 'Hex_applied': hex_applied, 'Hex_after': hex_after, 'Bytes_after': bytes_after, 'Check_sum_match': matching_check_sum }
        # fieldnames = ['Time stamp', 'Before_correction', 'After_correction']
        with open('Rb_Corrections.csv', 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile,fieldnames = Column_names02)
            writer.writerow(Correction_info)

    signal.clear()

# Method to set the receiver configuration 
async def sendCmd_Rx(cmdVal, reader, writer):
    # Send the command
    writer.write(cmdVal.encode('utf-8') + b"\r\n")
    await writer.drain()

    # Read the response to the command
    command_response = await reader.readuntil(b"NGS-C60 Telnet W>")
    return command_response.decode('utf-8')

async def Receiver(Rx_mode):
    # Define connection parameters
    host = "172.16.26.42"
    port = 2001
    username = "ngsc60admin"
    password = "NgsAdmin@C60"
    myencoding ='utf-8'

    reader, writer = await asyncio.open_connection(host, port)

    # Read the initial server response
    initial_response = await reader.readuntil(b"Enter User ID : ")

    # Send the username
    writer.write(username.encode(myencoding) + b"\r\n")
    await writer.drain()

    # Read the password prompt
    password_response = await reader.readuntil(b"Enter Password : ")
    # Send the password
    await sendCmd_Rx(password,reader,writer)
     
    #command_response = await sendCmd_Rx("help",reader,writer)
    
    command_response = await sendCmd_Rx(Rx_mode,reader,writer)

    # Print the response
    print(command_response)

    # Finally, close the telnet session
    writer.write(b"exit\r\n")
    await writer.drain()

    # Close the connection
    writer.close()
    await writer.wait_closed()
    print(f"{Rx_mode} activated")

def mjd_to_utc(mjd, trkl):

   # Split into MJD and seconds
    mjd, day_fraction = divmod(mjd, 1)
    seconds_in_day = day_fraction * 86400

    # Convert MJD to date (MJD 0 corresponds to 1858-11-17)
    mjd_start = datetime(1858, 11, 17)
    date = mjd_start + timedelta(days=mjd)

    # Convert seconds to time and add trkl seconds
    time = (mjd_start + timedelta(seconds=seconds_in_day + trkl)).time()

    # Combine date and time
    combined_datetime = datetime.combine(date, time)

    # Format the new datetime object back into a string 
    return combined_datetime.strftime("%Y-%m-%d %H:%M:%S")

# Following 3 methods to define the file path correctly 

def is_it_today():
    current_utc_time = datetime.utcnow()
    current_local_time = current_utc_time + timedelta(hours=5, minutes=30)
    # Check if the local time is on or after 5:30 AM
    return current_local_time.hour > 5 or (current_local_time.hour == 5 and current_local_time.minute >= 30)


def extract_time_from_filename(filename):
    """
    Extracts and converts the time part of the filename to a datetime object.
    Assumes filename format is 'IRNPLI60299.HHMMSS'.
    """
    time_part = filename.split('.')[-1]  # Get the last part after the '.'
    return datetime.strptime(time_part, "%H%M%S")  # Convert to datetime object for easy comparison

def mjd_today():
    # Calculate today's Modified Julian Date.
    jd = datetime.utcnow() + timedelta(hours=5, minutes=30)
    mjd = jd.toordinal() + 1721424.5 - 2400000.5
    return int(mjd)

def latest_file_in_directory(directory, file_prefix):
    # Find the latest file in a directory with a specific prefix based on the filename's time part.
    files = [f for f in os.listdir(directory) if f.startswith(file_prefix)]
    if not files:
        print("No LATEST files to read")
        return None, None, None
    else:
        # Sort files by the extracted time, newest first
        sorted_files = sorted(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)), reverse=True)
        latest_file = sorted_files[0]  # The first file in the sorted list is the newest

        # Get the modification time of the latest file (Note this is in UTC time as per python getmtime method)
        modification_time = os.path.getmtime(os.path.join(directory, latest_file))

        # readable_time_utc = datetime.utcfromtimestamp(modification_time).strftime("%Y-%m-%d %H:%M:%S")

        # Convert the timestamp to a human-readable format
        readable_time = datetime.fromtimestamp(modification_time).strftime("%Y-%m-%d %H:%M:%S")


        # Return the latest file along with its local PC's timestamp
        return latest_file, modification_time, readable_time

# Method to read the CGGTTS file content 

def read_file_data(file_path):
    # Read lines from a file, skipping the first 'skip_lines' lines.
    lines_rx_ref = []
    unique_mjd_values = set()  # To store unique MJD values
    unique_sv_id = set()  # To store the Unique SV ID values
    unique_FRC =set()
    df_01 =pd.DataFrame()
    Required_Colm_data_01 = []
    combined_Colm_data_01 = pd.DataFrame()

    with open(file_path, 'r') as file:
        # lines = file.readlines()[skip_lines:]
        frc_is_at = None
        
        file_content = file.read()

        # Split the file into lines
        lines = file_content.split('\n')

        data_after_head = []
        # Flag to indicate if we are currently inside a header block
        inside_header = False
        frc_is_at = None
        prev_line = None  # Variable to keep track of the previous line
        
        for line in lines:
            # find the position of the FRC in the line 
            if "hhmmss  s  .1dg .1dg    .1ns" in line and prev_line:
                frc_position = prev_line.find('FRC')
                if frc_position != -1:
                    frc_is_at = frc_position
            
            # Start of the header
            if line.startswith("CGGTTS")or line.startswith("GGTTS"):
                inside_header = True

            # If we're not inside a header, process the line as data
            elif not inside_header:
                data_after_head.append(line)

            # End of the header
            if "hhmmss  s  .1dg .1dg    .1ns" in line:
                inside_header = False
                
            prev_line = line  # Update the prev_line with the current line

        # Create DataFrame from the data list
        data_rows = []

        for line in data_after_head:
            if line.strip():  # Skip empty lines
                # Extract the columns based on their fixed positions
                data_row = {
                    'SAT': line[0:3].strip(),
                    'CL': line[4:6].strip(),
                    'MJD': line[7:12].strip(),
                    'STTIME': line[13:19].strip(),
                    'TRKL': line[20:24].strip(),
                    'ELV': line[25:28].strip(),
                    'AZTH': line[29:33].strip(),
                    'REFSV': line[34:45].strip(),
                    'SRSV': line[46:52].strip(),
                    'REFSYS': line[53:64].strip()                                            
                }
                
                # Use the 'FRC' position if found
                if frc_is_at is not None and len(line) > frc_is_at + 2:
                    data_row['FRC'] = line[frc_is_at:frc_is_at + 3].strip()
                else:
                    # if it is CGGTTS version 1.0 there is no FRC column in the data format but the data is of L1C
                    data_row['FRC'] = "L1C"

                data_rows.append(data_row)

        # Create DataFrame from the data list
        df_split = pd.DataFrame(data_rows)

        df_split = df_split[df_split['SAT'].notna()] # Skip the lines where SAT column is missing 
        df_01['SAT'] = df_split['SAT']
        df_split['STTIME'] = df_split['STTIME']  # Keep as string for hhmmss processing
        df_split['TRKL'] = df_split['TRKL'].astype(float)
        df_split['MJD'] = df_split['MJD'].astype(str).str.replace('"', '').astype(float)

        # Process STTIME and combine it with MJD
        def convert_sttime_to_seconds(sttime_str):
            # Extract hours, minutes, seconds and convert to total seconds
            hours, minutes, seconds = map(int, [sttime_str[:2], sttime_str[2:4], sttime_str[4:6]])
            return (hours * 3600 + minutes * 60 + seconds)/86400

        # Apply the conversion to STTIME and add it to MJD
        df_split['MJD'] += df_split['STTIME'].apply(lambda x: convert_sttime_to_seconds(x))
        df_01['MJD'] = df_split['MJD']
        
        # Convert other relevant columns to desired datatypes
        df_01['ELV'] = df_split['ELV'].astype(float)
        df_01['REFSV'] = df_split['REFSV'].astype(float)
        df_01['SRSV'] = df_split['SRSV'].astype(float)
        df_01['REFSYS'] = df_split['REFSYS'].astype(float)
        df_01['FRC'] = df_split['FRC'].astype(str)
        df_01['TRKL']  = df_split['TRKL'].astype(float)

        Required_Colm_data_01.append(df_01)
        
        unique_FRC.update(df_01['FRC'].unique())
        unique_mjd_values.update(df_01['MJD'].unique())
        unique_sv_id.update(df_01['SAT'].unique())
        
        combined_Colm_data_01 = pd.concat([combined_Colm_data_01, df_01])

    unique_mjd_values = sorted(unique_mjd_values)
    # Sort the Uniques MJD time stamps if there are multiple sessions or time stamps 
    unique_mjd_int_values1 = sorted(set(int(mjd) for mjd in unique_mjd_values if not pd.isna(mjd)))

    # this function returns the combined required data, unique time stamps , Unique satellites in the data, Unique frequencies in the measurements 
    return combined_Colm_data_01,unique_mjd_int_values1, unique_sv_id, unique_FRC   

# Method to perform Common view time time difference 
def process_CV(df1, df2, unique_MJD_times, unique_SATs, Freq_used):
    # Convert SAT values in df1 and df2 to integers if they are strings
    df1['SAT'] = df1['SAT'].astype(int)
    df2['SAT'] = df2['SAT'].astype(int)

    # Ensure that MJD is of float type in both dataframes
    df1['MJD'] = df1['MJD'].astype(float)
    df2['MJD'] = df2['MJD'].astype(float)

    # Convert unique_SATs to a set of integers
    unique_SATs = {int(sat) for sat in unique_SATs}

    # Filter the DataFrames based on MJD, SAT, and FRC
    df1_filtered = df1[df1['MJD'].isin(unique_MJD_times) & df1['SAT'].isin(unique_SATs) & df1['FRC'].isin(Freq_used)]
    df2_filtered = df2[df2['MJD'].isin(unique_MJD_times) & df2['SAT'].isin(unique_SATs) & df2['FRC'].isin(Freq_used)]

    # Merge the filtered DataFrames
    merged_df = pd.merge(df1_filtered, df2_filtered, on=['SAT', 'MJD', 'FRC'], suffixes=('_df1', '_df2'))

    # Compute differences
    merged_df['CV_diff'] = (merged_df['REFSYS_df1'] - merged_df['REFSYS_df2']) * 0.1

    # Group by 'MJD' and calculate average CV_diff
    result = merged_df.groupby('MJD').agg({'CV_diff': 'mean'})
    result.columns = ['CV_avg_diff']  # Value is in nano seconds 
    result.reset_index(inplace=True)

    # Check for multiple unique MJD values
    unique_mjd_values = result['MJD'].unique()
    if len(unique_mjd_values) > 1:
        print("Error: More than one unique MJD value found.")
    
    # Return the last (largest) unique MJD value
    unique_mjd = unique_mjd_values[-1]
    print(f"Unique MJD value returned: {unique_mjd}")

    return result, unique_mjd

# Method to apply Corrections in Common View mode 

def apply_CV_corrections (CV_session, Present_error, Prev_error, time_bw_errors, correction_delay):

    # Slope of the Time interval errors measurements 
    CV_diff_slope = (Present_error - Prev_error) / time_bw_errors
    print(f"CV_diff slope: {CV_diff_slope}")
    # Frequency delta f1 correction
    delta_f1 = 0.25*CV_diff_slope * (1E-2)
    print(f"delta_f1: {delta_f1}")
    
    # Frequency delta f2 correction [corresponds to Phase correction]
    delta_f2 =  ((0-Present_error) / (5*16*60)) *1E-2 # Phase time constant 24 minutes = 24*60 sec
    print(f"delta_f2: {delta_f2}")
    
    # Frequency delta f3 correction [corresponds to Phase correction]
    # current_timestamp = time.mktime(time.strptime(time.ctime(time.time()), "%a %b %d %H:%M:%S %Y"))
    # print(f"curreent time stamp: {current_timestamp}")
    # print(f"current CV time stamp (STTS time) : {current_CV_time}")
                                                                                    
    delta_f3 =  (CV_diff_slope * correction_delay* 1E-2) / (4*16* 60)
    # delta_f3 =  (CV_diff_slope * correction_delay*0.5 * 1E-2) / (24 * 60)
    print(f"delta_f3: {delta_f3}")
    
    # Total correction will be in Hz
    total_correction = (delta_f1 - delta_f2 + delta_f3)
    # total_correction = (delta_f1 - delta_f2)
    # total_correction = (delta_f1 + delta_f3)
    print(f"Total correction applied: {total_correction}")

    if abs(total_correction) < 0.070:
        # if total_correction > 0 and total_correction < 0.00008  : # Less than lower limit 
        #     signal.set()
        #     send_cmd_Rb(0.00008, 1)
        #     steer_action =1
        #     total_correction = 0.00008
        #     print("Freq Correction is less than Positive lower limit hence, lower limit is applied")
        # elif total_correction < 0 and total_correction > -0.00008: # Less than lower limit
        #     signal.set()
        #     send_cmd_Rb(-0.00008, 1)
        #     steer_action =1
        #     total_correction = -0.00008
        #     print("Freq Correction is less than Negative lower limit hence, lower limit is applied")
        # else:  # Between Max and Min limits
        signal.set()
        send_cmd_Rb(total_correction, 1)
        steer_action =1
        print("Freq Correction is in limits & send to Rb")
    elif abs(total_correction) > 0.070:
    # if abs(total_correction) > 0.070:
        if total_correction > 0:
            signal.set()
            send_cmd_Rb(0.070, 1)
            steer_action =1
            print("Freq Correction is more than positive limits & send to Rb")
        else: # total_correction < 0:
            signal.set()
            send_cmd_Rb(-0.070, 1)
            steer_action =1
            print("Freq Correction is less than Negitive limits & send to Rb")
    else:  # Between Max and Min limits
            signal.set()
            send_cmd_Rb(total_correction, 1)
            steer_action =1
            print("Freq Correction is in limits & send to Rb")

    # print(f"Previous record stored from 2nd session  :\n {Prev_CV_record}")
    # Prev_CV_record = CV_performance.copy()  # Replace the Previous values with the current values
        
    Time = time.ctime(time.time())
    # Create a new row to append
    new_row = {'Time': Time, 'CV_Session': CV_session,'Correction_delay': correction_delay, 'CV_Time_Diff': Present_error, 'delta_f1': delta_f1, 'delta_f2': delta_f2, 'delta_f3': delta_f3, 'Corr_applied': total_correction }
    # print(f"New Row: {new_row}")
    
    # Write the data to a CSV file for record 
    with open('CV_Corrections.csv', 'a', newline='') as csvfile:
        Column_name = ['Time', 'CV_Session', 'Correction_delay','CV_Time_Diff', 'delta_f1','delta_f2','delta_f3','Corr_applied']
        writer = csv.DictWriter(csvfile, fieldnames = Column_name)
        writer.writerow(new_row) 


# Main program stars from here 
read_count =1 
avg_read =0  
Ster_sessions =1
PID_flip=1
corr_intr = 900   # Correction interval before PID lock mode
first_time = 1
Fst =0

# Ensure shift_in_device_units does not exceed 32-bit signed integer limits
max_int32 = 2**31 - 1
min_int32 = -2**31


steering_int = 60 # Periodic time interval of applying corrections
phase_time_const = 1.5*steering_int   # Phase time constant: Time required to correct the phase offset 



steering= False
signal = threading.Event()
phase = threading.Event()
lock_mode = 0
one_time_UL = 0
near_lock =0 
corr_count = 1   # Apply PID correction once for the first time 
corr_count_LM = 1 # Apply Entering lock mode correction once for the first time
init_lock = 0 # Signal to initiate PID locking


count = 0
set_point = 0
tau = 1 
steer_action = 0
TIC_data = []
time_data = []
TIC_4_slope =[]
first_entry = 1
Near_Lock_mode =0
Unlock_I =0
Unlock_II =0
Phase_corr =0
Init_lock_sett=1
data_point = []
slow_corr = 1  
i=0 
Universal = 0
Ini_slope = 1
limit_counter =0
first_corr = 1
corr_counter =0
wait_time =0

# Initialisaiton 

Timing_mode = True
CV_mode = False

CV_session = 1
repeat_search = True
CV_performance = pd.DataFrame()
Prev_CV_record = pd.DataFrame()
freq_4_slope =[] 


# Excel sheet to store the Rb Corrections information 
with open('Rb_Corrections.csv', 'w', newline='') as csvfile:
        Column_names02 = ['Time stamp', 'Before_correction', 'After_correction','Hex_before', 'Bytes_before', 'Bytes_applied', 'Hex_applied', 'Hex_after', 'Bytes_after', 'Check_sum_match']
        writer = csv.DictWriter(csvfile, fieldnames = Column_names02)
        writer.writeheader()


# Excel sheet to store the CV Corrections information 
with open('CV_Corrections.csv', 'w', newline='') as csvfile:
    Column_names03 = ['Time', 'CV_Session', 'Correction_delay','CV_Time_Diff','delta_f1', 'delta_f2', 'delta_f3', 'Corr_applied']
    writer = csv.DictWriter(csvfile, fieldnames = Column_names03)
    writer.writeheader()

# def main():

while True: 
    # When the receiver is in Timing Mode 
    if Timing_mode and not CV_mode : 
        # print("Hellow world")
        asyncio.run(Receiver("SET MOS TIMING"))
        # Open the TIC serial port 
        time.sleep(1)
        TIC_ser = serial.Serial(port = 'COM12',baudrate = 115200 )
        print("TIC Comport is open: ", TIC_ser.isOpen())
        
        if not TIC_ser.isOpen():
            print("TIC Comport is not open")
            #TIC_ser.open()
            #print('COM5 is open', TIC_ser.isOpen())
        else:
            latest_readings = []
            TIC_4_slope = []
            
            error_record =[]
            Current_DO_file = None
            Current_Ref_file = None
            # Wait for some time till the header files of the TIC lapsed & GNSS position fix is done for the receiver  
            time.sleep(10)   
            
            start_time= datetime.now()
            with open('TIC_data.csv', 'w', newline='') as csvfile:
                Column_name = ['Time stamp', 'TIC reading']
                writer = csv.DictWriter(csvfile, fieldnames = Column_name)
                writer.writeheader()
                
                
                while True:
                    data = TIC_ser.readline().decode('utf-8').strip()
                    
                    if data.__contains__("TI(A->B)"):
                        data1 = data.split(" ")
                        if float(data1[0])<1:
                            
                            nowt = datetime.now()
                            time_stamp = nowt.strftime("%d-%m-%Y %H:%M:%S")
                            
                            with open('TIC_data.csv', 'a', newline='') as csvfile:
                                Column_name = ['Time stamp', 'TIC reading']
                                writer = csv.DictWriter(csvfile, fieldnames = Column_name)
                                writer.writerow({'Time stamp':time_stamp, 'TIC reading': data1[0]})
                            
                            latest_readings.append(float(data1[0]))
                            
                            # If latest readings list has more than 5 entries, remove the oldest one
                            if len(latest_readings) > 3:
                                latest_readings.pop(0)    
                            
                            avg_reading =0
                            # Calculate and print the avervaluesprocess_CVage of the latest 3 readings
                            if latest_readings: 
                                avg_reading = sum(latest_readings) / len(latest_readings)
                                read_count =read_count + 1 
                                print(f"Latest 3 readings average value in ns : {avg_reading*1E+9}")
                                error_UL = set_point - avg_reading
                            
                            # Check when to activate the CV mode 
                                error_record.append(error_UL)
                                
                                if len(error_record) > 20:
                                    error_record.pop(0) 
                                
                                    # Check if all values in error_record are less than 5E-9 shift to time transfer mode 
                                    # if all(each_value < 5E-9 for each_value in error_record):
                                        # Timing_mode = 0
                                        # CV_mode = 1
                                        # break
                                
                                if abs(avg_reading) > 1E-6: # UN LOCK condition
                                    print("UNLOCK mode: More than 1 us")
                                    Universal = 1
                                    lock_flag =0  # 0 means not locked yet 
                                    if (error_UL < 0) & (one_time_UL == 0):  # Apply correction immedietly once as the reading starts if error <0 
                                        corr_to_be = 0.9 # the frequency corretion is applied with maximum drift for 300 s 
                                        one_time_UL =1
                                        steer_action = 0
                                        signal.set()
                                        send_cmd_Rb(corr_to_be, 0)
                                        
                                    elif (error_UL > 0) & (one_time_UL == 0):  # Apply correction immedietly once as the reading starts if error >0
                                        corr_to_be = -0.9 # the frequency corretion is applied with maximum drift for 300 s 
                                        one_time_UL =1
                                        steer_action = 0
                                        signal.set()
                                        send_cmd_Rb(corr_to_be, 0)
                                        
                                    elif (read_count% 100 ) == 0: # Apply correction EVERY 300 seconds (5 minutes)
                                        if error_UL > 0: 
                                            corr_to_be = -0.9
                                            steer_action = 0
                                            signal.set()
                                            send_cmd_Rb(corr_to_be, 0)
                                        elif error_UL < 0: 
                                            corr_to_be = 0.9
                                            steer_action = 0
                                            signal.set()
                                            send_cmd_Rb(corr_to_be, 0)                   
                                                    
                                elif (100E-9 < abs(avg_reading) < 1E-6)  and not steering: # Near to the LOCK condition 
                                    print("UNLOCK mode: 100 ns to 1 us ")
                                    Universal = 1
                                    if (error_UL > 0) & (Unlock_II == 0): # Apply correction immedietly once as the reading starts if error >0
                                        Unlock_II =1
                                        steer_action = 0
                                        signal.set()
                                        send_cmd_Rb(-0.05, 0)   # 700 ns of drift to be compensated in 10 minutes, NOt locked yet 
                                    
                                    elif (error_UL < 0) & (Unlock_II == 0): # Apply correction immedietly once as the reading starts if error <0
                                        Unlock_II =1
                                        steer_action = 0
                                        signal.set()
                                        send_cmd_Rb(0.05, 0)   #  700 ns of drift to be compensated in 10 minutes, NOt locked yet
                                    
                                    if ((read_count% 30 ) == 0): # Apply correction EVERY 600 seconds (10 minutes)
                                        if error_UL > 0: 
                                            corr_to_be = -0.05
                                            steer_action = 0
                                            signal.set()
                                            send_cmd_Rb(corr_to_be, 0)
                                        elif error_UL < 0: 
                                            corr_to_be = 0.05
                                            steer_action = 0
                                            signal.set()
                                            send_cmd_Rb(corr_to_be, 0)   
                                
                                elif (20E-9 < abs(avg_reading) < 100E-9) and not steering : # Near to the LOCK condition 
                                    
                                    print("UNLOCK mode: 20 ns to 100 ns ")
                                    if (error_UL > 0) & (Unlock_I == 0): # Apply correction immedietly once as the reading starts if error >0
                                        Unlock_I =1
                                        steer_action = 0
                                        signal.set()
                                        send_cmd_Rb(-0.01, 0)   # 700 ns of drift to be compensated in 10 minutes, NOt locked yet 
                                    
                                    elif (error_UL < 0) & (Unlock_I == 0): # Apply correction immedietly once as the reading starts if error <0
                                        Unlock_I =1
                                        steer_action = 0
                                        signal.set()
                                        send_cmd_Rb(0.01, 0)   #  700 ns of drift to be compensated in 10 minutes, NOt locked yet
                                    
                                    if ((read_count% 30 ) == 0): # Apply correction EVERY 600 seconds (10 minutes)
                                        if error_UL > 0: 
                                            corr_to_be = -0.01
                                            steer_action = 0
                                            signal.set()
                                            send_cmd_Rb(corr_to_be, 0)
                                        elif error_UL < 0: 
                                            corr_to_be = 0.01
                                            steer_action = 0
                                            signal.set()
                                            send_cmd_Rb(corr_to_be, 0)     
                                
                                elif (5E-9 < abs(avg_reading) < 20E-9) and not steering: # Near to the LOCK condition 
                                    print("UNLOCK mode: 3 ns to 20 ns ")
                                    if (error_UL > 0) & (Unlock_I == 0): # Apply correction immedietly once as the reading starts if error >0
                                        Unlock_I =1
                                        steer_action = 0
                                        signal.set()
                                        send_cmd_Rb(-0.005, 0)   # 700 ns of drift to be compensated in 10 minutes, NOt locked yet 
                                    
                                    elif (error_UL < 0) & (Unlock_I == 0): # Apply correction immedietly once as the reading starts if error <0
                                        Unlock_I =1
                                        steer_action = 0
                                        signal.set()
                                        send_cmd_Rb(0.005, 0)   #  700 ns of drift to be compensated in 10 minutes, NOt locked yet
                                    
                                    if ((read_count% 15 ) == 0): # Apply correction EVERY 600 seconds (10 minutes)
                                        if error_UL > 0: 
                                            corr_to_be = -0.005
                                            steer_action = 0
                                            signal.set()
                                            send_cmd_Rb(corr_to_be, 0)
                                        elif error_UL < 0: 
                                            corr_to_be = 0.005
                                            steer_action = 0
                                            signal.set()
                                            send_cmd_Rb(corr_to_be, 0) 
                                
                                elif ((3E-9 < abs(avg_reading) < 5E-9)) and not steering : # Initiate LOCK condition 
                                    print(" Near LOCK mode : 1 ns to 4 ns")
                                    if (error_UL > 0) & (corr_count_LM ==1) : # Apply correction immedietly once to slowdown  the drift rate if error >0
                                        Near_Lock_mode =1
                                        corr_count_LM = 0
                                        Unlock_I =0
                                        steer_action = 0
                                        signal.set()
                                        #send_cmd_Rb(-0.00178, 0)   # 700 ns of drift to be compensated in 10 minutes  
                                        send_cmd_Rb(-0.003350, 0)
                                        TIC_4_slope.append(float(data1[0]))
                                        if len(TIC_4_slope) > 3: # Every latest 3 data points
                                            TIC_4_slope.pop(0)
                                            data_point = list(range(1, len(TIC_4_slope) + 1))
                                            slope, intercept = np.polyfit(data_point, TIC_4_slope,1) # y = mx + c ; ouput p = [m,c]
                                            #print(f"Slope of the TIC_data (Frequency): {slope}")
                                            prev_slope= slope
                                            if slope <0:
                                                Ini_slope =-1
                                            else:
                                                Ini_slope = 1
                                    
                                    elif (error_UL < 0) & (corr_count_LM ==1) : # Apply correction immedietly once to slowdown  the drift rate if error >0
                                        Near_Lock_mode =1
                                        corr_count_LM = 0
                                        Unlock_I=0
                                        steer_action = 0
                                        #slow_corr =0  # Repeat Slow correction. Needed if the required correction is not applied correctly 
                                        signal.set()
                                        #send_cmd_Rb(0.00178, 0)   #  700 ns of drift to be compensated in 10 minutes
                                        send_cmd_Rb(0.003350, 0)
                                        TIC_4_slope.append(float(data1[0]))
                                        if len(TIC_4_slope) > 3: # Every latest 3 data points
                                            TIC_4_slope.pop(0)
                                            data_point = list(range(1, len(TIC_4_slope) + 1))
                                            slope, intercept = np.polyfit(data_point, TIC_4_slope,1) # y = mx + c ; ouput p = [m,c]
                                            #print(f"Slope of the TIC_data (Frequency): {slope}")
                                            prev_slope= slope
                                            if slope <0:
                                                Ini_slope =-1
                                            else:
                                                Ini_slope = 1
                                                
                                elif (abs(avg_reading) < 100E-9) and steering:
                                    read_count = 0
                                    wait_time =0
                                                        
                                    if steering:
                                        count = count+1 
                                        freq_4_slope.append(float(data1[0]))                        
                                        if len(freq_4_slope) > steering_int: # Every latest 60 s
                                            freq_4_slope.pop(0)
                                        #if ((count % steering_int ==0) & (len(freq_4_slope)  == steering_int)) :
                                        if ((count % steering_int ==0)) :
                                            data_pointF = list(range(1, len(freq_4_slope) + 1))
                                            slope, intercept = np.polyfit(data_pointF, freq_4_slope,1) # y = mx + c ; ouput p = [m,c]
                                            print(f"Slope of the TIC_data (Frequency): {slope}")
                                            first_time = 0
                                            Freq_corr = slope*1E+7
                                            phase_corr = ((0-float(data1[0]))*1E+7)/phase_time_const 
                                            Total_corr = Freq_corr - phase_corr
                                            print(f"Total Correction applied: {Total_corr}")
                                            # if abs(Total_corr) < 0.011: # Max limit 
                                            #     if Total_corr > 0 and Total_corr < 0.00008  : # Less than lower limit 
                                            #         signal.set()
                                            #         send_cmd_Rb(0.00008, 1)
                                            #         steer_action =1
                                            #         print("Freq Correction is less than Positive lower limit hence, lower limit is applied")
                                            #     elif Total_corr < 0 and Total_corr < -0.00008: # Less than lower limit
                                            #         signal.set()
                                            #         send_cmd_Rb(-0.00008, 1)
                                            #         steer_action =1
                                            #         print("Freq Correction is less than Negative lower limit hence, lower limit is applied")
                                            #     else:  # Between Max and Min limits
                                            #         signal.set()
                                            #         send_cmd_Rb(Total_corr, 1)
                                            #         steer_action =1
                                            #         print("Freq Correction is in limits & send to Rb")
                                            # elif abs(Total_corr) > 0.011: # max limit
                                            if abs(Total_corr) > 0.011: # max limit
                                                if Total_corr > 0:
                                                    signal.set()
                                                    send_cmd_Rb(0.010, 1)
                                                    steer_action =1
                                                    print("Freq Correction is more than positive limits & send to Rb")
                                                else: #Total_corr < 0:
                                                    signal.set()
                                                    send_cmd_Rb(-0.010, 1)
                                                    steer_action =1
                                                    print("Freq Correction is less than Negitive limits & send to Rb")
                                            else:  # Between Max and Min limits
                                                    signal.set()
                                                    send_cmd_Rb(Total_corr, 1)
                                                    steer_action =1
                                                    print("Freq Correction is in limits & send to Rb")
                                            
                                            check_error_value = all(abs(value*1E+9) < 1 for value in freq_4_slope) # check is all the errors is less than 1 ns  
                                            
                                            print(f"Rb is with in 1 ns wrt NavIC : {check_error_value}")
                                            
                                            if check_error_value and abs(slope) < (5E-12):
                                                CV_mode = True 
                                                Timing_mode = False # Activate the Common view mode
                                                TIC_ser.close() 
                                                freq_4_slope = [] # reset the array to continue with the loop 
                                                count =0 
                                                error_wrt_navic = float(data1[0]) # Store the value of the TIC error as an intial value 
                                                break
        
                                elif (abs(avg_reading) > 100E-9) and steering : # If the TIC  reading is in lock range
                                    # Stop steering and apply phase correction  
                                    steering = False


                                elif abs(avg_reading) < 3E-9:# Activate the steering algo
                                    steering = True
                                    print('Steering Activated..................')
                                    # if recevr_mode == 1: # Activate PID only in Timing mode 
                                    # PID_ON =1
                            
                            # PID_ON = PID_value # Update the PID status 
                            
                time.sleep(1)
                
    # When the receiver is in Time transfer Mode 
    elif CV_mode and not Timing_mode:
    
            print("Common View Mode Activated ..........")
            first_session = True # Flag to consider the available files as first session f iles
            CV_start_time= datetime.utcfromtimestamp(time.time())
            asyncio.run(Receiver("SET MOS TIME TRANSFER")) 
            print("Wait for 3 minutes for the receiver to switch configuration")
            time.sleep(150)

            # Define the base directory from where the files need to read 
            DO_base_dir = r"C:\Users\VISHAL\Documents\Accord\Accord_vbs\data_log\CV43_V3"
            Ref_base_dir = r"C:\Users\VISHAL\Documents\Accord\Accord_vbs\data_log\CV42_V3"

            rept_search_time = 60 # Waiting time to check for the new CGGTTS files  (seconds)
            Previous_DO_file = None
            Previous_Ref_file = None
            Got_New_DO_file = False
            Got_New_Ref_file = False
            both_files_found = False
            Prev_CV_record = []

            while True:
                
                CV_performance = []
            # Initialisation of the data frames 
                df_DO = pd.DataFrame()
                df_Ref= pd.DataFrame()
                    

                # Get today's MJD and construct the folder path
                today_mjd = mjd_today()
                
                if is_it_today():
                    
                    today_mjd = mjd_today()
                else:
                    # Calculate the MJD for the previous day
                    yesterday_utc = datetime.utcnow() - timedelta(days=1)
                    yesterday_local = yesterday_utc + timedelta(hours=5, minutes=30)
                    yesterday_mjd = yesterday_local.toordinal() + 1721424.5 - 2400000.5
                    today_mjd = int(yesterday_mjd)

                # while repeat_search == True: # Repeat the search untill new and correct files are found 
                    
                DO_folder_path = os.path.join(DO_base_dir, str(today_mjd))
                Ref_folder_path = os.path.join(Ref_base_dir, str(today_mjd))

                DO_file_found = False
                Ref_file_found = False
                
                while not (DO_file_found and Ref_file_found):  # Loop until both files are found
                    # Check and process DO folder and file
                    if os.path.exists(DO_folder_path) and not Got_New_DO_file:
                        DO_file_prefix = f"IRRRSL{today_mjd}"
                        result = latest_file_in_directory(DO_folder_path, DO_file_prefix)
                        
                        if result is not None:
                            DO_latest_file, time_of_fileDO, local_time_fileDO = result

                            if DO_latest_file is not None and (DO_latest_file != Previous_DO_file):
                                
                            
                                # Convert the string time to a datetime object in UTC (Note: to use this, take care of local PC time zone settings )
                                # DOfile_time_UTC= datetime.strptime(time_of_fileDO, "%Y-%m-%d %H:%M:%S")

                                DOfile_time_UTC = datetime.utcfromtimestamp(time_of_fileDO)
                                # Get the current UTC time
                                current_utc_time = datetime.utcnow()

                                # Calculate the time difference in seconds
                                time_diff_DO = (current_utc_time - DOfile_time_UTC).total_seconds()

                                print(f"DO Latest file: {DO_latest_file}, Last modified time: {local_time_fileDO} generated {round(time_diff_DO)} seconds back")
                            
                                # Check file detected is generated in last 18 minutes or more 
                                if time_diff_DO < 1080:  # 18*60 seconds 
                                    DO_file_found = True
                                else: 
                                    print("The DO file found is older than 18 minutes")
                                    DO_file_found = False
                            else:
                                print(f"No new DO file available after : {DO_latest_file} ")
                                DO_file_found = False
                        
                        else:
                            print("Waiting for the latest DO file to be created...")
                            DO_file_found = False
                    else:
                        print("Waiting for the new MJD folder to be created for DO files...")
                    
                    # Check and process Ref folder and file
                    if os.path.exists(Ref_folder_path) and not Got_New_Ref_file:
                        Ref_file_prefix = f"IRNPLI{today_mjd}"
                        result = latest_file_in_directory(Ref_folder_path, Ref_file_prefix)
                        
                        if result is not None:
                            Ref_latest_file, time_of_fileRef, local_time_fileRef = result
                            
                            if Ref_latest_file is not None and (Ref_latest_file != Previous_Ref_file):
                                
                                # converting file stamp to UTC time 
                                Reffile_time_UTC = datetime.utcfromtimestamp(time_of_fileRef)
                                # Get the current UTC time
                                current_utc_time = datetime.utcnow()

                                # Calculate the time difference in seconds
                                time_diff_Ref = (current_utc_time - Reffile_time_UTC).total_seconds()
                                print(f"Ref Latest file: {Ref_latest_file}, Last modified time: {local_time_fileRef} generated {round(time_diff_Ref)} seconds back")
                                # print(f"Reference file generated {round(time_diff_Ref)} seconds back from now")
                                # Check file detected is generated in last 16 minutes or more 
                                if time_diff_Ref < 1080:  # 18*60 seconds 
                                    Ref_file_found = True
                                else: 
                                    print("The Ref file found is older than 18 minutes")
                                    Ref_file_found = False
                            else:
                                print(f"No new Ref file available after : {Ref_latest_file}")
                                Ref_file_found = False
                        else:
                            print("Waiting for the latest REF file to be created...")
                            Ref_file_found = False
                    else:         
                        print("Ref file is Waiting for the new MJD folder to be created for REF files...")
                        
                    
                    if DO_file_found and Ref_file_found:
                        both_files_found = True  # Stop search 
                        Got_New_DO_file = True
                        Got_New_Ref_file =True

                    time.sleep(60)  # Wait a bit before searching again
                
                current_timestamp = time.time()

                print(f"Both files found ?: {both_files_found}")
                print(f"first session : {first_session}")
                # At the beginning of the programm consider already available file as the latest file {further we will check if that file is of previous session or older than that }
                # If already available files are less than 15 minutes take the files and perform common view 
                if first_session and both_files_found:
                    

                    # first_session = False  # better to confirm this is not first session only when the files are processed and cv_difference is not none 
                    Got_New_DO_file = False  # Confirm the file is processed 
                    Got_New_Ref_file = False # confirm the file is processed 

                    # both_files_found = False
                    DO_file_found = False  # Resetting for the next iteration
                    Ref_file_found = False  # Resetting for the next iteration

                    file_path_DO = os.path.join(DO_folder_path, DO_latest_file)
                    df_DO, Un_time_DO, Un_SAT_DO, Un_freq_DO = read_file_data(file_path_DO)
                    print(f"DO Latest file 1st session {DO_latest_file} read successfully")

                    file_path_Ref = os.path.join(Ref_folder_path, Ref_latest_file)
                    df_Ref, Un_time_Ref, Un_SAT_Ref, Un_freq_Ref = read_file_data(file_path_Ref)
                    print(f"REF Latest file 1st session {Ref_latest_file} read successfully")    

                    # Previous_DO_file = DO_latest_file
                    # Previous_Ref_file = Ref_latest_file

                else:
                    # If its not 1st session 

                    if DO_latest_file is not None and Previous_DO_file != DO_latest_file:
                        file_path_DO = os.path.join(DO_folder_path, DO_latest_file)
                        # print(f"File path DO file: {file_path_DO}")    
                        df_DO, Un_time_DO, Un_SAT_DO, Un_freq_DO  = read_file_data(file_path_DO)
                        
                        # Convert each float value in Un_time_DO to a string and join them with a comma
                        Un_time_DO_str = ', '.join(str(time_val) for time_val in Un_time_DO)
                        
                        print(f"DO Latest file {DO_latest_file} read successfully")
                        

                    if Ref_latest_file is not None and Previous_Ref_file != Ref_latest_file:

                        file_path_Ref = os.path.join(Ref_folder_path, Ref_latest_file)
                    
                        df_Ref, Un_time_Ref, Un_SAT_Ref, Un_freq_Ref  = read_file_data(file_path_Ref)

                        # Convert each float value in Un_time_DO to a string and join them with a commadf_DO  first_session
                        Un_time_Ref_str = ', '.join(str(time_val) for time_val in Un_time_Ref)
                        
                        print(f"REF Latest file {Ref_latest_file} read successfully") 
                        
                                         

                if df_DO is not None and not df_DO.empty: 
                    print(f"Data frame df_DO:\n{df_DO}")
                else:
                    print("Looking for the latest DO file...  ")

                if df_Ref is not None and not df_Ref.empty:
                    print(f"Data frame df_Ref:\n{df_Ref}")
                else:
                    print("Looking for the Latest Ref file... ")
                
                if not df_DO.empty and not df_Ref.empty and both_files_found :
                    # Check if the CGGTTS files belong to the same session defined by BIPM as per UTC time stamp 
                    if sorted(set(df_DO["MJD"]).intersection(set(df_Ref["MJD"]))) != 0 : 
                        # Common view algorithm 
                        all_unique_SAT = set(df_DO["SAT"]).union( set(df_Ref["SAT"]))
                        all_unique_MJDs = sorted(set(df_DO["MJD"]).union(set(df_Ref["MJD"])))
                        Freq_CV = "LSC" # available frequencies are LSC, L5C, 5S, 1S for IRNSS 
                        Freq_CV_list = [Freq_CV]  # Convert to a list
                        if set(df_DO["MJD"]) == (set(df_Ref["MJD"])): # If the both files belong to the same time stamp proceed with the CV and update the latest files 
                            
                            Got_New_Ref_file = False # Now we can accept that we got the new, not empty, and same MJD files
                            Got_New_DO_file = False # Now we can accept that we got the new, not empty and same MJD files 
                            DO_file_found = False  # Repeat search for the new files 
                            Ref_file_found = False 
                            both_files_found = False
                            
                            Time_diff, CV_STtime = process_CV(df_Ref, df_DO, all_unique_MJDs, all_unique_SAT,Freq_CV_list)
                            time_diff_value = Time_diff['CV_avg_diff'].iloc[0] 
                            # print(f"Commonview time difference value: {time_diff_value}")
                            if time_diff_value is not None :  # check if the CV_diff is valid and store the values 
                                # print(f"time differece : \n {Time_diff}")
                                
                                CV_performance =[]
                                CV_file_row = []
                                Time = time.ctime(time.time())
                                # # Create a new row to append
                                new_row = {'Time': Time, 'CV_STtime': CV_STtime,'CV_Session': CV_session, 'CV_Time_Diff': time_diff_value}
                                print(f"NEW ROW :{new_row}")
                                # # Append the new row to the DataFrame
                            
                                CV_performance.append(new_row)
                                # # Write the data to a CSV file for record 
                                # CV_performance_df = pd.DataFrame(CV_performance)
                                # CV_performance_df.to_csv(r'C:\Users\VISHAL\Desktop\project\data\CV_steer_result.csv', mode='a', header=False, index=False)
                                # # CV_performance = pd.DataFrame(CV_performance)
                                
                                                                   

                                if abs(CV_performance[-1]['CV_Time_Diff']) > 1000 : # Go back to Timing mode because it is not easy to correct such a big drift through CV (1000 ns)
                                    Timing_mode = True
                                    CV_mode = False
                                    print("Activating TIMING MODE as the difference is more than 1 micro second")
                                    break
                                
                                                
                                def time_to_timestamp(time_str):
                                    return time.mktime(time.strptime(time_str, "%a %b %d %H:%M:%S %Y"))

                                if (CV_session > 1) and not first_session:
                                    # Convert 'Time' strings to timestamps for comparison
                                    current_CV_time = time_to_timestamp(CV_performance[0]['Time'])
                                    current_CV_STtime = CV_performance[0]['CV_STtime']
                                    prev_CV_STtime = Prev_CV_record[0]['CV_STtime']

                                    print(f"previous_CV_STtime: {prev_CV_STtime}")
                                    # prev_CV_time = time_to_timestamp(Prev_CV_record[0]['Time'])
                                    # Convert current_CV_time (UNIX timestamp) to datetime
                                    current_CV_time_dt = datetime.utcfromtimestamp(current_CV_time)
                                    # Difference between the sessions as per STTime in CGGTTS files
                                    session_diff = (current_CV_STtime - prev_CV_STtime)*86400 # converting back into seconds *86400
                                    
                                    # The difference between the STTime and the current time in seconds 
                                    current_timestamp_utc = datetime.utcfromtimestamp(time.time())
                                    half_trkl =seconds_to_add = df_DO["TRKL"].unique()[0]/2

                                    current_CV_STtime = mjd_to_utc(CV_performance[0]['CV_STtime'], half_trkl)
                                    print(f"Current_CV_STtime: {current_CV_STtime}")
                                    print(f"Current_CV_time_dt: {current_CV_time_dt}")
                                    current_CV_STtime_dt = datetime.strptime(current_CV_STtime, "%Y-%m-%d %H:%M:%S")
                                    # correction_delay = current_CV_time - current_CV_STtime.apply(lambda x: current_timestamp_utc - x)
                                    correction_delay = (current_CV_time_dt - current_CV_STtime_dt).total_seconds()
                                    
                                    
                                    print(f"Common View Time difference: {time_diff_value}")
                                    print(f"Time lapsed from the previous CV session: {session_diff}")
                                    print(f"Correction delay: {correction_delay}")
                                    
                                    if 0 <= session_diff < (30 * 60):  # previous correction applied is not more than 30 minutes
                                        # Calculate the slope
                                        print(f"Previous record time diff: {Prev_CV_record[0]['CV_Time_Diff']}")
                                        print(f"Current CV Time difference value: {time_diff_value}")
                                        print(f"time since CV difference is measured:{session_diff} ")
                                        
                                        apply_CV_corrections(CV_session, time_diff_value, Prev_CV_record[0]['CV_Time_Diff'], session_diff, correction_delay)

                                        # print(f"Previous record stored from 2nd session  :\n {Prev_CV_record}")
                                        Prev_CV_record = CV_performance.copy()  # Replace the Previous values with the current values
                                            
                                        Previous_DO_file = DO_latest_file # Update the latest file read
                                        Previous_Ref_file = Ref_latest_file # Update the latest file read
                                                                        
                                        print("Please Wait 12 minutes to repeat the process..... ")
                                        time.sleep(720)   # Wait for few minutes to repeat search for new files 
                                        CV_session = CV_session+1
                                        first_session = False
                                        DO_file_found = False  # Repeat search for the new files 
                                        Ref_file_found = False 
                                        both_files_found = False  
                                    else:
                                        print("Time since previous correction applied is more than 30 minutes. There may be some missing sessions in between")
                                
                                elif first_session and time_diff_value is not None : 
                                    Prev_CV_record = CV_performance.copy() #  store this first session results
                                    # Prev_CV_record = [{'CV_Time_Diff': cv_record['CV_Time_Diff']} for cv_record in CV_performance]
                                    print(f"Last Error wrt Navic : {error_wrt_navic}")
                                    print(f"Common View error in 1st session : {time_diff_value}")
                                    
                                    current_time = datetime.utcfromtimestamp(time.time())
                                    time_lapsed_CVmode = (current_time - CV_start_time).total_seconds()

                                    print(f"Time Lapsed since NaVIC mode: {time_lapsed_CVmode}")
                                    correction_delay = 0 
                                    apply_CV_corrections(CV_session, time_diff_value, error_wrt_navic, time_lapsed_CVmode, correction_delay)
                                    
                                    # print(f"Previous record stored as 1st session  :\n {Prev_CV_record}")
                                    Previous_DO_file = DO_latest_file # Update the latest file read
                                    Previous_Ref_file = Ref_latest_file # Update the latest file read
                                    CV_session = CV_session+1
                                    first_session = False
                                    DO_file_found = False  # Repeat search for the new files 
                                    Ref_file_found = False 
                                    both_files_found = False 
                                    print("Please Wait 12 minutes to repeat the process..... ")
                                    time.sleep(720)   # Wait for few minutes to repeat search for new files 

                                else: # It means it is 1st session of the CV_session 
                                    new_row_record = {'Time': time.ctime(time.time()), 'CV_Session': CV_session, 'Time_Diff': time_diff_value}
                                    Prev_CV_record.append(new_row_record)
                            else:
                                print("CV Time difference is found to be NONE")
                                DO_file_found = False  # Repeat search for the new files 
                                Ref_file_found = False 
                                both_files_found = False
                    else: 
                        print("These files doesnt belong to the same timeperiod to perform CV ")
                        # first_session = False
                        DO_file_found = False  # Repeat search for the new files 
                        Ref_file_found = False 
                        both_files_found = False                
                    
                else:
                    print(f"one of the file is Empty, cannot caluclate CV ")

                time.sleep(rept_search_time) # Waiting time to check for the new CGGTTS files 