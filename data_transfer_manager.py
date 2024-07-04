# data_transfer_manager.py
import os
import requests
import time
import threading
import subprocess
import urllib3

class DataTransferManager:
    def __init__(self, exe_path, ip_address, parent_directory, file_history, source):
        self.exe_path = exe_path
        self.ip_address = ip_address
        self.parent_directory = parent_directory
        self.file_history = file_history
        self.list_url = 'https://bhartiyasamay.in/do/rx/list'  # Replace with the actual URL of your endpoint
        self.item_url = 'https://bhartiyasamay.in/do/rx'  # Replace with the actual URL of your endpoint
        self.source = source
        self.type = "navic"
        self.filter_ext = [".ini", "_log", "_config"]
        self.sent_files = self._get_sent_files()

    def _execute_command(self, command):
        subprocess.run(command, shell=True)
    
    def _trigger_cggtts_ftp_client(self):
        os_thread = threading.Thread(target=self._execute_os_system)
        os_thread.start()

    def _execute_os_system(self):
        os.system(f'{self.exe_path} {self.ip_address} {self.parent_directory}')

    def _upload(self, rx_data_list):
        for rx_data in rx_data_list:
            try:
                response = requests.post(self.item_url, json=rx_data, verify=False)
            except Exception as e:
                msg = f"An error occurred while sending receiver data '{rx_data}': {e}"
                print(msg)

    def _get_sent_files(self):
        if os.path.exists(self.file_history):
            with open(self.file_history, "r") as file:
                return set(file.read().splitlines())
        else:
            return set()

    def _update_sent_files(self):
        with open(self.file_history, "w") as file:
            file.write("\n".join(self.sent_files))

    def _send_file_data_to_endpoint(self, file_path):
        if file_path:
            lines_to_skip = 17  
            with open(file_path, "r") as infile:
                lines = infile.readlines()[lines_to_skip:]
                headings = lines[0].strip().split()
                lines = lines[2:]
                rx_data_list = []
                for i in range(len(lines)):
                    rx_data = {"source": self.source, "type": self.type}
                    columns = lines[i].strip().split()
                    if len(columns) < len(headings):
                        print(f"Error in line {i}: Insufficient columns. Skipping this line.")
                        continue
                    for j in range(len(headings)):
                        rx_data[headings[j]] = columns[j]
                    rx_data_list.append(rx_data)
                self._upload(rx_data_list)

    def _check_filter_ext(self, filename):
        for ext in self.filter_ext:
            if filename.endswith(ext):
                return True

    def _delete_cggtts_config(self):
        cggtts_config_path = os.path.join(self.parent_directory, "cggtts_config.ini")
        if os.path.exists(cggtts_config_path):
            os.remove(cggtts_config_path)
            print("Deleted cggtts_config file.")
        else:
            print("cggtts_config file not found.")

    def start_app(self):
        sent_file_count = 0
        for root, _, files in os.walk(self.parent_directory):
            for filename in files:
                if self._check_filter_ext(filename):
                    continue
                file_path = os.path.join(root, filename)
                if os.path.isfile(file_path) and filename not in self.sent_files:
                    try:
                        sent_file_count += 1
                        self._send_file_data_to_endpoint(file_path)
                        self.sent_files.add(filename)
                        msg = f"Uploaded '{file_path}'"
                        print(msg)
                    except Exception as e:
                        msg = f"An error occurred while sending '{file_path}': {e}"
                        print(msg)
        self._update_sent_files()
        if sent_file_count < 1:
            time.sleep(10)
            msg = "Triggering CGGTTS FTP Client........"
            print(msg)
            self._trigger_cggtts_ftp_client()
            self.start_app()

    def run_data_transfer(self):
        self._delete_cggtts_config()  # Delete cggtts_config before starting the data transfer
        while True:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            msg = "Data Transfer in progress........."
            print(msg)
            self.start_app()  
            time.sleep(300)  # 300 seconds = 5 minutes
