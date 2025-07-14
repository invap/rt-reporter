# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import subprocess
import threading
import time
import struct

from rt_reporter.communication_channel_conf import CommunicationChannelConf


class CommunicationChannel(threading.Thread):
    def __init__(self, output_file, process_name, timeout):
        super().__init__()
        # Event for controlling the execution of the monitor (TBS by set_event)
        self._stop_event = None
        # Store files path and process name
        self._process_name = process_name
        self._output_file = output_file
        # Reporting time
        self._timeout = timeout
        time.sleep(1)

    def set_event(self, stop_event):
        self._stop_event = stop_event

    def run(self):
        event_logs_map = {}
        start_time_epoch = time.time()
        # Create a channel and starts a subprocess.
        channel_conf = CommunicationChannelConf()
        channel = subprocess.Popen([self._process_name], stdout=subprocess.PIPE)
        output_file = open(self._output_file, "w")
        while True:
            # Thread control.
            if (self._stop_event.is_set() or
                    (self._timeout != 0 and time.time()-start_time_epoch >= self._timeout)):
                break
            buffer = channel.stdout.read(channel_conf.capacity * channel_conf.max_pkg_size)
            # Process packages from communication channel.
            pkgs = [
                buffer[i : i + channel_conf.max_pkg_size]
                for i in range(0, len(buffer), channel_conf.max_pkg_size)
            ]
            for pkg in pkgs:
                # Process the sequence of bytes and dump the information to the file
                # unsigned long long: 8, unsigned long: 4, string: 1012
                unpacked_data = struct.unpack("QI1012s", pkg[0:])
                timestamp = unpacked_data[0]
                event_type = unpacked_data[1]
                data_string = str(unpacked_data[2])[2:]
                stripped_data_string = data_string[:1010].strip()
                match event_type:
                    case 0:
                        result = (str(timestamp)+","+"timed_event"+","+stripped_data_string)
                        output_file.write(result + "\n")
                    case 1:
                        result = (str(timestamp)+","+"state_event"+","+stripped_data_string)
                        output_file.write(result + "\n")
                    case 2:
                        result = (str(timestamp)+","+"process_event"+","+stripped_data_string)
                        output_file.write(result + "\n")
                    case 3:
                        result = (str(timestamp)+","+"component_event"+","+stripped_data_string)
                        output_file.write(result + "\n")
                    case 6:
                        # This case captures the EndOfReportEvent so there is nothing to write.
                        pass
                    case _:
                        event_type_name = "invalid"
                        result = (str(timestamp)+","+str(event_type_name)+","+stripped_data_string)
                        output_file.write(result + "\n")
                time.sleep(1 / 100000)
        # Close the channel and terminates the subprocess.
        channel.terminate()
        channel.stdout.close()
        # close the output files
        output_file.close()
