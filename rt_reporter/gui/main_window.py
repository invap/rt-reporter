# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial
import threading

import wx
from rt_reporter.src.communication_channel import CommunicationChannel
from rt_reporter.gui.generation_status_window import GenerationStatusWindow


class MainWindow(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="Reporter")
        self.Bind(wx.EVT_CLOSE, self.on_close)
        # Creamos un notebook
        self.reporter_panel = ReporterPanel(parent=self, main_window=self)
        # Agregamos los paneles al sizer principal
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.main_sizer.Add(self.reporter_panel, 1, wx.EXPAND)
        # Establecemos el sizer principal para la ventana
        self.SetSizerAndFit(self.main_sizer)
        self.Show()

    def on_close(self, event):
        # del self.control_panel
        self.Destroy()
        wx.Exit()


class ReporterPanel(wx.Notebook):
    def __init__(self, parent, main_window: wx.Frame):
        super().__init__(parent=parent)
        # build the control panel
        self.executable_chosen = False
        self.setup_reporter_panel = SetupReporterPanel(
            parent=self, main_window=main_window
        )
        self.AddPage(self.setup_reporter_panel, "Configuration")


class SetupReporterPanel(wx.Panel):
    def __init__(self, parent, main_window: wx.Frame):
        super().__init__(parent=parent)
        self.parent = parent
        self.main_window = main_window
        self._comm_channel = None  # CommunicationChannel generated on START
        self._reportStatus = None  # Status window generated on START
        # Event for controlling the thread
        self._stop_event = threading.Event()
        # create visual elements
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        # create Select Object file to report
        self._set_up_source_file_components()
        # create the play pause controls
        self.main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.TOP, border=20)
        self.start = wx.Button(self, label="Start")
        self.start.Bind(wx.EVT_BUTTON, self.on_start)
        self._disable_start_button()
        self.stop_button = wx.Button(self, label="Stop")
        self.stop_button.Bind(wx.EVT_BUTTON, self.on_stop)
        self._disable_stop_button()
        self.run_ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.run_ctrl_sizer.Add(self.start, 0, wx.RIGHT, border=15)
        self.run_ctrl_sizer.Add(self.stop_button, 0)
        self.main_sizer.Add(
            self.run_ctrl_sizer, 0, wx.CENTER | wx.TOP | wx.BOTTOM, border=10
        )
        self.SetSizer(self.main_sizer)
        self.text_Path = ""

    def _set_up_source_file_components(self):
        action_label_component = wx.StaticText(self, label="Select executable to report:")
        self.main_sizer.Add(
            action_label_component, 0, wx.LEFT | wx.TOP | wx.RIGHT, border=15
        )

        folder_icon = wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, (16, 16))
        folder_selection_button = wx.BitmapButton(self, bitmap=folder_icon)
        folder_selection_button.Bind(wx.EVT_BUTTON, self.select_file)
        self.text_Obj = wx.TextCtrl(self, -1, "", size=(600, 33))

        folder_selection_sizer = wx.BoxSizer(wx.HORIZONTAL)
        folder_selection_sizer.Add(self.text_Obj, 0, wx.ALL, border=10)
        folder_selection_sizer.Add(
            folder_selection_button, 0, wx.TOP | wx.BOTTOM | wx.RIGHT, border=10
        )
        self.main_sizer.Add(folder_selection_sizer, 0)

    def select_file(self, event):
        # Open Dialog
        dialog = wx.FileDialog(
            self,
            "Select executable to report",
            "",
            "",
            "All files (*.*)|*.*",
            wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if dialog.ShowModal() == wx.ID_OK:
            # Accommodate buttons and pause event to the current state
            self._enable_start_button()
            decoded_choice = dialog.GetPath().rsplit("/", 1)
            self.text_Path = decoded_choice[0]
            self.text_Obj.SetLabel(decoded_choice[0] + "/" + decoded_choice[1])
        dialog.Destroy()

    def on_stop(self, event):
        # Adjust visual interface according to STOP.
        self._enable_start_button()
        self._disable_stop_button()
        self._stop_event.set()
        # Close the status window.
        self._reportStatus.close()
        # enable close button TODO

    def on_start(self, event):
        # disable close button TODO
        # Creates the thread for the communication channel.
        acquirer = CommunicationChannel(
            self.text_Path, self.text_Obj.GetValue()
        )
        # Creates a thread for controlling the acquisition process
        application_thread = threading.Thread(
            target=self._run_acquisition, args=[acquirer]
        )
        # Adjust visual interface according to START.
        self._disable_start_button()
        self._enable_stop_button()
        # Starts the acquisition thread.
        application_thread.start()
        # Create visual status window.
        self._reportStatus = GenerationStatusWindow(acquirer.get_event_count)
        self._reportStatus.Show()
        # enable close button TODO

    def _run_acquisition(self, process_thread):
        # Configure the monitor by setting up control event.
        process_thread.set_event(self._stop_event)
        # Events setup for managing the running mode.
        self._stop_event.clear()
        # Starts the acquisition thread.
        process_thread.start()
        # Waiting for the verification process to finish, either naturally or manually.
        process_thread.join()

    def _enable_start_button(self):
        wx.CallAfter(self.start.Enable)

    def _disable_start_button(self):
        wx.CallAfter(self.start.Disable)

    def _enable_stop_button(self):
        wx.CallAfter(self.stop_button.Enable)

    def _disable_stop_button(self):
        wx.CallAfter(self.stop_button.Disable)
