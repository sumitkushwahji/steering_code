import pandas as pd
import csv
import time
from threading import Event

signal = Event()

def process_CV(df1, df2, unique_MJD_times, unique_SATs, Freq_used):
    df1['SAT'] = df1['SAT'].astype(int)
    df2['SAT'] = df2['SAT'].astype(int)
    df1['MJD'] = df1['MJD'].astype(float)
    df2['MJD'] = df2['MJD'].astype(float)
    unique_SATs = {int(sat) for sat in unique_SATs}
    df1_filtered = df1[df1['MJD'].isin(unique_MJD_times) & df1['SAT'].isin(unique_SATs) & df1['FRC'].isin(Freq_used)]
    df2_filtered = df2[df2['MJD'].isin(unique_MJD_times) & df2['SAT'].isin(unique_SATs) & df2['FRC'].isin(Freq_used)]
    merged_df = pd.merge(df1_filtered, df2_filtered, on=['SAT', 'MJD', 'FRC'], suffixes=('_df1', '_df2'))
    merged_df['CV_diff'] = (merged_df['REFSYS_df1'] - merged_df['REFSYS_df2']) * 0.1
    result = merged_df.groupby('MJD').agg({'CV_diff': 'mean'})
    result.columns = ['CV_avg_diff']
    result.reset_index(inplace=True)
    unique_mjd_values = result['MJD'].unique()
    if len(unique_mjd_values) > 1:
        print("Error: More than one unique MJD value found.")
    unique_mjd = unique_mjd_values[-1]
    print(f"Unique MJD value returned: {unique_mjd}")
    return result, unique_mjd

def apply_CV_corrections(CV_session, Present_error, Prev_error, time_bw_errors, correction_delay, send_cmd_Rb):
    CV_diff_slope = (Present_error - Prev_error) / time_bw_errors
    print(f"CV_diff slope: {CV_diff_slope}")
    delta_f1 = 0.25 * CV_diff_slope * 1E-2
    print(f"delta_f1: {delta_f1}")
    delta_f2 = ((0 - Present_error) / (5 * 16 * 60)) * 1E-2
    print(f"delta_f2: {delta_f2}")
    delta_f3 = (CV_diff_slope * correction_delay * 1E-2) / (4 * 16 * 60)
    print(f"delta_f3: {delta_f3}")
    total_correction = (delta_f1 - delta_f2 + delta_f3)
    print(f"Total correction applied: {total_correction}")
    if abs(total_correction) < 0.070:
        signal.set()
        send_cmd_Rb(total_correction, 1)
        steer_action = 1
        print("Freq Correction is in limits & send to Rb")
    elif abs(total_correction) > 0.070:
        if total_correction > 0:
            signal.set()
            send_cmd_Rb(0.070, 1)
            steer_action = 1
            print("Freq Correction is more than positive limits & send to Rb")
        else:
            signal.set()
            send_cmd_Rb(-0.070, 1)
            steer_action = 1
            print("Freq Correction is less than Negative limits & send to Rb")
    else:
        signal.set()
        send_cmd_Rb(total_correction, 1)
        steer_action = 1
        print("Freq Correction is in limits & send to Rb")
    Time = time.ctime(time.time())
    new_row = {'Time': Time, 'CV_Session': CV_session, 'Correction_delay': correction_delay, 'CV_Time_Diff': Present_error, 'delta_f1': delta_f1, 'delta_f2': delta_f2, 'delta_f3': delta_f3, 'Corr_applied': total_correction}
    with open('CV_Corrections.csv', 'a', newline='') as csvfile:
        Column_name = ['Time', 'CV_Session', 'Correction_delay', 'CV_Time_Diff', 'delta_f1', 'delta_f2', 'delta_f3', 'Corr_applied']
        writer = csv.DictWriter(csvfile, fieldnames=Column_name)
        writer.writerow(new_row)
