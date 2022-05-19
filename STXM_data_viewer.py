from PyQt5.QtWidgets import QGraphicsView, QWidget, QLineEdit, QComboBox, QVBoxLayout, QDialog, QGroupBox, QTextBrowser, QMainWindow, QApplication, QPushButton, QLabel, QMessageBox, QDateTimeEdit, QSpinBox, QProgressBar
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
import pyqtgraph as pg
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
        self.yrangeSB = self.findChild(QSpinBox, "yrangeSB")
        self.yrangeSB.setMaximum(9999)
        self.xresSB = self.findChild(QSpinBox, "xresSB")
        self.xresSB.setMaximum(9999)
        self.yresSB = self.findChild(QSpinBox, "yresSB")
        self.yresSB.setMaximum(9999)
        self.eminSB = self.findChild(QSpinBox, "eminSB")
        self.eminSB.setMaximum(9999)
        self.emaxSB = self.findChild(QSpinBox, "emaxSB")
        self.emaxSB.setMaximum(9999)

        self.scanCB = self.findChild(QComboBox, "scanCB")
        self.fileCB = self.findChild(QComboBox, "fileCB")

        self.progressBar = self.findChild(QProgressBar, "progressBar")

        self.textBrowser = self.findChild(QTextBrowser, "textBrowser")
        self.textBrowser.moveCursor(QtGui.QTextCursor.End)

        self.dirLE = self.findChild(QLineEdit, "dirLE")

        self.filterGB = self.findChild(QGroupBox, "filtersGB")

        self.submitBTN = self.findChild(QPushButton, "submitBTN")
        self.clearBTN = self.findChild(QPushButton, "clearBTN")
        self.filterBTN = self.findChild(QPushButton, "filterBTN")

        self.progBar = self.findChild(QProgressBar, "progressBar")
        self.progBar.hide()

        # self.fileGV = self.findChild(QGraphicsView, "graphicsView")

        # clear filters
        self.scan_type = False
        self.start_date = False
        self.end_date = False
        self.xres = False
        self.yres = False
        self.xrange = False
        self.yrange = False
        self.energy = False

        # hide filter selectors to start
        self.hideFilters()


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
        self.fileCB.activated.connect(lambda: self.displayHDF(self.fileCB.currentText()))

    def hideFilters(self):
        self.filterLBL.hide()
        self.startLBL.hide()
        self.endLBL.hide()
        self.xrangeLBL.hide()
        self.yrangeLBL.hide()
        self.xresLBL.hide()
        self.yresLBL.hide()
        self.energyLBL.hide()
        self.toLBL.hide()

        self.scanCB.hide()
        self.startDT.hide()
        self.endDT.hide()
        self.xrangeSB.hide()
        self.yrangeSB.hide()
        self.xresSB.hide()
        self.yresSB.hide()
        self.eminSB.hide()
        self.emaxSB.hide()

    def showFilters(self):
        self.filterLBL.show()
        self.startLBL.show()
        self.endLBL.show()
        self.xrangeLBL.show()
        self.yrangeLBL.show()
        self.xresLBL.show()
        self.yresLBL.show()
        self.energyLBL.show()
        self.toLBL.show()

        self.scanCB.show()
        self.startDT.show()
        self.endDT.show()
        self.xrangeSB.show()
        self.yrangeSB.show()
        self.xresSB.show()
        self.yresSB.show()
        self.eminSB.show()
        self.emaxSB.show()

    def clearSelections(self):
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

        # hide filters
        self.hideFilters()

        # reset image
        pixmap = QtGui.QPixmap("white.png")
        self.imgLBL.setPixmap(pixmap)

    def displayHDF(self, filename):
        if filename == "Select a File":
            pixmap = QtGui.QPixmap("white.png")
        else:
            self.textBrowser.append("Displaying file " + filename)
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)
            db_file = self.collection.find_one({"name": filename})
            data = pickle.loads(db_file["data"])

            img = Image.fromarray(data, 'RGB')
            img.save(filename[:-5] + '.png')
            img.show()

            img = QtGui.QImage(data.data, data.shape[1], data.shape[0], QtGui.QImage.Format_Grayscale16)
            pixmap = QtGui.QPixmap(img)


        self.imgLBL.setPixmap(pixmap)


    def threadFinished(self):
        self.textBrowser.append('Database Ready.')
        self.textBrowser.moveCursor(QtGui.QTextCursor.End)
        self.showFilters()
        # self.progBar.hide()

    def submit(self):
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

        if self.filterLBL.isHidden():
            self.textBrowser.append("ERROR: No filters to submit. Create a database first.")
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)
        else:
            self.fileCB.clear()
            self.fileCB.addItem("Select a File")

            pixmap = QtGui.QPixmap("white.png")
            self.imgLBL.setPixmap(pixmap)

            self.textBrowser.append("Filters submitted.")
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)

            if self.scanCB.currentText() != "Scan Type...":
                self.scan_type = True
            else:
                self.scan_type = False

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
            else:
                self.xres = False

            if self.yresSB.value() != 0:
                self.yres = True
            else:
                self.yres = False

            if self.xrangeSB.value() != 0:
                self.xrange = True
            else:
                self.xrange = False

            if self.yrangeSB.value() != 0:
                self.yrange = True
            else:
                self.yrange = False

            if self.emaxSB.value() != 0:
                self.energy = True
            else:
                self.energy = False

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

            # if (self.scan_type and self.start_date and self.end_date and self.xres and self.yres and
            #         self.xrange and self.yrange and self.energy):
            #     # all filters
            #     filtered = list(self.collection.find({"scan_type": self.scanCB.currentText(),
            #                                           "start_time": start,
            #                                           "end_time:": end,
            #                                           "xrange": self.xrangeSB.value(),
            #                                           "yrange": self.yrangeSB.value(),
            #                                           "xres": self.xresSB.value(),
            #                                           "yes": self.yresSB.value(),
            #                                           "energy": {
            #                                               "$in": list(range(self.eminSB.value(), self.emaxSB.value()))}
            #                                           }))

            if (self.scan_type and not self.start_date and not self.end_date and not self.xres and not self.yres and
                    not self.xrange and not self.yrange and not self.energy ):
                # only scan_type filter
                filtered = list(self.collection.find({"scan_type": self.scanCB.currentText()}))

            elif (not self.scan_type and self.start_date and not self.end_date and not self.xres and not self.yres and
                    not self.xrange and not self.yrange and not self.energy ):
                # only start date filter
                filtered = list(self.collection.find({"start_time": start}))

            elif (not self.scan_type and not self.start_date and self.end_date and not self.xres and not self.yres and
                    not self.xrange and not self.yrange and not self.energy):
                # only end date filter
                filtered = list(self.collection.find({"end_time": self.endDT.dateTime()}))

            elif (not self.scan_type and not self.start_date and not self.end_date and self.xres and not self.yres and
                    not self.xrange and not self.yrange and not self.energy ):
                # only x resolution filter
                filtered = list(self.collection.find({"xresolution": self.xresSB.value()}))

            elif (not self.scan_type and not self.start_date and not self.end_date and not self.xres and self.yres and
                    not self.xrange and not self.yrange and not self.energy ):
                # only y resolution filter
                filtered = list(self.collection.find({"yresolution": self.yresSB.value()}))

            elif (not self.scan_type and not self.start_date and not self.end_date and not self.xres and not self.yres and
                     self.xrange and not self.yrange and not self.energy):
                # only x range filter
                filtered = list(self.collection.find({"xrange" : self.xrangeSB.value()}))

            elif (not self.scan_type and not self.start_date and not self.end_date and not self.xres and not self.yres and
                    not self.xrange and self.yrange and not self.energy ):
                # only y range filter
                filtered = list(self.collection.find({"yrange" : self.yrangeSB.value()}))

            elif (not self.scan_type and not self.start_date and not self.end_date and not self.xres and not self.yres and
                    not self.xrange and not self.yrange and self.energy ):
                # only energy filter
                filtered = list(self.collection.find({"energies" : {'$in': list(range(self.eminSB.value(), self.emaxSB.value()))}}))

            # elif (self.scan_type and self.start_date and not self.end_date and not self.xres and not self.yres and
            #         not self.xrange and not self.yrange and not self.energy ):
            #     # scan type and start date
            #     filtered = list(self.collection.find({"scan_type": self.scanCB.currentText(),
            #                                           "start_time": start
            #                                           }))
            # elif (self.scan_type and not self.start_date and self.end_date and not self.xres and not self.yres and
            #       not self.xrange and not self.yrange and not self.energy):
            #     # scan type and end date
            #     filtered = list(self.collection.find({"scan_type": self.scanCB.currentText(),
            #                                           "end_date": end,
            #                                           }))
            #
            # elif (self.scan_type and not self.start_date and not self.end_date and not self.xres and not self.yres and
            #           not self.xrange and not self.yrange and not self.energy):
            #     # scan type and xres
            #     filtered = list(self.collection.find({"scan_type": self.scanCB.currentText(),
            #                                           "xresolution": self.xresSB.value(),
            #                                           }))
            #
            # elif (self.scan_type and not self.start_date and not self.end_date and not self.xres and self.yres and
            #       not self.xrange and not self.yrange and not self.energy):
            #     # scan type and yres
            #     filtered = list(self.collection.find({"scan_type": self.scanCB.currentText(),
            #                                           "yresolution": self.yresSB.value(),
            #                                           }))
            #
            # elif (self.scan_type and not self.start_date and not self.end_date and not self.xres and not self.yres and
            #       self.xrange and not self.yrange and not self.energy):
            #     # scan type and xrange
            #     filtered = list(self.collection.find({"scan_type": self.scanCB.currentText(),
            #                                           "yrange": self.xrangeSB.value(),
            #                                           }))
            # elif (self.scan_type and not self.start_date and not self.end_date and not self.xres and not self.yres and
            #       not self.xrange and self.yrange and not self.energy):
            #     # scan type and yrange
            #     filtered = list(self.collection.find({"scan_type": self.scanCB.currentText(),
            #                                           "yrange": self.yrangeSB.value(),
            #                                           }))
            #
            # elif (self.scan_type and not self.start_date and not self.end_date and not self.xres and not self.yres and
            #       not self.xrange and not self.yrange and self.energy):
            #     # scan type and energy
            #     filtered = list(self.collection.find({"scan_type": self.scanCB.currentText(),
            #                                           "energy": {"$in": list(range(self.eminSB.value(), self.emaxSB.value()))}
            #                                           }))
            else:
                # no filters
                self.textBrowser.append("No filters applied.")
                filtered = [{}]

            if self.scan_type:
                if self.start_date:
                    if self.end_date:
                        if self.xrange:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters
                                            pass
                                        else:
                                            # all but energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but yres filter
                                            pass
                                        else:
                                            # all but yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but xres filter
                                            pass
                                        else:
                                            # all but xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but yres, xres filter
                                            pass
                                        else:
                                            # all but yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but yrange
                                            pass
                                        else:
                                            # all but energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but yres, yrange filter
                                            pass
                                        else:
                                            # all but yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but xres, yrange filter
                                            pass
                                        else:
                                            # all but xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but yres, xres yrange filter
                                            pass
                                        else:
                                            # all but yres, xres, yrange, and energy filters
                                            pass
                        else:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but xrange
                                            pass
                                        else:
                                            # all but xrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but xrange, yres filter
                                            pass
                                        else:
                                            # all but xrange, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but xrange, xres filter
                                            pass
                                        else:
                                            # all but xrange, xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but xrange, yres, xres filter
                                            pass
                                        else:
                                            # all but xrange, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but xrange, yrange
                                            pass
                                        else:
                                            # all but xrange, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but xrange, yres, yrange filter
                                            pass
                                        else:
                                            # all but xrange, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but xrange, xres, yrange filter
                                            pass
                                        else:
                                            # all but xrange, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but xrange, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but xrange, yres, xres, yrange, and energy filters
                                            pass
                    else:
                        if self.xrange:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but end_date
                                            pass
                                        else:
                                            # all but end, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, yres filter
                                            pass
                                        else:
                                            # all but end, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but end, xres filter
                                            pass
                                        else:
                                            # all but end, xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, yres, xres filter
                                            pass
                                        else:
                                            # all but end, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but end, yrange
                                            pass
                                        else:
                                            # all but end, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, yres, yrange filter
                                            pass
                                        else:
                                            # all but end, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but end, xres, yrange filter
                                            pass
                                        else:
                                            # all but end, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but end, yres, xres, yrange, and energy filters
                                            pass
                        else:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but end, xrange
                                            pass
                                        else:
                                            # all but end, xrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, xrange, yres filter
                                            pass
                                        else:
                                            # all but end, xrange, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but end, xrange, xres filter
                                            pass
                                        else:
                                            # all but end, xrange, xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, xrange, yres, xres filter
                                            pass
                                        else:
                                            # all but end, xrange, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but end, xrange, yrange
                                            pass
                                        else:
                                            # all but end, xrange, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, xrange, yres, yrange filter
                                            pass
                                        else:
                                            # all but end, xrange, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but end, xrange, xres, yrange filter
                                            pass
                                        else:
                                            # all but end, xrange, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, xrange, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but end, xrange, yres, xres, yrange, and energy filters
                                            pass
                else:
                    if self.end_date:
                        if self.xrange:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but start
                                            pass
                                        else:
                                            # all but start, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, yres filter
                                            pass
                                        else:
                                            # all but start, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but start, xres filter
                                            pass
                                        else:
                                            # all but start,  xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, yres, xres filter
                                            pass
                                        else:
                                            # all but start, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but start, yrange
                                            pass
                                        else:
                                            # all but start, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, yres, yrange filter
                                            pass
                                        else:
                                            # all but start, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but start, xres, yrange filter
                                            pass
                                        else:
                                            # all but start, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but start, yres, xres, yrange, and energy filters
                                            pass
                        else:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but start, xrange
                                            pass
                                        else:
                                            # all but start,  xrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, xrange, yres filter
                                            pass
                                        else:
                                            # all but start,  xrange, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but start, xrange, xres filter
                                            pass
                                        else:
                                            # all but start, xrange, xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, xrange, yres, xres filter
                                            pass
                                        else:
                                            # all but start, xrange, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but start, xrange, yrange
                                            pass
                                        else:
                                            # all but start, xrange, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, xrange, yres, yrange filter
                                            pass
                                        else:
                                            # all but start, xrange, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but start, xrange, xres, yrange filter
                                            pass
                                        else:
                                            # all but start, xrange, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, xrange, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but start, xrange, yres, xres, yrange, and energy filters
                                            pass
                    else:
                        if self.xrange:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but start, end_date
                                            pass
                                        else:
                                            # all but start, end, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, end, yres filter
                                            pass
                                        else:
                                            # all but start, end, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but start, end, xres filter
                                            pass
                                        else:
                                            # all but start, end, xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, end, yres, xres filter
                                            pass
                                        else:
                                            # all but start, end, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but start, end, yrange
                                            pass
                                        else:
                                            # all but start, end, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, end, yres, yrange filter
                                            pass
                                        else:
                                            # all but start, end, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but start, end, xres, yrange filter
                                            pass
                                        else:
                                            # all but start, end, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, end, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but start, end, yres, xres, yrange, and energy filters
                                            pass
                        else:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but start, end, xrange
                                            pass
                                        else:
                                            # all but start, end, xrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, end, xrange, yres filter
                                            pass
                                        else:
                                            # all but start, end, xrange, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but start, end, xrange, xres filter
                                            pass
                                        else:
                                            # all but start, end, xrange, xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, end, xrange, yres, xres filter
                                            pass
                                        else:
                                            # all but start, end, xrange, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but start, end, xrange, yrange
                                            pass
                                        else:
                                            # all but start, end, xrange, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, end, xrange, yres, yrange filter
                                            pass
                                        else:
                                            # all but start, end, xrange, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but start, end, xrange, xres, yrange filter
                                            pass
                                        else:
                                            # all but start, end, xrange, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but start, end, xrange, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but start, end, xrange, yres, xres, yrange, and energy filters
                                            pass
            else:
                if self.start_date:
                    if self.end_date:
                        if self.xrange:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters
                                            pass
                                        else:
                                            # all but energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but yres filter
                                            pass
                                        else:
                                            # all but yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but xres filter
                                            pass
                                        else:
                                            # all but xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but yres, xres filter
                                            pass
                                        else:
                                            # all but yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but yrange
                                            pass
                                        else:
                                            # all but energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but yres, yrange filter
                                            pass
                                        else:
                                            # all but yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but xres, yrange filter
                                            pass
                                        else:
                                            # all but xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but yres, xres yrange filter
                                            pass
                                        else:
                                            # all but yres, xres, yrange, and energy filters
                                            pass
                        else:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but xrange
                                            pass
                                        else:
                                            # all but xrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but xrange, yres filter
                                            pass
                                        else:
                                            # all but xrange, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but xrange, xres filter
                                            pass
                                        else:
                                            # all but xrange, xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but xrange, yres, xres filter
                                            pass
                                        else:
                                            # all but xrange, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but xrange, yrange
                                            pass
                                        else:
                                            # all but xrange, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but xrange, yres, yrange filter
                                            pass
                                        else:
                                            # all but xrange, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but xrange, xres, yrange filter
                                            pass
                                        else:
                                            # all but xrange, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but xrange, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but xrange, yres, xres, yrange, and energy filters
                                            pass
                    else:
                        if self.xrange:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but end_date
                                            pass
                                        else:
                                            # all but end, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, yres filter
                                            pass
                                        else:
                                            # all but end, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but end, xres filter
                                            pass
                                        else:
                                            # all but end, xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, yres, xres filter
                                            pass
                                        else:
                                            # all but end, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but end, yrange
                                            pass
                                        else:
                                            # all but end, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, yres, yrange filter
                                            pass
                                        else:
                                            # all but end, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but end, xres, yrange filter
                                            pass
                                        else:
                                            # all but end, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but end, yres, xres, yrange, and energy filters
                                            pass
                        else:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but end, xrange
                                            pass
                                        else:
                                            # all but end, xrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, xrange, yres filter
                                            pass
                                        else:
                                            # all but end, xrange, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but end, xrange, xres filter
                                            pass
                                        else:
                                            # all but end, xrange, xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, xrange, yres, xres filter
                                            pass
                                        else:
                                            # all but end, xrange, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but end, xrange, yrange
                                            pass
                                        else:
                                            # all but end, xrange, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, xrange, yres, yrange filter
                                            pass
                                        else:
                                            # all but end, xrange, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but end, xrange, xres, yrange filter
                                            pass
                                        else:
                                            # all but end, xrange, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but end, xrange, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but end, xrange, yres, xres, yrange, and energy filters
                                            pass
                else:
                    if self.end_date:
                        if self.xrange:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but scan, start
                                            pass
                                        else:
                                            # all but scan, start, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, yres filter
                                            pass
                                        else:
                                            # all but scan, start, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but scan, start, xres filter
                                            pass
                                        else:
                                            # all but scan, start,  xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, yres, xres filter
                                            pass
                                        else:
                                            # all but scan, start, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but scan, start, yrange
                                            pass
                                        else:
                                            # all but scan, start, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, yres, yrange filter
                                            pass
                                        else:
                                            # all but scan, start, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but scan, start, xres, yrange filter
                                            pass
                                        else:
                                            # all but scan, start, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but scan, start, yres, xres, yrange, and energy filters
                                            pass
                        else:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but scan, start, xrange
                                            pass
                                        else:
                                            # all but scan, start,  xrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, xrange, yres filter
                                            pass
                                        else:
                                            # all but scan, start,  xrange, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but scan, start, xrange, xres filter
                                            pass
                                        else:
                                            # all but scan, start, xrange, xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, xrange, yres, xres filter
                                            pass
                                        else:
                                            # all but scan, start, xrange, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but scan, start, xrange, yrange
                                            pass
                                        else:
                                            # all but scan, start, xrange, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, xrange, yres, yrange filter
                                            pass
                                        else:
                                            # all but scan, start, xrange, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but scan, start, xrange, xres, yrange filter
                                            pass
                                        else:
                                            # all but scan, start, xrange, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, xrange, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but scan, start, xrange, yres, xres, yrange, and energy filters
                                            pass
                    else:
                        if self.xrange:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but scan, start, end_date
                                            pass
                                        else:
                                            # all but scan, start, end, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, end, yres filter
                                            pass
                                        else:
                                            # all but scan, start, end, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but scan, start, end, xres filter
                                            pass
                                        else:
                                            # all but scan, start, end, xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, end, yres, xres filter
                                            pass
                                        else:
                                            # all but scan, start, end, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but scan, start, end, yrange
                                            pass
                                        else:
                                            # all but scan, start, end, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, end, yres, yrange filter
                                            pass
                                        else:
                                            # all but scan, start, end, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but scan, start, end, xres, yrange filter
                                            pass
                                        else:
                                            # all but scan, start, end, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, end, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but scan, start, end, yres, xres, yrange, and energy filters
                                            pass
                        else:
                            if self.yrange:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but scan, start, end, xrange
                                            pass
                                        else:
                                            # all but scan, start, end, xrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, end, xrange, yres filter
                                            pass
                                        else:
                                            # all but scan, start, end, xrange, yres and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but scan, start, end, xrange, xres filter
                                            pass
                                        else:
                                            # all but scan, start, end, xrange, xres, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, end, xrange, yres, xres filter
                                            pass
                                        else:
                                            # all but scan, start, end, xrange, yres, xres, and energy filters
                                            pass
                            else:
                                if self.xres:
                                    if self.yres:
                                        if self.energy:
                                            # all filters but scan, start, end, xrange, yrange
                                            pass
                                        else:
                                            # all but scan, start, end, xrange, energy, yrange filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, end, xrange, yres, yrange filter
                                            pass
                                        else:
                                            # all but scan, start, end, xrange, yres, yrange, and energy filters
                                            pass
                                else:
                                    if self.yres:
                                        if self.energy:
                                            # all but scan, start, end, xrange, xres, yrange filter
                                            pass
                                        else:
                                            # all but scan, start, end, xrange, xres, yrange, energy filter
                                            pass
                                    else:
                                        if self.energy:
                                            # all but scan, start, end, xrange, yres, xres yrange filter
                                            pass
                                        else:
                                            # all but scan, start, end, xrange, yres, xres, yrange, and energy filters
                                            pass


            for item in filtered:
                self.fileCB.addItem(item['name'])


    def trackProgress(self, progress):
        self.progBar.setValue(progress)

    def prepareDatabase(self, directory, progress_callback):
        # files = glob.glob(direct + "\\*.hdf5", recursive=True)
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
                serialized_data = bson.Binary(pickle.dumps(data, protocol=2))
                scan_type = f['entry0']['counter0']['stxm_scan_type'][()].decode('utf8')

                start_time = f['entry0']['start_time'][()].decode('utf8')
                # make start_time match the dateTime.toSting() format
                if start_time != "":
                    start_year = start_time[:4]
                    start_month = start_time[5:7]
                    start_day = start_time[8:10]

                    start_hour = start_time[11:13]
                    start_minute = start_time[14:16]

                    start = datetime.datetime.strptime(start_year + start_month + start_day + start_hour + start_minute,
                                                       "%Y%m%d%H%M")

                    start_str = datetime.datetime.strftime(start, "%a %b %d %H:%M:00 %Y").rstrip()
                    print (start_str)

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
                if xpoints.size == 1:
                    xpoints = np.append(xpoints, 0)
                    xres = 1
                else:
                    xres = xpoints.size
                xstart = xpoints[0]
                xstop = xpoints[-1]
                xrange = np.fabs(xstop - xstart)
                ypoints = (f['entry0']['counter0']['sample_y'][()])
                if ypoints.size == 1:
                    ypoints = np.append(ypoints, 0)
                    yres = 1
                else:
                    yres = ypoints.size
                ystart = ypoints[0]
                ystop = ypoints[-1]
                yrange = np.fabs(ystop - ystart)

                energies_lst = list(f['entry0']['counter0']['energy'][()])
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
                                                         # "data": data,
                                                         "data": serialized_data,
                                                         "scan_type": scan_type,
                                                         "start_time": start_str,
                                                         "end_time": end_str,
                                                         "xrange": int(xrange),
                                                         "yrange": int(yrange),
                                                         "xresolution": xres,
                                                         "yresolution": yres,
                                                         "energies": energies_lst
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