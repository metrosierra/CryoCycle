#%%
import os
import json
import sys
import threading
import numpy as np
import time

from generic_instrument_dependencies.generic_instrument import GenericInstrument

here = os.path.dirname(os.path.abspath(__file__))     # .../Cryocycle/drivers
root = os.path.dirname(here)                          # .../Cryocycle
json_path = os.path.join(root, "config", "ctc100", "initial_config_matterhorn.json")



#%%

class TempControl_CTC100(GenericInstrument):
    def __init__(self, address, name, baud_rate = 9600):
        self.write_term = '\n'
        self.read_term = '\r\n'
        super().__init__(address, name = name,
                        write_term = self.write_term, 
                        read_term = self.read_term)
        
        self.baud_rate = baud_rate
        self.client.baud_rate = self.baud_rate

        self.data_length = 100
        self.data_names = self.get_data("names")
        self.data = np.zeros((len(self.data_names), self.data_length))

        self.is_monitoring = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return
    
    def close(self):
        self.stop_logging()
        time.sleep(2)
        self.client.close()
        self.client = None
        self.__exit__(None, None, None)
        return
    
    def get_outputnames(self):
        return self.query("getOutputNames?")

    def get_output(self):
        return self.query("getOutput?")
    
    
    
    """ PID/Output related functions"""
    
    def get_pid_status(self, channel = "hpump"):
        # Get PID status for a given channel, e.g., "hpump" or "switch"
        command = self.query(channel + ".PID.Mode?")
        print(f"PID status for {channel}: {command}")
        return command
    
    def set_pid_status(self, status = "Off", channel = "hpump"):
        # Set PID status for a given channel, e.g., "hpump" or "switch"
        command = f"{channel}.PID.Mode {status}"
        self.write(command)
        print(f"Set PID status for {channel} to {status}")
        return
    
    def set_output_unit(self, units = "V", channel = "hpump"): # Unit can be "V", "W", "A"
        return self.write(f"{channel}.Units {units}")
    
    def set_output_range(self, range = "50V .2A", channel = "hpump"): # Range, Auto, "xV xA"
        return self.write(f"{channel}.Range {range}")
    
    def set_output_limits(self, low_limit = "0.0", high_limit = "30.0", channel = "hpump"):
        self.write(f"{channel}.LowLmt {low_limit}")
        self.write(f"{channel}.HiLmt {high_limit}")
        return
    
    def set_output_io_type(self, io_type = "Meas out", channel = "hpump"): # "Meas out", "Set out"
        return self.write(f"{channel}.IOType {io_type}")
    
    def set_pid_input(self, input = "Tp", channel = "hpump"): 
        return self.write(f"{channel}.PID.Input {input}")
    
    def set_pid_setpoint(self, setpoint = "40.000", channel = "hpump"): # temperature trying to keep the input channel at
        return self.write(f"{channel}.PID.Setpoint {setpoint}")
    
    def set_pid_ramp_rate(self, rate = "0.0", channel = "hpump"): # rate of ramp, 0 means max rate availble
        return self.write(f"{channel}.PID.Ramp {rate}")
    
    def set_pid_ramp_t(self, ramp_t = "40.000", channel = "hpump"): # target temperature to ramp to
        return self.write(f"{channel}.PID.RampT {ramp_t}")
    
    def set_pid_PID(self, P = "1.0", I = "0.0", D = "0.0", channel = "hpump"): # proportional, integral, and derivative gain factors for PID feedback
        self.write(f"{channel}.PID.P {P}")
        self.write(f"{channel}.PID.I {I}")
        self.write(f"{channel}.PID.D {D}")
        return
    
    def set_output_stepy(self, step_y = 1.5, channel = "hpump"):
        return self.write(f"{channel}.Tune.StepY {step_y}")
    
    def set_output_lag(self, lag_time_s = 30.0, channel = "hpump"):
        return self.write(f"{channel}.Tune.Lag {lag_time_s}")
    
    
    
    """ Alarm related functions"""
    
    def get_alarm_status(self, channel = "Tr"): # Alarm for input channels, e.g. the temperature channels Tp, Tr, T1s and Tsw
        command = self.query(channel + ".Alarm.Mode?")
        command_output = self.query(channel + ".Alarm.Output?")
        print(f"Alarm status for {channel}: {command}, Output: {command_output}")
        return command, command_output
    
    def set_alarm_min_max(self, min_val = "0", max_val = "5", channel = "Tr"):
        self.write(f"{channel}.Alarm.Min {min_val}")
        self.write(f"{channel}.Alarm.Max {max_val}")
        return
    
    def set_alarm_relay(self, relay_satus = "None", channel = "Tr"):
        return self.write(f"{channel}.Alarm.Relay {relay_satus}")
    
    def set_alarm_lag(self, lag_time_s = "0.0", channel = "Tr"): # Time for the alarm to trigger after threshold is crossed
        return self.write(f"{channel}.Alarm.Lag {lag_time_s}")
    
    def set_alarm_sound(self, sound_status = "None", channel = "Tr"): # "1 beep", "2 beeps"...
        return self.write(f"{channel}.Alarm.Sound {sound_status}")
    
    def set_alarm_latch(self, latch_status = "Off", channel = "Tr"):
        return self.write(f"{channel}.Alarm.Latch {latch_status}")
    
    def set_alarm_mode(self, mode = "Level", channel = "Tr"): # "Off", "Level", "Rate /s"
        return self.write(f"{channel}.Alarm.Mode {mode}")
    
    def set_alarm_output(self, output_channel = "switch", channel = "Tr"): # Output channel is the channel that will be turned off once alarm triggers
        return self.write(f"{channel}.Alarm.Output {output_channel}")
    
    """ Input related functions"""
    
    def set_input_sensor(self, sensor = "ROX", channel = "Tr"): # Sensor types, Diode, ROX, RTD, Therm
        return self.write(f"{channel}.Sensor {sensor}")
    
    def set_input_range(self, range = "Auto", channel = "Tr"): # Range, Auto, 10e, 30e, 100e, 30e, ..., 2.5V
        return self.write(f"{channel}.Range {range}")
    
    def set_input_current(self, current = "AC", channel = "Tr"): # current type, Forward, Reverse, AC, Off
        return self.write(f"{channel}.Current {current}")
    
    def set_input_power(self, power = "Auto", channel = "Tr"): # power, Auto, Low, High
        return self.write(f"{channel}.Power {power}")
    

    
    def get_data(self, type = 'values'):
        """ Collects data from temp controller and updates dictionary """
        if type == 'values':
            output = self.get_output()  
            output = [float(x) for x in output.replace(' ','').split(',')]
            
        elif type == 'names':
            output = self.get_outputnames()
            output = [x for x in output.replace(' ','').split(',')]

        return output

    def __data_loop__(self, refresh_s = 1.0):
        while self.is_monitoring:
            try:
                new_data = self.get_data("values") 
                if self.data.shape[1] < self.data_length:
                    self.data = np.column_stack((self.data, new_data))

                else: 
                    self.data = np.roll(self.data, -1, axis=1)
                    self.data[:,-1] = new_data
            except Exception as e:
                print(f"Error occurred: {e}")
                print("Stopping data update loop")
                break
            
            time.sleep(refresh_s)
        self.is_monitoring = False
        return

    def start_logging(self, refresh_s = 1.0):
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self.__data_loop__, args=(refresh_s,), daemon=True)
        self.monitoring_thread.start()
        return 
    
    def stop_logging(self):
        self.is_monitoring = False  
        if self.monitoring_thread:
            self.monitoring_thread.join()
        return
    
    def set_output(self, status = "on"):
        return self.write(f"outputEnable {status}")
    
    
    def wait_for_sample(self):
        return self.write("waitForSample")
    
    
    
    def set_pid_off(self):
        """Ping someone to check"""
        self.set_pid_status(status = "Off", channel = "hpump")
        self.set_pid_status(status = "Off", channel = "switch")
    
        return
    
    
    def set_initial_input_config(self):
        """Do I hardcode initial config ? or let the user set them ? The inputs are Tp, Tr, T1s, Tsw"""
        input_channels = ["Tp", "Tr", "T1s", "Tsw"]        
        return
    
    
    
    def set_initial_output_config(self):
        """Do I hardcode initial config ? or let the user set them ? The outputs are hpump and switch"""
        return
    
    
    
    def run_evaporation(self):
        """Run evaporation"""
        self.set_pid_off()
        self.set_output("on")
        
        while True:
            tp = self.check_temperature_condition(channel = "Tp")
            tr = self.check_temperature_condition(channel = "Tr")
            
            if tp < 30 and tr < 3.0:
                break
            time.sleep(2)
            
        self.set_pid_setpoint(setpoint = "20.000", channel = "switch")
        self.set_pid_status(status = "On", channel = "switch")
        
        return
    
    
    def run_condensation(self):
        """Run condensation"""
        self.set_output("on")
        self.set_pid_off()
        self.set_pid_setpoint(setpoint = "40.000", channel = "hpump")  
        self.set_pid_status(status = "On", channel = "hpump")
        
        return
    
    
    def check_temperature_condition(self, channel = "Tr"):
        output_values = self.get_data("values")
        output_names = self.get_data("names")
        channel_index = output_names.index(channel)
        channel_temp = output_values[channel_index]
   
        return channel_temp
    
    



if __name__ == '__main__':
    with TempControl_CTC100('ASRL/dev/ttyUSB0::INSTR', 'CTC100') as tc:
        print("Connected to CTC100 interactive window session")
        print("\n>>>> USE TEMP CONTROLLER OBJECT AS tc <<<<\n")
        import code; code.interact(local=locals())