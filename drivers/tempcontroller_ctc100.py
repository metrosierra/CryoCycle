import os
import sys

from generic_instrument_dependencies.generic_instrument import GenericInstrument


class TempControl_CTC100(GenericInstrument):
    def __init__(self, address, name):
        self.write_term = '\n'
        self.read_term = '\r\n'
        super().__init__(address, name = name,
                        write_term = self.write_term, 
                        read_term = self.read_term)
        
        self.baud_rate = 9600
        self.client.baud_rate = self.baud_rate


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return
    
    def close(self):
        self.client.close()
        self.client = None
        self.__exit__(None, None, None)
        return
    

if __name__ == '__main__':
    with TempControl_CTC100('GPIB::1::INSTR', 'CTC100') as temp_controller:
        print("Connected to CTC100 interactive window session")
        import code; code.interact(local=locals())