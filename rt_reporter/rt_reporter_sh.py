# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import argparse
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
from rt_reporter.rabbitmq_utility.rabbitmq_server_connections import rabbitmq_server_connection
from rt_reporter.rabbitmq_utility.rabbitmq_utility import (
    RabbitMQError,
    publish_message, connect_to_server, connect_to_channel_exchange
)
from rt_reporter.rabbitmq_utility.rabbitmq_server_config import rabbitmq_server_config, rabbitmq_exchange_config
from rt_reporter.utility import (
    is_valid_file_with_extension_nex,
    is_valid_file_with_extension
)


# Errors:
# -1: Input file error
# -2: RabbitMQ server setup error

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
        epilog = "Example: python -m rt_reporter.rt_reporter_sh /path/to/sut --host=https://myrabbitmq.org.ar --port=5672 --user=my_user --password=my_password --log_file=output.log --log_level=event --timeout=120"
    )
    parser.add_argument("sut", type=str, help="Path to the executable binary.")
    parser.add_argument('--host', type=str, default='localhost', help='RabbitMQ server host.')
    parser.add_argument('--port', type=int, default=5672, help='RabbitMQ server port.')
    parser.add_argument('--user', default='guest', help='RabbitMQ server user.')
    parser.add_argument('--password', default='guest', help='RabbitMQ server password.')
    parser.add_argument('--exchange', type=str, default='my_event_exchange', help='Name of the exchange at the RabbitMQ event server.')
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
    timeout = args.timeout if args.timeout >= 0 else 0
    logger.info(f"Timeout for event acquisition from the SUT: {timeout} seconds.")
    # RabbitMQ server configuration
    rabbitmq_server_config.host = args.host
    rabbitmq_server_config.port = args.port
    rabbitmq_server_config.user = args.user
    rabbitmq_server_config.password = args.password
    # RabbitMQ exchange configuration
    rabbitmq_exchange_config.exchange = args.exchange
    # Other configuration
    config.timeout = timeout
    # Create a channel to communicate with the sut and starts a subprocess.
    channel_conf = CommunicationChannelConf()
    sut_pipe_channel = subprocess.Popen([args.sut], stdout=subprocess.PIPE)
    # Set up the connection to the RabbitMQ connection to server
    try:
        connection = connect_to_server(rabbitmq_server_config)
    except RabbitMQError:
        logger.critical(f"Error setting up the connection to the RabbitMQ server.")
        exit(-2)
    # Set up the RabbitMQ channel and exchange for events with the RabbitMQ server
    try:
        channel = connect_to_channel_exchange(rabbitmq_server_config, rabbitmq_exchange_config, connection)
    except RabbitMQError:
        logger.critical(f"Error setting up the channel and exchange at the RabbitMQ server.")
        exit(-2)
    # Set up connection for events with the RabbitMQ server
    rabbitmq_server_connection.connection = connection
    rabbitmq_server_connection.channel = channel
    rabbitmq_server_connection.exchange = rabbitmq_exchange_config.exchange
    # Start publishing events to the RabbitMQ server
    logger.info(f"Start publishing events to RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port}.")
    #Start event acquisition from the sut
    start_time_epoch = time.time()
    while True:
        # Handle SIGINT
        if signal_flags['stop']:
            logger.info("SIGINT received. Stopping the event acquisition process.")
            break
        # Handle SIGTSTP
        if signal_flags['pause']:
            logger.info("SIGTSTP received. Pausing the event acquisition process.")
            while signal_flags['pause'] and not signal_flags['stop']:
                time.sleep(1)  # Efficiently wait for signals
            if signal_flags['stop']:
                logger.info("SIGINT received. Stopping the event acquisition process.")
                break
            logger.info("SIGTSTP received. Resuming the event acquisition process.")
        # Timeout handling for event acquisition.
        if config.timeout != 0 and time.time() - start_time_epoch >= config.timeout:
            logger.info(f"Acquired events for {config.timeout} seconds. Timeout reached.")
            break
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
                    event = (str(timestamp) + "," + "timed_event" + "," + stripped_data_string + "\n")
                case 1:
                    event = (str(timestamp) + "," + "state_event" + "," + stripped_data_string + "\n")
                case 2:
                    event = (str(timestamp) + "," + "process_event" + "," + stripped_data_string + "\n")
                case 3:
                    event = (str(timestamp) + "," + "component_event" + "," + stripped_data_string + "\n")
                case 4:
                    # This case captures the EndOfReportEvent so there is nothing to write.
                    event = None
                case _:
                    event = (str(timestamp) + "," + "invalid" + "," + stripped_data_string + "\n")
            if event is not None:
                # Publish event at RabbitMQ server
                try:
                    publish_message(
                        rabbitmq_server_connection,
                        'events',
                        event,
                        pika.BasicProperties(
                            delivery_mode=2,  # Persistent message
                        )
                    )
                except RabbitMQError:
                    logger.info("Error sending event to the RabbitMQ event server.")
                    exit(-2)
                # Log event send
                cleaned_event = event.rstrip('\n\r')
                logger.debug(f"Sent event: {cleaned_event}.")
                time.sleep(1 / 100000)
    # Send poison pill with the events routing_key to the RabbitMQ server
    try:
        publish_message(
            rabbitmq_server_connection,
            'events',
            '',
            pika.BasicProperties(
                delivery_mode=2,
                headers={'termination': True}
            )
        )
    except RabbitMQError:
        logger.info("Error sending with the events routing_key to the RabbitMQ server.")
        exit(-2)
    else:
        logger.info("Poison pill sent with the events routing_key to the RabbitMQ server.")
    # Stop publishing events to the RabbitMQ server
    logger.info(f"Stop publishing events to RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port}.")
    # Close connection if it exists
    if connection and connection.is_open:
        try:
            connection.close()
            logger.info(f"Connection to RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port} closed.")
        except Exception as e:
            logger.error(f"Error closing connection to RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port}: {e}.")
    exit(0)


if __name__ == "__main__":
    main()
