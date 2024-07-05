import asyncio
import time
import csv
import numpy as np
from datetime import datetime

from receiver import Receiver
from serial_communication import SerialCommunication
from rb_device import RbDevice
import initialization
from shared_resources import serial_comm

# Global variables
steering = False
freq_4_slope = []
error_record = []
initialization.one_time_UL = 0
initialization.Unlock_II = 0
Unlock_I = 0
corr_count_LM = 1
Universal = 0
lock_flag = 0
signal = None  # Assuming you have a global signal object




def timing_mode_impliment():
    # Initialize global variables and CSV files
    initialization.initialize_globals()
    initialization.initialize_csv_files()

    # Initialize RB device and receiver
    
    receiver = Receiver(
        host="172.16.26.42", port=2001, username="ngsc60admin", password="NgsAdmin@C60"
    )
    asyncio.run(receiver.configure_receiver("SET MOS TIMING"))

    # Instantiate the SerialCommunication class
    TIC_ser = SerialCommunication(port="COM3", baudrate=115200)
    
    rb_device = RbDevice(serial_comm)
    # Open the TIC serial port
    time.sleep(1)
    TIC_ser.open()

    # Check if the port is open
    if not TIC_ser.is_open():
        print("TIC Comport is not open")
    else:
        print("TIC Comport is open: ", TIC_ser.is_open())
        latest_readings = []
        TIC_4_slope = []

        # Wait for some time for initialization
        time.sleep(10)

        start_time = datetime.now()
        with open("TIC_data.csv", "w", newline="") as csvfile:
            Column_name = ["Time stamp", "TIC reading"]
            writer = csv.DictWriter(csvfile, fieldnames=Column_name)
            writer.writeheader()

            while True:
                data = TIC_ser.readline().decode("utf-8").strip()

                if data.__contains__("TI(A->B)"):
                    data1 = data.split(" ")
                    if float(data1[0]) < 1:
                        nowt = datetime.now()
                        time_stamp = nowt.strftime("%d-%m-%Y %H:%M:%S")

                        with open("TIC_data.csv", "a", newline="") as csvfile:
                            Column_name = ["Time stamp", "TIC reading"]
                            writer = csv.DictWriter(csvfile, fieldnames=Column_name)
                            writer.writerow(
                                {"Time stamp": time_stamp, "TIC reading": data1[0]}
                            )

                        latest_readings.append(float(data1[0]))

                        # If latest readings list has more than 3 entries, remove the oldest one
                        if len(latest_readings) > 3:
                            latest_readings.pop(0)

                        avg_reading = 0
                        # Calculate and print the average of the latest 3 readings
                        if latest_readings:
                            avg_reading = sum(latest_readings) / len(latest_readings)
                            initialization.read_count += 1
                            print(
                                f"Latest 3 readings average value in ns : {avg_reading*1E+9}"
                            )
                            error_UL = (
                                initialization.set_point - avg_reading
                            )
                            # More conditions and actions based on error_UL
                            error_record.append(error_UL)

                            if len(error_record) > 20:
                                error_record.pop(0)

                            if abs(avg_reading) > 1E-6:  # UN LOCK condition
                                print("UNLOCK mode: More than 1 us")
                                initialization.Universal = 1
                                lock_flag = 0  # 0 means not locked yet
                                if (error_UL < 0) & (
                                    initialization.one_time_UL == 0
                                ):  # Apply correction immediately once as the reading starts if error < 0
                                    corr_to_be = 0.9  # the frequency correction is applied with maximum drift for 300 s
                                    initialization.one_time_UL = 1
                                    initialization.steer_action = 0
                                    initialization.signal.set()
                                    rb_device.send_cmd_Rb(corr_to_be, 0)
                                elif (error_UL > 0) & (
                                    initialization.one_time_UL == 0):  # Apply correction immediately once as the reading starts if error > 0
                                    corr_to_be = -0.9  # the frequency correction is applied with maximum drift for 300 s
                                    initialization.one_time_UL = 1
                                    initialization.steer_action = 0
                                    initialization.signal.set()
                                    rb_device.send_cmd_Rb(corr_to_be, 0)
                                elif (
                                    initialization.read_count % 100
                                ) == 0:  # Apply correction EVERY 300 seconds (5 minutes)
                                    if error_UL > 0:
                                        corr_to_be = -0.9
                                        initialization.steer_action = 0
                                        initialization.signal.set()
                                        rb_device.send_cmd_Rb(corr_to_be, 0)
                                    elif error_UL < 0:
                                        corr_to_be = 0.9
                                        initialization.steer_action = 0
                                        initialization.signal.set()
                                        rb_device.send_cmd_Rb(corr_to_be, 0)

                            elif (
                                100E-9 < abs(avg_reading) < 1E-6) and not initialization.steering:  # Near to the LOCK condition
                                print("UNLOCK mode: 100 ns to 1 us ")
                                initialization.Universal = 1
                                if (error_UL > 0) & (
                                    initialization.Unlock_II == 0
                                ):  # Apply correction immediately once as the reading starts if error > 0
                                    initialization.Unlock_II = 1
                                    initialization.steer_action = 0
                                    initialization.signal.set()
                                    rb_device.send_cmd_Rb(
                                        -0.05, 0
                                    )  # 700 ns of drift to be compensated in 10 minutes, Not locked yet
                                elif (error_UL < 0) & (
                                    initialization.Unlock_II == 0
                                ):  # Apply correction immediately once as the reading starts if error < 0
                                    initialization.Unlock_II = 1
                                    initialization.steer_action = 0
                                    initialization.signal.set()
                                    rb_device.send_cmd_Rb(
                                        0.05, 0
                                    )  # 700 ns of drift to be compensated in 10 minutes, Not locked yet
                                if ((
                                    initialization.read_count % 30
                                ) == 0):  # Apply correction EVERY 600 seconds (10 minutes)
                                    if error_UL > 0:
                                        corr_to_be = -0.05
                                        initialization.steer_action = 0
                                        initialization.signal.set()
                                        rb_device.send_cmd_Rb(corr_to_be, 0)
                                    elif error_UL < 0:
                                        corr_to_be = 0.05
                                        initialization.steer_action = 0
                                        initialization.signal.set()
                                        rb_device.send_cmd_Rb(corr_to_be, 0)

                            elif (
                                20E-9 < abs(avg_reading) < 100E-9
                            ) and not initialization.steering:  # Near to the LOCK condition
                                print("UNLOCK mode: 20 ns to 100 ns ")
                                if (error_UL > 0) & (
                                    initialization.Unlock_I == 0
                                ):  # Apply correction immediately once as the reading starts if error > 0
                                    initialization.Unlock_I = 1
                                    initialization.steer_action = 0
                                    initialization.signal.set()
                                    rb_device.send_cmd_Rb(
                                        -0.01, 0
                                    )  # 700 ns of drift to be compensated in 10 minutes, Not locked yet
                                elif (error_UL < 0) & (
                                    initialization.Unlock_I == 0
                                ):  # Apply correction immediately once as the reading starts if error < 0
                                    initialization.Unlock_I = 1
                                    initialization.steer_action = 0
                                    initialization.signal.set()
                                    rb_device.send_cmd_Rb(
                                        0.01, 0
                                    )  # 700 ns of drift to be compensated in 10 minutes, Not locked yet
                                if ((
                                    initialization.read_count % 30
                                ) == 0):  # Apply correction EVERY 600 seconds (10 minutes)
                                    if error_UL > 0:
                                        corr_to_be = -0.01
                                        initialization.steer_action = 0
                                        initialization.signal.set()
                                        rb_device.send_cmd_Rb(corr_to_be, 0)
                                    elif error_UL < 0:
                                        corr_to_be = 0.01
                                        initialization.steer_action = 0
                                        initialization.signal.set()
                                        rb_device.send_cmd_Rb(corr_to_be, 0)

                            elif (
                                5E-9 < abs(avg_reading) < 20E-9
                            ) and not initialization.steering:  # Near to the LOCK condition
                                print("UNLOCK mode: 3 ns to 20 ns ")
                                if (error_UL > 0) & (
                                    initialization.Unlock_I == 0
                                ):  # Apply correction immediately once as the reading starts if error > 0
                                    initialization.Unlock_I = 1
                                    initialization.steer_action = 0
                                    initialization.signal.set()
                                    rb_device.send_cmd_Rb(
                                        -0.005, 0
                                    )  # 700 ns of drift to be compensated in 10 minutes, Not locked yet
                                elif (error_UL < 0) & (
                                    initialization.Unlock_I == 0
                                ):  # Apply correction immediately once as the reading starts if error < 0
                                    initialization.Unlock_I = 1
                                    initialization.steer_action = 0
                                    initialization.signal.set()
                                    rb_device.send_cmd_Rb(
                                        0.005, 0
                                    )  # 700 ns of drift to be compensated in 10 minutes, Not locked yet
                                if ((
                                    initialization.read_count % 15
                                ) == 0):  # Apply correction EVERY 600 seconds (10 minutes)
                                    if error_UL > 0:
                                        corr_to_be = -0.005
                                        initialization.steer_action = 0
                                        initialization.signal.set()
                                        rb_device.send_cmd_Rb(corr_to_be, 0)
                                    elif error_UL < 0:
                                        corr_to_be = 0.005
                                        initialization.steer_action = 0
                                        initialization.signal.set()
                                        rb_device.send_cmd_Rb(corr_to_be, 0)

                            elif (
                                (3E-9 < abs(avg_reading) < 5E-9)
                            ) and not initialization.steering:  # Initiate LOCK condition
                                print(" Near LOCK mode : 1 ns to 4 ns")
                                if (error_UL > 0) & (
                                    initialization.corr_count_LM == 1
                                ):  # Apply correction immedietly once to slowdown  the drift rate if error >0
                                    initialization.Near_Lock_mode = 1
                                    initialization.corr_count_LM = 0
                                    initialization.Unlock_I = 0
                                    initialization.steer_action = 0
                                    initialization.signal.set()
                                    # rb_device.send_cmd_Rb(-0.00178, 0)   # 700 ns of drift to be compensated in 10 minutes
                                    rb_device.send_cmd_Rb(-0.003350, 0)
                                    TIC_4_slope.append(float(data1[0]))
                                    if (
                                        len(TIC_4_slope) > 3
                                    ):  # Every latest 3 data points
                                        TIC_4_slope.pop(0)
                                        data_point = list(
                                            range(1, len(TIC_4_slope) + 1)
                                        )
                                        slope, initialization.intercept = np.polyfit(
                                            data_point, TIC_4_slope, 1
                                        )  # y = mx + c ; ouput p = [m,c]
                                        # print(f"Slope of the TIC_data (Frequency): {slope}")
                                        initialization.prev_slope = slope
                                        if slope < 0:
                                            initialization.Ini_slope = -1
                                        else:
                                            initialization.Ini_slope = 1

                                elif (error_UL < 0) & (
                                    initialization.corr_count_LM == 1
                                ):  # Apply correction immedietly once to slowdown  the drift rate if error >0
                                    initialization.Near_Lock_mode = 1
                                    initialization.corr_count_LM = 0
                                    initialization.Unlock_I = 0
                                    initialization.steer_action = 0
                                    # slow_corr =0  # Repeat Slow correction. Needed if the required correction is not applied correctly
                                    initialization.signal.set()
                                    # rb_device.send_cmd_Rb(0.00178, 0)   #  700 ns of drift to be compensated in 10 minutes
                                    rb_device.send_cmd_Rb(0.003350, 0)
                                    TIC_4_slope.append(float(data1[0]))
                                    if (
                                        len(TIC_4_slope) > 3
                                    ):  # Every latest 3 data points
                                        TIC_4_slope.pop(0)
                                        data_point = list(
                                            range(1, len(TIC_4_slope) + 1)
                                        )
                                        slope, initialization.intercept = np.polyfit(
                                            data_point, TIC_4_slope, 1
                                        )  # y = mx + c ; ouput p = [m,c]
                                        # print(f"Slope of the TIC_data (Frequency): {slope}")
                                        initialization.prev_slope = slope
                                        if slope < 0:
                                            initialization.Ini_slope = -1
                                        else:
                                            initialization.Ini_slope = 1

                            elif (abs(avg_reading) < 100E-9) and initialization.steering:
                                initialization.read_count = 0
                                initialization.wait_time = 0

                                if initialization.steering:
                                    initialization.count = initialization.count + 1
                                    initialization.freq_4_slope.append(float(data1[0]))
                                    if (
                                        len(initialization.freq_4_slope) > initialization.steering_int
                                    ):  # Every latest 60 s
                                        initialization.freq_4_slope.pop(0)
                                    # if ((count % steering_int ==0) & (len(freq_4_slope)  == steering_int)) :
                                    if initialization.count % initialization.steering_int == 0:
                                        initialization.data_pointF = list(
                                            range(1, len(initialization.freq_4_slope) + 1)
                                        )
                                        slope, initialization.intercept = np.polyfit(
                                            initialization.data_pointF, initialization.freq_4_slope, 1
                                        )  # y = mx + c ; ouput p = [m,c]
                                        print(
                                            f"Slope of the TIC_data (Frequency): {slope}"
                                        )
                                        initialization.first_time = 0
                                        Freq_corr = slope * 1E7
                                        phase_corr = (
                                            (0 - float(data1[0])) * 1E7
                                        ) / initialization.phase_time_const
                                        Total_corr = Freq_corr - phase_corr
                                        print(f"Total Correction applied: {Total_corr}")
                                        if abs(Total_corr) > 0.011:  # max limit
                                            if Total_corr > 0:
                                                initialization.signal.set()
                                                rb_device.send_cmd_Rb(0.010, 1)
                                                initialization.steer_action = 1
                                                print(
                                                    "Freq Correction is more than positive limits & send to Rb"
                                                )
                                            else:  # Total_corr < 0:
                                                initialization.signal.set()
                                                rb_device.send_cmd_Rb(-0.010, 1)
                                                initialization.steer_action = 1
                                                print(
                                                    "Freq Correction is less than Negitive limits & send to Rb"
                                                )
                                        else:  # Between Max and Min limits
                                            initialization.signal.set()
                                            rb_device.send_cmd_Rb(Total_corr, 1)
                                            initialization.steer_action = 1
                                            print(
                                                "Freq Correction is in limits & send to Rb"
                                            )

                                        check_error_value = all(
                                            abs(value * 1E9) < 1
                                            for value in initialization.freq_4_slope
                                        )  # check is all the errors is less than 1 ns

                                        print(
                                            f"Rb is with in 1 ns wrt NavIC : {check_error_value}"
                                        )

                                        if check_error_value and abs(slope) < (5E-12):
                                            initialization.CV_mode = True
                                            initialization.Timing_mode = (
                                                False  # Activate the Common view mode
                                            )
                                            TIC_ser.close()
                                            initialization.freq_4_slope = (
                                                []
                                            )  # reset the array to continue with the loop
                                            initialization.count = 0
                                            error_wrt_navic = float(
                                                data1[0]
                                            )  # Store the value of the TIC error as an intial value
                                            break

                            elif (
                                abs(avg_reading) > 100E-9
                            ) and initialization.steering:  # If the TIC  reading is in lock range
                                # Stop steering and apply phase correction
                                initialization.steering = False

                            elif abs(avg_reading) < 3E-9:  # Activate the steering algo
                                initialization.steering = True
                                print("Steering Activated..................")
                                # if recevr_mode == 1: # Activate PID only in Timing mode
                                # PID_ON =1

                time.sleep(1)  # Adjust sleep time as needed
