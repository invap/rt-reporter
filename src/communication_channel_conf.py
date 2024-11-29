# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial


class CommunicationChannelConf:
    """
    Information about how the sender packs the data in the channel
    """

    def __init__(self):
        # 64K(os default) max string length to call (from the code) a test action (to be executed by the simulator)
        self.buffer_size = 65536
        # 8 (time long) + 4 (enum) + 4 (padding) + 1008 (all have data field with 1008)
        self.max_pkg_size = 1024
        self.capacity = int(self.buffer_size / self.max_pkg_size)
