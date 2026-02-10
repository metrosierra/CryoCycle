import logging
from pyvisa import ResourceManager, VisaIOError
import numpy as np
import threading
import time
from queue import Queue
from datetime import datetime, timezone
import json
import matplotlib.pyplot as plt 
import requests
import os




class Slack:
    
    
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.config = None


    def load_config(self, config_name=False):
        config_path = os.path.join(self.config_dir, config_name)
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        return self.config
    

    def send_message_to_slack(self, error_code: int, json_slack= False):
        
        if not json_slack:
            print("Please provide a valid json congif file")
            return 
        
        if error_code is None:
            print("Please provide an error code")
            return
        
        cfg = json_slack
        
        
        
        url = cfg["slack_url"]

        message = cfg["error_code_messages"][str(error_code)]
        
        r = requests.post(url, json={"text": message}, timeout=5)
        r.raise_for_status()
        return
    
    