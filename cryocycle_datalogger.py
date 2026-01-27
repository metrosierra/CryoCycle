import sys
import os
import numpy as np
import json

config_relative_path = 'config/'
drivers_relative_path = '/'
sys.path.insert(1, os.path.join(sys.path[0], drivers_relative_path)) ### TO POINT TO DEVICE INTERFACING FOLDER
abs_path = os.path.dirname(os.path.abspath(__file__))
if abs_path not in sys.path:
    sys.path.insert(0, abs_path)

from drivers.tempcontroller_ctc100 import TempControl_CTC100
from drivers.liveplotter_heavy import LivePlotAgent 


class CryoCycler:

    def __init__(self, config_dir = config_relative_path):

        self.config_dir = config_dir
        self.config = self.load_config()
        self.handshake()

        if self.tempcontroller: 
            self.data_monitoring_refresh_s = 1
            self.data_logging_cycle_s = 20
            self.tempcontroller.start_logging(refresh_s = self.data_monitoring_refresh_s)

        self.liveplot_tempcontroller()


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return 
    
    def close(self):
        if self.tempcontroller:
            self.tempcontroller.close()
            self.tempcontroller = None
        if self.liveplotter:
            self.liveplotter.close()
            self.liveplotter = None

        self.__exit__(None, None, None)
        return

    def load_config(self):
        config_path = os.path.join(self.config_dir, 'config.json')
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        return self.config

    def handshake(self):
        
        print("Trying to establish driver instantiations...")
        try:
            self.liveplotter: LivePlotAgent = LivePlotAgent()
            self.liveplot_refresh_rate = self.config["liveplotter"]["refresh_rate"]

            self.tempcontroller: TempControl_CTC100 = TempControl_CTC100(**self.config["tempcontroller"]["init_args"])
            self.tempcontroller_macro_dir = os.path.join(self.config_dir, self.config["tempcontroller"]["macro_dir"])
            print(f"Loading temp controller macros from {self.tempcontroller_macro_dir}")
            self.load_tempcontroller_macros(self.tempcontroller_macro_dir)
            self.log_dir = self.config["logging"]["relative_dir"]

            print("Driver instantiation successful!!!.")
            return 

        except Exception as e:
            print(f"Error during driver instantiation: {e}")

    def load_tempcontroller_macros(self, macro_dir):
        macro_files = [f for f in os.listdir(macro_dir) if f.endswith('.txt')]
        self.tempcontroller_macros = {}
        for file in macro_files:
            macro_name = os.path.splitext(file)[0]
            with open(os.path.join(macro_dir, file), 'r') as f:
                self.tempcontroller_macros[macro_name] = f.read()
        return self.tempcontroller_macros

    def liveplot_tempcontroller(self):

        no_plots = 5
        
        def get_data():
            return self.tempcontroller.data[:no_plots]

        plot_args ={
            'refresh_interval': self.liveplot_refresh_rate,
            'title': "Live Temp Controller Data",
            'xlabel': "Time (s)",
            'ylabel': "Temperature (°K)",
            'no_plots': no_plots,
            'plot_labels': self.tempcontroller.data_names[:no_plots],
        }

        self.liveplotter.new_liveplot(data_func = get_data, kill_func = None, **plot_args)

        return 
    
    
    



if __name__ == '__main__':
    with CryoCycler()as cc:
        print("\n>>>> USE CRYOCYCLER OBJECT AS cc <<<<\n")
        import code; code.interact(local=locals())