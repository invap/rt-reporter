import wx
from src.mainReporter import MainReporterWindow


if __name__ == '__main__':
    app = wx.App()
    mainReporter = MainReporterWindow()
    app.MainLoop()

