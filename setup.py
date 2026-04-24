import cx_Freeze
from cx_Freeze import *

setup(
    name = "GeneTech",
    options = {'build_exe':{'packages':['pyqt5', 'schemdraw',
                                        'matplotlib', 'dnaplotlib',
                                        'py4j', 'sbol2', 'sbol3', 'PIL']}},
    executables = [
        Executable(
            "Genetech.py",
            )
        ] 


    )
