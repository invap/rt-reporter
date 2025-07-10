# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import os
import pika


# RabbitMQ functions
def is_rabbitmq_server_active(host, port, user, password, timeout=2):
    try:
        credentials = pika.PlainCredentials(user, password)
        parameters = pika.ConnectionParameters(
            host=host,
            port=port,
            credentials=credentials,
            connection_attempts=1,
            socket_timeout=timeout,
            stack_timeout=timeout,
            client_properties={'connection_name': 'rt-reporter_connection_test'}
        )
        connection = pika.BlockingConnection(parameters)
        connection.close()
        return True
    except Exception:
        return False


def connect_to_rabbitmq_server(host, port, user, password, exchange):
    # Connection parameters with CLI arguments
    credentials = pika.PlainCredentials(user, password)
    parameters = pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials,
        connection_attempts=3,
        retry_delay=1,
        heartbeat=30,
        client_properties={'connection_name': 'rt_file_tools.file_feeder'}
    )
    connection = pika.BlockingConnection(parameters)
    rabbitmq_channel = connection.channel()
    # Declare exchange for the RabbitMQ connection channel
    rabbitmq_channel.exchange_declare(
        exchange=exchange,
        exchange_type='fanout',
        durable=True
    )
    return connection, rabbitmq_channel


# Path validation functions
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


def validate_output_path(path):
    try:
        path = path.resolve()
    except (OSError, RuntimeError) as e:
        return False, f"Invalid path: {str(e)}"
    if path.exists():
        if path.is_dir():
            if not os.access(path, os.W_OK):
                return False, "No write permission in directory."
            return True, "Directory is valid."
        else:
            if not os.access(path, os.W_OK):
                return False, "No write permission for file."
            return True, "File is valid."
    else:
        parent = path.parent
        if not parent.exists():
            return False, f"Parent directory {parent} does not exist."
        if not os.access(parent, os.W_OK):
            return False, f"No write permission in parent directory {parent}."
        return True, "Path is valid for new file."
