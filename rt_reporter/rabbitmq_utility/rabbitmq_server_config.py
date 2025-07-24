# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

from rt_reporter.rabbitmq_utility.rabbitmq_utility import RabbitMQ_server_config, RabbitMQ_exchange_config

# Instances shared globally
rabbitmq_server_config = RabbitMQ_server_config()
rabbitmq_exchange_config = RabbitMQ_exchange_config()