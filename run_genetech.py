#!/usr/bin/env python
# run_genetech.py - Launcher with all fixes

import os
import sys
import numpy as np

# Add numpy compatibility fixes
if not hasattr(np, 'Inf'):
    np.Inf = np.inf
if not hasattr(np, 'NaN'):
    np.NaN = np.nan
if not hasattr(np, 'NINF'):
    np.NINF = -np.inf
if not hasattr(np, 'PINF'):
    np.PINF = np.inf

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Now import and run GeneTech
from Genetech import MainPage
from PyQt5 import QtWidgets

if __name__ == '__main__':
    print("="*60)
    print("🧬 GeneTech with NumPy compatibility fixes")
    print("="*60)
    print(f"NumPy version: {np.__version__}")
    print(f"Python version: {sys.version}")
    print("="*60)
    
    app = QtWidgets.QApplication(sys.argv)
    window = MainPage()
    window.show()
    sys.exit(app.exec_())
