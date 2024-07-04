import serial
import time

class SerialCommunication:
    def __init__(self, port, baudrate):
        self.ser = serial.Serial(port=port, baudrate=baudrate, bytesize=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE, timeout=1)

    def open(self):
        if not self.ser.isOpen():
            self.ser.open()
        print(f"Port {self.ser.port} is open: {self.ser.isOpen()}")

    def close(self):
        if self.ser.isOpen():
            self.ser.close()

    def write(self, data):
        try:
            self.ser.write(data)
        except serial.serialutil.PortNotOpenError as e:
            print(f"Port not open error: {e}")
            try:
                self.ser.open()
                self.ser.write(data)
            except serial.serialutil.SerialException as n:
                print(f"Port could not open error: {n}")
                return False
        except serial.serialutil.SerialException as e:
            print(f"Serial error: {e}")
            return False
        time.sleep(0.1)
        return True

    def read(self, size=1):
        return self.ser.read(size)

    def readline(self):
        return self.ser.readline()

    def flush_input(self):
        self.ser.flushInput()

    def is_open(self):
        return self.ser.isOpen()
