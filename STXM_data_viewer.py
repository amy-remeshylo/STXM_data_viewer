from PyQt5.QtWidgets import QComboBox, QVBoxLayout, QDialog, QGroupBox, QTextBrowser, QMainWindow, QApplication, QPushButton, QLabel, QMessageBox, QDateTimeEdit, QSpinBox, QProgressBar
from PyQt5 import uic
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QRunnable, pyqtSignal, QObject, QThreadPool
import sys

class WorkerSignals(QObject):
    # define worker signals
    finished = pyqtSignal()
    progress = pyqtSignal(int)


class Worker(QRunnable):
        def __init__(self, fn, *args, **kwargs):
            super(Worker, self).__init__()
            self.fn = fn
            self.args = args
            self.kwargs = kwargs
            self.signals = WorkerSignals()

        def run(self):
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit()

class progressDialog(QDialog):
    def __init(self, parent):
        super(progressDialog,self).__init__(parent=parent)

        self.setWindowTitle("Preparing Database...")
        self.progLBL = QLabel("Preparing Database...")
        self.progBar = QProgressBar()

        self.layout = QVBoxLayout()

        self.layout.addWidget(self.progLBL)
        self.layout.addWidget(self.progBar)

        self.setLayout(self.layout)


class UI(QMainWindow):
    def __init__(self):
        super(UI,self).__init__()

        #load the ui file
        uic.loadUi("STXM_data_viewer.ui",self)
        self.setWindowTitle("STXM Data Viewer")

        # define widgets
        self.filterLBL = self.findChild(QLabel, "filerLBL")
        self.startLBL = self.findChild(QLabel, "startLBL")
        self.endLBL = self.findChild(QLabel, "endLBL")
        self.xrangeLBL = self.findChild(QLabel, "xrangeLBL")
        self.yrangeLBL = self.findChild(QLabel, "yrangeLBL")
        self.xresLBL = self.findChild(QLabel, "xresLBL")
        self.yresLBL = self.findChild(QLabel, "yresLBL")
        self.energyLBL = self.findChild(QLabel, "energyLBL")
        self.toLBL = self.findChild(QLabel, "toLBL")

        self.startDT = self.findChild(QDateTimeEdit, "startDT")
        self.endDT = self.findChild(QDateTimeEdit, "endDT")

        self.xrangeSB = self.findChild(QSpinBox, "xrangeSB")
        self.yrangeSB = self.findChild(QSpinBox, "yrangeSB")
        self.xresSB = self.findChild(QSpinBox, "xresSB")
        self.yresSB = self.findChild(QSpinBox, "yresSB")
        self.eminSB = self.findChild(QSpinBox, "eminSB")
        self.emaxSB = self.findChild(QSpinBox, "emaxSB")

        self.scanCB = self.findChild(QComboBox, "scanCB")
        self.fileCB = self.findChild(QComboBox, "fileCB")

        self.progressBar = self.findChild(QProgressBar, "progressBar")

        self.textBrowser = self.findChild(QTextBrowser, "textBrowser")

        self.filterGB = self.findChild(QGroupBox, "filtersGB")

        self.submitBTN = self.findChild(QPushButton, "submitBTN")

        # set up threadpool
        self.threadpool = QThreadPool()

        # connect signals to slots
        self.connectSignals()

    def connectSignals(self):
        self.submitBTN.clicked.connect(self.submit)

    def submit(self):
        self.textBrowser.append("Filters submitted. Preparing database.")
        worker = Worker(self.prepareDatabase)
        worker.signals.finished.connect(lambda: self.textBrowser.append('Database Ready.'))
        self.threadpool.start(worker)
        dlg = progressDialog(parent=self)
        # QMessageBox.about(self,"Preparing Database...","Preparing Database")
        dlg.show()

    def prepareDatabase(self):
        pass

def main():
    app = QApplication(sys.argv)
    UIWindow = UI()
    UIWindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()