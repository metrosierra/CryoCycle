#%%
import os
import sys
import threading
import numpy as np
import time

from generic_instrument_dependencies.generic_instrument import GenericInstrument


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
    


if __name__ == '__main__':
    with TempControl_CTC100('ASRL/dev/ttyUSB0::INSTR', 'CTC100') as tc:
        print("Connected to CTC100 interactive window session")
        print("\n>>>> USE TEMP CONTROLLER OBJECT AS tc <<<<\n")
        import code; code.interact(local=locals())