from PyQt5.QtWidgets import QMainWindow, QApplication, QPushButton, QLabel, QMessageBox, QDateTimeEdit, QSpinBox, QProgressBar
from PyQt5 import uic
from PyQt5.QtGui import QPixmap
import sys

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

        self.progressBar = self.findChild(QProgressBar, "progressBar")

        self.submitBTN = self.findChild(QPushButton, "submitBTN")

        # connect signals to slots
        self.connectSignals()

    def connectSignals(self):
        self.submitBTN.clicked.connect(self.submit)

    def submit (self):
        pass



def main():
    app = QApplication(sys.argv)
    UIWindow = UI()
    UIWindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()