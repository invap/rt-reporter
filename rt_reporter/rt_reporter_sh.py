# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import argparse
import logging
import os

from rt_reporter.config import config
from rt_reporter.errors.reporter_errors import ReporterError
from rt_reporter.logging_configuration import (
    LoggingLevel,
    LoggingDestination,
    set_up_logging,
    configure_logging_destination,
    configure_logging_level
)
from rt_reporter import rabbitmq_server_connections
from rt_reporter.reporter import rt_reporter_runner
from rt_reporter.utility import (
    is_valid_file_with_extension_nex,
    is_valid_file_with_extension
)


# Exit codes:
# -1: Input file error
# -2: RabbitMQ configuration error
# -3: Reporter error
# -4: Unexpected error
def main():
    # Argument processing
    parser = argparse.ArgumentParser(
        prog="The Runtime Reporter",
        description="Reports events obtained from an execution of a SUT by publishing them to a RabbitMQ server.",
        epilog="Example: python -m rt_reporter.rt_reporter_sh /path/to/sut --rabbitmq_config_file=./rabbitmq_config.toml --log_file=output.log --log_level=event --timeout=120"
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
        exit(-2)
    logger.info(f"RabbitMQ infrastructure configuration file: {args.rabbitmq_config_file}")
    # Create RabbitMQ communication infrastructure
    rabbitmq_server_connections.build_rabbitmq_server_connections(args.rabbitmq_config_file)
    # Run the rt_reporter
    try:
        rt_reporter_runner(args.sut)
    except ReporterError:
        logger.critical("Reporter error.")
        exit(-3)
    except Exception as e:
        logger.critical(f"Unexpected error: {e}.")
        exit(-4)
    # Close connection if it exists
    rabbitmq_server_connections.rabbitmq_event_server_connection.close()
    exit(0)


if __name__ == "__main__":
    main()
