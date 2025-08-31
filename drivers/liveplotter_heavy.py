#!/usr/bin/env python3

from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import pyqtgraph as pg
import numpy as np
from PyQt5.QtWidgets import QApplication
import time
import threading

from functools import partial
import multiprocess as mp, queue
from queue import Empty
import operator


'''
General threadsafe subprocessed live plotter using pyqtgraph 
brought over by Mingsong WU circa 2023

This version is more performant but might take up more cpu

workerbee, liveplotterwindow, livemultwindow, LiveWindowLike set up 
the plot styling and update system

liveplotprocess, liveplotagent, __Qapp_liveplot__ set up the data transfer
ecosystem based on multiprocessing task/data queues

USER ACCESSED FUNCTIONS AT BOTTOM OF SCRIPT
'''

class __WorkerBee__(QtCore.QThread): 
    """
    WorkerBee is a QThread object that emits a signal every
                                                    refresh_interval seconds.
    The signal is connected to a slot in the LivePlotterWindow object that
                                                            updates the plot.
    """

    signal1 = QtCore.pyqtSignal(np.ndarray)
    signal2 = QtCore.pyqtSignal(bool)
    # signal is a pyqtSignal object that emits a numpy array

    def __init__(self, data_func, isHidden_toggle, refresh_interval):
        super().__init__()

        self.isHidden = isHidden_toggle
        self.data_func = data_func
        self.refresh_interval = refresh_interval

    def run(self):

        while not self.isHidden():
            data = self.data_func()
            self.signal1.emit(data)
            time.sleep(self.refresh_interval)
        self.quit()
        print("WorkerBee vi saluta")
        self.signal2.emit(True)

class __LiveWindowLike__(QtWidgets.QWidget):

    def __init__(
        self,
        data_func,
        title,
        xlabel,
        ylabel,
        refresh_interval,
        no_plots,
        plot_labels,
        verbose,
    ):
        super().__init__()
        self.window = pg.GraphicsLayoutWidget(show=True, title="Live Plotting Window")
        self.window.resize(900, 500)
        pg.setConfigOptions(antialias=True)
        
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title = title
        self.refresh_interval = refresh_interval
        self.no_plots = no_plots
        self.plot_labels = plot_labels
        self.verbose = verbose

        self.worker = __WorkerBee__(data_func, self.isHidden, self.refresh_interval)
        self.make_connection(self.worker)

    def __exit__(self, exc_type, exc_value, traceback):
        self.window.close()
        if self.verbose:
            print("LivePlotterWindow exiting ciao bella ciao")

    def isHidden(self):
        return self.window.isHidden()

    def make_connection(self, data_object):
        data_object.signal1.connect(self.update)
        data_object.signal2.connect(self.self_destruct)
        return self

    @QtCore.pyqtSlot(bool)
    def self_destruct(self, yes):
        if yes:
            self.__exit__(None, None, None)

    @QtCore.pyqtSlot(np.ndarray)
    def update(self, data):
        if data.shape == (0,):
            if self.verbose:
                print("data is empty, skipping this cycle, please correct this")
        else:
            self.set_data(data)
        return self 

class __LivePlotterWindow__(__LiveWindowLike__):
    """
    LivePlotterWindow is a QWidget object that contains a pyqtgraph window.
    The pyqtgraph window is updated by the WorkerBee object.
    """

    def __init__(self, **kwargs):

        super().__init__(**kwargs)
        self.setup_plots()
        self.worker.start()


    def setup_plots(self):
        """
        Setup the plots, axes, legend, and styling.
        """
        self.graph = self.window.addPlot(title=self.title)
        self.graph.setTitle(self.title, color="grey", size="20pt")

        legend = self.graph.addLegend()

        ##################### style points #####################
        self.graph.showGrid(x=True, y=True)
        self.styling = {"font-size": "20px", "color": "grey"}
        # self.graph.setTitle(self.title)
        self.tickfont = QtGui.QFont()
        self.tickfont.setPixelSize(20)
        self.graph.getAxis("bottom").setTickFont(self.tickfont)
        self.graph.getAxis("left").setTickFont(self.tickfont)
        self.graph.getAxis("right").setTickFont(self.tickfont)
        self.set_xlabel(self.xlabel)
        self.set_ylabel(self.ylabel)
        
        ########################################################
        self.initial_xydata = [[[0.0], [0.0]]]
        self.plots = []

        for i in range(self.no_plots):
            self.plots.append(
                self.graph.plot(pen=i, name = f"Channel {self.plot_labels[i]}!!!")
                if self.plot_labels
                else self.graph.plot(pen=i, name = f"Channel {i+1}!!!")
                )

    def set_xlabel(self, label):
        self.graph.setLabel("bottom", label, **self.styling)

    def set_ylabel(self, label):
        self.graph.setLabel("left", label, **self.styling)

    def set_data(self, data):
        try:
            last_numbers = "|"
            for i, plot in enumerate(self.plots):
                plot.setData(np.arange(len(data[i])), data[i])
                last_numbers += f" {data[i][-1]} |"

            self.graph.setTitle(last_numbers, color="white", size="20pt")
            
        except IndexError:
            print("IndexError: data is not in the correct format")

