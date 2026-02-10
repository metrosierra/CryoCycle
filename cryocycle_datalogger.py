import sys
import os
import numpy as np
import json
import threading
import time


config_relative_path = 'config/'
drivers_relative_path = '/'
sys.path.insert(1, os.path.join(sys.path[0], drivers_relative_path)) ### TO POINT TO DEVICE INTERFACING FOLDER
abs_path = os.path.dirname(os.path.abspath(__file__))
if abs_path not in sys.path:
    sys.path.insert(0, abs_path)

from drivers.tempcontroller_ctc100 import TempControl_CTC100
from drivers.generic_instrument_dependencies.generic_instrument import GenericInstrument
from drivers.liveplotter_heavy import LivePlotAgent 
from drivers.slack import Slack

json_matterhorn_config_path = ".json" 



class CryoCycler:

    def __init__(self, config_dir = config_relative_path):

        self.config_dir = config_dir
        self.config = self.load_config('config.json')
        self.handshake()

        if self.tempcontroller: 
            self.data_monitoring_refresh_s = 1
            self.data_logging_cycle_s = 20
            self.tempcontroller.start_logging(refresh_s = self.data_monitoring_refresh_s)

        self.slack = Slack(config_dir="config")
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

    def load_config(self, config_name=False):
        config_path = os.path.join(self.config_dir, config_name)
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
    
    
    
    
    def run_ctc100_automatic_cycle_thread(self, stop_event = None, evap_time = False, cond_time = False, json_location = None, slack_json_location = None): # function to run in thread (in the background)
        """
        Docstring for run_ctc100_automatic_cycle_thread
        
        :param evap_time: See the next  function for a clear discription of these
        :param cond_time: See the next  function for a clear discription of these
        
        This function runs the cycle by checking every 10 minutes what time it is during the day in minutes. If the evap time or cond time are within ± 15min of that time, it starts the process.
        
        It also takes into consideration what happens if a leak or a sudden heating up of th ecryo after successfully evaporating. 
        
        
        
        """
        if json_location is None:
            print("Please provide a json config file of the conditions for your cryo. And example should be found alongside this repo.")
            return 
        if slack_json_location is None:
            print("Please provide a json file of the error codes and slack webhook url.")
            return
            
        self.slack_config = self.load_config(slack_json_location)
        self.cryo_config = self.load_config(json_location) 
        
        self.tempcontroller.set_initial_input_config(self.cryo_config)
        self.tempcontroller.set_initial_output_config(self.cryo_config)

        
        
        cycle_cfg = self.cryo_config["temperature_conditions"]["cryo_cycle"]
        Tr_abort_temp_thresh = float(cycle_cfg["Tr_cold_abort_temp"])
        reset_time_for_new_day_1 = float(cycle_cfg["reseting_time_1"])
        reset_time_for_new_day_2 = float(cycle_cfg["reseting_time_2"])
        time_since_last_cond = float(cycle_cfg["cond_min_elapsed_time"])
        cycle_time_window = float(cycle_cfg["time_within_range"])
        Tr_monitoring_temperature_thresh = float(cycle_cfg["evap_monitering_temp"])
        time_between_time_of_day_check = float(cycle_cfg["cycle_check_time"])
          
            
        if evap_time is False or cond_time is False:
            print("Both start_evaporation_time and start_condensation_time must be specified (in hours).")
            return None
            
        

        start_evap = evap_time * 60 # time in minutes
        start_cond = cond_time * 60 # time in minutes
        evap_ran_today = False 
        cond_ran_today = False
        monitor_after_evap = False
        t_condensation = None
        t_evap = None
    
        
        while not stop_event.is_set():
            
            
            if float(self.tempcontroller.get_channel_value(channel="Tr")) > Tr_abort_temp_thresh:
                """Message error slack channel"""
                print("Tr way too high, please check before running automatic cryo cycle")
                self.slack.send_message_to_slack(error_code = 6, json_slack=self.slack_config)
                return 6
            
            
            now = self.get_local_system_time() # local time of system (bound to internet) in minutes
            
            
            if reset_time_for_new_day_1 < now < reset_time_for_new_day_2: # reset at new day 2:00-4:00am giving a window incase condensation is aborting late
                evap_ran_today = False # flags to allow running of scheduled processes only once per day
                cond_ran_today = False
                monitor_after_evap = False
            
            cond_ok = (t_condensation is not None) and ((time.time() - t_condensation) > time_since_last_cond) # when code runs for the first time, it doesnt evap and goes straight to condensation when the time is right
            
            if abs(now - start_evap) <= cycle_time_window and (not evap_ran_today) and cond_ok: # check if time is within 15 min of scheduled evap time + check if evap has not run today + check if condensation has been running for at least 4h
                print("Starting scheduled evaporation process")
                evap_status = self.tempcontroller.run_evaporation(stop_event=stop_event, json_config_file=self.cryo_config)
                self.slack.send_message_to_slack(error_code= evap_status, json_slack=self.slack_config)
                t_evap = time.time()
                evap_ran_today = True
                monitor_after_evap = True # Monitor evap temp throughout the day to make sure the cryo doesnt run out of helium
                
                
            if monitor_after_evap and (not cond_ran_today):
                Tr = float(self.tempcontroller.get_channel_value(channel="Tr"))
                if Tr > Tr_monitoring_temperature_thresh:
                    print("Tr > 3K after evaporation -> starting immediate condensation") # If helium runout, start condensation now, and wont start again when cond time is there. Send alert message with hold time 
                    monitor_cond_status = self.tempcontroller.run_condensation(stop_event=stop_event, json_config_file=self.cryo_config)
                    self.slack.send_message_to_slack(error_code= monitor_cond_status, json_slack=self.slack_config)
                    t_condensation = time.time()
                    cond_ran_today = True

                    held_s = time.time() - t_evap
                    print(f"Held cryo for {held_s/3600:.2f} hours")
                    
                    """Slack notification: Evaporation held for {held_s/3600:.2f} hours, immediate condensation started.
                    """
                    
                    monitor_after_evap = False
                
                
                
            
            if abs(now - start_cond) <= cycle_time_window and (not cond_ran_today): # check if time is within 15 min of scheduled cond time + check if cond has not run today
                print("Starting scheduled condensation process")
                t_condensation = time.time()
                cond_status = self.tempcontroller.run_condensation(stop_event=stop_event, json_config_file=self.cryo_config)
                self.slack.send_message_to_slack(error_code= cond_status, json_slack=self.slack_config)
                cond_ran_today = True
            
            stop_event.wait(time_between_time_of_day_check)
            # time.sleep(60*10) # Check every 10 minutes
                
        print("Auto cycle thread exiting cleanly")
        return
    
    
    def run_ctc100_automatic_cycle(self, start_evaporation_time: int, start_condensation_time: int, json_cryo_config_path):
        
        """
        
        example run: run_ctc100_automatic_cycle(start_evaporation_time= 6, start_condensation_time= 21, json_cryo_config_path= "ctc100/matterhorn_configuration.json")
        
        Start evopoartion and condinsaton time variables need to be an integer that represents military time, i.e. 6am = 6, 7:30am = 7.5, 5pm = 17h = 17...
        
        Dont set condinsation time too late, at least before midnight (0).
        
        To abort manually at any time this thread without having to kill the terminal, run tempcontroller.stop_ctc100_automatic_cycle()
        
        To change configurations, change them in the cryo's individual json config files, instructions on formating will be written there.
        
        Abort systems have been made inside each individual evaporation and condinsation function inside the tempcontroller driver. Each abort has a specific code error which will be sent to the allocated slack chennel to warn individuals. 
        
        Make sure to run this where the condition cycle happens first.
        
        """
        
        
        if getattr(self, "_auto_cycle_thread", None) and self._auto_cycle_thread.is_alive():
            print("Auto cycle already running. Stop it first with stop_ctc100_automatic_cycle().")
            return
    
        stop_event = threading.Event()
        self._auto_cycle_stop = stop_event    
    
        

        
        t = threading.Thread(target=self.run_ctc100_automatic_cycle_thread, args=(stop_event, start_evaporation_time, start_condensation_time, json_cryo_config_path), daemon=True)
        self._auto_cycle_thread = t
        t.start()
        
        return
    
    
    
    
    



if __name__ == '__main__':
    with CryoCycler()as cc:
        print("\n>>>> USE CRYOCYCLER OBJECT AS cc <<<<\n")
        import code; code.interact(local=locals())