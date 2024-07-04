# initialization.py


import threading
import pandas as pd
import csv


def initialize_csv_files():
    with open("Rb_Corrections.csv", "w", newline="") as csvfile:
        Column_names02 = [
            "Time stamp",
            "Before_correction",
            "After_correction",
            "Hex_before",
            "Bytes_before",
            "Bytes_applied",
            "Hex_applied",
            "Hex_after",
            "Bytes_after",
            "Check_sum_match",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=Column_names02)
        writer.writeheader()

    with open("CV_Corrections.csv", "w", newline="") as csvfile:
        Column_names03 = [
            "Time",
            "CV_Session",
            "Correction_delay",
            "CV_Time_Diff",
            "delta_f1",
            "delta_f2",
            "delta_f3",
            "Corr_applied",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=Column_names03)
        writer.writeheader()

    with open("TIC_data.csv", "w", newline="") as csvfile:
        Column_name = ["Time stamp", "TIC reading"]
        writer = csv.DictWriter(csvfile, fieldnames=Column_name)
        writer.writeheader()


def initialize_globals():
    global signal, phase, lock_mode, one_time_UL, near_lock, corr_count, corr_count_LM, init_lock
    global count, set_point, tau, steer_action, TIC_data, time_data, TIC_4_slope, first_entry
    global Near_Lock_mode, Unlock_I, Unlock_II, Phase_corr, Init_lock_sett, data_point, slow_corr
    global i, Universal, Ini_slope, limit_counter, first_corr, corr_counter, wait_time
    global Timing_mode, CV_mode, CV_session, repeat_search, CV_performance, Prev_CV_record, freq_4_slope
    global read_count, avg_read, Ster_sessions, PID_flip, corr_intr, first_time, Fst, max_int32, min_int32
    global steering_int, phase_time_const

    signal = threading.Event()
    phase = threading.Event()
    lock_mode = 0
    one_time_UL = 0
    near_lock = 0
    corr_count = 1
    corr_count_LM = 1
    init_lock = 0
    count = 0
    set_point = 0
    tau = 1
    steer_action = 0
    TIC_data = []
    time_data = []
    TIC_4_slope = []
    first_entry = 1
    Near_Lock_mode = 0
    Unlock_I = 0
    Unlock_II = 0
    Phase_corr = 0
    Init_lock_sett = 1
    data_point = []
    slow_corr = 1
    i = 0
    Universal = 0
    Ini_slope = 1
    limit_counter = 0
    first_corr = 1
    corr_counter = 0
    wait_time = 0
    Timing_mode = True
    CV_mode = False
    CV_session = 1
    repeat_search = True
    CV_performance = pd.DataFrame()
    Prev_CV_record = pd.DataFrame()
    freq_4_slope = []
    read_count = 1
    avg_read = 0
    Ster_sessions = 1
    PID_flip = 1
    corr_intr = 900
    first_time = 1
    Fst = 0
    max_int32 = 2**31 - 1
    min_int32 = -(2**31)
    steering_int = 60
    phase_time_const = 1.5 * steering_int
