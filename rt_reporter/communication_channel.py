# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import subprocess
import threading
import time
import struct

import pika

from rt_reporter.communication_channel_conf import CommunicationChannelConf


class CommunicationChannel(threading.Thread):
    def __init__(self, process_name, host_addr, host_port, timeout):
        super().__init__()
        # Event for controlling the execution of the monitor (TBS by set_event)
        self._stop_event = None
        # Store process name and RabbitMQ server
        self._process_name = process_name
        self._host_addr = host_addr
        self._host_port = host_port
        # Reporting time
        self._timeout = timeout
        # Open and clear the main log file
        self._event_logs_map = {}
        time.sleep(1)

    def set_event(self, stop_event):
        self._stop_event = stop_event

    def run(self):
        start_time_epoch = time.time()
        # Create a channel to communicate with the sut and starts a subprocess.
        channel_conf = CommunicationChannelConf()
        channel = subprocess.Popen([self._process_name], stdout=subprocess.PIPE)
        # Connection parameters with CLI arguments
        credentials = pika.PlainCredentials('guest', 'guest')
        parameters = pika.ConnectionParameters(
            host=self._host_addr,
            port=self._host_port,
            credentials=credentials
        )
        # Creat the RabbitMQ connection channel
        connection = pika.BlockingConnection(parameters)
        rabbitmq_channel = connection.channel()
        # Declare exchange for the RabbitMQ connection channel
        rabbitmq_channel.exchange_declare(exchange='broadcast', exchange_type='fanout')
        while True:
            # Thread control.
            if (self._stop_event.is_set() or
                    (self._timeout != 0 and time.time() - start_time_epoch >= self._timeout)):
                break
            buffer = channel.stdout.read(channel_conf.capacity * channel_conf.max_pkg_size)
            # Process packages from communication channel.
            pkgs = [
                buffer[i: i + channel_conf.max_pkg_size]
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
                        result = (str(timestamp) + "," + "timed_event" + "," + stripped_data_string + "\n")
                    case 1:
                        result = (str(timestamp) + "," + "state_event" + "," + stripped_data_string + "\n")
                    case 2:
                        result = (str(timestamp) + "," + "process_event" + "," + stripped_data_string + "\n")
                    case 3:
                        result = (str(timestamp) + "," + "component_event" + "," + stripped_data_string + "\n")
                    case 4:
                        # This case captures the EndOfReportEvent so there is nothing to write.
                        result = None
                    case _:
                        result = (str(timestamp) + "," + "invalid" + "," + stripped_data_string + "\n")
                if result is not None:
                    rabbitmq_channel.basic_publish(
                        exchange='broadcast',
                        routing_key='',
                        body=result
                    )
                time.sleep(1 / 100000)
        # Close the channel and terminates the subprocess.
        channel.terminate()
        channel.stdout.close()
        # Close the RabbitMQ connection.
        connection.close()
