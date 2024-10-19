# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import time

import wx


class ReporterGenerationStatus(wx.Frame):
    def __init__(self, parent, generator):
        super().__init__(None, title="Reporting: ",
                         style=wx.CAPTION | wx.RESIZE_BORDER)  # TODO take some name of the component
        self.generator_process = generator
        # information's variables to show
        self.__stat_event_process_count = 0
        self.__stat_event_component_count = 0
        self.__stat_time_elapsed = time.time()
        # Create a html panel to show the information
        txt_style = wx.VSCROLL | wx.HSCROLL | wx.BORDER_SIMPLE
        self.status_text = wx.TextCtrl(self, -1, "", size=(600, -1))
        self.html_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.html_sizer.Add(self.status_text)
        self.main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.Centre()
        self.status_text.SetLabel("Initiating...")
        self.timer = wx.CallLater(50, self.on_timer)
        # show
        self.Show()

    def on_timer(self):
        self.status_text.SetLabel(
            f'Reporting time (sec.): {round(time.time() - self.__stat_time_elapsed, 1)}\n' +
            f'Timed events count: {self.generator_process.get_count()[0]}\n' +
            f'State events count: {self.generator_process.get_count()[1]}\n' +
            f'Component events count: {self.generator_process.get_count()[2]}\n' +
            f'process events count: {self.generator_process.get_count()[3]}\n' +
            f'Report file size: {round(self.generator_process.get_count()[2],1)} MBytes\n'
        )
        self.status_text.Refresh()
        self.Refresh()
        self.Update()
        self.timer.Restart(50)

    def close(self):
        self.timer.Stop()
        self.Close(True)
