
import numpy as np
import os
import h5py
import bson
import pickle

def prepare_database(collection, directory, progress_callback):
    '''
    Finds and submits HDF5 files in a specified directory to the database
    :param collection: the database collection to write to
    :param directory: the root directory in which to find files, as a string
    :param progress_callback: the percent completion of the database, as an integer
    '''
    collection.delete_many({})

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
        name = os.path.basename(file)

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

                start_int = int(start_year + start_month + start_day + start_hour + start_minute)

            end_time = f['entry0']['end_time'][()].decode('utf8')
            # make end_time match the dateTime().toString() format
            if end_time != "":
                end_year = end_time[:4]
                end_month = end_time[5:7]
                end_day = end_time[8:10]

                end_hour = end_time[11:13]
                end_minute = end_time[14:16]

                end_int = int(end_year + end_month + end_day + end_hour + end_minute)

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
            pass
        else:
            try:
                # store entry in db
                result = collection.insert_one({"name": name,
                                                     "directory": directory,
                                                     "file_path": file,
                                                     "data": serialized_data,
                                                     "scan_type": scan_type,
                                                     "start_time": start_int,
                                                     "end_time": end_int,
                                                     "xrange": int(xrange),
                                                     "yrange": int(yrange),
                                                     "xresolution": xres,
                                                     "yresolution": yres,
                                                     "energy_min": min(energies_lst),
                                                     "energy_max": max(energies_lst)
                                                     })

            except Exception as e:
                pass
        finally:
            # clean up
            f.close()

        progress_callback.emit(int((index / max_index) * 100))
        index += 1
