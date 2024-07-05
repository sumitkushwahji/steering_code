from serial_communication import SerialCommunication

# Initialize Serial Communication globally
serial_comm = SerialCommunication(port="COM5", baudrate=9600)
serial_comm.open()
