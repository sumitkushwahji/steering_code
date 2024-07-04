from receiver import Receiver
import asyncio
from initialization import initialize_globals  # Import the function to initialize globals
import pandas as pd
import time
import os
from datetime import datetime, timedelta

# Initialize global variables
initialize_globals()

def cv_mode_implement():
    global CV_mode, CV_session, repeat_search, CV_performance, Prev_CV_record
    global Timing_mode, error_wrt_navic, rept_search_time, first_session, CV_start_time
    global DO_base_dir, Ref_base_dir, Previous_DO_file, Previous_Ref_file
    global Got_New_DO_file, Got_New_Ref_file, both_files_found, Freq_CV, CV_performance, file_path_DO
    global df_DO, Un_time_DO, Un_SAT_DO, Un_freq_DO, df_Ref, Un_time_Ref, Un_SAT_Ref, Un_freq_Ref, time_diff_value

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
    DO_base_dir = r"C:\Users\VISHAL\Documents\Accord\Accord_vbs\data_log\CV43_V3"
    Ref_base_dir = r"C:\Users\VISHAL\Documents\Accord\Accord_vbs\data_log\CV42_V3"

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

                    if time_diff_value is not None and Time_diff.empty is False:
                        CV_STtime_str = CV_STtime.strftime("%Y-%m-%d %H:%M:%S")
                        CV_performance = {
                            "Common View Configuration Status": "Good",
                            "CV_AVG_Time_diff": time_diff_value,
                            "CV_start_time": CV_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "CV_STtime": CV_STtime_str,
                            "DO file": DO_latest_file,
                            "Ref file": Ref_latest_file,
                        }

                        print("Common View Time Difference :\n", Time_diff)
                        Prev_CV_record.append(CV_performance)
                    else:
                        CV_performance = {
                            "Common View Configuration Status": "Error",
                            "DO file": DO_latest_file,
                            "Ref file": Ref_latest_file,
                        }
                        print("Common View Processing Error")
                        Prev_CV_record.append(CV_performance)
                else:
                    CV_performance = {
                        "Common View Configuration Status": "Error",
                        "DO file": DO_latest_file,
                        "Ref file": Ref_latest_file,
                    }
                    print("Common View Processing Error")
                    Prev_CV_record.append(CV_performance)

            else:
                CV_performance = {
                    "Common View Configuration Status": "Error",
                    "DO file": DO_latest_file,
                    "Ref file": Ref_latest_file,
                }
                print("Common View Processing Error")
                Prev_CV_record.append(CV_performance)

        if first_session:
            first_session = False

        # Save the previous DO and Ref files
        Previous_DO_file = DO_latest_file
        Previous_Ref_file = Ref_latest_file

        # Wait for some time before next search
        time.sleep(rept_search_time)
