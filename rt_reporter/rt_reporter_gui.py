# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import wx
from rt_reporter.gui.main_window import MainWindow


if __name__ == "__main__":
    app = wx.App()
    mainReporter = MainWindow()
    app.MainLoop()
