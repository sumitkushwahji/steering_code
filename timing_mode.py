import asyncio
import time
import csv
import numpy as np
from datetime import datetime

from receiver import Receiver
from serial_communication import SerialCommunication
from rb_device import RbDevice
import initialization

# Global variables
steering = False
freq_4_slope = []
error_record = []
one_time_UL = 0
Unlock_II = 0
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
    rb_device = RbDevice()
    receiver = Receiver(
        host="172.16.26.42", port=2001, username="ngsc60admin", password="NgsAdmin@C60"
    )
    asyncio.run(receiver.configure_receiver("SET MOS TIMING"))

    # Instantiate the SerialCommunication class
    TIC_ser = SerialCommunication(port="COM12", baudrate=115200)

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
                            initialization.error_UL = (
                                initialization.set_point - avg_reading
                            )
                            # -----------------------------------------------------------------------
                            # Example conditions and actions based on error_UL
                            if initialization.error_UL > 0:
                                # Apply correction
                                corr_to_be = -0.9
                                signal.set()  # Set threading event
                                rb_device.send_command(corr_to_be, 0)
                            elif initialization.error_UL < 0:
                                # Apply correction
                                corr_to_be = 0.9
                                signal.set()  # Set threading event
                                rb_device.send_command(corr_to_be, 0)
                            # -------------------------------------------------------------------------
                            # More conditions and actions based on error_UL
                            error_record.append(initialization.error_UL)

                            if len(error_record) > 20:
                                error_record.pop(0)

                            if abs(avg_reading) > 1e-6:  # UN LOCK condition
                                print("UNLOCK mode: More than 1 us")
                                Universal = 1
                                lock_flag = 0  # 0 means not locked yet
                                if (initialization.error_UL < 0) & (
                                    one_time_UL == 0
                                ):  # Apply correction immediately once as the reading starts if error < 0
                                    corr_to_be = 0.9  # the frequency correction is applied with maximum drift for 300 s
                                    one_time_UL = 1
                                    signal.set()
                                    rb_device.send_command(corr_to_be, 0)
                                elif (initialization.error_UL > 0) & (
                                    one_time_UL == 0
                                ):  # Apply correction immediately once as the reading starts if error > 0
                                    corr_to_be = (
                                        -0.9
                                    )  # the frequency correction is applied with maximum drift for 300 s
                                    one_time_UL = 1
                                    signal.set()
                                    rb_device.send_command(corr_to_be, 0)
                                elif (
                                    initialization.read_count % 100
                                ) == 0:  # Apply correction EVERY 300 seconds (5 minutes)
                                    if initialization.error_UL > 0:
                                        corr_to_be = -0.9
                                        signal.set()
                                        rb_device.send_command(corr_to_be, 0)
                                    elif initialization.error_UL < 0:
                                        corr_to_be = 0.9
                                        signal.set()
                                        rb_device.send_command(corr_to_be, 0)

                            elif (
                                100e-9 < abs(avg_reading) < 1e-6
                            ) and not steering:  # Near to the LOCK condition
                                print("UNLOCK mode: 100 ns to 1 us ")
                                Universal = 1
                                if (initialization.error_UL > 0) & (
                                    Unlock_II == 0
                                ):  # Apply correction immediately once as the reading starts if error > 0
                                    Unlock_II = 1
                                    signal.set()
                                    rb_device.send_command(
                                        -0.05, 0
                                    )  # 700 ns of drift to be compensated in 10 minutes, Not locked yet
                                elif (initialization.error_UL < 0) & (
                                    Unlock_II == 0
                                ):  # Apply correction immediately once as the reading starts if error < 0
                                    Unlock_II = 1
                                    signal.set()
                                    rb_device.send_command(
                                        0.05, 0
                                    )  # 700 ns of drift to be compensated in 10 minutes, Not locked yet
                                if (
                                    initialization.read_count % 30
                                ) == 0:  # Apply correction EVERY 600 seconds (10 minutes)
                                    if initialization.error_UL > 0:
                                        corr_to_be = -0.05
                                        signal.set()
                                        rb_device.send_command(corr_to_be, 0)
                                    elif initialization.error_UL < 0:
                                        corr_to_be = 0.05
                                        signal.set()
                                        rb_device.send_command(corr_to_be, 0)

                            elif (
                                20e-9 < abs(avg_reading) < 100e-9
                            ) and not steering:  # Near to the LOCK condition
                                print("UNLOCK mode: 20 ns to 100 ns ")
                                if (initialization.error_UL > 0) & (
                                    Unlock_I == 0
                                ):  # Apply correction immediately once as the reading starts if error > 0
                                    Unlock_I = 1
                                    signal.set()
                                    rb_device.send_command(
                                        -0.01, 0
                                    )  # 700 ns of drift to be compensated in 10 minutes, Not locked yet
                                elif (initialization.error_UL < 0) & (
                                    Unlock_I == 0
                                ):  # Apply correction immediately once as the reading starts if error < 0
                                    Unlock_I = 1
                                    signal.set()
                                    rb_device.send_command(
                                        0.01, 0
                                    )  # 700 ns of drift to be compensated in 10 minutes, Not locked yet
                                if (
                                    initialization.read_count % 30
                                ) == 0:  # Apply correction EVERY 600 seconds (10 minutes)
                                    if initialization.error_UL > 0:
                                        corr_to_be = -0.01
                                        signal.set()
                                        rb_device.send_command(corr_to_be, 0)
                                    elif initialization.error_UL < 0:
                                        corr_to_be = 0.01
                                        signal.set()
                                        rb_device.send_command(corr_to_be, 0)

                            elif (
                                5e-9 < abs(avg_reading) < 20e-9
                            ) and not steering:  # Near to the LOCK condition
                                print("UNLOCK mode: 3 ns to 20 ns ")
                                if (initialization.error_UL > 0) & (
                                    Unlock_I == 0
                                ):  # Apply correction immediately once as the reading starts if error > 0
                                    Unlock_I = 1
                                    signal.set()
                                    rb_device.send_command(
                                        -0.005, 0
                                    )  # 700 ns of drift to be compensated in 10 minutes, Not locked yet
                                elif (initialization.error_UL < 0) & (
                                    Unlock_I == 0
                                ):  # Apply correction immediately once as the reading starts if error < 0
                                    Unlock_I = 1
                                    signal.set()
                                    rb_device.send_command(
                                        0.005, 0
                                    )  # 700 ns of drift to be compensated in 10 minutes, Not locked yet
                                if (
                                    initialization.read_count % 15
                                ) == 0:  # Apply correction EVERY 600 seconds (10 minutes)
                                    if initialization.error_UL > 0:
                                        corr_to_be = -0.005
                                        signal.set()
                                        rb_device.send_command(corr_to_be, 0)
                                    elif initialization.error_UL < 0:
                                        corr_to_be = 0.005
                                        signal.set()
                                        rb_device.send_command(corr_to_be, 0)

                            elif (
                                (3e-9 < abs(avg_reading) < 5e-9)
                            ) and not steering:  # Initiate LOCK condition
                                print(" Near LOCK mode : 1 ns to 4 ns")
                                if (initialization.error_UL > 0) & (
                                    corr_count_LM == 1
                                ):  # Apply correction immedietly once to slowdown  the drift rate if error >0
                                    Near_Lock_mode = 1
                                    corr_count_LM = 0
                                    Unlock_I = 0
                                    steer_action = 0
                                    signal.set()
                                    # rb_device.send_command(-0.00178, 0)   # 700 ns of drift to be compensated in 10 minutes
                                    rb_device.send_command(-0.003350, 0)
                                    TIC_4_slope.append(float(data1[0]))
                                    if (
                                        len(TIC_4_slope) > 3
                                    ):  # Every latest 3 data points
                                        TIC_4_slope.pop(0)
                                        data_point = list(
                                            range(1, len(TIC_4_slope) + 1)
                                        )
                                        slope, intercept = np.polyfit(
                                            data_point, TIC_4_slope, 1
                                        )  # y = mx + c ; ouput p = [m,c]
                                        # print(f"Slope of the TIC_data (Frequency): {slope}")
                                        prev_slope = slope
                                        if slope < 0:
                                            Ini_slope = -1
                                        else:
                                            Ini_slope = 1

                                elif (initialization.error_UL < 0) & (
                                    corr_count_LM == 1
                                ):  # Apply correction immedietly once to slowdown  the drift rate if error >0
                                    Near_Lock_mode = 1
                                    corr_count_LM = 0
                                    Unlock_I = 0
                                    steer_action = 0
                                    # slow_corr =0  # Repeat Slow correction. Needed if the required correction is not applied correctly
                                    signal.set()
                                    # rb_device.send_command(0.00178, 0)   #  700 ns of drift to be compensated in 10 minutes
                                    rb_device.send_command(0.003350, 0)
                                    TIC_4_slope.append(float(data1[0]))
                                    if (
                                        len(TIC_4_slope) > 3
                                    ):  # Every latest 3 data points
                                        TIC_4_slope.pop(0)
                                        data_point = list(
                                            range(1, len(TIC_4_slope) + 1)
                                        )
                                        slope, intercept = np.polyfit(
                                            data_point, TIC_4_slope, 1
                                        )  # y = mx + c ; ouput p = [m,c]
                                        # print(f"Slope of the TIC_data (Frequency): {slope}")
                                        prev_slope = slope
                                        if slope < 0:
                                            Ini_slope = -1
                                        else:
                                            Ini_slope = 1

                            elif (abs(avg_reading) < 100e-9) and steering:
                                read_count = 0
                                wait_time = 0

                                if steering:
                                    count = count + 1
                                    freq_4_slope.append(float(data1[0]))
                                    if (
                                        len(freq_4_slope) > initialization.steering_int
                                    ):  # Every latest 60 s
                                        freq_4_slope.pop(0)
                                    # if ((count % steering_int ==0) & (len(freq_4_slope)  == steering_int)) :
                                    if count % initialization.steering_int == 0:
                                        data_pointF = list(
                                            range(1, len(freq_4_slope) + 1)
                                        )
                                        slope, intercept = np.polyfit(
                                            data_pointF, freq_4_slope, 1
                                        )  # y = mx + c ; ouput p = [m,c]
                                        print(
                                            f"Slope of the TIC_data (Frequency): {slope}"
                                        )
                                        first_time = 0
                                        Freq_corr = slope * 1e7
                                        phase_corr = (
                                            (0 - float(data1[0])) * 1e7
                                        ) / initialization.phase_time_const
                                        Total_corr = Freq_corr - phase_corr
                                        print(f"Total Correction applied: {Total_corr}")
                                        if abs(Total_corr) > 0.011:  # max limit
                                            if Total_corr > 0:
                                                signal.set()
                                                rb_device.send_command(0.010, 1)
                                                steer_action = 1
                                                print(
                                                    "Freq Correction is more than positive limits & send to Rb"
                                                )
                                            else:  # Total_corr < 0:
                                                signal.set()
                                                rb_device.send_command(-0.010, 1)
                                                steer_action = 1
                                                print(
                                                    "Freq Correction is less than Negitive limits & send to Rb"
                                                )
                                        else:  # Between Max and Min limits
                                            signal.set()
                                            rb_device.send_command(Total_corr, 1)
                                            steer_action = 1
                                            print(
                                                "Freq Correction is in limits & send to Rb"
                                            )

                                        check_error_value = all(
                                            abs(value * 1e9) < 1
                                            for value in freq_4_slope
                                        )  # check is all the errors is less than 1 ns

                                        print(
                                            f"Rb is with in 1 ns wrt NavIC : {check_error_value}"
                                        )

                                        if check_error_value and abs(slope) < (5e-12):
                                            CV_mode = True
                                            Timing_mode = (
                                                False  # Activate the Common view mode
                                            )
                                            TIC_ser.close()
                                            freq_4_slope = (
                                                []
                                            )  # reset the array to continue with the loop
                                            count = 0
                                            error_wrt_navic = float(
                                                data1[0]
                                            )  # Store the value of the TIC error as an intial value
                                            break

                            elif (
                                abs(avg_reading) > 100e-9
                            ) and steering:  # If the TIC  reading is in lock range
                                # Stop steering and apply phase correction
                                steering = False

                            elif abs(avg_reading) < 3e-9:  # Activate the steering algo
                                steering = True
                                print("Steering Activated..................")
                                # if recevr_mode == 1: # Activate PID only in Timing mode
                                # PID_ON =1

                time.sleep(1)  # Adjust sleep time as needed
