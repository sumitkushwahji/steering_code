from receiver import Receiver
import asyncio
from initialization import initialize_globals  # Import the function to initialize globals
import pandas as pd
import time
import os
from datetime import datetime, timedelta
from utils import mjd_today, is_it_today, mjd_to_utc, extract_time_from_filename
from file_operations import latest_file_in_directory, read_file_data
from cv_processing import process_CV, apply_CV_corrections

# Initialize global variables
initialize_globals()

def cv_mode_implement():
    global CV_mode, CV_session, repeat_search, CV_performance, Prev_CV_record
    global Timing_mode, error_wrt_navic, rept_search_time, first_session, CV_start_time
    global DO_base_dir, Ref_base_dir, Previous_DO_file, Previous_Ref_file
    global Got_New_DO_file, Got_New_Ref_file, both_files_found, Freq_CV, CV_performance, file_path_DO
    global df_DO, Un_time_DO, Un_SAT_DO, Un_freq_DO, df_Ref, Un_time_Ref, Un_SAT_Ref, Un_freq_Ref, time_diff_value, steering

    print("Common View Mode Activated ..........")
    first_session = True  # Flag to consider the available files as first session files
    CV_start_time = datetime.utcfromtimestamp(time.time())

    # Receiver Configuration
    receiver = Receiver(
        host="172.16.26.42", port=2001, username="ngsc60admin", password="NgsAdmin@C60"
    )
    asyncio.run(receiver.configure_receiver("SET MOS TIME TRANSFER"))

    print("Wait for 3 minutes for the receiver to switch configuration")
    time.sleep(150)

    # Define the base directory from where the files need to read
    DO_base_dir = r"C:\Users\acer\Desktop\Project\npl\Data_Log_DO"
    Ref_base_dir = r"C:\Users\acer\Desktop\Project\npl\Data_Log_REF"

    rept_search_time = 60  # Waiting time to check for the new CGGTTS files  (seconds)
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
        df_Ref = pd.DataFrame()

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

        DO_folder_path = os.path.join(DO_base_dir, str(today_mjd))
        Ref_folder_path = os.path.join(Ref_base_dir, str(today_mjd))

        DO_file_found = False
        Ref_file_found = False

        while not (DO_file_found and Ref_file_found):
            if os.path.exists(DO_folder_path) and not Got_New_DO_file:
                DO_file_prefix = f"IRRRSL{today_mjd}"
                result = latest_file_in_directory(DO_folder_path, DO_file_prefix)

                if result is not None:
                    DO_latest_file, time_of_fileDO, local_time_fileDO = result

                    if DO_latest_file is not None and (DO_latest_file != Previous_DO_file):
                        DOfile_time_UTC = datetime.utcfromtimestamp(time_of_fileDO)
                        current_utc_time = datetime.utcnow()
                        time_diff_DO = (current_utc_time - DOfile_time_UTC).total_seconds()

                        print(
                            f"DO Latest file: {DO_latest_file}, Last modified time: {local_time_fileDO} generated {round(time_diff_DO)} seconds back"
                        )

                        if time_diff_DO < 1080:
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

            if os.path.exists(Ref_folder_path) and not Got_New_Ref_file:
                Ref_file_prefix = f"IRNPLI{today_mjd}"
                result = latest_file_in_directory(Ref_folder_path, Ref_file_prefix)

                if result is not None:
                    Ref_latest_file, time_of_fileRef, local_time_fileRef = result

                    if Ref_latest_file is not None and (Ref_latest_file != Previous_Ref_file):
                        Reffile_time_UTC = datetime.utcfromtimestamp(time_of_fileRef)
                        current_utc_time = datetime.utcnow()
                        time_diff_Ref = (current_utc_time - Reffile_time_UTC).total_seconds()
                        print(
                            f"Ref Latest file: {Ref_latest_file}, Last modified time: {local_time_fileRef} generated {round(time_diff_Ref)} seconds back"
                        )
                        if time_diff_Ref < 1080:
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
                both_files_found = True
                Got_New_DO_file = True
                Got_New_Ref_file = True

            time.sleep(60)

        current_timestamp = time.time()

        print(f"Both files found ?: {both_files_found}")
        print(f"first session : {first_session}")

        if first_session and both_files_found:
            Got_New_DO_file = False
            Got_New_Ref_file = False
            DO_file_found = False
            Ref_file_found = False

            file_path_DO = os.path.join(DO_folder_path, DO_latest_file)
            df_DO, Un_time_DO, Un_SAT_DO, Un_freq_DO = read_file_data(file_path_DO)
            print(f"DO Latest file 1st session {DO_latest_file} read successfully")

            file_path_Ref = os.path.join(Ref_folder_path, Ref_latest_file)
            df_Ref, Un_time_Ref, Un_SAT_Ref, Un_freq_Ref = read_file_data(file_path_Ref)
            print(f"REF Latest file 1st session {Ref_latest_file} read successfully")

        else:
            if DO_latest_file is not None and Previous_DO_file != DO_latest_file:
                file_path_DO = os.path.join(DO_folder_path, DO_latest_file)
                df_DO, Un_time_DO, Un_SAT_DO, Un_freq_DO = read_file_data(file_path_DO)
                Un_time_DO_str = ", ".join(str(time_val) for time_val in Un_time_DO)
                print(f"DO Latest file {DO_latest_file} read successfully")

            if Ref_latest_file is not None and Previous_Ref_file != Ref_latest_file:
                file_path_Ref = os.path.join(Ref_folder_path, Ref_latest_file)
                df_Ref, Un_time_Ref, Un_SAT_Ref, Un_freq_Ref = read_file_data(file_path_Ref)
                Un_time_Ref_str = ", ".join(str(time_val) for time_val in Un_time_Ref)
                print(f"REF Latest file {Ref_latest_file} read successfully")

        if df_DO is not None and not df_DO.empty:
            print(f"Data frame df_DO:\n{df_DO}")
        else:
            print("Looking for the latest DO file...")

        if df_Ref is not None and not df_Ref.empty:
            print(f"Data frame df_Ref:\n{df_Ref}")
        else:
            print("Looking for the Latest Ref file...")

        if not df_DO.empty and not df_Ref.empty and both_files_found:
            if sorted(set(df_DO["MJD"]).intersection(set(df_Ref["MJD"]))) != 0:
                all_unique_SAT = set(df_DO["SAT"]).union(set(df_Ref["SAT"]))
                all_unique_MJDs = sorted(set(df_DO["MJD"]).union(set(df_Ref["MJD"])))
                Freq_CV = "LSC"
                Freq_CV_list = [Freq_CV]
                if set(df_DO["MJD"]) == (set(df_Ref["MJD"])):
                    Got_New_Ref_file = False
                    Got_New_DO_file = False
                    DO_file_found = False
                    Ref_file_found = False
                    both_files_found = False

                    Time_diff, CV_STtime = process_CV(df_Ref, df_DO, all_unique_MJDs, all_unique_SAT, Freq_CV_list)
                    time_diff_value = Time_diff["CV_avg_diff"].iloc[0]

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