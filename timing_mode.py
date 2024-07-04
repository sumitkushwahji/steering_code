import asyncio
import serial
import time
import csv
from datetime import datetime


# Receiver Configuration
receiver = Receiver(host="172.16.26.42", port=2001, username="ngsc60admin", password="NgsAdmin@C60")
asyncio.run(receiver.configure_receiver("SET MOS TIMING"))



# Open the TIC serial port
time.sleep(1)
TIC_ser = serial.Serial(port="COM12", baudrate=115200)
print("TIC Comport is open: ", TIC_ser.isOpen())

if not TIC_ser.isOpen():
    print("TIC Comport is not open")
    # TIC_ser.open()
    # print('COM5 is open', TIC_ser.isOpen())
else:
    latest_readings = []
    TIC_4_slope = []

    error_record = []
    Current_DO_file = None
    Current_Ref_file = None
    # Wait for some time till the header files of the TIC lapsed & GNSS position fix is done for the receiver
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

                    # If latest readings list has more than 5 entries, remove the oldest one
                    if len(latest_readings) > 3:
                        latest_readings.pop(0)

                    avg_reading = 0
                    # Calculate and print the avervaluesprocess_CVage of the latest 3 readings
                    if latest_readings:
                        avg_reading = sum(latest_readings) / len(latest_readings)
                        read_count = read_count + 1
                        print(
                            f"Latest 3 readings average value in ns : {avg_reading*1E+9}"
                        )
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

                        if abs(avg_reading) > 1e-6:  # UN LOCK condition
                            print("UNLOCK mode: More than 1 us")
                            Universal = 1
                            lock_flag = 0  # 0 means not locked yet
                            if (error_UL < 0) & (
                                one_time_UL == 0
                            ):  # Apply correction immedietly once as the reading starts if error <0
                                corr_to_be = 0.9  # the frequency corretion is applied with maximum drift for 300 s
                                one_time_UL = 1
                                steer_action = 0
                                signal.set()
                                send_cmd_Rb(corr_to_be, 0)

                            elif (error_UL > 0) & (
                                one_time_UL == 0
                            ):  # Apply correction immedietly once as the reading starts if error >0
                                corr_to_be = (
                                    -0.9
                                )  # the frequency corretion is applied with maximum drift for 300 s
                                one_time_UL = 1
                                steer_action = 0
                                signal.set()
                                send_cmd_Rb(corr_to_be, 0)

                            elif (
                                read_count % 100
                            ) == 0:  # Apply correction EVERY 300 seconds (5 minutes)
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

                        elif (
                            100e-9 < abs(avg_reading) < 1e-6
                        ) and not steering:  # Near to the LOCK condition
                            print("UNLOCK mode: 100 ns to 1 us ")
                            Universal = 1
                            if (error_UL > 0) & (
                                Unlock_II == 0
                            ):  # Apply correction immedietly once as the reading starts if error >0
                                Unlock_II = 1
                                steer_action = 0
                                signal.set()
                                send_cmd_Rb(
                                    -0.05, 0
                                )  # 700 ns of drift to be compensated in 10 minutes, NOt locked yet

                            elif (error_UL < 0) & (
                                Unlock_II == 0
                            ):  # Apply correction immedietly once as the reading starts if error <0
                                Unlock_II = 1
                                steer_action = 0
                                signal.set()
                                send_cmd_Rb(
                                    0.05, 0
                                )  #  700 ns of drift to be compensated in 10 minutes, NOt locked yet

                            if (
                                read_count % 30
                            ) == 0:  # Apply correction EVERY 600 seconds (10 minutes)
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

                        elif (
                            20e-9 < abs(avg_reading) < 100e-9
                        ) and not steering:  # Near to the LOCK condition

                            print("UNLOCK mode: 20 ns to 100 ns ")
                            if (error_UL > 0) & (
                                Unlock_I == 0
                            ):  # Apply correction immedietly once as the reading starts if error >0
                                Unlock_I = 1
                                steer_action = 0
                                signal.set()
                                send_cmd_Rb(
                                    -0.01, 0
                                )  # 700 ns of drift to be compensated in 10 minutes, NOt locked yet

                            elif (error_UL < 0) & (
                                Unlock_I == 0
                            ):  # Apply correction immedietly once as the reading starts if error <0
                                Unlock_I = 1
                                steer_action = 0
                                signal.set()
                                send_cmd_Rb(
                                    0.01, 0
                                )  #  700 ns of drift to be compensated in 10 minutes, NOt locked yet

                            if (
                                read_count % 30
                            ) == 0:  # Apply correction EVERY 600 seconds (10 minutes)
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

                        elif (
                            5e-9 < abs(avg_reading) < 20e-9
                        ) and not steering:  # Near to the LOCK condition
                            print("UNLOCK mode: 3 ns to 20 ns ")
                            if (error_UL > 0) & (
                                Unlock_I == 0
                            ):  # Apply correction immedietly once as the reading starts if error >0
                                Unlock_I = 1
                                steer_action = 0
                                signal.set()
                                send_cmd_Rb(
                                    -0.005, 0
                                )  # 700 ns of drift to be compensated in 10 minutes, NOt locked yet

                            elif (error_UL < 0) & (
                                Unlock_I == 0
                            ):  # Apply correction immedietly once as the reading starts if error <0
                                Unlock_I = 1
                                steer_action = 0
                                signal.set()
                                send_cmd_Rb(
                                    0.005, 0
                                )  #  700 ns of drift to be compensated in 10 minutes, NOt locked yet

                            if (
                                read_count % 15
                            ) == 0:  # Apply correction EVERY 600 seconds (10 minutes)
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

                        elif (
                            (3e-9 < abs(avg_reading) < 5e-9)
                        ) and not steering:  # Initiate LOCK condition
                            print(" Near LOCK mode : 1 ns to 4 ns")
                            if (error_UL > 0) & (
                                corr_count_LM == 1
                            ):  # Apply correction immedietly once to slowdown  the drift rate if error >0
                                Near_Lock_mode = 1
                                corr_count_LM = 0
                                Unlock_I = 0
                                steer_action = 0
                                signal.set()
                                # send_cmd_Rb(-0.00178, 0)   # 700 ns of drift to be compensated in 10 minutes
                                send_cmd_Rb(-0.003350, 0)
                                TIC_4_slope.append(float(data1[0]))
                                if len(TIC_4_slope) > 3:  # Every latest 3 data points
                                    TIC_4_slope.pop(0)
                                    data_point = list(range(1, len(TIC_4_slope) + 1))
                                    slope, intercept = np.polyfit(
                                        data_point, TIC_4_slope, 1
                                    )  # y = mx + c ; ouput p = [m,c]
                                    # print(f"Slope of the TIC_data (Frequency): {slope}")
                                    prev_slope = slope
                                    if slope < 0:
                                        Ini_slope = -1
                                    else:
                                        Ini_slope = 1

                            elif (error_UL < 0) & (
                                corr_count_LM == 1
                            ):  # Apply correction immedietly once to slowdown  the drift rate if error >0
                                Near_Lock_mode = 1
                                corr_count_LM = 0
                                Unlock_I = 0
                                steer_action = 0
                                # slow_corr =0  # Repeat Slow correction. Needed if the required correction is not applied correctly
                                signal.set()
                                # send_cmd_Rb(0.00178, 0)   #  700 ns of drift to be compensated in 10 minutes
                                send_cmd_Rb(0.003350, 0)
                                TIC_4_slope.append(float(data1[0]))
                                if len(TIC_4_slope) > 3:  # Every latest 3 data points
                                    TIC_4_slope.pop(0)
                                    data_point = list(range(1, len(TIC_4_slope) + 1))
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
                                    len(freq_4_slope) > steering_int
                                ):  # Every latest 60 s
                                    freq_4_slope.pop(0)
                                # if ((count % steering_int ==0) & (len(freq_4_slope)  == steering_int)) :
                                if count % steering_int == 0:
                                    data_pointF = list(range(1, len(freq_4_slope) + 1))
                                    slope, intercept = np.polyfit(
                                        data_pointF, freq_4_slope, 1
                                    )  # y = mx + c ; ouput p = [m,c]
                                    print(f"Slope of the TIC_data (Frequency): {slope}")
                                    first_time = 0
                                    Freq_corr = slope * 1e7
                                    phase_corr = (
                                        (0 - float(data1[0])) * 1e7
                                    ) / phase_time_const
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
                                    if abs(Total_corr) > 0.011:  # max limit
                                        if Total_corr > 0:
                                            signal.set()
                                            send_cmd_Rb(0.010, 1)
                                            steer_action = 1
                                            print(
                                                "Freq Correction is more than positive limits & send to Rb"
                                            )
                                        else:  # Total_corr < 0:
                                            signal.set()
                                            send_cmd_Rb(-0.010, 1)
                                            steer_action = 1
                                            print(
                                                "Freq Correction is less than Negitive limits & send to Rb"
                                            )
                                    else:  # Between Max and Min limits
                                        signal.set()
                                        send_cmd_Rb(Total_corr, 1)
                                        steer_action = 1
                                        print(
                                            "Freq Correction is in limits & send to Rb"
                                        )

                                    check_error_value = all(
                                        abs(value * 1e9) < 1 for value in freq_4_slope
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

                    # PID_ON = PID_value # Update the PID status

        time.sleep(1)