class __LiveMultiWindow__(__LiveWindowLike__):

    ### this is link to the parent class decorated functions

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.window = pg.GraphicsLayoutWidget(show = True, title = "Live Plotting Window")
        self.window.resize(900,500)
        # just antialiasing
        pg.setConfigOptions(antialias = True)
        # Creates graph object
        
        self.graphs = []
        self.plot = []
        self.initial_ydata = np.array([[0.]])
        self.setup_plots()
        self.worker.start()

    def setup_plots(self):
        self.tickfont = QtGui.QFont()
        self.tickfont.setPixelSize(20)
        for i in range(self.no_plots): 
            if i % 3 ==0:
                self.window.nextRow()
            self.graphs.append(self.window.addPlot(title = self.title))
            self.graphs[i].addLegend()
            self.graphs[i].showGrid(x = True, y = True)
            self.graphs[i].getAxis("bottom").setTickFont(self.tickfont)
            self.graphs[i].getAxis("left").setTickFont(self.tickfont)

        self.styling = {"font-size": "20px", "color": "grey"}

        self.set_xlabel(self.xlabel)
        self.set_ylabel(self.ylabel)

        # creating maybe multiple line plot subclass objects for the self.graph object, store in list
        self.data_store = [[]]
        ### storing lineplot instances into list, with indexed data store list
        for i in range(self.no_plots):
            ### setting pen as integer makes line colour cycle through 9 hues by default
            ### check pyqtgraph documentation on styling...it's quite messy
            self.plot.append(self.graphs[i].plot(pen=i, name = f"Channel {self.plot_labels[i]}!!!")
                if self.plot_labels
                else self.graphs[i].plot(pen=i, name = f"Channel {i+1}!!!"))
            
            legend = self.graphs[i].addLegend()
            self.data_store.append(self.initial_ydata)
        
    def set_xlabel(self, label):
        for i in range(self.no_plots):
            self.graphs[i].setLabel('bottom', label, **self.styling)
        return self
    def set_ylabel(self, label):
        for i in range(self.no_plots):
            self.graphs[i].setLabel('left', label, **self.styling)
        return self

    def set_data(self, data):
        for i in range(self.no_plots):
            self.data_store[i] = data[i]
            self.plot[i].setData(np.arange(len(data[i])), data[i])
        return self

class __LiveHeatMap__(__LiveWindowLike__):
    
    def __init__(self, **kwargs):

        super().__init__(**kwargs)
        self.setup_plots()
        self.worker.start()

    def setup_plots(self):
        self.initial_data = np.fromfunction(lambda i, j: (1+0.3*np.sin(i)) * (i)**2 + (j)**2, (100, 100))

        self.graph = self.window.addPlot(title=self.title)
        self.graph.setTitle(self.title, color="grey", size="20pt")

        legend = self.graph.addLegend()

        ##################### style points #####################
        self.graph.showGrid(x=True, y=True)
        self.styling = {"font-size": "20px", "color": "grey"}
        self.tickfont = QtGui.QFont()
        self.tickfont.setPixelSize(20)
        self.graph.getAxis("bottom").setTickFont(self.tickfont)
        self.graph.getAxis("left").setTickFont(self.tickfont)
        self.graph.getAxis("right").setTickFont(self.tickfont)
        self.set_xlabel(self.xlabel)
        self.set_ylabel(self.ylabel)

        self.img = pg.ImageItem(image=self.initial_data) # create monochrome image from demonstration data
        self.graph.addItem(self.img)            # add to PlotItem 'plot'
        self.cm = pg.colormap.get('CET-L17') # prepare a linear color map
        self.bar = pg.ColorBarItem( values= (0, 100), cmap=self.cm ) # prepare interactive color bar
        # Have ColorBarItem control colors of img and appear in 'plot':
        self.bar.setImageItem(self.img, insert_in = self.graph ) 
        return self

    def set_xlabel(self, label):
        self.graph.setLabel("bottom", label, **self.styling)
        return 
    
    def set_ylabel(self, label):
        self.graph.setLabel("left", label, **self.styling)
        return
    
    def set_data(self, data):
        self.img.updateImage(data)
        return 
###################################################################################
###################################################################################
###################################################################################
def __Qapp_liveplot__(task_q, state_q, data_q, clock, verbose):
    app = QApplication([])
    try:
        liveplot_instance = __LivePlotProcess__(
            task_q, state_q, data_q, clock, app, verbose
        )
    except Exception as e:
        raise e
    # return liveplot_instance
