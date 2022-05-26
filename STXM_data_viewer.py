import datetime
import getopt
import pickle
import sys
from PIL import Image, ImageOps
from PyQt5 import QtGui
from PyQt5 import uic
from PyQt5.QtCore import QRunnable, pyqtSignal, QObject, QThreadPool
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QApplication
from pymongo import MongoClient
import prepare_database

USAGE = f"Usage: python {sys.argv[0]} [--help] | [-v] [--version] [-p] [--progress] [-d <dir>] [--directory <dir>]"
VERSION = f"{sys.argv[0]} version 1.0"


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

        # load the ui file
        uic.loadUi("STXM_data_viewer.ui", self)
        self.setWindowTitle("STXM Data Viewer")

        self.xrangeSB.setMaximum(9999)
        self.xrangeSB.setMinimum(0)

        self.yrangeSB.setMaximum(9999)
        self.yrangeSB.setMinimum(0)

        self.xresSB.setMaximum(9999)
        self.xresSB.setMinimum(0)

        self.yresSB.setMaximum(9999)
        self.yresSB.setMinimum(0)

        self.eminSB.setMaximum(9999)
        self.eminSB.setMinimum(0)

        self.emaxSB.setMaximum(9999)
        self.emaxSB.setMinimum(0)

        self.textBrowser.moveCursor(QtGui.QTextCursor.End)

        self.dirLE.setReadOnly(True)

        self.progressBar.hide()

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
        # check if db is created at time of launch
        directory = ""
        for item in self.collection.find({}):
            self.fileCB.addItem(item["name"])
            directory = item["directory"]

        # database is already active
        if directory != "":
            self.textBrowser.append("<p style='color:black; margin:0; padding:0'>Database ready.</p>")
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)
            self.filterAllowed = True
            self.dirLE.setText(directory)

        # no active database
        else:
            self.textBrowser.append("<p style='color:black; margin:0; padding:0'>Create a database to start.</p>")
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)
            self.filterAllowed = False
            self.dirLE.setText("")

        # connect signals to slots
        self.submitBTN.clicked.connect(self.submit_database)
        self.clearBTN.clicked.connect(self.clear_selections)
        self.filterBTN.clicked.connect(self.filter_data)
        self.toolBTN.clicked.connect(self.select_directory)
        self.fileCB.activated.connect(lambda: self.display_hdf(self.fileCB.currentText()))

        self.directory, self.trackP = self.parse(sys.argv[1:])

        if self.directory != "":
            self.submit_database()

    def parse(self, args):
        try:
            options, arguments = getopt.getopt(
                args,
                "vhpd:",
                ["version", "help", "progress", "directory="])
        except getopt.GetoptError as err:
            print(err)
            print(USAGE)
            sys.exit()

        directory = ""
        progress = False
        for o, a in options:
            if o in ("-v", "--version"):
                print(VERSION)
                sys.exit()
            if o in ("-h", "--help"):
                print(USAGE)
                sys.exit()
            if o in ("-p", "--progress"):
                progress = True
            if o in ("-d", "--directory"):
                directory = a

        if len(arguments) > 4:
            raise SystemExit(USAGE)
        elif len(options) == 1 and progress:
            print("Progress flag may not be used without -d option")
            raise SystemExit(USAGE)

        return directory, progress

    def select_directory(self):
        '''
        Opens a file explorer window to allow user to choose a directory to search for .hdf5 files
        '''
        directory = QFileDialog.getExistingDirectory(self, "Select Folder", "C:\\controls\\stxm_data")
        if directory == '':
            # cancel pressed
            self.clear_selections()
        self.dirLE.setText(directory)

    def clear_selections(self):
        '''
        Clears all directory and file selections made by user
        '''
        # show clear message on text browser
        self.textBrowser.append("<p style='color:black; margin:0; padding:0'>Selections Cleared.</p>")
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
        self.progressBar.hide()
        self.progressBar.setValue(0)

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

        # clear db
        self.collection.delete_many({})

    def display_hdf(self, filename):
        '''
        Displays an HDF5 file's data to the screen as an image
        :param filename: the filename of the file to be displayed, as a string
        '''
        if filename == "Select a File":
            # no file selected
            pixmap = QtGui.QPixmap("white.png")
        else:
            # display selected file
            try:
                self.textBrowser.append(
                    "<p style='color:black; margin:0; padding:0'>Displaying file " + filename + "</p>")
                self.textBrowser.moveCursor(QtGui.QTextCursor.End)
                db_file = self.collection.find_one({"name": filename})
                data = pickle.loads(db_file["data"])

                # normalize data
                data /= (data.max() / 255)

                # convert numpy array to image
                img = Image.fromarray(data[0].astype("uint8"), "L")
                ImageOps.flip(img).save("temp.png")

                pixmap = QtGui.QPixmap("temp.png")
            except Exception as e:
                self.textBrowser.append("<p style='color:red; margin:0; padding:0'>ERROR: " + str(e) + "</p>")
                self.textBrowser.moveCursor(QtGui.QTextCursor.End)

        # display pixmap
        self.imgLBL.setPixmap(pixmap)

        # rearrange start data to a viewable form
        date = db_file['start_time']
        date_dt = datetime.datetime.strptime(str(date), "%Y%m%d%H%M")
        date_str = datetime.datetime.strftime(date_dt, "%b %d %Y, %H:%M")

        # set tool tip text
        self.imgLBL.setToolTip(f"<b>Scan Type:</b> {db_file['scan_type']}<br></br>"
                               f"<b>Energy:</b> {db_file['energy_min']} - {db_file['energy_max']} eV<br></br>"
                               f"<b>Date:</b> {date_str}")

        # show tool tip for 30s
        self.imgLBL.setToolTipDuration(30000)

    def thread_finished(self):
        '''
        Declares the thread finished on the log and allows filtering of database files
        '''

        # populate dropdown
        self.fileCB.clear()
        self.fileCB.addItem("Select a File")
        for item in self.collection.find({}):
            self.fileCB.addItem(item["name"])

        self.textBrowser.append(self.format_msg("log_msg", "Database ready."))
        self.textBrowser.moveCursor(QtGui.QTextCursor.End)

        # conditions for command line args
        if self.trackP:
            print("Database ready.")

        if self.directory != "":
            sys.exit()

        # allow filtering
        self.filterAllowed = True

        # hide progress bar
        self.progressBar.hide()

    def submit_database(self):
        '''
        Creates a thread for database preparation and updates status on log
        '''
        self.textBrowser.append(self.format_msg("log_msg", "Directory submitted. Preparing database."))
        self.textBrowser.moveCursor(QtGui.QTextCursor.End)

        if self.trackP:
            print("Directory submitted. Preparing database.")

        # directory specified from command line
        if self.directory != "":
            self.dirLE.setText(self.directory)

        # directory specified in GUI
        if self.dirLE.text() != "":
            self.progressBar.setValue(0)
            self.progressBar.show()
            worker = Worker(prepare_database.prepare_database, self.collection, self.dirLE.text())
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.progress.connect(self.track_progress)
            self.threadpool.start(worker)

        # no directory specified
        else:
            self.textBrowser.append(self.format_msg("log_error", "ERROR: File Directory field is required."))
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)

    def filter_data(self):
        '''
        Filters files in database according to user selections
        '''

        self.fileCB.clear()
        self.fileCB.addItem("Select a File")

        if not self.filterAllowed:
            self.textBrowser.append(self.format_msg("log_error", "ERROR: No filters to submit. Create a database first."))
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)
        elif self.eminSB.value() > self.emaxSB.value():
            self.textBrowser.append(self.format_msg("log_error", "ERROR: Energy maximum cannot be less than energy minimum."))
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)
        else:
            pixmap = QtGui.QPixmap("white.png")
            self.imgLBL.setPixmap(pixmap)

            self.textBrowser.append(self.format_msg("log_msg", "Filters submitted."))
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)

            if self.scanCB.currentText() != "Scan Type...":
                self.scan_type = True
                scan = [self.scanCB.currentText()]
            else:
                self.scan_type = False
                scan = ["coarse image scan", "sample image", "sample focus", "generic scan", "sample point spectrum",
                        "sample line spectrum", "sample image stack", "osa image", "osa focus", "detector image"]

            if self.startDT.dateTime() != datetime.datetime(2000, 1, 1, 00, 00):
                self.start_date = True
                # find startDT object to use with filter
                start_str = self.startDT.dateTime().toString()
                # datetime object
                start_dt = datetime.datetime.strptime(start_str, "%a %b %d %H:%M:00 %Y")
                # turn into a comparable integer
                start_int = int(datetime.datetime.strftime(start_dt, "%Y%m%d%H%M"))
            else:
                self.start_date = False
                start_dt = datetime.datetime(1970, 1, 1, 00, 00)
                # turn into a comparable integer
                start_int = int(datetime.datetime.strftime(start_dt, "%Y%m%d%H%M"))

            if self.endDT.dateTime() != datetime.datetime(2000, 1, 1, 00, 00):
                self.end_date = True
                # find endtDT object to use with filter
                end_str = self.endDT.dateTime().toString()
                # datetime object
                end_dt = datetime.datetime.strptime(end_str, "%a %b %d %H:%M:00 %Y")
                # turn into a comparable integer
                end_int = int(datetime.datetime.strftime(end_dt, "%Y%m%d%H%M"))
            else:
                self.end_date = False
                end_dt = datetime.datetime.now()
                end_int = int(datetime.datetime.strftime(end_dt, "%Y%m%d%H%M"))

            if self.xresSB.value() != 0:
                self.xres = True
                xresolution = [self.xresSB.value()]
            else:
                self.xres = False
                xresolution = list(range(0, 1000))

            if self.yresSB.value() != 0:
                self.yres = True
                yresolution = [self.xresSB.value()]
            else:
                self.yres = False
                yresolution = list(range(0, 1000))

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

            if (not self.scan_type and not self.start_date and not self.end_date and not self.xrange and not self.yrange
                    and not self.xres and not self.yres and not self.energy):
                self.textBrowser.append(self.format_msg("log_msg", "No filters applied."))
                self.textBrowser.append(self.format_msg("log_msg", "Default values may not be used as filters."))
                self.textBrowser.moveCursor(QtGui.QTextCursor.End)

            filtered = self.collection.find({"scan_type": {"$in": scan},
                                             "xresolution": {"$in": xresolution},
                                             "yresolution": {"$in": yresolution},
                                             "xrange": {"$in": xrang},
                                             "yrange": {"$in": yrang},
                                             "energy_min": {"$gte": emin},
                                             "energy_max": {"$lte": emax},
                                             "start_time": {"$gte": start_int},
                                             "end_time": {"$lte": end_int}
                                             })

            # populate dropdown with filtered items
            for item in filtered:
                self.fileCB.addItem(item['name'])

    def track_progress(self, progress):
        '''
        Displays progress of database creation to screen
        :param progress: the percent completion of the database, as an integer
        '''
        self.progressBar.setValue(progress)

        if self.trackP:
            print(f"Database creation: {progress}%", end="\r")
            if progress == 100:
                print(end="\n")


    def format_msg(self, format, msg):
        '''
        Provides markup tags to messages based on specified formats
        :param format: the formatting rule to follow, as a string. One of "log_msg", "log_error".
        :param msg: the message to be formatted, as a string
        :return: the formatted message, as a string
        '''
        if format == "log_msg":
            msg = "<p style='color:black; margin:0; padding:0'>" + msg + "</p>"
        elif format == "log_error":
            msg = "<p style='color:red; margin:0; padding:0'>" + msg + "</p>"
        else:
            pass
        return msg


def main():
    app = QApplication(sys.argv)
    UIWindow = UI()
    if not sys.argv[1:]:
        UIWindow.show()
    # UIWindow.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
