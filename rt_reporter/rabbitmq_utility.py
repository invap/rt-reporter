# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import logging
import pika
from pika.exceptions import (
    AMQPConnectionError,
    ProbableAuthenticationError,
    ProbableAccessDeniedError,
    IncompatibleProtocolError,
    ChannelClosed,
    ConnectionClosed,
    DuplicateConsumerTag
)

from rt_reporter.rabbitmq_server_config import rabbitmq_server_config


class RabbitMQError(Exception):
    def __init__(self):
        super().__init__("RabbitMQ server error.")


def rabbitmq_connect_to_server():
    # Connection parameters with CLI arguments
    credentials = pika.PlainCredentials(rabbitmq_server_config.user, rabbitmq_server_config.password)
    parameters = pika.ConnectionParameters(
        host=rabbitmq_server_config.host,
        port=rabbitmq_server_config.port,
        credentials=credentials,
        connection_attempts=3,
        retry_delay=1,
        heartbeat=0,
        client_properties={'connection_name': 'rt_file_tools.file_feeder'}
    )
    # Setting up the RabbitMQ connection
    try:
        connection = pika.BlockingConnection(parameters)
    except IncompatibleProtocolError as e:
        logging.error(f"Protocol version at RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port} error: {e}.")
        raise RabbitMQError()
    except ProbableAuthenticationError as e:
        logging.error(f"Authentication to RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port} failed with user {rabbitmq_server_config.user} and password {rabbitmq_server_config.password}: {e}.")
        raise RabbitMQError()
    except ProbableAccessDeniedError as e:
        logging.error(f"User {rabbitmq_server_config.user} lacks access permissions to RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port}: {e}.")
        raise RabbitMQError()
    except AMQPConnectionError as e:
        logging.error(f"Connection to RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port} failed: {e}.")
        raise RabbitMQError()
    except TypeError as e:
        logging.error(f"Invalid argument types: {e}.")
        raise RabbitMQError()
    # Setting up the RabbitMQ channel and exchange
    try:
        # Declare RabbitMQ connection channel
        rabbitmq_channel = connection.channel()
        # Declare exchange for the RabbitMQ connection channel
        rabbitmq_channel.exchange_declare(
            exchange=rabbitmq_server_config.exchange,
            exchange_type='fanout',
            durable=True
        )
    except ChannelClosed as e:
        logging.error(f"Channel closed: {e}.")
        raise RabbitMQError()
    except ConnectionClosed as e:
        logging.error(f"Unexpected connection loss during operation: {e}.")
        raise RabbitMQError()
    except TypeError as e:
        logging.error(f"Invalid argument types: {e}.")
        raise RabbitMQError()
    else:
        logging.info(f"Connection to RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port} established.")
        return connection, rabbitmq_channel

def rabbitmq_declare_queue(rabbitmq_channel):
    # Declare queue
    try:
        result = rabbitmq_channel.queue_declare(queue='', exclusive=True)
        queue_name = result.method.queue
    except ChannelClosed as e:
        logging.error(f"Channel closed: {e}.")
        raise RabbitMQError()
    except ConnectionClosed as e:
        logging.error(f"Unexpected connection loss during operation: {e}.")
        raise RabbitMQError()
    except TypeError as e:
        logging.error(f"Invalid argument types: {e}.")
        raise RabbitMQError()
    # Bind queue
    try:
        rabbitmq_channel.queue_bind(
            exchange=rabbitmq_server_config.exchange,
            queue=queue_name
        )
    except ChannelClosed as e:
        logging.error(f"Binding violates server rules: {e}.")
        raise RabbitMQError()
    except ConnectionClosed as e:
        logging.error(f"Connection lost during binding operation: {e}.")
        raise RabbitMQError()
    except ValueError as e:
        logging.error(f"Missing required arguments: {e}.")
        raise RabbitMQError()
    except TypeError as e:
        logging.error(f"Invalid argument types: {e}.")
        raise RabbitMQError()
    else:
        logging.info(f"Queue created and bound to {rabbitmq_server_config.exchange} at RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port} established.")
        return queue_name

def rabbitmq_register_consumer(rabbitmq_channel, queue_name, callback):
        # Register consumer
        try:
            rabbitmq_channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=True
            )
        except ChannelClosed as e:
            logging.error(f"Error configuring RabbitMQ channel for consumption. Channel error: {e}.")
            raise RabbitMQError()
        except DuplicateConsumerTag as e:
            logging.error(f"Error configuring RabbitMQ channel for consumption. Consumer tag already in use - specify unique tag: {e}.")
            raise RabbitMQError()
        except ConnectionClosed as e:
            logging.error(f"Error configuring RabbitMQ channel for consumption. Connection lost while starting consumer: {e}.")
            raise RabbitMQError()
        except ValueError as e:
            logging.error(f"Invalid argument: {e}.")
            raise RabbitMQError()
        except TypeError as e:
            logging.error(f"Type error: {e}.")
            raise RabbitMQError()
        else:
            logging.info(f"Consumer attached to {queue_name} at RabbitMQ server at {rabbitmq_server_config.host}:{rabbitmq_server_config.port} established.")


def setup_rabbitmq(callback):
    # Full RabbitMQ setup: connection, queue, binding, consumer
    # Create connection and channel
    try:
        connection, rabbitmq_channel = rabbitmq_connect_to_server()
    except RabbitMQError:
        logging.error(f"RabbitMQ connection or channel setup failed.")
        return None, None
    # Declare and bind queue
    try:
        queue_name = rabbitmq_declare_queue(rabbitmq_channel)
    except RabbitMQError:
        logging.error(f"Queue declaration at RabbitMQ failed.")
        return None, None
    # Register consumer
    try:
        rabbitmq_register_consumer(rabbitmq_channel, queue_name, callback)
    except RabbitMQError:
        logging.error(f"Queue declaration at RabbitMQ failed.")
        return None, None
    return connection, rabbitmq_channel

