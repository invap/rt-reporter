import wx
from src.communitationChannelReporter import CommunicationChannelReporter


class MainReporterWindow(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='INVAP (VESE) - Rerporter')
        self.Bind(wx.EVT_CLOSE, self.on_close)
        # Creamos un divisor para dividir la ventana en dos partes
        # splitter = wx.SplitterWindow(self, -1, style=wx.SP_3DSASH)

        # Creamos un notebook
        self.reporter_panel = ReporterPanel(parent=self, main_window=self)

        # Establecemos los tamaños de cada panel
        # splitter.SplitVertically(self.control_panel, self.display_panel, -200)
        # splitter.SetMinimumPaneSize(20)

        # Agregamos los paneles al sizer principal
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.main_sizer.Add(self.reporter_panel, 1, wx.EXPAND)

        # Establecemos el sizer principal para la ventana
        self.SetSizer(self.main_sizer)

        # Establecemos el tamaño de la ventana y la mostramos
        self.SetSize((800, 600))
        self.Show()

    def on_close(self, event):
        # del self.control_panel
        self.Destroy()
        wx.Exit()


class ReporterPanel(wx.Notebook):
    def __init__(self, parent, main_window: wx.Frame):
        super().__init__(parent=parent)
        # build the control panel
        self.setup_reporter_panel = SetupReporterPanel(parent=self, main_window=main_window)
        self.AddPage(self.setup_reporter_panel, 'Configuración')


class SetupReporterPanel(wx.Panel):
    """
    The setup panel controls de initial configuration to perform any simulation
    """

    def __init__(self, parent, main_window: wx.Frame):
        super().__init__(parent=parent)
        self.main_window = main_window
        self.comm_channel = None  # generated on play
        # create visual elements
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        # create Select Object file to report
        self.button_Obj = wx.Button(self, label="Seleccionar archivo fuente a reportar: ")
        self.button_Obj.Bind(wx.EVT_BUTTON, self.select_file)
        self.text_Obj = wx.TextCtrl(self, -1, "", size=(600, -1))
        self.main_sizer.Add(self.button_Obj, 0, wx.LEFT | wx.TOP, 20)
        self.main_sizer.Add(self.text_Obj, 0, wx.LEFT | wx.TOP, 10)
        self.label_Output = wx.StaticText(self, label="Archivo a generar:")
        self.main_sizer.Add(self.label_Output, 0, wx.LEFT | wx.TOP, 10)
        self.text_Output = wx.TextCtrl(self, -1, "", size=(600, -1))
        self.main_sizer.Add(self.text_Output, 0, wx.LEFT | wx.TOP, 10)
        # create the play pause controls
        self.main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 20)
        self.play_button = wx.Button(self, label="Start")
        self.stop_button = wx.Button(self, label="Stop")
        self.play_button.Bind(wx.EVT_BUTTON, self.on_start)
        self.stop_button.Bind(wx.EVT_BUTTON, self.on_stop)
        self.run_ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.run_ctrl_sizer.Add(self.play_button, 0, wx.ALL, 5)
        self.run_ctrl_sizer.Add(self.stop_button, 0, wx.ALL, 5)
        self.main_sizer.Add(self.run_ctrl_sizer, 0, wx.CENTER | wx.TOP, 10)
        self.SetSizer(self.main_sizer)
        # create the communication Channel
        self.comm_channel: CommunicationChannelReporter = None

    def select_file(self, event):
        # Open Dialog
        dialog = wx.FileDialog(self, "Seleccionar archivo a reportar", "", "", "All files (*.*)|*.*",
                               wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            self.text_Obj.SetLabel(dialog.GetPath())
            self.text_Output.SetLabel(dialog.GetPath() + "_log.txt")
        dialog.Destroy()

    def on_start(self, event):
        # disable close button TODO
        files_to_get = [self.text_Obj.GetValue(), self.text_Output.GetValue()]
        self.comm_channel = CommunicationChannelReporter(files_to_get[0], files_to_get[1])
        # enable close button TODO

    def on_stop(self, event):
        self.comm_channel.stop()
        # enable close button TODO
