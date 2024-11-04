# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

class CommunicationChannelConf:
    """
    Information about how the sender packs the data in the channel
    """

    def __init__(self):
        """64K(os default) max string length to call (from the code) a test action (to be executed by the simulator)"""
        self.buffer_size = 65536
        # 8 (time long) + 4 (enum timed, state, process or component) + (1025  | 1025 ) (both have data field with 1024)
        self.max_pkg_size = 1040
        self.capacity = int(self.buffer_size / self.max_pkg_size)