###################################################################################

class __LivePlotProcess__:
    def __init__(self, task_q, state_q, data_q, clock, app, verbose):
        self.app = app
        self.verbose = verbose
        self.windows = {}
        self.window_no = 0
        self.clock_interval = clock
        self.task_q = task_q
        self.state_q = state_q
        self.data_q = data_q
        self.isalive = True
        self.window_states = {}
        self.main_loop()

    def main_loop(self):

        while self.isalive:
            if len(self.windows) > 0 and self.state_q.empty():
                for key in self.windows:
                    self.window_states[str(key)] = not self.windows[str(key)].isHidden()
                self.state_q.put(self.window_states)

            if self.task_q.empty():
                pass
            else:
                new_task = self.task_q.get()
                if new_task[0] == "new_live_plot":
                    ### task[1] should be window identifier key (any str)
                    ### task[2] should be plotter kwargs
                    if self.verbose:
                        print("command received!!")
                        print(new_task)
                    self.new_window(new_task[1], **new_task[2])

                elif new_task[0] == "new_multi_plot":
                    if self.verbose:
                        print("command received!!")
                        print(new_task)
                    self.new_multiwindow(new_task[1], **new_task[2])

                elif new_task[0] == "new_heatmap":
                    if self.verbose:
                        print("command received!!")
                        print(new_task)
                    self.new_liveplot_heatmap(new_task[1], **new_task[2])

                elif new_task[0] == "break":
                    self.isalive = False
                    if self.verbose:
                        print("stopping process loop")

            time.sleep(self.clock_interval)

            self.app.processEvents()

        if self.verbose:
            print("Exiting LivePlotProcess")
        self.__exit__(None, None, None)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.verbose:
            print("LivePlotProcess exiting ciao bella ciao")
        return

    def __internal_data_func__(self, key):
        try:
            dict = self.data_q.get_nowait()
            return dict[str(key)]
        except Empty:
            return np.array([])
        except KeyError:
            if self.verbose:
                print("Keyerror, buffering")
            return np.array([])
        except Exception as e:
            print(e)
            return np.array([])

    def new_window(self, key, **plot_kwargs):
        ### we can pass a self function because it has no direct
        ### link to the customer package which houses whatever
        ### incompatible dll that cannot be pickled via Process
        refresh_interval = plot_kwargs['refresh_interval']
        if not refresh_interval:
            plot_kwargs['refresh_interval'] = self.clock_interval * 5

        if self.verbose:
            print(f"Refreshing plot at {refresh_interval}s")

        self.windows[str(key)] = __LivePlotterWindow__(
            data_func = partial(self.__internal_data_func__, str(key)),
            **plot_kwargs,
            verbose = self.verbose,
        )
        self.window_no += 1
        return self
    
    def new_multiwindow(self, key, **plot_kwargs):
        ### we can pass a self function because it has no direct
        ### link to the customer package which houses whatever
        ### incompatible dll that cannot be pickled via Process
        refresh_interval = plot_kwargs['refresh_interval']
        if not refresh_interval:
            plot_kwargs['refresh_interval'] = self.clock_interval * 5

        if self.verbose:
            print(f"Refreshing plot at {refresh_interval}s")

        self.windows[str(key)] = __LiveMultiWindow__(
            data_func = partial(self.__internal_data_func__, str(key)),
            **plot_kwargs,
            verbose = self.verbose,
        )
        self.window_no += 1
        return self

    def new_liveplot_heatmap(self, key, **plot_kwargs):
        refresh_interval = plot_kwargs['refresh_interval']
        if not refresh_interval:
            plot_kwargs['refresh_interval'] = self.clock_interval * 5

        if self.verbose:
            print(f"Refreshing plot at {refresh_interval}s")

        self.windows[str(key)] = __LiveHeatMap__(
            data_func = partial(self.__internal_data_func__, str(key)),
            **plot_kwargs,
            verbose = self.verbose,
        )
        self.window_no += 1
        return self


