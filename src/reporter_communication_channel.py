# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import subprocess
import threading
import time
import struct

from src.communication_channel_conf import CommunicationChannelConf


class ReporterCommunicationChannel(threading.Thread):
    def __init__(self, files_path, process_name):
        super().__init__()
        # Event for controlling the execution of the monitor (TBS by set_event)
        self._stop_event = None
        # Store files path and process name
        self._files_path = files_path
        self._process_name = process_name
        # Open and clear the main log file
        self._event_logs_map = {}
        # Status
        self._timed_events_count = 0
        self._state_events_count = 0
        self._process_events_count = 0
        self._component_events_count = 0
        time.sleep(1)

    def set_event(self, stop_event):
        self._stop_event = stop_event

    def get_count(self):
        return [
            self._timed_events_count,
            self._state_events_count,
            self._process_events_count,
            self._component_events_count,
        ]

    def run(self):
        event_logs_map = {}
        # Create a channel and starts a subprocess.
        channel_conf = CommunicationChannelConf()
        channel = subprocess.Popen([self._process_name], stdout=subprocess.PIPE)
        event_logs_map["main"] = open(self._process_name + "_log.csv", "w")
        while True:
            # Thread control.
            if self._stop_event.is_set():
                break
            buffer = channel.stdout.read(
                channel_conf.capacity * channel_conf.max_pkg_size
            )
            # Process packages from communication channel.
            pkgs = [
                buffer[i : i + channel_conf.max_pkg_size]
                for i in range(0, len(buffer), channel_conf.max_pkg_size)
            ]
            for pkg in pkgs:
                if self._stop_event.is_set():
                    break
                # Process the sequence of bytes and dump the information to the file
                unpacked_data = struct.unpack(
                    "qi1028s", pkg[0:]
                )  # long8, enum1, data(1024)
                timestamp = unpacked_data[0]
                event_type = unpacked_data[1]
                data_string = str(unpacked_data[2])[2:]
                stripped_data_string = data_string[:1020].strip()
                match event_type:
                    case 0:
                        self._timed_events_count += 1
                        result = (
                            str(timestamp)
                            + ","
                            + "timed_event"
                            + ","
                            + stripped_data_string
                        )
                        event_logs_map["main"].write(result + "\n")
                    case 1:
                        self._state_events_count += 1
                        result = (
                            str(timestamp)
                            + ","
                            + "state_event"
                            + ","
                            + stripped_data_string
                        )
                        event_logs_map["main"].write(result + "\n")
                    case 2:
                        self._process_events_count += 1
                        result = (
                            str(timestamp)
                            + ","
                            + "process_event"
                            + ","
                            + stripped_data_string
                        )
                        event_logs_map["main"].write(result + "\n")
                    case 3:
                        self._component_events_count += 1
                        result = (
                            str(timestamp)
                            + ","
                            + "component_event"
                            + ","
                            + stripped_data_string
                        )
                        event_logs_map["main"].write(result + "\n")
                    case 4:
                        # "self-loggable component log_init_event"
                        event_logs_map[stripped_data_string] = open(
                            self._files_path + "/" + stripped_data_string + "_log.csv",
                            "w",
                        )
                    case 5:
                        self._component_events_count += 1
                        decoded_data_string = stripped_data_string.split(",", 1)
                        comp_name = decoded_data_string[0]
                        result = str(timestamp) + "," + decoded_data_string[1]
                        event_logs_map[comp_name].write(result + "\n")
                    case _:
                        event_type_name = "invalid"
                        result = (
                            str(timestamp)
                            + ","
                            + str(event_type_name)
                            + ","
                            + stripped_data_string
                        )
                        event_logs_map["main"].write(result + "\n")
                time.sleep(1 / 100000)
        # Close the channel and terminates the subprocess.
        channel.stdout.close()
        channel.terminate()
        # close the output files
        for comp_name in event_logs_map:
            event_logs_map[comp_name].close()
