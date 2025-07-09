# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import argparse
import logging
import os
import sys
import threading
from pathlib import Path
import pika
from pynput import keyboard

from rt_reporter.logging_configuration import (
    _set_up_logging,
    LoggingLevel,
    LoggingDestination,
    _configure_logging_destination,
    _configure_logging_level
)
from rt_reporter.communication_channel import CommunicationChannel

# Stop event for finishing the reporting process
stop_event = threading.Event()


def on_press(key):
    global stop_event
    try:
        # Check if the key has a `char` attribute (printable key)
        if key.char == "s":
            stop_event.set()
    except AttributeError:
        # Handle special keys (like ctrl, alt, etc.) here if needed
        pass


def _run_acquisition(process_thread):
    global stop_event
    # Start the listener in a separate thread
    with keyboard.Listener(on_press=on_press) as listener:
        # Configure the monitor by setting up control event.
        process_thread.set_event(stop_event)
        # Events setup for managing the running mode.
        stop_event.clear()
        # Starts the acquisition thread.
        process_thread.start()
        # Waiting for the verification process to finish, either naturally or manually.
        process_thread.join()


def main():
    # Argument processing
    parser = argparse.ArgumentParser(
        prog="python -m rt_reporter.rt_reporter_sh",
        description="Reports events of a software artifact to be used by The Runtime Monitor.",
        epilog="Example: python -m rt_reporter.rt_reporter_sh path/to/sut --host=[localhost] --port=[5673] --timeout=5"
    )
    parser.add_argument("sut", type=str, help="Path to the executable binary.")
    parser.add_argument('--host', default='localhost', required=True, help='RabbitMQ server host')
    parser.add_argument('--port', default=5673, type=int, required=True, help='RabbitMQ server port')
    parser.add_argument("--log_level", type=str, choices=["debug", "event", "info", "warnings", "errors", "critical"], default="info", required=False, help="Log verbose level (optional argument)")
    parser.add_argument('--log_file', required=False, help='Path to log file (optional argument).')
    parser.add_argument("--timeout", type=int, nargs="?", help="Timeout for the acquisition process in seconds.")

    # Declaration of useful functions
    def validate_input_path(path):
        try:
            path.resolve()  # Normalize and validate
        except (OSError, RuntimeError):
            return False, "Invalid path syntax or characters."
        # Check existence
        if not path.exists():
            return False, "Path does not exist."
        # Check if it's a file
        if not path.is_file():
            return False, "Path is not a file."
        # Check read permission
        if not os.access(path, os.R_OK):
            return False, "No read permission."
        return True, "Path is valid."

    def is_rabbitmq(host, port, timeout=2):
        try:
            logging.info(f"Testing connection to RabbitMQ server at {args.host}:{args.port}.")
            credentials = pika.PlainCredentials('guest', 'guest')
            parameters=pika.ConnectionParameters(
                host=host,
                port=port,
                credentials=credentials,
                connection_attempts=1,
                socket_timeout=timeout,
                stack_timeout=timeout,
                client_properties={'connection_name': 'rt-reporter.connection_test'}
            )
            connection = pika.BlockingConnection(parameters)
            connection.close()
            return True
        except Exception:
            return False

    # Start the execution of The Runtime Reporter
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
                exit(-3)
    # Configure logging destination.
    if args.log_file is None:
        logging_destination = LoggingDestination.CONSOLE
    else:
        valid, message = validate_input_path(args.log_file)
        if not valid:
            print(f"Log file error. {message}", file=sys.stderr)
            exit(-3)
        else:
            logging_destination = LoggingDestination.FILE
    _set_up_logging()
    _configure_logging_destination(logging_destination, args.log_file)
    _configure_logging_level(logging_level)
    # Validate and normalise the SUT path
    input_path = Path(args.sut)
    valid, message = validate_input_path(input_path)
    if not valid:
        print(f"Executable binary file error. {message}", file=sys.stderr)
        exit(-1)
    logging.info(f"SUT path: {input_path}")
    sut_file_path = str(input_path)
    # Validate the existence of the RabbitMQ server
    if not is_rabbitmq(args.host, args.port, timeout=2):
        print(f"RabbitMQ server not active.", file=sys.stderr)
        exit(-2)
    logging.info(f"RabbitMQ server active at {args.host}:{args.port}.")
    # Determine timeout
    if args.timeout is None:
        timeout = 0
    else:
        timeout = args.timeout
    logging.info(f"Timeout: {timeout} seconds.")
    # Creates the thread for the communication channel.
    acquirer = CommunicationChannel(sut_file_path, args.host, args.port, timeout)
    # Create a new thread to read from the pipe
    process_thread = threading.Thread(target=_run_acquisition, args=[acquirer])
    # Starts the monitor thread
    process_thread.start()
    # Waiting for the verification process to finish, either naturally or manually.
    process_thread.join()


if __name__ == "__main__":
    main()
