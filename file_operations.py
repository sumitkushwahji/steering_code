import os
from datetime import datetime
import pandas as pd

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


def read_file_data(file_path):
    # Read lines from a file, skipping the first 'skip_lines' lines.
    lines_rx_ref = []
    unique_mjd_values = set()  # To store unique MJD values
    unique_sv_id = set()  # To store the Unique SV ID values
    unique_FRC = set()
    df_01 = pd.DataFrame()
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
            if line.startswith("CGGTTS") or line.startswith("GGTTS"):
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
            return (hours * 3600 + minutes * 60 + seconds) / 86400

        # Apply the conversion to STTIME and add it to MJD
        df_split['MJD'] += df_split['STTIME'].apply(lambda x: convert_sttime_to_seconds(x))
        df_01['MJD'] = df_split['MJD']
        
        # Convert other relevant columns to desired datatypes
        df_01['ELV'] = df_split['ELV'].astype(float)
        df_01['REFSV'] = df_split['REFSV'].astype(float)
        df_01['SRSV'] = df_split['SRSV'].astype(float)
        df_01['REFSYS'] = df_split['REFSYS'].astype(float)
        df_01['FRC'] = df_split['FRC'].astype(str)
        df_01['TRKL'] = df_split['TRKL'].astype(float)

        Required_Colm_data_01.append(df_01)
        
        unique_FRC.update(df_01['FRC'].unique())
        unique_mjd_values.update(df_01['MJD'].unique())
        unique_sv_id.update(df_01['SAT'].unique())
        
        combined_Colm_data_01 = pd.concat([combined_Colm_data_01, df_01])

    unique_mjd_values = sorted(unique_mjd_values)
    # Sort the Uniques MJD time stamps if there are multiple sessions or time stamps 
    unique_mjd_int_values1 = sorted(set(int(mjd) for mjd in unique_mjd_values if not pd.isna(mjd)))

    # this function returns the combined required data, unique time stamps, Unique satellites in the data, Unique frequencies in the measurements 
    return combined_Colm_data_01, unique_mjd_int_values1, unique_sv_id, unique_FRC
