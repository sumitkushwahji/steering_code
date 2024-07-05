# rb_device.py



import struct
import math
from datetime import datetime
from utilities import compute_checksum
import csv
import initialization


initialization.initialize_globals

class RbDevice:
    def __init__(self, serial_comm):
        self.serial_comm = serial_comm

    def read_current(self):
        read_ram = "2D 04 00 29"
        print("Reading the current shift from Rb")

        if not self.serial_comm.write(bytes.fromhex(read_ram)):
            return None, None, None, None

        data_read = self.serial_comm.read(9)
        if len(data_read) != 9:
            print(f"Warning: Received {len(data_read)} bytes, expected 9.")
            return None, None, None, None

        current_value_bytes = data_read[4:8]
        current_value = int.from_bytes(current_value_bytes, byteorder='big', signed=True)
        curr_in_hz = current_value * 3.725 * 1E-9
        # print("Current shift in Hz:", curr_in_Hz)
        check_sum_match = 1
        # Checksum validation (optional, but recommended)


        received_checksum = data_read[8]
        calculated_checksum = compute_checksum(data_read[4:8].hex())
        calculated_checksum_int = int(calculated_checksum, 16)

        if received_checksum != calculated_checksum_int:
            print(f"Checksum mismatch: received {received_checksum}, calculated {calculated_checksum_int}")
            check_sum_match = 0
            return None

        self.serial_comm.flush_input()

        return curr_in_hz, current_value, current_value_bytes.hex(), check_sum_match

    def send_cmd_Rb(self, apply_corr, lock_flag):
        initialization.signal.wait()
        
        if lock_flag == 0:
            new_shift = apply_corr
        else:
            curr_value, hex_before, bytes_before, matching_check_sum = self.read_current()
            new_shift = apply_corr + curr_value

        if math.isnan(new_shift):
            print("Error: New_shift is NaN. Cannot proceed with the operation.")
            initialization.signal.clear()
            return

        try:
            shift_in_device_units = round(new_shift / 3.725 * 1E9)
        except ValueError as e:
            print(f"ValueError occurred: {e}")
            initialization.signal.clear()
            return

        shift_in_device_units_clamped = max(min(shift_in_device_units, 2147483647), -2147483648)
        shift_bytes = shift_in_device_units_clamped.to_bytes(4, byteorder='big', signed=True)
        shift_hex = shift_bytes.hex()
        cmnd = "2e 09 00 27 " + " ".join(shift_hex[i:i+2] for i in range(0, len(shift_hex), 2)) + compute_checksum(shift_hex).replace("0x", "")

        if not self.serial_comm.write(bytes.fromhex(cmnd)):
            return

        print("Command Sent")

        if lock_flag == 1:
            curr_new_value, hex_after, bytes_after, matching_check_sum = self.read_current()
            Correction_info = {
                'Time stamp': datetime.now(), 'Before_correction': curr_value, 'After_correction': curr_new_value,
                'Hex_before': hex_before, 'Bytes_before': bytes_before, 'Bytes_applied': shift_bytes.hex(),
                'Hex_applied': shift_hex, 'Hex_after': hex_after, 'Bytes_after': bytes_after, 'Check_sum_match': matching_check_sum
            }
            with open('Rb_Corrections.csv', 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=Correction_info.keys())
                writer.writerow(Correction_info)

        initialization.signal.clear()
