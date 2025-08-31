import os
import sys
abs_path = os.path.dirname(os.path.abspath(__file__))
if abs_path not in sys.path:
    sys.path.insert(1, abs_path)
