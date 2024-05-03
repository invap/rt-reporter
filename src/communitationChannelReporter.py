import subprocess
import threading
import time
import struct

from src.reportGenStatus import ReporterGenerationStatus


class CommunicationChannelReporter:
    def __init__(self, path, process_name):
        # Load Channel conf
        self.__chn_conf = CommunicationChannelConf()
        # Create a pipe
        self.__channel = subprocess.Popen([process_name], stdout=subprocess.PIPE)
        # Create a new thread to read from the pipe
        self.__process_thread = threading.Thread(target=self.__process_incoming_data, args=())
        # Create a flag to stop and pause the process
        self.__stop_event = threading.Event()
        # Start the thread
        self.__delay = 0
        # Store files path
        self.__output_files_path = path
        # Open and clear the output files
        self.__output_files = {"main": open(process_name + "_log.txt", "w")}
        # Status
        self.__timed_events_count = 0
        self.__state_events_count = 0
        self.__workflow_events_count = 0
        self.__component_events_count = 0
        # create the visualizer
        self.__reportStatus = ReporterGenerationStatus(self, self)
        self.__reportStatus.Show()
        time.sleep(1)
        # Start the thread
        self.__process_thread.start()

    def get_count(self):
        return [self.__timed_events_count, self.__state_events_count, self.__workflow_events_count, self.__component_events_count]

    def set_delay(self, u_time):
        self.__delay = u_time

    def stop(self):
        self.__reportStatus.close()
        # send stop to the thread
        self.__stop_event.set()
        # close the channel
        self.__channel.stdout.close()
        # wait for the thread to end
        self.__process_thread.join(1)
        # kill the subprocess
        self.__channel.terminate()
        # close the output files
        for comp_name in self.__output_files:
            self.__output_files[comp_name].close()

    def __process_incoming_data(self):
        while True:
            # update the own visualizer
            if self.__stop_event.is_set():
                break
            buffer = self.__channel.stdout.read(self.__chn_conf.capacity * self.__chn_conf.max_pkg_size)
            pkgs = [buffer[i:i + self.__chn_conf.max_pkg_size] for i in
                    range(0, len(buffer), self.__chn_conf.max_pkg_size)]
            for pkg in pkgs:
                if self.__stop_event.is_set():
                    break
                # Process the sequence of bytes and dump the information to the file
                unpacked_data = struct.unpack('qi1028s', pkg[0:])  # long8, enum1, data(1024)
                timestamp = unpacked_data[0]
                event_type = unpacked_data[1]
                data_string = str(unpacked_data[2])[2:]
                stripped_data_string = data_string[:1020].strip()
                match event_type:
                    case 0:
                        self.__timed_events_count += 1
                        result = str(timestamp) + "," + "timed_event" + "," + stripped_data_string
                        self.__output_files["main"].write(result + "\n")
                    case 1:
                        self.__state_events_count += 1
                        result = str(timestamp) + "," + "state_event" + "," + stripped_data_string
                        self.__output_files["main"].write(result + "\n")
                    case 2:
                        self.__workflow_events_count += 1
                        result = str(timestamp) + "," + "workflow_event" + "," + stripped_data_string
                        self.__output_files["main"].write(result + "\n")
                    case 3:
                        self.__component_events_count += 1
                        result = str(timestamp) + "," + "component_event" + "," + stripped_data_string
                        self.__output_files["main"].write(result + "\n")
                    case 4:
                        # "init_event"
                        self.__output_files[stripped_data_string] = open(self.__output_files_path+"/"+stripped_data_string+"_log.txt", "w")
                    case 5:
                        self.__component_events_count += 1
                        decoded_data_string = stripped_data_string.split(",", 1)
                        comp_name = decoded_data_string[0]
                        result = str(timestamp) + "," + decoded_data_string[1]
                        self.__output_files[comp_name].write(result + "\n")
                    case _:
                        event_type_name = "invalid"
                        result = str(timestamp) + "," + str(event_type_name) + "," + stripped_data_string
                        self.__output_files["main"].write(result + "\n")
                time.sleep(1 / 100000)


class CommunicationChannelConf:
    """
    Information about how the sender packs the data in the channel
    """

    def __init__(self):
        """64K(os default) max string length to call (from the code) a test action (to be executed by the simulator)"""
        self.buffer_size = 65536
        # 8 (time long) + 4 (enum timed, state, workflow or component) + (1025  | 1025 ) (both have data field with 1024)
        self.max_pkg_size = 1040
        self.capacity = int(self.buffer_size / self.max_pkg_size)
