# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import json
import struct
import subprocess
import threading
import signal
import time
import pika
import logging
# Create a logger for the reporter component
logger = logging.getLogger(__name__)

from rt_reporter.errors.reporter_errors import ReporterError
from rt_reporter import rabbitmq_server_connections
from rt_reporter.config import config
from rt_reporter.communication_channel_conf import CommunicationChannelConf

from rt_rabbitmq_wrapper.exchange_types.event.event_dict_codec import EventDictCoDec
from rt_rabbitmq_wrapper.exchange_types.event.event_csv_codec import EventCSVCoDec
from rt_rabbitmq_wrapper.exchange_types.event.event_codec_errors import (
    EventCSVError,
    EventTypeError
)
from rt_rabbitmq_wrapper.rabbitmq_utility import RabbitMQError


def rt_reporter_runner(sut_file):
    # Signal handling flags
    signal_flags = {'stop': False, 'pause': False}

    # Signal handling functions
    def sigint_handler(signum, frame):
        signal_flags['stop'] = True

    def sigtstp_handler(signum, frame):
        signal_flags['pause'] = not signal_flags['pause']  # Toggle pause state

    # Registering signal handlers
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTSTP, sigtstp_handler)

    # Create reporter
    reporter = Reporter(sut_file, signal_flags)

    def _run_reporting():
        # Starts the monitor thread
        reporter.start()
        # Waiting for the verification process to finish, either naturally or manually.
        reporter.join()

    # Creates the application thread for controlling the monitor
    application_thread = threading.Thread(target=_run_reporting, daemon=True)
    # Runs the application thread
    application_thread.start()
    # Waiting for the application thread to finish
    application_thread.join()


class Reporter(threading.Thread):
    def __init__(self, sut, signal_flags):
        super().__init__()
        # Create a channel to communicate with the sut and starts a subprocess.
        self._channel_conf = CommunicationChannelConf()
        self._sut_pipe_channel = subprocess.Popen([sut], stdout=subprocess.PIPE)
        # Signaling flags
        self._signal_flags = signal_flags

    def run(self):
        # Start receiving events from the RabbitMQ server
        logger.info(f"Start sending events to exchange {rabbitmq_server_connections.rabbitmq_event_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.port}.")
        # Start event acquisition from the sut
        start_time_epoch = time.time()
        number_of_events = 0
        # Control variables
        stop = False
        timeout = False
        while not timeout and not stop:
            # Handle SIGINT
            if self._signal_flags['stop']:
                logger.info("SIGINT received. Stopping the event acquisition process.")
                stop = True
            # Handle SIGTSTP
            if self._signal_flags['pause']:
                logger.info("SIGTSTP received. Pausing the event acquisition process.")
                while self._signal_flags['pause'] and not self._signal_flags['stop']:
                    time.sleep(1)  # Efficiently wait for signals
                if self._signal_flags['stop']:
                    logger.info("SIGINT received. Stopping the event acquisition process.")
                    stop = True
                if not self._signal_flags['pause']:
                    logger.info("SIGTSTP received. Resuming the event acquisition process.")
            # Timeout handling for event acquisition.
            if config.timeout != 0 and time.time() - start_time_epoch >= config.timeout:
                timeout = True
            # Process packages from communication channel.
            buffer = self._sut_pipe_channel.stdout.read(self._channel_conf.capacity * self._channel_conf.max_pkg_size)
            pkgs = [
                buffer[i: i + self._channel_conf.max_pkg_size]
                for i in range(0, len(buffer), self._channel_conf.max_pkg_size)
            ]
            for pkg in pkgs:
                # unsigned long long: 8, unsigned long: 4, string: 1012
                unpacked_data = struct.unpack("QI1012s", pkg[0:])
                timestamp = unpacked_data[0]
                event_type = unpacked_data[1]
                data_string = str(unpacked_data[2])[2:]
                stripped_data_string = data_string[:1010].strip()
                match event_type:
                    case 0:
                        event_csv = (str(timestamp) + "," + "timed_event" + "," + stripped_data_string)
                    case 1:
                        event_csv = (str(timestamp) + "," + "state_event" + "," + stripped_data_string)
                    case 2:
                        event_csv = (str(timestamp) + "," + "process_event" + "," + stripped_data_string)
                    case 3:
                        event_csv = (str(timestamp) + "," + "component_event" + "," + stripped_data_string)
                    case 4:
                        # This case captures the EndOfReportEvent so there is nothing to write.
                        event_csv = None
                    case _:
                        event_csv = (str(timestamp) + "," + "invalid" + "," + stripped_data_string)
                if event_csv is not None:
                    try:
                        event = EventCSVCoDec.from_csv(event_csv)
                    except EventCSVError:
                        logger.info(f"Error parsing event csv: [ {event_csv} ].")
                        raise ReporterError()
                    try:
                        event_dict = EventDictCoDec.to_dict(event)
                    except EventTypeError:
                        logger.info(f"Error building dictionary from event: [ {event} ].")
                        raise ReporterError()
                    try:
                        rabbitmq_server_connections.rabbitmq_event_server_connection.publish_message(
                            json.dumps(event_dict, indent=4),
                            pika.BasicProperties(
                                delivery_mode=2,  # Persistent message
                            )
                        )
                    except RabbitMQError:
                        logger.info(f"Error sending event to the exchange {rabbitmq_server_connections.rabbitmq_event_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.port}.")
                        raise ReporterError()
                    # Log event send
                    logger.debug(f"Sent event: {event_dict}.")
                    # Only increment number_of_events is it is a valid event
                    number_of_events += 1
                    time.sleep(1 / 100000)
        # Send poison pill with the events routing_key to the RabbitMQ server
        try:
            rabbitmq_server_connections.rabbitmq_event_server_connection.publish_message(
                '',
                pika.BasicProperties(
                    delivery_mode=2,
                    headers={'termination': True}
                )
            )
        except RabbitMQError:
            logger.critical(f"Error sending poison pill to the exchange {rabbitmq_server_connections.rabbitmq_event_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.port}.")
            raise ReporterError()
        else:
            logger.info(f"Poison pill sent to the exchange {rabbitmq_server_connections.rabbitmq_event_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.port}.")
        # Stop publishing events to the RabbitMQ server
        logger.info(f"Stop sending events to the exchange {rabbitmq_server_connections.rabbitmq_event_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.port}.")
        # Logging the reason for stoping the verification process to the RabbitMQ server
        if timeout:
            logger.info(f"Events acquired: {number_of_events} - Time (secs.): {time.time() - start_time_epoch:.3f} - Process COMPLETED, timeout reached.")
        elif stop:
            logger.info(f"Events acquired: {number_of_events} - Time (secs.): {time.time() - start_time_epoch:.3f} - Process STOPPED, SIGINT received.")
        else:
            logger.info(f"Events acquired: {number_of_events} - Time (secs.): {time.time() - start_time_epoch:.3f} - Process STOPPED, unknown reason.")
