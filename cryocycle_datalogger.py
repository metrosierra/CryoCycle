import sys
import os
import numpy as np

config_relative_path = '/'
drivers_relative_path = '/'
sys.path.insert(1, os.path.join(sys.path[0], drivers_relative_path)) ### TO POINT TO DEVICE INTERFACING FOLDER
abs_path = os.path.dirname(os.path.abspath(__file__))
if abs_path not in sys.path:
    sys.path.insert(0, abs_path)

from drivers.tempcontroller_ctc100 import TempControl_CTC100
from drivers.liveplotter_heavy import LivePlotAgent 