# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import argparse
import logging
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path
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
from rt_reporter.rabbitmq_utility import (
    rabbitmq_connect_to_server, setup_rabbitmq
)
from rt_reporter.rabbitmq_server_config import rabbitmq_server_config
from rt_reporter.utility import validate_input_path

# Errors:
# -1: Logging infrastructure error
# -2: Input file error
# -3: RabbitMQ server setup error

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
        prog = "python -m rt_file_tools.file_feeder.file_feeder_sh",
        description = "Reports events dear from file containing the events in cvs format to a RabbitMQ server.",
        epilog="Example: python -m rt_reporter.rt_reporter_sh path/to/file --host [localhost] --port [5673] --timeout 5"
    )
    parser.add_argument("sut", type=str, help="Path to the executable binary.")
    parser.add_argument('--host', type=str, default='localhost', help='RabbitMQ server host')
    parser.add_argument('--port', type=int, default=5673, help='RabbitMQ server port')
    parser.add_argument('--user', default='guest', help='RabbitMQ server user')
    parser.add_argument('--password', default='guest', help='RabbitMQ server password')
    parser.add_argument('--exchange', type=str, default='my_exchange', help='Name of the exchange at the RabbitMQ server')
    parser.add_argument("--log_level", type=str, choices=["debug", "event", "info", "warnings", "errors", "critical"], default="event", help="Log verbose level (optional argument)")
    parser.add_argument('--log_file', help='Path to log file (optional argument).')
    parser.add_argument("--timeout", type=int, default=0, help="Timeout for the event acquisition process in seconds (0 = no timeout).")
    # Parse arguments
    args = parser.parse_args()
    # Set up the logging infrastructure
    # Configure logging level.
    if args.log_level is None:
        logging_level = LoggingLevel.INFO
    else:
        match args.log_level:
            case "debug":
                logging_level = LoggingLevel.DEBUG
            case "event":
                logging_level = LoggingLevel.EVENT
            case "info":
                logging_level = LoggingLevel.INFO
            case "warnings":
                logging_level = LoggingLevel.WARNING
            case "errors":
                logging_level = LoggingLevel.ERROR
            case "critical":
                logging_level = LoggingLevel.CRITICAL
            case _:
                print(f"Logging level error: {args.log_level} is not a logging level.", file=sys.stderr)
                exit(-1)
    # Configure logging destination.
    if args.log_file is None:
        logging_destination = LoggingDestination.CONSOLE
    else:
        valid, message = validate_input_path(args.log_file)
        if not valid:
            print(f"Log file error. {message}", file=sys.stderr)
            exit(-1)
        else:
            logging_destination = LoggingDestination.FILE
    set_up_logging()
    configure_logging_destination(logging_destination, args.log_file)
    configure_logging_level(logging_level)
    # Validate and normalise the SUT path
    input_path = Path(args.sut)
    valid, message = validate_input_path(input_path)
    if not valid:
        print(f"Executable binary file error. {message}", file=sys.stderr)
        exit(-2)
    logging.info(f"SUT path: {input_path}")
    sut_file_path = str(input_path)
    # Determine timeout
    timeout = args.timeout if args.timeout >= 0 else 0
    logging.info(f"Timeout for message reception: {timeout} seconds.")
    # RabbitMQ server configuration
    rabbitmq_server_config.host = args.host
    rabbitmq_server_config.port = args.port
    rabbitmq_server_config.user = args.user
    rabbitmq_server_config.password = args.password
    rabbitmq_server_config.exchange = args.exchange
    # Other configuration
    config.timeout = timeout
    #Start event acquisition from the sut
    start_time_epoch = time.time()
    # Create a channel to communicate with the sut and starts a subprocess.
    channel_conf = CommunicationChannelConf()
    sut_pipe_channel = subprocess.Popen([sut_file_path], stdout=subprocess.PIPE)
    # Establish connection to the RabbitMQ server.
    logging.info(f"Establishing connection to RabbitMQ server at {args.host}:{args.port}.")
    connection, rabbitmq_channel = rabbitmq_connect_to_server()
    logging.info(f"Connection to RabbitMQ server at {args.host}:{args.port} established.")
    # Start publishing events to the RabbitMQ server
    logging.info(f"Start publishing events to RabbitMQ server at {args.host}:{args.port}.")
    while True:
        # Handle SIGINT
        if signal_flags['stop']:
            logging.info("SIGINT received. Stopping the event acquisition process.")
            break
        # Handle SIGTSTP
        if signal_flags['pause']:
            logging.info("SIGTSTP received. Pausing the event acquisition process.")
            while signal_flags['pause'] and not signal_flags['stop']:
                signal.pause()  # Efficiently wait for signals
            if signal_flags['stop']:
                logging.info("SIGINT received. Stopping the event acquisition process.")
                break
            logging.info("SIGTSTP received. Resuming the event acquisition process.")
        # Timeout handling for event acquisition.
        if config.timeout != 0 and time.time() - start_time_epoch >= config.timeout:
            logging.info(f"Acquired events for {config.timeout} seconds. Timeout reached.")
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
                rabbitmq_channel.basic_publish(
                    exchange=rabbitmq_server_config.exchange,
                    routing_key='events',
                    body=event,
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # Persistent message
                    )
                )
                cleaned_event = event.rstrip('\n\r')
                logging.log(LoggingLevel.EVENT, f"Sent event: {cleaned_event}.")
                time.sleep(1 / 100000)
    # Always attempt to send poison pill if the channel is available
    if rabbitmq_channel and rabbitmq_channel.is_open:
        rabbitmq_channel.basic_publish(
            exchange=rabbitmq_server_config.exchange,
            routing_key='events',
            body='',
            properties=pika.BasicProperties(
                delivery_mode=2,
                headers={'termination': True}
            )
        )
        logging.log(LoggingLevel.EVENT, "Poison pill sent. Event acquisition stopped.")
    # Close connection if it exists
    if connection and connection.is_open:
        try:
            connection.close()
            logging.info(f"Connection to RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port} closed.")
        except Exception as e:
            logging.error(f"Error closing connection to RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port}: {e}.")
    logging.info(f"Stop publishing events to RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port}.")
    exit(0)


if __name__ == "__main__":
    main()
