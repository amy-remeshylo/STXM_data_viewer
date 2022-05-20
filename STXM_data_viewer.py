from PyQt5.QtWidgets import QToolButton, QLineEdit, QComboBox,  QFileDialog, QGroupBox, QTextBrowser, QMainWindow, QApplication, QPushButton, QLabel, QMessageBox, QDateTimeEdit, QSpinBox, QProgressBar
from PyQt5 import uic
from PyQt5.QtCore import QRunnable, pyqtSignal, QObject, QThreadPool
from PyQt5 import QtGui
import sys
from pymongo import MongoClient
import bson
import h5py
import numpy as np
import datetime
import os
import pickle
from PIL import Image

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

class UI(QMainWindow):
    def __init__(self):
        '''
        Creates an instance of a UI object
        '''
        super(UI, self).__init__()

        #load the ui file
        uic.loadUi("STXM_data_viewer.ui",self)
        self.setWindowTitle("STXM Data Viewer")

        # define widgets
        self.filterLBL = self.findChild(QLabel, "filterLBL")
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
        self.xrangeSB.setMaximum(9999)
        self.xrangeSB.setMinimum(0)
        self.yrangeSB = self.findChild(QSpinBox, "yrangeSB")
        self.yrangeSB.setMaximum(9999)
        self.yrangeSB.setMinimum(0)
        self.xresSB = self.findChild(QSpinBox, "xresSB")
        self.xresSB.setMaximum(9999)
        self.xresSB.setMinimum(0)
        self.yresSB = self.findChild(QSpinBox, "yresSB")
        self.yresSB.setMaximum(9999)
        self.yresSB.setMinimum(0)
        self.eminSB = self.findChild(QSpinBox, "eminSB")
        self.eminSB.setMaximum(9999)
        self.eminSB.setMinimum(0)
        self.emaxSB = self.findChild(QSpinBox, "emaxSB")
        self.emaxSB.setMaximum(9999)
        self.emaxSB.setMinimum(0)

        self.scanCB = self.findChild(QComboBox, "scanCB")
        self.fileCB = self.findChild(QComboBox, "fileCB")

        self.progressBar = self.findChild(QProgressBar, "progressBar")

        self.textBrowser = self.findChild(QTextBrowser, "textBrowser")
        self.textBrowser.moveCursor(QtGui.QTextCursor.End)

        self.dirLE = self.findChild(QLineEdit, "dirLE")
        self.dirLE.setReadOnly(True)

        self.filterGB = self.findChild(QGroupBox, "filtersGB")

        self.submitBTN = self.findChild(QPushButton, "submitBTN")
        self.clearBTN = self.findChild(QPushButton, "clearBTN")
        self.filterBTN = self.findChild(QPushButton, "filterBTN")
        self.toolBTN = self.findChild(QToolButton, "toolBTN")

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

        # set filter boolean false (no filters may be used)
        self.filterAllowed = False

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
        self.clearBTN.clicked.connect(self.clearSelections)
        self.filterBTN.clicked.connect(self.filter)
        self.toolBTN.clicked.connect(self.selectDirectory)
        self.fileCB.activated.connect(lambda: self.displayHDF(self.fileCB.currentText()))

    def selectDirectory(self):
        '''
        Opens a file explorer window to allow user to choose a directory to search for .hdf5 files
        '''
        directory = QFileDialog.getExistingDirectory(self, "Select Folder", "C:\controls\stxm_data")
        if directory == '':
            # cancel pressed
            self.clearSelections()
        self.dirLE.setText(directory)

    def clearSelections(self):
        '''
        Clears all directory and file selections made by user
        '''
        # show clear message on text browser
        self.textBrowser.append("Selections Cleared.")
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

        # disallow filters
        self.filterAllowed = False

        # reset image
        pixmap = QtGui.QPixmap("white.png")
        self.imgLBL.setPixmap(pixmap)

    def displayHDF(self, filename):
        '''
        Displays an HDF5 file's data to the screen as an image
        :param filename: the filename of the file to be displayed, as a string
        '''
        if filename == "Select a File":
            pixmap = QtGui.QPixmap("white.png")
        else:
            self.textBrowser.append("Displaying file " + filename)
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)
            db_file = self.collection.find_one({"name": filename})
            data = pickle.loads(db_file["data"])

            squeezed_data = np.squeeze(data, axis=0)

            img = Image.fromarray(squeezed_data, 'L')
            img.show()

            img2 = QtGui.QImage(squeezed_data.data, squeezed_data.shape[1], squeezed_data.shape[0], QtGui.QImage.Format_Grayscale16)
            pixmap = QtGui.QPixmap(img2)


        self.imgLBL.setPixmap(pixmap)


    def threadFinished(self):
        '''
        Declares the thread finished on the log and allows filtering of database files
        '''
        self.textBrowser.append('Database Ready.')
        self.textBrowser.moveCursor(QtGui.QTextCursor.End)
        # allow filtering
        self.filterAllowed = True

    def submit(self):
        '''
        Creates a thread for database preparation and updates status on log
        '''
        self.textBrowser.append("Directory submitted. Preparing database.")
        self.textBrowser.moveCursor(QtGui.QTextCursor.End)
        if self.dirLE.text() != "":
            self.progBar.setValue(0)
            self.progBar.show()
            # worker = Worker(lambda: self.prepareDatabase(self.dirLE.text(), self.signals.progress))
            worker = Worker(self.prepareDatabase, self.dirLE.text())
            worker.signals.finished.connect(self.threadFinished)
            worker.signals.progress.connect(self.trackProgress)
            self.threadpool.start(worker)
        else:
            self.textBrowser.append("ERROR: File Directory field is required.")
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)

    def filter(self):
        '''
        Filters files in database according to user selections
        '''

        self.fileCB.clear()
        self.fileCB.addItem("Select a File")

        if not self.filterAllowed:
            self.textBrowser.append("ERROR: No filters to submit. Create a database first.")
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)
        elif self.eminSB.value() > self.emaxSB.value():
            self.textBrowser.append("ERROR: Energy maximum cannot be less than energy minimum.")
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)
        else:
            pixmap = QtGui.QPixmap("white.png")
            self.imgLBL.setPixmap(pixmap)

            self.textBrowser.append("Filters submitted.")
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)

            if self.scanCB.currentText() != "Scan Type...":
                self.scan_type = True
                scan = [self.scanCB.currentText()]
            else:
                self.scan_type = False
                scan = ["coarse image scan", "sample image", "sample focus", "generic scan", ""]
            if self.startDT.dateTime() != datetime.datetime(2000, 1, 1, 00, 00):
                self.start_date = True
            else:
                self.start_date = False

            if self.endDT.dateTime() != datetime.datetime(2000, 1, 1, 00, 00):
                self.end_date = True
            else:
                self.end_date = False

            if self.xresSB.value() != 0:
                self.xres = True
                xresolution = [self.xresSB.value()]
            else:
                self.xres = False
                xresolution = list(range(0,1000))

            if self.yresSB.value() != 0:
                self.yres = True
                yresolution = [self.xresSB.value()]
            else:
                self.yres = False
                yresolution = list(range(0,1000))

            if self.xrangeSB.value() != 0:
                self.xrange = True
                xrang = [self.xrangeSB.value()]
            else:
                self.xrange = False
                xrang = list(range(0, 1000))

            if self.yrangeSB.value() != 0:
                self.yrange = True
                yrang = [self.yrangeSB.value()]
            else:
                self.yrange = False
                yrang = list(range(0, 1000))

            if self.emaxSB.value() != 0:
                self.energy = True
                emax = self.emaxSB.value()
            else:
                self.energy = False
                emax = 9999

            emin = self.eminSB.value()

            # find startDT string object to use with filter
            start = self.startDT.dateTime().toString().rstrip()
            # add 0 padding if necessary
            if len(start) == 23:
                s_beginning = start[:8]
                s_ending = start[8:]
                start = s_beginning + "0" + s_ending

            # find endDT string object to use with filter
            end = self.endDT.dateTime().toString().rstrip()
            # add 0 padding if necessary
            if len(end) == 23:
                e_beginning = end[:8]
                e_ending = end[8:]
                end = e_beginning + "0" + e_ending


            if (not self.scan_type and not self.start_date and not self.end_date and not self.xrange and not self.yrange
                and not self.xres and not self.yres and not self.energy):
                self.textBrowser.append("No filters applied.")
                self.textBrowser.append("Default values may not be used as filters.")
                self.textBrowser.moveCursor(QtGui.QTextCursor.End)

            filtered = self.collection.find({"scan_type": {"$in": scan},
                                             "xresolution": {"$in": xresolution},
                                             "yresolution": {"$in": yresolution},
                                             "xrange": {"$in": xrang},
                                             "yrange": {"$in": yrang},
                                             "energy_min": {"$gte": emin},
                                             "energy_max": {"$lte": emax}
                                             })

            # populate dropdown with filtered items
            for item in filtered:
                self.fileCB.addItem(item['name'])


    def trackProgress(self, progress):
        '''
        Displays progress of database creation to screen
        :param progress: the percent completion of the database, as an integer
        '''
        self.progBar.setValue(progress)

    def prepareDatabase(self, directory, progress_callback):
        '''
        Finds and submits HDF5 files in a specified directory to the database
        :param directory: the root directory in which to find files, as a string
        :param progress_callback: the percent completion of the database, as an integer
        '''
        self.collection.delete_many({})

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

        if len(file_paths) == 0:
            # self.textBrowser.append("No hdf5 files found in directory.")
            progress_callback.emit(100)

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
                # put data into serialized binary form for database storage
                serialized_data = bson.Binary(pickle.dumps(data, protocol=2))

                scan_type = f['entry0']['counter0']['stxm_scan_type'][()].decode('utf8')

                start_time = f['entry0']['start_time'][()].decode('utf8')
                # make start_time match the dateTime().toSting() format
                if start_time != "":
                    start_year = start_time[:4]
                    start_month = start_time[5:7]
                    start_day = start_time[8:10]

                    start_hour = start_time[11:13]
                    start_minute = start_time[14:16]

                    start = datetime.datetime.strptime(start_year + start_month + start_day + start_hour + start_minute,
                                                       "%Y%m%d%H%M")

                    start_str = datetime.datetime.strftime(start, "%a %b %d %H:%M:00 %Y").rstrip()

                end_time = f['entry0']['end_time'][()].decode('utf8')
                # make end_time match the dateTime().toString() format
                if end_time != "":
                    end_year = end_time[:4]
                    end_month = end_time[5:7]
                    end_day = end_time[8:10]

                    end_hour = end_time[11:13]
                    end_minute = end_time[14:16]

                    end = datetime.datetime.strptime(end_year + end_month + end_day + end_hour + end_minute, "%Y%m%d%H%M")

                    end_str = datetime.datetime.strftime(end, "%a %b %d %H:%M:00 %Y")

                counter0_attrs = list(f['entry0']['counter0'].attrs)
                # 'signal' is in counter0_attrs list
                ctr0_signal = f['entry0']['counter0'].attrs['signal']
                ctr0_data = f['entry0']['counter0'][ctr0_signal][()]

                xpoints = (f['entry0']['counter0']['sample_x'][()])
                # pad with 0 if needed
                if xpoints.size == 1:
                    xpoints = np.append(xpoints, 0)
                    xres = 1
                else:
                    xres = xpoints.size
                xstart = xpoints[0]
                xstop = xpoints[-1]
                xrange = np.fabs(xstop - xstart)
                ypoints = (f['entry0']['counter0']['sample_y'][()])

                # pad with 0 if needed
                if ypoints.size == 1:
                    ypoints = np.append(ypoints, 0)
                    yres = 1
                else:
                    yres = ypoints.size
                ystart = ypoints[0]
                ystop = ypoints[-1]
                yrange = np.fabs(ystop - ystart)

                energies_lst = list(f['entry0']['counter0']['energy'][()])
                # convert energies to integers for database storage and filtering
                i = 0
                for energy in energies_lst:
                    energies_lst[i] = int(energy)
                    i += 1

            except Exception as e:
                self.textBrowser.append("ERROR: " + str(e))
                self.textBrowser.moveCursor(QtGui.QTextCursor.End)
            else:
                try:
                    # store entry in db
                    result = self.collection.insert_one({"name": name,
                                                         "file_path": file,
                                                         "data": serialized_data,
                                                         "scan_type": scan_type,
                                                         "start_time": start_str,
                                                         "end_time": end_str,
                                                         "xrange": int(xrange),
                                                         "yrange": int(yrange),
                                                         "xresolution": xres,
                                                         "yresolution": yres,
                                                         "energy_min": min(energies_lst),
                                                         "energy_max": max(energies_lst)
                                                         })

                except Exception as e:
                    self.textBrowser.append(e)
            finally:
                # clean up
                f.close()

            self.fileCB.addItem(name)
            self.textBrowser.append(name)
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)
            progress_callback.emit(int((index / max_index) * 100))
            index += 1

def main():
    app = QApplication(sys.argv)
    UIWindow = UI()
    UIWindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()