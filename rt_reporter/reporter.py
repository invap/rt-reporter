# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import json
import struct
import subprocess
import threading
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
    EventTypeError,
)
from rt_rabbitmq_wrapper.rabbitmq_utility import RabbitMQError


class Reporter(threading.Thread):
    def __init__(self, sut, sut_args, signal_flags):
        super().__init__()
        # Create a channel to communicate with the sut and starts a subprocess.
        self._channel_conf = CommunicationChannelConf()
        self._sut_pipe_channel = subprocess.Popen([sut] + sut_args, stdout=subprocess.PIPE)
        # Signaling flags
        self._signal_flags = signal_flags

    # Raises: ReporterError
    def run(self):
        # Initialize start_time_epoch for testing timeout for events acquisition from the SUT. Also initialize number_of_events 
        # for logging the number of events processed during the event acquisition.
        start_time_epoch = time.time()
        number_of_events = 0
        # Initialize control flags for managing the monitoring process (i.e., stopping the monitoring process when a poison pill is received 
        # from the RabbitMQ server, when a SIGINT signal is received, when a verdict message is received from the RabbitMQ server that according 
        # to the stop policy should stop the monitoring process, or when the time elapsed since the reception of the last message exceeds the 
        # timeout specified in the configuration). The control dictionary has a method should_stop() that returns True if any of the flags 
        # poison_received, signal_stop, verdict_stop or timeout_stop is set to True, and False otherwise; this method is used for managing the 
        # execution of the monitoring process and its threads.
        control = {
            "signal_stop": False,
            "timeout_stop": False,
            # The monitoring process should stop if any of the flags poison_received, signal_stop, verdict_stop or timeout_stop is set to True.
            "should_stop": lambda:control["signal_stop"] or control["timeout_stop"]
        }

        # Signal handler thread infrastructure, which updates the control dictionary with the signal_stop flag if a SIGINT is received 
        # and with the pause flag if a SIGTSTP is received. The thread runs until the monitoring process should stop according to the 
        # control dictionary.
        #
        # Funtions for determining whether the monitoring process should stop according to the reception of signals SIGINT and SIGTSTP.
        @staticmethod
        def _check_signals():
            while not control["should_stop"]():
                # Handle SIGINT.
                if self._signal_flags["stop"]:
                    logger.info("SIGINT received. Stopping the event reception process.")
                    control["signal_stop"] = True
                # Handle SIGTSTP.
                if self._signal_flags["pause"]:
                    logger.info("SIGTSTP received. Pausing the event reception process.")
                    while self._signal_flags["pause"] and not self._signal_flags["stop"]:
                        time.sleep(1)  # Efficiently wait for signals.
                    if self._signal_flags["stop"]:
                        logger.info("SIGINT received. Stopping the event reception process.")
                        control["signal_stop"] = True
                    if not self._signal_flags["pause"]:
                        logger.info("SIGTSTP received. Resuming the event reception process.")
                        control["signal_stop"] = False
                control["signal_stop"] = False
                time.sleep(1)  # Sleep to avoid busy waiting.

        # Create the signal handler thread.
        signal_thread = threading.Thread(
            target=_check_signals,
            args=(),
            daemon=True
        )
        # -- END of signal handler thread infrastructure

        # Timeout checker thread infrastructure, which updates the control dictionary with the timeout_stop flag if the time elapsed since 
        # the reception of the last message exceeds the timeout specified in the configuration. The thread runs until the monitoring process 
        # should stop according to the control dictionary.
        #
        # Function for determining whether the monitoring process should stop according to the timeout of message reception from the RabbitMQ 
        # server.
        @staticmethod
        def _check_timeout():
            while not control["should_stop"]():
                if 0 < config.timeout < (time.time() - start_time_epoch):
                    control["timeout_stop"] = True
                time.sleep(1)  # Sleep to avoid busy waiting

        # Create the timeout checker thread.
        timeout_thread = threading.Thread(
            target=_check_timeout,
            args=(),
            daemon=True
        )
        # -- END of timeout checker thread infrastructure

        # Start the threads for checking signals, timeout and verdicts for determining termination of the monitoring process.
        #
        # Start the thread checking signals.
        signal_thread.start()
        # Start the thread checking timeout.
        timeout_thread.start()

        # Log the start of the sending of events to the RabbitMQ server.
        #
        # Start receiving events from the RabbitMQ server
        logger.info(f"Start sending events to exchange {rabbitmq_server_connections.rabbitmq_events_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_events_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_events_server_connection.server_info.port}.")

        # Main loop of the acquiring events from the SUT and sending events to the RabbitMQ server and processes them until the 
        # control dictionary indicates that the monitoring process should stop.
        while not control["should_stop"]():
            # Process packages from communication channel
            buffer = self._sut_pipe_channel.stdout.read(self._channel_conf.capacity * self._channel_conf.max_pkg_size)
            pkgs = [
                buffer[i : i + self._channel_conf.max_pkg_size]
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
                        event_csv = f"{timestamp},timed_event,{stripped_data_string}"
                    case 1:
                        event_csv = f"{timestamp},state_event,{stripped_data_string}"
                    case 2:
                        event_csv = f"{timestamp},process_event,{stripped_data_string}"
                    case 3:
                        event_csv = f"{timestamp},component_event,{stripped_data_string}"
                    case 4:
                        # This case captures the EndOfReportEvent so there is nothing to write.
                        event_csv = None
                    case _:
                        event_csv = f"{timestamp},invalid,{stripped_data_string}"
                if event_csv is not None:
                    try:
                        event = EventCSVCoDec.from_csv(event_csv)
                    except EventCSVError:
                        logger.error(f"Error parsing event csv: [ {event_csv} ].")
                        raise ReporterError()
                    try:
                        event_dict = EventDictCoDec.to_dict(event)
                    except EventTypeError:
                        logger.error(
                            f"Error building dictionary from event: [ {event} ]."
                        )
                        raise ReporterError()
                    try:
                        rabbitmq_server_connections.rabbitmq_events_server_connection.publish_message(
                            json.dumps(event_dict, indent=4),
                            pika.BasicProperties(
                                delivery_mode=2,  # Persistent message
                            ),
                        )
                    except RabbitMQError:
                        logger.error(
                            f"Error sending event to the exchange {rabbitmq_server_connections.rabbitmq_events_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_events_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_events_server_connection.server_info.port}."
                        )
                        raise ReporterError()
                    else:
                        # Log event send
                        logger.debug(f"Sent event: {event_dict}.")
                        # Only increment number_of_events is it is a valid event
                        number_of_events += 1
                        time.sleep(1 / 100000)
                else:
                    # Log invalid event
                    logger.error(f"Invalid event type: {event_type} with data: {data_string}.")
            
        # Log the stop of the sending of events to the RabbitMQ server.
        #
        # Send poison pill with the events routing_key to the RabbitMQ server
        try:
            rabbitmq_server_connections.rabbitmq_events_server_connection.publish_message(
                "", pika.BasicProperties(delivery_mode=2, headers={"termination": True})
            )
        except RabbitMQError:
            logger.error(f"Error sending poison pill to the exchange {rabbitmq_server_connections.rabbitmq_events_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_events_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_events_server_connection.server_info.port}.")
            raise ReporterError()
        else:
            logger.info(f"Poison pill sent to the exchange {rabbitmq_server_connections.rabbitmq_events_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_events_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_events_server_connection.server_info.port}.")
        # Stop publishing events to the RabbitMQ server
        logger.info(f"Stop sending events to the exchange {rabbitmq_server_connections.rabbitmq_events_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_events_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_events_server_connection.server_info.port}.")

        # Logging the reason for stoping the acquisition process.
        if control["signal_stop"]:
            logger.info(f"Events acquired: {number_of_events} - Time (secs.): {time.time()-start_time_epoch:.3f} - Process STOPPED, SIGINT received.")
        elif control["timeout_stop"]:
            logger.info(f"Events acquired: {number_of_events} - Time (secs.): {time.time()-start_time_epoch:.3f} - Process STOPPED, timeout reached ({time.time()-start_time_epoch} secs.).")
        else:
            logger.info(f"Events acquired: {number_of_events} - Time (secs.): {time.time()-start_time_epoch:.3f} - Process STOPPED, unknown reason.")

        # Wait for threads for checking signals and timeout to finish before closing the connection to the RabbitMQ server and ending 
        # the run() method, as they may be processing messages from the RabbitMQ server until the control dictionary indicates that the 
        # monitoring process should stop.
        #
        # Wait for the thread checking signals to finish.
        signal_thread.join(timeout=5)
        # Wait for the thread checking timeout to finish.
        timeout_thread.join(timeout=5)