class LivePlotAgent:
    """
    We want to try to phase towards using multiprocess.Process method instead
    of threading.Thread to initialise the async live plot QT app. This is because
    pyqt does not like to be sub-threaded, but is ok with sub-processing.

    Sub-threading method (plot_live_plot) works with spyder, not with anything else.
    To be console-agnostic, we try sub-processing, mediated by ProcessManager class.

    LivePlotAgent class hosts the Queue method which lets us pipe commands and data into
    the live plotting subprocess.
    """

    def __init__(self, clock=0.1, verbose=False):
        """
        self.queue = something.Queue()

        """
        self.clock_interval = clock
        self.verbose = verbose
        self.task_q = mp.Queue()
        self.state_q = mp.Queue()
        self.data_q = mp.Queue(maxsize=50)  ##need to play with buffer size
        self.process = mp.Process(
            target=__Qapp_liveplot__,
            args=(
                self.task_q,
                self.state_q,
                self.data_q,
                self.clock_interval,
                self.verbose,
            ),
        )
        self.process.daemon = True
        self.process.start()
        self.window_no = 0
        self.available_window_keys = []
        self.data = {}
        self.states = {}
        self.active = True
        threading.Thread(
            target=self.__transmit_data__, daemon=True, name="Data broadcast thread"
        ).start()
        threading.Thread(
            target=self.__check_states__,
            daemon=True,
            name="Window isalive state check thread",
        ).start()
        if self.verbose:
            print("LivePlotAgent initialised")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.active = False
        self.task_q.put(["break", None, None])
        if self.verbose:
            print("command sent!")
        time.sleep(1)
        self.__flush_queues__()
        self.process.terminate()
        return self

    def __flush_queues__(self):

        def __internal_flush__(self, queue):
            while not queue.empty():
                try:
                    queue.get_nowait()
                except Empty:
                    pass
            return 
        if self.verbose:
            print("flushing memory queues")
        # self.task_q.close()
        # self.state_q.close()
        # self.data_q.close()
        while not self.task_q.empty():
            __internal_flush__(self, self.task_q)
        while not self.state_q.empty():
            __internal_flush__(self, self.state_q)
        while not self.data_q.empty():
            __internal_flush__(self, self.data_q)
        return self

    def __fetch_data__(self, data_func, key, kill_func):
        alive = True
        start = time.time()

        while time.time() - start < 5:
            self.data[str(key)] = data_func()
            time.sleep(self.clock_interval)

        while alive:
            try:
                window_isopen = self.states[str(key)]
                if window_isopen:
                    self.data[str(key)] = data_func()
                    time.sleep(self.clock_interval)
                else:
                    if kill_func:
                        kill_func()
                    alive = False
            except KeyError as e:
                pass

        if self.verbose:
            print("thread exiting!!!!!!!!!!!")
        return

    def __transmit_data__(self):
        if self.verbose:
            print("starting transmission data thread")
        while self.active:
            if True in self.states.values():
                self.data_q.put(self.data)
            time.sleep(1e-20)

    def __check_states__(self):
        while self.active:
            if not self.state_q.empty():
                try:
                    states = self.state_q.get()
                    self.states = states
                    self._garbage_collection_()
                    self.available_window_keys = list(
                        map(
                            str,
                            np.arange(0, len(self.states), 1)[
                                list(map(operator.not_, self.states.values()))
                            ],
                        )
                    )
                except (Empty, KeyError) as e:
                    pass
            time.sleep(2)

    def _garbage_collection_(self):
        for key in self.states:
            if not self.states[key] and key not in self.available_window_keys:
                if self.verbose:
                    print(f"Cleaning data for key:{key}")
                self.data[key] = np.array([])

    def __new_plot_prep__(self, data_func=None, kill_func=None):
        avail_win = None
        if len(self.available_window_keys) > 0:
            avail_win = min(self.available_window_keys)

        if avail_win and self.window_no - int(avail_win) > 1:
            key = avail_win
        else:
            key = str(self.window_no)
            self.window_no += 1

        if self.verbose:
            print(f"Key: {key}")
        ### some dummy data if data func is None
        if not data_func:
            data_func = lambda: np.array(
                [[np.linspace(0, 1, 1000), np.random.rand(1000)]]
            )

        self.data[key] = data_func()
        self.states[key] = True

        threading.Thread(
            target=self.__fetch_data__,
            args=(
                data_func,
                key,
                kill_func,
            ),
            daemon=True,
            name="FetchData thread for key {}".format(key),
        ).start()
        return key


    def new_liveplot_heatmap(self, data_func=None, kill_func=None, **plot_settings):
        key = self.__new_plot_prep__(data_func, kill_func)
        self.task_q.put(["new_heatmap", key, plot_settings])
        if self.verbose:
            print("command sent!")
        return self

    def new_liveplot_multi(self, data_func=None, kill_func=None, **plot_settings):
        key = self.__new_plot_prep__(data_func, kill_func)
        self.task_q.put(["new_multi_plot", key, plot_settings])
        if self.verbose:
            print("command sent!")
        return self

    def new_liveplot(self, data_func=None, kill_func=None, **plot_settings):
        key = self.__new_plot_prep__(data_func, kill_func)
        self.task_q.put(["new_live_plot", key, plot_settings])
        # self.task_q.put(['dummy', key, plot_settings])
        if self.verbose:
            print("command sent!")
        return self

    def close(self):
        self.__exit__(None, None, None)
        return