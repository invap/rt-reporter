# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import argparse
import json
import logging
import os
import signal
import struct
import subprocess
import time
import pika

from rt_reporter.communication_channel_conf import CommunicationChannelConf
from rt_reporter.config import config
from rt_reporter.logging_configuration import (
    LoggingLevel,
    LoggingDestination,
    set_up_logging,
    configure_logging_destination,
    configure_logging_level
)
from rt_reporter import rabbitmq_server_connections
from rt_rabbitmq_wrapper.rabbitmq_utility import (
    RabbitMQError,
)
from rt_reporter.utility import (
    is_valid_file_with_extension_nex,
    is_valid_file_with_extension
)
from rt_rabbitmq_wrapper.exchange_types.event.event_dict_codec import EventDictCoDec
from rt_rabbitmq_wrapper.exchange_types.event.event_csv_codec import EventCSVCoDec
from rt_rabbitmq_wrapper.exchange_types.event.event_codec_errors import (
    EventCSVError,
    EventTypeError
)


# Errors:
# -1: Input file error
# -2: RabbitMQ server setup error
# -3: Other errors
def main():
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

    # Argument processing
    parser = argparse.ArgumentParser(
        prog = "The Runtime Reporter",
        description = "Reports events obtained from an execution of a SUT by publishing them to a RabbitMQ server.",
        epilog = "Example: python -m rt_reporter.rt_reporter_sh /path/to/sut --rabbitmq_config_file=./rabbitmq_config.toml --log_file=output.log --log_level=event --timeout=120"
    )
    parser.add_argument("sut", type=str, help="Path to the executable binary.")
    parser.add_argument("--rabbitmq_config_file", type=str, default='./rabbitmq_config.toml', help='Path to the TOML file containing the RabbitMQ server configuration.')
    parser.add_argument("--log_level", type=str, choices=["debug", "info", "warnings", "errors", "critical"], default="info", help="Log verbose level.")
    parser.add_argument('--log_file', help='Path to log file.')
    parser.add_argument("--timeout", type=int, default=0, help="Timeout for the event acquisition process in seconds (0 = no timeout).")
    # Parse arguments
    args = parser.parse_args()
    # Set up the logging infrastructure
    # Configure logging level.
    match args.log_level:
        case "debug":
            logging_level = LoggingLevel.DEBUG
        case "info":
            logging_level = LoggingLevel.INFO
        case "warnings":
            logging_level = LoggingLevel.WARNING
        case "errors":
            logging_level = LoggingLevel.ERROR
        case "critical":
            logging_level = LoggingLevel.CRITICAL
        case _:
            logging_level = LoggingLevel.INFO
    # Configure logging destination.
    if args.log_file is None:
        logging_destination = LoggingDestination.CONSOLE
    else:
        valid_log_file = is_valid_file_with_extension_nex(args.log_file, "log")
        if not valid_log_file:
            logging_destination = LoggingDestination.CONSOLE
        else:
            logging_destination = LoggingDestination.FILE
    set_up_logging()
    configure_logging_destination(logging_destination, args.log_file)
    configure_logging_level(logging_level)
    # Create a logger for this component
    logger = logging.getLogger("rt_reporter.rt_reporter_sh")
    logger.info(f"Log verbosity level: {logging_level}.")
    if args.log_file is None:
        logger.info("Log destination: CONSOLE.")
    else:
        if not valid_log_file:
            logger.info("Log file error. Log destination: CONSOLE.")
        else:
            logger.info(f"Log destination: FILE ({args.log_file}).")
    # Validate and normalise the SUT path and check that it is executable
    valid_sut_file = (
            is_valid_file_with_extension(args.sut, "any") and
            os.path.isfile(args.sut) and
            os.access(args.sut, os.X_OK)
    )
    if not valid_sut_file:
        logger.error(f"SUT binary file error or permission denied: {args.sut}")
        exit(-1)
    logger.info(f"SUT path: {args.sut}")
    # Determine timeout
    config.timeout = args.timeout if args.timeout >= 0 else 0
    logger.info(f"Timeout for event acquisition from the SUT: {config.timeout} seconds.")
    # RabbitMQ infrastructure configuration
    valid = is_valid_file_with_extension(args.rabbitmq_config_file, "toml")
    if not valid:
        logger.critical(f"RabbitMQ infrastructure configuration file error.")
        exit(-1)
    logger.info(f"RabbitMQ infrastructure configuration file: {args.rabbitmq_config_file}")
    rabbitmq_server_connections.build_rabbitmq_server_connections(args.rabbitmq_config_file)
    # Start receiving events from the RabbitMQ server
    logger.info(f"Start sending events to exchange {rabbitmq_server_connections.rabbitmq_event_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.port}.")
    # Create a channel to communicate with the sut and starts a subprocess.
    channel_conf = CommunicationChannelConf()
    sut_pipe_channel = subprocess.Popen([args.sut], stdout=subprocess.PIPE)
    # Start event acquisition from the sut
    start_time_epoch = time.time()
    number_of_events = 0
    # Control variables
    stop = False
    completed = False
    while not completed and not stop:
        # Handle SIGINT
        if signal_flags['stop']:
            logger.info("SIGINT received. Stopping the event acquisition process.")
            stop = True
        # Handle SIGTSTP
        if signal_flags['pause']:
            logger.info("SIGTSTP received. Pausing the event acquisition process.")
            while signal_flags['pause'] and not signal_flags['stop']:
                time.sleep(1)  # Efficiently wait for signals
            if signal_flags['stop']:
                logger.info("SIGINT received. Stopping the event acquisition process.")
                stop = True
            if not signal_flags['pause']:
                logger.info("SIGTSTP received. Resuming the event acquisition process.")
        # Timeout handling for event acquisition.
        if config.timeout != 0 and time.time() - start_time_epoch >= config.timeout:
            completed = True
        # Process packages from communication channel.
        buffer = sut_pipe_channel.stdout.read(channel_conf.capacity * channel_conf.max_pkg_size)
        pkgs = [
            buffer[i: i + channel_conf.max_pkg_size]
            for i in range(0, len(buffer), channel_conf.max_pkg_size)
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
                    event_dict = EventDictCoDec.to_dict(event)
                except EventCSVError:
                    logger.info(f"Error parsing event csv: [ {event_csv} ].")
                    exit(-3)
                except EventTypeError:
                    logger.info(f"Error building dictionary from event: [ {event} ].")
                    exit(-3)
                try:
                    rabbitmq_server_connections.rabbitmq_event_server_connection.publish_message(
                        json.dumps(event_dict, indent=4),
                        pika.BasicProperties(
                            delivery_mode=2,  # Persistent message
                        )
                    )
                except RabbitMQError:
                    logger.info(f"Error sending event to the exchange {rabbitmq_server_connections.rabbitmq_event_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.port}.")
                    exit(-2)
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
        exit(-2)
    else:
        logger.info(f"Poison pill sent to the exchange {rabbitmq_server_connections.rabbitmq_event_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.port}.")
    # Stop publishing events to the RabbitMQ server
    logger.info(f"Stop sending events to the exchange {rabbitmq_server_connections.rabbitmq_event_server_connection.exchange} at the RabbitMQ server at {rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.host}:{rabbitmq_server_connections.rabbitmq_event_server_connection.server_info.port}.")
    # Close connection if it exists
    rabbitmq_server_connections.rabbitmq_event_server_connection.close()
    # Logging the reason for stoping the verification process to the RabbitMQ server
    if completed:
        logger.info(f"Events acquired: {number_of_events} - Time (secs.): {time.time() - start_time_epoch:.3f} - Process COMPLETED, timeout reached.")
    elif stop:
        logger.info(f"Events acquired: {number_of_events} - Time (secs.): {time.time() - start_time_epoch:.3f} - Process STOPPED, SIGINT received.")
    else:
        logger.info(f"Events acquired: {number_of_events} - Time (secs.): {time.time() - start_time_epoch:.3f} - Process STOPPED, unknown reason.")
    exit(0)


if __name__ == "__main__":
    main()
