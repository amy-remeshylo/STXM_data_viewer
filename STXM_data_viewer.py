from PyQt5.QtWidgets import QWidget, QLineEdit, QComboBox, QVBoxLayout, QDialog, QGroupBox, QTextBrowser, QMainWindow, QApplication, QPushButton, QLabel, QMessageBox, QDateTimeEdit, QSpinBox, QProgressBar
from PyQt5 import uic
from PyQt5.QtCore import QRunnable, pyqtSignal, QObject, QThreadPool
from PyQt5 import QtGui
import sys
from pymongo import MongoClient
import h5py
import numpy as np
import glob
import datetime
import os

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

            self.kwargs['progress_callback'] = self.signals.progress

        def run(self):
            self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit()

# class progressDialog(QDialog):
#     def __init__(self):
#         super(progressDialog, self).__init__()
#
#         uic.loadUi("preparing_database_dlg.ui", self)
#         self.setWindowTitle("Preparing Database")
#
#         self.progBar = self.findChild(QProgressBar, "progressBar")
#         self.progBar.setValue(0)


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
        self.dirLBL = self.findChild(QLabel, "dirLBL")
        self.imgLBL = self.findChild(QLabel, "imgLBL")

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
        self.textBrowser.moveCursor(QtGui.QTextCursor.End)

        self.dirLE = self.findChild(QLineEdit, "dirLE")

        self.filterGB = self.findChild(QGroupBox, "filtersGB")

        self.submitBTN = self.findChild(QPushButton, "submitBTN")
        self.clearBTN = self.findChild(QPushButton, "clearBTN")

        self.progBar = self.findChild(QProgressBar, "progressBar")
        self.progBar.hide()

        # clear filters
        self.scan_type = False
        self.start_date = False
        self.end_date = False
        self.xres = False
        self.yres = False
        self.xrange = False
        self.yrange = False
        self.energy = False

        # set up threadpool
        self.threadpool = QThreadPool()

        # set up mongodb database
        self.cluster = "mongodb://localhost:27017"
        self.client = MongoClient(self.cluster)
        self.db = self.client["STXM_data_viewer"]
        self.collection = self.db["STXM_data"]
        # start with a cleared db
        self.collection.delete_many({})

        # connect signals to slots
        self.submitBTN.clicked.connect(self.submit)
        self.clearBTN.clicked.connect(self.clear)

    def clear(self):
        # show clear message on text browser
        self.textBrowser.append("Filters Cleared.")
        self.textBrowser.moveCursor(QtGui.QTextCursor.End)
        # clear line edit and set all spin boxes, combo boxes, and date times back to default
        self.dirLE.setText("")
        self.xrangeSB.setValue(0)
        self.yrangeSB.setValue(0)
        self.xresSB.setValue(0)
        self.yresSB.setValue(0)
        self.eminSB.setValue(0)
        self.emaxSB.setValue(0)
        self.scanCB.setCurrentIndex(0)
        self.startDT.setDateTime(datetime.datetime(2000, 1, 1, 00, 00))
        self.endDT.setDateTime(datetime.datetime(2000, 1, 1, 00, 00))

        # clear filter combo box
        self.fileCB.clear()
        self.fileCB.addItem("Select a File")

        # reset and hide progress bar from view
        self.progBar.hide()
        self.progBar.setValue(0)

        # clear filters
        self.scan_type = False
        self.start_date = False
        self.end_date = False
        self.xres = False
        self.yres = False
        self.xrange = False
        self.yrange = False
        self.energy = False

    def threadFinished(self):
        self.textBrowser.append('Database Ready.')
        self.textBrowser.moveCursor(QtGui.QTextCursor.End)
        # self.progBar.hide()

    def submit(self):
        self.textBrowser.append("Filters submitted. Preparing database.")
        self.textBrowser.moveCursor(QtGui.QTextCursor.End)
        if self.dirLE.text() != "":
            self.progBar.setValue(0)
            self.progBar.show()
            # worker = Worker(lambda: self.prepareDatabase(self.dirLE.text(), self.signals.progress))
            worker = Worker(self.prepareDatabase, self.dirLE.text())
            worker.signals.finished.connect(self.threadFinished)
            worker.signals.progress.connect(self.trackProgress)
            self.threadpool.start(worker)
            # dlg = progressDialog()
            # dlg.exec_()
        else:
            self.textBrowser.append("ERROR: File Directory field is required.")
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)
    #
    # def filter(self):
    #     if self.scanTE.currentIndex() != 0:
    #         self.scan_type = True
    #     else:
    #         self.scan_type = False
    #
    #     if self.startDT.dateTime() != datetime.datetime(2000, 1, 1, 00, 00):
    #         self.start_date = True
    #     else:
    #         self.start_date = False
    #
    #     if self.endDT.dateTime() != datetime.datetime(2000, 1, 1, 00, 00):
    #         self.end_date = True
    #     else:
    #         self.end_date = False
    #
    #     if self.xresSB.value() != 0:
    #         self.xres = True
    #     else:
    #         self.xres = False
    #
    #     if self.yresSB.value() != 0:
    #         self.yres = True
    #     else:
    #         self.yres = False
    #
    #     if self.xrangeSB.value() != 0:
    #         self.xrange = True
    #     else:
    #         self.xrange = False
    #
    #     if self.yrangeSB.value() != 0:
    #         self.yrange = True
    #     else:
    #         self.yrange = False
    #
    #     if self.emaxSB != 0:
    #         self.energy = True
    #     else:
    #         self.energy = False
    #
    #     if (not self.scan_type and not self.start_date and not self.end_date and not self.xres and not self.yres and
    #             not self.xrange and not self.yrange and not self.energy ):
    #         # no filters
    #         filtered = self.collection.find({})
    #         print (filtered)
    #
    #     for item in filtered:
    #         self.fileCB.addItems(item.name)


    def trackProgress(self, progress):
        self.progBar.setValue(progress)

    def prepareDatabase(self, directory, progress_callback):
        # files = glob.glob(direct + "\\*.hdf5", recursive=True)

        file_paths = []  # List which will store all the full filepaths.

        # Walk the tree.
        for root, directories, files in os.walk(directory):
            for filename in files:
                if filename[-5:] == ".hdf5":
                    # Join the two strings in order to form the full filepath.
                    filepath = os.path.join(root, filename)
                    file_paths.append(filepath)  # Add it to the list.

        # max index and current index for calculation of % completion
        max_index = len(file_paths)
        index = 1

        for file in file_paths:
            name = ""
            i = 1
            character = file[-i]
            while character != "\\":
                name = character + name
                i += 1
                character = file[-i]

            f = h5py.File(file, "r")

            try:
                # get info to put into database
                data = f['entry0']['counter0']['data'][()]
                scan_type = f['entry0']['counter0']['stxm_scan_type'][()].decode('utf8')
                start_time = f['entry0']['start_time'][()].decode('utf8')
                end_time = f['entry0']['end_time'][()].decode('utf8')
                counter0_attrs = list(f['entry0']['counter0'].attrs)
                # 'signal' is in counter0_attrs list
                ctr0_signal = f['entry0']['counter0'].attrs['signal']
                ctr0_data = f['entry0']['counter0'][ctr0_signal][()]

                xpoints = np.array(f['entry0']['counter0']['sample_x'][()])
                if xpoints.size == 1:
                    xpoints = np.append(xpoints, 0)
                    xres = 1
                else:
                    xres = xpoints.size
                xstart = xpoints[0]
                xstop = xpoints[-1]
                xrange = np.fabs(xstop - xstart)
                ypoints = np.array(f['entry0']['counter0']['sample_y'][()])
                if ypoints.size == 1:
                    ypoints = np.append(ypoints, 0)
                    yres = 1
                else:
                    yres = ypoints.size
                ystart = ypoints[0]
                ystop = ypoints[-1]
                yrange = np.fabs(ystop - ystart)

                energies_lst = list(f['entry0']['counter0']['energy'][()])
            except Exception as e:
                self.textBrowser.append("ERROR: " + str(e))
                self.textBrowser.moveCursor(QtGui.QTextCursor.End)
            else:
                # store entry in db
                result = self.collection.insert_one({"name": name,
                                                     "file_path": file,
                                                     "scan_type": scan_type,
                                                     "start_time": start_time,
                                                     "end_time": end_time,
                                                     "xrange": xrange,
                                                     "yrange": yrange,
                                                     "xresolution": xres,
                                                     "yresolution": yres,
                                                     "energies": energies_lst
                                                     })
                self.fileCB.addItem(name)
            finally:
                # clean up
                f.close()

            self.textBrowser.append(name)
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)
            progress_callback.emit(int((index / max_index) * 100))
            index += 1

        # self.filter()

def main():
    app = QApplication(sys.argv)
    UIWindow = UI()
    UIWindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()