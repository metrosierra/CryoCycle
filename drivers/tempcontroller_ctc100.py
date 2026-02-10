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
        self._auto_cycle_stop = None
        self._auto_cycle_thread = None
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
    
    def get_pid_status(self, channel = False):
        # Get PID status for a given channel, e.g., "hpump" or "switch"
        
        if channel:
            if channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'hpump' or 'switch'.")
            return None
        return self.query(channel + ".PID.Mode?")
    
    
    def set_pid_status(self, status = False, channel = False):
        # Set PID status for a given channel, e.g., "hpump" or "switch"
        
        if channel:
            if channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'hpump' or 'switch'.")
            return None
        if status:
            if status in ["On", "ON", "on"]:
                status = "On"
            elif status in ["Off", "OFF", "off"]:
                status = "Off"
            else:
                print(f"Invalid status: {status}. Must be 'On' or 'Off'.")
                return None

        return self.query(f"{channel}.PID.Mode {status}")
    
    
    def set_output_unit(self, units = False, channel = False): # Unit can be "V", "W", "A"
        
        if channel:
            if channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'hpump' or 'switch'.")
            return None
            
        if units:
            if units in ["V", "v", "Volts", "volts"]:
                units = "V"
            elif units in ["A", "a", "Amps", "amps"]:
                units = "A"
            elif units in ["W", "w", "Watts", "watts"]:
                units = "W"
            else:
                print(f"Invalid units: {units}. Must be 'V', 'A', or 'W'.")
                return None
        
        return self.query(f"{channel}.Units {units}")
    
    
    
    
    def set_output_range(self, range = False, channel = False): # Range, Auto, "xV xA"
        if channel:
            if channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'hpump' or 'switch'.")
            return None
            
        if range:
            valid_ranges = ["50V 2A", "50V .6A", "50V .2A", "20V 2A", "20V .6A", "20V .2A", "Auto"]
            if str(range)not in valid_ranges:
                print(f"Invalid range: {range}. Must be one of {valid_ranges}.")
                return None
        else:
            print("Range not specified. Please provide a valid range.")
            return None
        
        return self.query(f"{channel}.Range {range}")
    
    
    
    def set_output_limits(self, low_limit = False, high_limit = False, channel = False):
        if channel:
            if channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'hpump' or 'switch'.")
            return None
        
        if low_limit is False or high_limit is False:
            print("Both low_limit and high_limit must be specified.")
            return None
        else:
            low_limit = str(low_limit)
            high_limit = str(high_limit)
        
        self.query(f"{channel}.LowLmt {low_limit}")
        self.query(f"{channel}.HiLmt {high_limit}")
        return
    


    def set_output_io_type(self, io_type = False, channel = False): # "Meas out", "Set out"
        if channel:
            if channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'hpump' or 'switch'.")
            return None

        if io_type:
            if io_type in ["Meas out", "meas out", "MEAS OUT", "Measured out", "measure out"]:
                io_type = "Meas out"
            elif io_type in ["Set out", "set out", "SET OUT"]:
                io_type = "Set out"
            else:
                print(f"Invalid io_type: {io_type}. Must be 'Meas out' or 'Set out'.")
                return None
        else:
            print("io_type not specified. Please provide 'Meas out' or 'Set out'.")
            return None
        
        return self.query(f"{channel}.IOType {io_type}")
    
    
    
    def set_pid_input(self, input = False, channel = False): 
        if channel:
            if channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'hpump' or 'switch'.")
            return None
        
        if input:
            if input in ["Tp", "tp", "TP"]:
                input = "Tp"
            elif input in ["Tr", "tr", "TR"]:
                input = "Tr"
            elif input in ["T1s", "t1s", "T1S"]:
                input = "T1s"
            elif input in ["Tsw", "tsw", "TSW"]:
                input = "Tsw"
            else:
                print(f"Invalid input: {input}. Must be 'Tp', 'Tr', 'T1s', or 'Tsw'.")
                return None
        else:
            print("Input not specified. Please provide 'Tp', 'Tr', 'T1s', or 'Tsw'.")
            return None
        
        return self.query(f"{channel}.PID.Input {input}")
    
    
    
    
    
    
    
    def set_pid_setpoint(self, setpoint = False, channel = False): # temperature trying to keep the input channel at
        if channel:
            if channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'hpump' or 'switch'.")
            return None
        
        if setpoint is False:
            print("Setpoint not specified. Please provide a valid setpoint.")
            return None
        else:
            setpoint = str(setpoint)
        
        return self.query(f"{channel}.PID.Setpoint {setpoint}")
    
    
    


    def set_pid_ramp_rate(self, rate = False, channel = False): # rate of ramp, 0 means max rate availble
        if channel:
            if channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'hpump' or 'switch'.")
            return None

        if rate is False:
            print("Rate not specified. Please provide a valid rate.")
            return None
        else:
            rate = str(rate)

        return self.query(f"{channel}.PID.Ramp {rate}")
    
    
    
    
    def set_pid_ramp_t(self, ramp_t = False, channel = False): # target temperature to ramp to
        if channel:
            if channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'hpump' or 'switch'.")
            return None
        if ramp_t is False:
            print("Ramp target temperature not specified. Please provide a valid temperature.")
            return None
        else:
            ramp_t = str(ramp_t)
            
        return self.query(f"{channel}.PID.RampT {ramp_t}")
    
    
    
    
    
    
    def set_pid_PID(self, P = False, I = False, D = False, channel = False): # proportional, integral, and derivative gain factors for PID feedback
        
        if channel:
            if channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'hpump' or 'switch'.")
            return None

        if P is False:
            print("P not specified. Please provide a valid P.")
            return None
        else:
            P = str(P)

        if I is False:
            print("I not specified. Please provide a valid I.")
            return None
        else:
            I = str(I)

        if D is False:
            print("D not specified. Please provide a valid D.")
            return None
        else:
            D = str(D)

        self.query(f"{channel}.PID.P {P}")
        self.query(f"{channel}.PID.I {I}")
        self.query(f"{channel}.PID.D {D}")
        return
    
    
    
    def set_output_stepy(self, step_y = False, channel = False):
        if channel:
            if channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'hpump' or 'switch'.")
            return None
        
        if step_y is False:
            print("StepY not specified. Please provide a valid StepY.")
            return None
        else:
            step_y = str(step_y)
        
        return self.query(f"{channel}.Tune.StepY {step_y}")
    
    def set_output_lag(self, lag_time_s = False, channel = False):
        if channel:
            if channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'hpump' or 'switch'.")
            return None

        if lag_time_s is False:
            print("Lag time not specified. Please provide a valid lag time.")
            return None
        else:
            lag_time_s = str(lag_time_s)
        
        return self.query(f"{channel}.Tune.Lag {lag_time_s}")
    
    def set_channel_off(self, channel = False):
        if channel in ["hpump", "Hpump", "HPUMP"]:
            channel = "hpump"
        elif channel in ["switch", "Switch", "SWITCH"]:
            channel = "switch"
        else:
            print(f"Invalid channel name: {channel}. Must be 'hpump' or 'switch'.")
            return None
        return self.query(f"{channel}.Off")
    
    
    """ Alarm related functions"""
    
    def get_alarm_status(self, channel = False): # Alarm for input channels, e.g. the temperature channels Tp, Tr, T1s and Tsw
        if channel:
            if channel in ["Tp", "tp", "TP"]:
                channel = "Tp"
            elif channel in ["Tr", "tr", "TR"]:
                channel = "Tr"
            elif channel in ["T1s", "t1s", "T1S"]:
                channel = "T1s"
            elif channel in ["Tsw", "tsw", "TSW"]:
                channel = "Tsw"
            else:
                print(f"Invalid channel name: {channel}. Must be 'Tp', 'Tr', 'T1s', or 'Tsw'.")
                return None
        else:
            print("Channel not specified. Please provide 'Tp', 'Tr', 'T1s', or 'Tsw'.")
            return None
        
        command = self.query(channel + ".Alarm.Mode?")
        command_output = self.query(channel + ".Alarm.Output?")

        return command, command_output
    
    
    
    def set_alarm_min_max(self, min_val = False, max_val = False, channel = False):
        if channel:
            if channel in ["Tp", "tp", "TP"]:
                channel = "Tp"
            elif channel in ["Tr", "tr", "TR"]:
                channel = "Tr"
            elif channel in ["T1s", "t1s", "T1S"]:
                channel = "T1s"
            elif channel in ["Tsw", "tsw", "TSW"]:
                channel = "Tsw"
            else:
                print(f"Invalid channel name: {channel}. Must be 'Tp', 'Tr', 'T1s', or 'Tsw'.")
                return None
        else:
            print("Channel not specified. Please provide 'Tp', 'Tr', 'T1s', or 'Tsw'.")
            return None
        
        if min_val is False or max_val is False:
            print("Both min_val and max_val must be specified.")
            return None
        else:
            min_val = str(min_val)
            max_val = str(max_val)
        
        self.query(f"{channel}.Alarm.Min {min_val}")
        self.query(f"{channel}.Alarm.Max {max_val}")
        return
    
    
    
    
    def set_alarm_lag(self, lag_time_s = False, channel = False): # Time for the alarm to trigger after threshold is crossed
        if channel:
            if channel in ["Tp", "tp", "TP"]:
                channel = "Tp"
            elif channel in ["Tr", "tr", "TR"]:
                channel = "Tr"
            elif channel in ["T1s", "t1s", "T1S"]:
                channel = "T1s"
            elif channel in ["Tsw", "tsw", "TSW"]:
                channel = "Tsw"
            else:
                print(f"Invalid channel name: {channel}. Must be 'Tp', 'Tr', 'T1s', or 'Tsw'.")
                return None
        else:
            print("Channel not specified. Please provide 'Tp', 'Tr', 'T1s', or 'Tsw'.")
            return None
        
        if lag_time_s is False:
            print("Lag time not specified. Please provide a valid lag time.")
            return None
        else:
            lag_time_s = str(lag_time_s)
            
        return self.query(f"{channel}.Alarm.Lag {lag_time_s}")
    
    
    
    
    def set_alarm_sound(self, sound_status = False, channel = False): # "1 beep", "2 beeps"...
        if channel:
            if channel in ["Tp", "tp", "TP"]:
                channel = "Tp"
            elif channel in ["Tr", "tr", "TR"]:
                channel = "Tr"
            elif channel in ["T1s", "t1s", "T1S"]:
                channel = "T1s"
            elif channel in ["Tsw", "tsw", "TSW"]:
                channel = "Tsw"
            else:
                print(f"Invalid channel name: {channel}. Must be 'Tp', 'Tr', 'T1s', or 'Tsw'.")
                return None
        else:
            print("Channel not specified. Please provide 'Tp', 'Tr', 'T1s', or 'Tsw'.")
            return None
        
        if sound_status:
            valid_sounds = ["None", "1 beep", "2 beeps", "3 beeps", "4. beeps"]
            if sound_status not in valid_sounds:
                print(f"Invalid sound status: {sound_status}. Must be one of {valid_sounds}.")
                return None
        else:
            print("Sound status not specified. Please provide a valid sound status.")
            return None
        
        
        return self.query(f"{channel}.Alarm.Sound {sound_status}")
    
    
    
    def set_alarm_latch(self, latch_status = False, channel = False):
        if channel:
            if channel in ["Tp", "tp", "TP"]:
                channel = "Tp"
            elif channel in ["Tr", "tr", "TR"]:
                channel = "Tr"
            elif channel in ["T1s", "t1s", "T1S"]:
                channel = "T1s"
            elif channel in ["Tsw", "tsw", "TSW"]:
                channel = "Tsw"
            else:
                print(f"Invalid channel name: {channel}. Must be 'Tp', 'Tr', 'T1s', or 'Tsw'.")
                return None
        else:
            print("Channel not specified. Please provide 'Tp', 'Tr', 'T1s', or 'Tsw'.")
            return None
        
        if latch_status:
            if latch_status in ["Yes", "YES", "yes", "On", "ON", "on"]:
                latch_status = "Yes"
            elif latch_status in ["Off", "OFF", "off", "No", "NO", "no"]:
                latch_status = "No"
            else:
                print(f"Invalid latch status: {latch_status}. Must be 'On' or 'Off'.")
                return None
        else:
            print("Latch status not specified. Please provide 'On' or 'Off'.")
            return None
        
        return self.query(f"{channel}.Alarm.Latch {latch_status}")
    
    
    
    def set_alarm_mode(self, mode = False, channel = False): # "Off", "Level", "Rate /s"
        if channel:
            if channel in ["Tp", "tp", "TP"]:
                channel = "Tp"
            elif channel in ["Tr", "tr", "TR"]:
                channel = "Tr"
            elif channel in ["T1s", "t1s", "T1S"]:
                channel = "T1s"
            elif channel in ["Tsw", "tsw", "TSW"]:
                channel = "Tsw"
            else:
                print(f"Invalid channel name: {channel}. Must be 'Tp', 'Tr', 'T1s', or 'Tsw'.")
                return None
        else:
            print("Channel not specified. Please provide 'Tp', 'Tr', 'T1s', or 'Tsw'.")
            return None
        
        if mode:
            if mode in ["Off", "OFF", "off"]:
                mode = "Off"
            elif mode in ["Level", "level", "LEVEL"]:
                mode = "Level"
            elif mode in ["Rate /s", "rate /s", "RATE /S", "Rate", "rate", "RATE"]:
                mode = "Rate /s"
            else:
                print(f"Invalid mode: {mode}. Must be 'Off', 'Level', or 'Rate /s'.")
                return None
        else:
            print("Mode not specified. Please provide 'Off', 'Level', or 'Rate /s'.")
            return None
        
        return self.query(f"{channel}.Alarm.Mode {mode}")
    
    
    
    
    
    def set_alarm_output(self, output_channel = False, channel = False): # Output channel is the channel that will be turned off once alarm triggers
        if channel:
            if channel in ["Tp", "tp", "TP"]:
                channel = "Tp"
            elif channel in ["Tr", "tr", "TR"]:
                channel = "Tr"
            elif channel in ["T1s", "t1s", "T1S"]:
                channel = "T1s"
            elif channel in ["Tsw", "tsw", "TSW"]:
                channel = "Tsw"
            else:
                print(f"Invalid channel name: {channel}. Must be 'Tp', 'Tr', 'T1s', or 'Tsw'.")
                return None
        else:
            print("Channel not specified. Please provide 'Tp', 'Tr', 'T1s', or 'Tsw'.")
            return None
        if output_channel:
            if output_channel in ["hpump", "Hpump", "HPUMP"]:
                output_channel = "hpump"
            elif output_channel in ["switch", "Switch", "SWITCH"]:
                output_channel = "switch"
            else:
                print(f"Invalid output channel name: {output_channel}. Must be 'hpump' or 'switch'.")
                return None
        else:
            print("Output channel not specified. Please provide 'hpump' or 'switch'.")
            return None
        
        return self.query(f"{channel}.Alarm.Output {output_channel}")
    
    
    
    
    
    """ Input related functions"""
    
    
    def get_channel_value(self, channel = False):
        if channel:
            if channel in ["Tp", "tp", "TP"]:
                channel = "Tp"
            elif channel in ["Tr", "tr", "TR"]:
                channel = "Tr"
            elif channel in ["T1s", "t1s", "T1S"]:
                channel = "T1s"
            elif channel in ["Tsw", "tsw", "TSW"]:
                channel = "Tsw"
            elif channel in ["hpump", "Hpump", "HPUMP"]:
                channel = "hpump"
            elif channel in ["switch", "Switch", "SWITCH"]:
                channel = "switch"
            else:
                print(f"Invalid channel name: {channel}. Must be 'Tp', 'Tr', 'T1s', 'Tsw', 'hpump', or 'switch'.")
                return None
        else:
            print("Channel not specified. Please provide 'Tp', 'Tr', 'T1s', 'Tsw', 'hpump', or 'switch'.")
            return None
        
        resp = self.query(f"{channel}.Value?")

        return resp.split("=", 1)[1].strip()
    
    def set_input_sensor(self, sensor = False, channel = False): # Sensor types, Diode, ROX, RTD, Therm
        if channel:
            if channel in ["Tp", "tp", "TP"]:
                channel = "Tp"
            elif channel in ["Tr", "tr", "TR"]:
                channel = "Tr"
            elif channel in ["T1s", "t1s", "T1S"]:
                channel = "T1s"
            elif channel in ["Tsw", "tsw", "TSW"]:
                channel = "Tsw"
            else:
                print(f"Invalid channel name: {channel}. Must be 'Tp', 'Tr', 'T1s', or 'Tsw'.")
                return None
        else:
            print("Channel not specified. Please provide 'Tp', 'Tr', 'T1s', or 'Tsw'.")
            return None
        
        if sensor:
            if sensor in ["Diode", "diode", "DIODE"]:
                sensor = "Diode"
            elif sensor in ["ROX", "rox", "Rox"]:
                sensor = "ROX"
            elif sensor in ["RTD", "rtd", "Rtd"]:
                sensor = "RTD"
            elif sensor in ["Therm", "therm", "THERM"]:
                sensor = "Therm"
            else:
                print(f"Invalid sensor type: {sensor}. Must be 'Diode', 'ROX', 'RTD', or 'Therm'.")
                return None
        else:
            print("Sensor type not specified. Please provide 'Diode', 'ROX', 'RTD', or 'Therm'.")
            return None
        
        return self.query(f"{channel}.Sensor {sensor}")
    
    
    
    
    def set_input_range(self, range = False, channel = False): # Range, Auto, 10e, 30e, 100e, 30e, ..., 2.5V
        if channel:
            if channel in ["Tp", "tp", "TP"]:
                channel = "Tp"
            elif channel in ["Tr", "tr", "TR"]:
                channel = "Tr"
            elif channel in ["T1s", "t1s", "T1S"]:
                channel = "T1s"
            elif channel in ["Tsw", "tsw", "TSW"]:
                channel = "Tsw"
            else:
                print(f"Invalid channel name: {channel}. Must be 'Tp', 'Tr', 'T1s', or 'Tsw'.")
                return None
        else:
            print("Channel not specified. Please provide 'Tp', 'Tr', 'T1s', or 'Tsw'.")
            return None
        
        if range is False:
            print("Range not specified. Please provide a valid range.")
            return None
        else:
            range = str(range) 
        
        return self.query(f"{channel}.Range {range}")
    
    
    
    def set_input_current(self, current = False, channel = False): # current type, Forward, Reverse, AC, Off
        if channel:
            if channel in ["Tp", "tp", "TP"]:
                channel = "Tp"
            elif channel in ["Tr", "tr", "TR"]:
                channel = "Tr"
            elif channel in ["T1s", "t1s", "T1S"]:
                channel = "T1s"
            elif channel in ["Tsw", "tsw", "TSW"]:
                channel = "Tsw"
            else:
                print(f"Invalid channel name: {channel}. Must be 'Tp', 'Tr', 'T1s', or 'Tsw'.")
                return None
        else:
            print("Channel not specified. Please provide 'Tp', 'Tr', 'T1s', or 'Tsw'.")
            return None
        
        if current:
            if current in ["Forward", "forward", "FORWARD"]:
                current = "Forward"
            elif current in ["Reverse", "reverse", "REVERSE"]:
                current = "Reverse"
            elif current in ["AC", "ac", "Ac"]:
                current = "AC"
            elif current in ["Off", "off", "OFF"]:
                current = "Off"
            else:
                print(f"Invalid current type: {current}. Must be 'Forward', 'Reverse', 'AC', or 'Off'.")
                return None
        else:
            print("Current type not specified. Please provide 'Forward', 'Reverse', 'AC', or 'Off'.")
            return None
        
        return self.query(f"{channel}.Current {current}")
    
    def set_input_power(self, power = False, channel = False): # power, Auto, Low, High
        if channel:
            if channel in ["Tp", "tp", "TP"]:
                channel = "Tp"
            elif channel in ["Tr", "tr", "TR"]:
                channel = "Tr"
            elif channel in ["T1s", "t1s", "T1S"]:
                channel = "T1s"
            elif channel in ["Tsw", "tsw", "TSW"]:
                channel = "Tsw"
            else:
                print(f"Invalid channel name: {channel}. Must be 'Tp', 'Tr', 'T1s', or 'Tsw'.")
                return None
        else:
            print("Channel not specified. Please provide 'Tp', 'Tr', 'T1s', or 'Tsw'.")
            return None
        if power:
            if power in ["Auto", "auto", "AUTO"]:
                power = "Auto"
            elif power in ["Low", "low", "LOW"]:
                power = "Low"
            elif power in ["High", "high", "HIGH"]:
                power = "High"
            else:
                print(f"Invalid power setting: {power}. Must be 'Auto', 'Low', or 'High'.")
                return None
        else:
            print("Power setting not specified. Please provide 'Auto', 'Low', or 'High'.")
            return None
        
        return self.query(f"{channel}.Power {power}")
    

    
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
    
    def set_output(self, status = False):
        if status:
            if status in ["On", "ON", "on"]:
                status = "on"
            elif status in ["Off", "OFF", "off"]:
                status = "off"
            else:
                print(f"Invalid status: {status}. Must be 'On' or 'Off'.")
                return None
        else:
            print("Status not specified. Please provide 'On' or 'Off'.")
            return None
        
        return self.query(f"outputEnable {status}")
    
    
    def wait_for_sample(self):
        return self.query("waitForSample")
    
    
    
    def set_pid_off(self):
        """Ping someone to check"""
        self.set_pid_status(status = "Off", channel = "hpump")
        self.set_pid_status(status = "Off", channel = "switch")
        self.set_channel_off(channel = "hpump")
        self.set_channel_off(channel = "switch")
    
        return


    def set_initial_input_config(self, cfg):

        inputs = cfg.get("inputs", {})

        for ch, s in inputs.items():
            if "Sensor" in s:
                self.set_input_sensor(sensor=str(s["Sensor"]), channel=ch)
            if "Range" in s:
                self.set_input_range(range=str(s["Range"]), channel=ch)
            if "Current" in s:
                self.set_input_current(current=str(s["Current"]), channel=ch)
            if "Power" in s:
                self.set_input_power(power=str(s["Power"]), channel=ch)

            alarm = s.get("Alarm", None)
            if isinstance(alarm, dict):
                if ("Min" in alarm) or ("Max" in alarm):
                    self.set_alarm_min_max(
                        min_val=str(alarm.get("Min", 0)),
                        max_val=str(alarm.get("Max", 0)),
                        channel=ch,
                    )
                
                if "Lag" in alarm:
                    self.set_alarm_lag(lag_time_s=str(alarm["Lag"]), channel=ch)
                if "Sound" in alarm:
                    self.set_alarm_sound(sound_status=str(alarm["Sound"]), channel=ch)
                if "Latch" in alarm:
                    self.set_alarm_latch(latch_status=str(alarm["Latch"]), channel=ch)
                if "Mode" in alarm:
                    self.set_alarm_mode(mode=str(alarm["Mode"]), channel=ch)
                if "Output" in alarm:
                    self.set_alarm_output(output_channel=str(alarm["Output"]), channel=ch)

        return     
        
    
    def set_initial_output_config(self, cfg):
        
        outputs = cfg.get("outputs", {})

        for ch, s in outputs.items():
            if "Units" in s:
                self.set_output_unit(units=str(s["Units"]), channel=ch)
            if "Range" in s:
                self.set_output_range(range=str(s["Range"]), channel=ch)

            if ("LowLmt" in s) or ("HiLmt" in s):
                low = str(s.get("LowLmt", 0.0))
                high = str(s.get("HiLmt", 0.0))
                self.set_output_limits(low_limit=low, high_limit=high, channel=ch)

            if "IOType" in s:
                self.set_output_io_type(io_type=str(s["IOType"]), channel=ch)

            pid = s.get("PID", None)
            if isinstance(pid, dict):
                if "Input" in pid:
                    self.set_pid_input(input=str(pid["Input"]), channel=ch)
                if "Setpoint" in pid:
                    self.set_pid_setpoint(setpoint=str(pid["Setpoint"]), channel=ch)
                if "Ramp" in pid:
                    self.set_pid_ramp_rate(rate=str(pid["Ramp"]), channel=ch)  # verify on your CTC
                self.set_pid_PID(
                    P=str(pid.get("P", 1.0)),
                    I=str(pid.get("I", 0.0)),
                    D=str(pid.get("D", 0.0)),
                    channel=ch,
                )

        return
    
    def _sleep_or_stop(self, stop_event, seconds: float) -> bool:
 
        if stop_event is None:  # incase stop_event isnt defined or anything, then is sleeps normally but cannot be stopped if it does
            time.sleep(seconds)
            return False
        return stop_event.wait(seconds) # waits seconds, as soon as someone calls stop_event.set() during the wait, it returns true and wakes early, else it returns False after timeout. Its a condition variable / futex style trigger like wake-up system
    
    def run_evaporation(self, stop_event=None, json_config_file = None):
        """Run evaporation"""
        
        if json_config_file is None:
            print("Please provide a json config file of the conditions for your cryo. And example should be found alongside this repo.")
            return 
        
        evap_cfg = json_config_file["temperature_conditions"]["evaporation"]
        Tp_start_thresh      = float(evap_cfg["Tp"])                     
        mini_cond_wait_s     = float(evap_cfg["mini_cond_wait_time"])    
        evap_wait_s          = float(evap_cfg["evap_wait_time"])         
        Tr_cold_thresh       = float(evap_cfg["Tr_cold"])                
        extra_evap_time_s    = float(evap_cfg["extra_evap_time"])        
        emergency_cond_s     = float(evap_cfg["emergency_cond_wait_time"])  
        Tr_warm_low          = float(evap_cfg["Tr_warm_low_end"])       
        Tr_warm_high         = float(evap_cfg["Tr_warm_high_end"])      
        extra_cond_check_s   = float(evap_cfg["extra_cond_time"])

        self.set_pid_off()
        self.set_output("on")
        t2 = time.time()
        
        while True: # Loop to check if the initial temperatures are met and safe to evaporate
            if stop_event is not None and stop_event.is_set():
                print("Evaporation stopped by user.")
                self.set_pid_off()
                return 1
            
        
            if float(self.get_channel_value(channel = "Tp")) > Tp_start_thresh: # Check if Tp is high enough to start evaporation, if yes, start evaporation PID Switch On
                self.set_pid_status(status = "On", channel = "switch") 
             
                break
            else:
                self.set_pid_off()     
                self.set_pid_status(status = "On", channel = "hpump") # If Tp is not high enough, condensate for 1.5h and try again 
                
                
                # time.sleep(60*90)
                if self._sleep_or_stop(stop_event, mini_cond_wait_s):
                    print("Evaporation stopped by user during pre-condensation wait.")
                    self.set_pid_off()
                    return 1
                
                self.set_pid_off()
                if abs(time.time() - t2) > 60*60*2: # 2 hours extra
                    """Slack notificaiton, evap starting conditions never met please check"""
                    return 2
                
        print("Starting Evaporation process")
        
        
        # time.sleep(60*60) # 1h wait to let the cryo evaporate and get down to low temp
        if self._sleep_or_stop(stop_event, evap_wait_s):
            print("Evaporation stopped by user during 1h evaporation wait.")
            self.set_pid_off()
            return 1

        
        t0 = time.time()  # Start timer to monitor how long its been since cold -ish
        while True:
            
            if stop_event is not None and stop_event.is_set():
                print("Evaporation stopped by user.")
                self.set_pid_off()
                return 1
            
            if float(self.get_channel_value(channel = "Tr")) < Tr_cold_thresh:  # Check if Tr is low enough, if cold enough, get out of the loop, evaporation was successful
                print("Evaporation complete. Cryo is cold. Happy Experimenting!")
                t_evaporation = time.time()
                return 0
            
            else:
                # time.sleep(60*5) 
                if self._sleep_or_stop(stop_event, extra_evap_time_s):
                    print("Evaporation stopped by user during Tr checks.")
                    self.set_pid_off()
                    return 1
                
                if abs(time.time() - t0) > 60*60: # 60 minutes extra
                    print("Evaporation taking too long. Aborting process.") # for the next 1h, check every 5 minutes to see if Tr is low enough, if Tr never gets to < 1K, attempt soft abort
                    self.set_pid_off()
                    self.set_pid_status(status = "On", channel = "hpump") # Soft abort = trying condensation procedure 
                    # time.sleep(60*60*2) # 2 hours condensation to make sure helium is back to normal level
                    
                    if self._sleep_or_stop(stop_event, emergency_cond_s):
                        print("Evaporation stopped by user during soft-abort condensation.")
                        self.set_pid_off()
                        return 1

                    
                    t1 = time.time()
                    while True:
                        if stop_event is not None and stop_event.is_set():
                            print("Evaporation stopped by user.")
                            self.set_pid_off()
                            return 1

                        if float(self.get_channel_value(channel = "Tp")) > Tp_start_thresh and Tr_warm_low < float(self.get_channel_value(channel = "Tr")) < Tr_warm_high: # Checking if soft abort was successful by checking if Tp is back to setpoint and that Tr is back to normal range. 
                            """pring slack channel with alert message that evap aborted softly"""
                            return 3
                        else:
                            # time.sleep(60*30)
                            if self._sleep_or_stop(stop_event, extra_cond_check_s):
                                print("Evaporation stopped by user during soft-abort checks.")
                                self.set_pid_off()
                                return 1

                            if abs(time.time() - t1) > 60*60: # for the next 1h, check every 30 min to see if soft abort was successful, if not, hard abort
                                print("resetting temp controller to safe state. Failed")
                                self.set_pid_off()
                                """ping slack channel with alert message that evap aborted hard"""
                                return 4
                    
                else:
                    continue 
            
        
               
        # Max runtime if aborts = 9h
    
    
    def run_condensation(self, stop_event=None, json_config_file=None):
        """Run condensation"""
        
        if json_config_file is None:
            print("Please provide a json config file of the conditions for your cryo. And example should be found alongside this repo.")
            return 
        
        cond_cfg = json_config_file["temperature_conditions"]["condensation"]
        cond_wait_s       = float(cond_cfg["cond_wait_time"])                
        Tp_end_thresh    = float(cond_cfg["Tp"])        
        Tr_warm_low          = float(cond_cfg["Tr_warm_low_end"])       
        Tr_warm_high         = float(cond_cfg["Tr_warm_high_end"]) 
        extra_cond_time_s     = float(cond_cfg["extra_cond_time"])  
        
        
        
        self.set_output("on")
        self.set_pid_off()
     

        self.set_pid_status(status = "On", channel = "hpump")
        print("Starting Condensation process")
           
        # time.sleep(60*60*1.5) # turning condensation on and waiting 1.5h to let the cryo condense enough helium
        if self._sleep_or_stop(stop_event, cond_wait_s):
            print("Condensation stopped by user during initial 1.5h wait.")
            self.set_pid_off()
            return 1

        t0 = time.time()
        while True:
            if stop_event is not None and stop_event.is_set():
                print("Condensation stopped by user.")
                self.set_pid_off()
                return 1
            
            if float(self.get_channel_value(channel = "Tp")) > Tp_end_thresh and Tr_warm_low < float(self.get_channel_value(channel = "Tr")) < Tr_warm_high: # checking if Tp is at the setpoint and that Tr is in the normal range
                print("Condensation complete. Cryo is ready!")
                return 0
            else:
                # time.sleep(60*5) # for the nect 1h30, check every 5 minutes to see if Tp and Tr are at the right values, if not, abort and send slack message.
                if self._sleep_or_stop(stop_event, extra_cond_time_s):
                    print("Condensation stopped by user during checks.")
                    self.set_pid_off()
                    return 1
                if time.time() - t0 > 60*90: # 90 minutes extra
                    print("Condensation taking too long. Aborting process.")
                    self.set_pid_off()
                    return 5
                else:
                    continue
                    
        
         # Max runtime if abort = 3h
    
    
    
    def force_abort(self):
        
        self.set_pid_off()
        self.set_output("off")
        self.query("abort")
        print("Aborted any running process and set to safe state.")
        return
    
    
    def kill_all(self):
        return self.query("kill.all")
    
    
    
    
    
    



if __name__ == '__main__':
    with TempControl_CTC100('ASRL/dev/ttyUSB0::INSTR', 'CTC100') as tc: #ASRL/dev/ttyUSB0::INSTR  ASRL/dev/ttyACM0::INSTR
        print("Connected to CTC100 interactive window session")
        print("\n>>>> USE TEMP CONTROLLER OBJECT AS tc <<<<\n")
        import code; code.interact(local=locals())
# %%
