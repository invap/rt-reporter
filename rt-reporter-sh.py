# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial
import struct
import subprocess
import sys
import threading
import time

from src.communication_channel_conf import CommunicationChannelConf

# Status
timed_events_count = 0
state_events_count = 0
process_events_count = 0
component_events_count = 0
# Sets up the delay
delay = 0
# Store files path
files_path = str()
# Declares event log files ductionary
event_logs_map = {}
# Channel configuration
chn_conf = CommunicationChannelConf()
# Communication channel
channel = None


def __process_incoming_data():
    # Declare the use of global variables
    global timed_events_count
    global state_events_count
    global process_events_count
    global component_events_count
    global delay
    global output_files_path
    global event_logs_map
    global chn_conf
    global channel
    # Data acquisition
    while True:
        buffer = channel.stdout.read(chn_conf.capacity * chn_conf.max_pkg_size)
        pkgs = [buffer[i:i + chn_conf.max_pkg_size] for i in
                range(0, len(buffer), chn_conf.max_pkg_size)]
        for pkg in pkgs:
            # Process the sequence of bytes and dump the information to the file
            unpacked_data = struct.unpack('qi1028s', pkg[0:])  # long8, enum1, data(1024)
            timestamp = unpacked_data[0]
            event_type = unpacked_data[1]
            data_string = str(unpacked_data[2])[2:]
            stripped_data_string = data_string[:1020].strip()
            match event_type:
                case 0:
                    timed_events_count += 1
                    result = str(timestamp) + "," + "timed_event" + "," + stripped_data_string
                    event_logs_map["main"].write(result + "\n")
                case 1:
                    state_events_count += 1
                    result = str(timestamp) + "," + "state_event" + "," + stripped_data_string
                    event_logs_map["main"].write(result + "\n")
                case 2:
                    process_events_count += 1
                    result = str(timestamp) + "," + "process_event" + "," + stripped_data_string
                    event_logs_map["main"].write(result + "\n")
                case 3:
                    component_events_count += 1
                    result = str(timestamp) + "," + "component_event" + "," + stripped_data_string
                    event_logs_map["main"].write(result + "\n")
                case 4:
                    # "self-loggable component log_init_event"
                    event_logs_map[stripped_data_string] = open(
                        files_path + "/" + stripped_data_string + "_log.csv", "w")
                case 5:
                    component_events_count += 1
                    decoded_data_string = stripped_data_string.split(",", 1)
                    comp_name = decoded_data_string[0]
                    result = str(timestamp) + "," + decoded_data_string[1]
                    event_logs_map[comp_name].write(result + "\n")
                case _:
                    event_type_name = "invalid"
                    result = str(timestamp) + "," + str(event_type_name) + "," + stripped_data_string
                    event_logs_map["main"].write(result + "\n")
            time.sleep(1 / 100000)


def main():
    # Building argument map
    if len(sys.argv) < 2:
        print("Erroneous number of arguments.", file=sys.stderr)
        exit(-1)
    try:
        open(sys.argv[1], "r")
    except FileNotFoundError:
        print("File not found.", file=sys.stderr)
        exit(-2)
    # Declare the use of global variables
    global timed_events_count
    global state_events_count
    global process_events_count
    global component_events_count
    global delay
    global files_path
    global event_logs_map
    global chn_conf
    global channel
    # Store files path
    decoded_choice = sys.argv[1].rsplit("/", 1)
    files_path = decoded_choice[0]
    file_name = decoded_choice[1]
    # Open and clear the output the main event log file
    event_logs_map["main"] = open(files_path + "/" + file_name + "_log.csv", "w")
    # Create a pipe and stores it globally
    channel = subprocess.Popen([files_path + "/" + file_name], stdout=subprocess.PIPE)
    # Create a new thread to read from the pipe
    process_thread = threading.Thread(target=__process_incoming_data, args=())
    # Start the thread
    process_thread.start()


if __name__ == '__main__':
    main()
