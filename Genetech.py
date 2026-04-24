import os
import re
import sys
import time
import traceback
from PIL import Image
import SBOL_File as sbol
import Logical_Representation as logic
import SBOL_visual as visual
from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import pyqtSlot, QCoreApplication, QBasicTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QDialog, QPushButton, QLabel, QLineEdit, QMessageBox, QFileDialog, QTabWidget, QWidget, QListWidget, QProgressBar, QInputDialog
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon, QFont, QPixmap
from itertools import product
from functions import *
from time import sleep
import random
from main import process
import sys

try:
    from nlp_groq import GroqNLParser
except Exception:
    GroqNLParser = None

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

sys.path.append("circuit_canvas/")
#from main_window import CircuitBuilder
try:
    from circuit_canvas.main_window import CircuitBuilder
except Exception:
    CircuitBuilder = None
from nlp_local import LocalNLParser
from gentech_database import GeneTechDatabase

font = QFont("Times", 11)

# The main class which operates the entire window
class MainPage(QtWidgets.QMainWindow):
    def __init__(self):
        USER_FILES_DIR.mkdir(exist_ok=True)

        # Lists which are being used in the code later
        self.result=[]
        self.tablist=[]
        self.checkList=[]
        self.checkxmlList=[]
        super(MainPage, self).__init__()

        #Loading the UI file which have been created for the main window
        loadUi(str(BASE_DIR / 'Genetech.ui'), self)

        #Setting the logos for the window
        self.setWindowIcon(QtGui.QIcon(str(BASE_DIR / 'icons' / 'SmallLogo.png')))
        self.setWindowTitle("GeneTech - v2.0")
        pixmap = QPixmap(str(BASE_DIR / 'icons' / 'BigLogo.png'))
        self.MainLogo.setPixmap(pixmap)

        #Initial Label in the status bar
        self.statusBar().showMessage('Ready')

        # Button Entries which have been coded and these are called when button are clicked
        self.SaveButton.clicked.connect(self.SaveLabel)
        self.DrawButton.clicked.connect(self.DrawWindow)
        self.ViewButton.clicked.connect(self.viewCircuit)
        self.ImportNotesButton.clicked.connect(self.FileOpenDialog)
        self.SaveNotesButton.clicked.connect(self.SaveNotes)
        self.EnterButton.clicked.connect(self.EnterExp)
        self.ExitButton.clicked.connect(self.ResetAll)
        self.DatabaseButton.clicked.connect(self.checkDatabase)

        self.CircuitList.doubleClicked.connect(self.saveImageDialog)
        self.xmlList.clicked.connect(self.ReadXMLFile)
        self.bexppp = self.InsertExpressionEdit.text()
        self.LabelforList = QLabel(self.tab)
        self.doubleSpinBox.setSuffix(" s")
        self.actionExit.triggered.connect(self.CloseApp)
        self.actionAbout.triggered.connect(self.About)

        # Add Natural Language button
        self.NLPButton = QPushButton("Natural Language", self)
        self.NLPButton.setFont(font)
        self.NLPButton.clicked.connect(self.natural_language_input)
        self.NLPButton.setStatusTip("Describe your circuit in plain English")
        self.gridLayout.addWidget(self.NLPButton, 4, 8, 1, 2)

        #Keyboard Shortcuts for some funtionalities
        self.EnterButton.setShortcut("Return")
        self.actionExit.setShortcut("Ctrl+Q")
        self.actionAbout.setShortcut("Ctrl+O")
        self.ExitButton.setShortcut("Ctrl+R")

        # Messages on the status bar when mouse is hovered on different windows parts
        self.actionAbout.setStatusTip("Know more about GeneTech by clicking this button")
        self.actionExit.setStatusTip("Reset")
        self.EnterButton.setStatusTip("Press the button for result")
        self.ExitButton.setStatusTip("Exit the window")
        self.InsertExpressionEdit.setStatusTip("Insert a Boolean expression here")

    def _handle_expression_error(self, stage, error):
        tb = traceback.format_exc()
        self.statusBar().showMessage(f'Expression processing failed during {stage}')
        print(tb)
        QMessageBox.critical(
            self,
            "Expression Error",
            f"The inserted expression could not be processed during {stage}.\n\n{error}\n\n{tb}"
        )

    def _normalize_expression_variables(self, bexp):
        variable_map = {
            "a": "IPTG",
            "b": "aTc",
            "c": "Arabinose",
        }

        def replace_token(match):
            token = match.group(0)
            return variable_map.get(token, token)

        normalized = re.sub(r"(?<![A-Za-z])(a|b|c)(?![A-Za-z])", replace_token, bexp)
        simplified_terms = []

        for raw_term in normalized.split("+"):
            if not raw_term:
                continue

            seen_literals = {}
            ordered_literals = []
            contradictory_term = False

            for literal in raw_term.split("."):
                literal = literal.strip()
                if not literal:
                    continue

                base_literal = literal[:-1] if literal.endswith("'") else literal
                polarity = literal.endswith("'")

                if base_literal in seen_literals:
                    if seen_literals[base_literal] != polarity:
                        contradictory_term = True
                        break
                    continue

                seen_literals[base_literal] = polarity
                ordered_literals.append(literal)

            if not contradictory_term and ordered_literals:
                simplified_terms.append(".".join(ordered_literals))

        return "+".join(simplified_terms)

    def _canonicalize_expression(self, bexp):
        if not bexp:
            return ""

        expr = bexp
        replacements = {
            '’': "'",
            '‘': "'",
            '”': '"',
            '“': '"',
            '`': "'",
            '′': "'",
            '‛': "'",
        }
        for old, new in replacements.items():
            expr = expr.replace(old, new)

        expr = re.sub(r'(?i)\biptg\b', 'IPTG', expr)
        expr = re.sub(r'(?i)\batc\b', 'aTc', expr)
        expr = re.sub(r'(?i)\barabinose\b', 'Arabinose', expr)

        expr = re.sub(r'(?i)\bnot\b', '!', expr)
        expr = re.sub(r'(?i)\band\b', '.', expr)
        expr = re.sub(r'(?i)\bor\b', '+', expr)
        expr = expr.replace('&', '.').replace('*', '.')
        expr = expr.replace('|', '+')

        # Convert prefix negation on literals into the postfix prime notation used by the mapper.
        expr = re.sub(r'([!~])\s*(IPTG|aTc|Arabinose|a|b|c)\b', r"\2'", expr)

        expr = re.sub(r'\s+', '', expr)
        expr = expr.replace('"', '')

        # Users often wrap each product term in parentheses; the backend only wants raw SOP products.
        previous = None
        while previous != expr:
            previous = expr
            expr = re.sub(r'\(([^()+]+)\)', r'\1', expr)

        expr = expr.replace('..', '.')
        expr = expr.replace('++', '+')
        expr = expr.strip('.+')
        return expr

    def _expression_candidates(self, bexp):
        candidates = []
        for candidate in [
            bexp,
            self._canonicalize_expression(bexp),
        ]:
            if not candidate:
                continue
            if candidate not in candidates:
                candidates.append(candidate)

        normalized_candidates = []
        for candidate in candidates:
            normalized = self._normalize_expression_variables(candidate)
            if normalized and normalized not in candidates and normalized not in normalized_candidates:
                normalized_candidates.append(normalized)

        candidates.extend(normalized_candidates)
        return candidates

    def _run_expression_pipeline(self, bexp, option, include_sbol=False, update_progress=False):
        try:
            attempted_expressions = []
            circuits = []
            synthesis_attempts = []
            max_attempts_per_candidate = 5

            for candidate in self._expression_candidates(bexp):
                if not candidate or candidate in attempted_expressions:
                    continue
                attempted_expressions.append(candidate)
                for attempt in range(1, max_attempts_per_candidate + 1):
                    synthesis_attempts.append(f"{candidate} [attempt {attempt}]")
                    process(candidate)
                    circuits = self.ReadCircuitsFile()
                    if circuits:
                        bexp = candidate
                        break
                if circuits:
                    break

            if not circuits:
                raise ValueError(
                    "No valid circuits could be generated from that expression. "
                    "Tried: " + ", ".join(synthesis_attempts) + ". "
                    "This usually means the current gate library cannot map that Boolean function into available circuits. "
                    "Try using IPTG, aTc, and Arabinose notation, or simple a/b/c shorthand."
                )
            DisplayData()
            DisplayCircuits()

            if update_progress:
                self.ProgressBar.setValue(25)
                sleep(1)
                self.ProgressBar.setValue(random.randint(30, 70))

            if include_sbol:
                sbol.SBOL_File(
                    self.spinBox.value(),
                    self.doubleSpinBox.value(),
                    option,
                    self.CircuitSpinBox.value()
                )

            if update_progress:
                self.ProgressBar.setValue(random.randint(75, 90))
                sleep(0.1)

            logic.Logical_Representation(
                self.spinBox.value(),
                self.doubleSpinBox.value(),
                option,
                self.CircuitSpinBox.value()
            )
            visual.SBOLv(
                self.spinBox.value(),
                self.doubleSpinBox.value(),
                option,
                self.CircuitSpinBox.value()
            )

            if update_progress:
                self.ProgressBar.setValue(100)
            return True
        except Exception as e:
            self._handle_expression_error("circuit generation", e)
            return False

    def _resolve_sbol_file_path(self, item_text):
        candidates = [
            USER_FILES_DIR / f"{item_text}.xml",
            BASE_DIR / f"{item_text}.xml",
        ]
        for path in candidates:
            if os.path.exists(path):
                return str(path)
        return str(candidates[0])

    def _show_sbol_empty_state(self, message):
        self.xmlList.clear()
        self.Notes.setText(message)
        self.statusBar().showMessage(message)

    def _load_first_sbol_file(self):
        if self.xmlList.count() == 0:
            return
        self.xmlList.setCurrentRow(0)
        self.ReadXMLFile()

    def _populate_truth_table(self, bexp):
        a = 0
        try:
            bexp = Convert(bexp)
            bexp = "".join(bexp.split())
            finalexp = []
            exp = bexp.split("+")
            for i in range(len(exp)):
                term = exp[i].split(".")
                finalterm = []
                for j in range(len(term)):
                    if term[j][-1] == "'":
                        finalterm.append("not(" + term[j][:-1] + ")")
                    else:
                        finalterm.append(term[j])
                finalexp.append("(" + " and ".join(finalterm) + ")")
            bexp = " or ".join(finalexp)
            code = compile(bexp, '', 'eval')
            TruthTable_Input = code.co_names
            for values1 in product(range(2), repeat=len(TruthTable_Input)):
                header_count = 2 ** (len(values1))
                List_TruthTable_Input = [[] for i in range(1, header_count + 1)]
            self.TruthList.clear()
            for BexpIndex in range(len(TruthTable_Input)):
                self.ttList.append(TruthTable_Input[BexpIndex])
                self.ttList.append("   ")
            self.ttList.append(":   ")
            self.ttList.append(bexp)
            s = [str(i) for i in self.ttList]
            res = " ".join(s)
            self.TruthList.addItem(res)
            self.ttList.clear()
            for values in product(range(2), repeat=len(TruthTable_Input)):
                for w in range(len(values)):
                    List_TruthTable_Input[a].append(str(values[w]))
                a += 1
                env = dict(zip(TruthTable_Input, values))
                pk = int(eval(code, env))

                for v in values:
                    self.ttList.append(v)
                    self.ttList.append("     ")
                self.ttList.append(":       ")
                self.ttList.append(pk)
                s = [str(i) for i in self.ttList]
                res = " ".join(s)
                self.TruthList.addItem(res)
                self.ttList.clear()
            return True
        except Exception as e:
            self.TruthList.clear()
            self.ttList.clear()
            self._handle_expression_error("truth table generation", e)
            return False

    def natural_language_input(self):
        """Convert natural language to Boolean expression using local parsing or Groq"""
        text, ok = QInputDialog.getMultiLineText(
            self,
            "Natural Language Input",
            "Describe your circuit in plain English:\n\n"
        )
        
        if ok and text:
            self.statusBar().showMessage('🤖 Processing input...')
            QApplication.processEvents()
            
            try:
                expression = None
                parser_name = "Local Parser"

                # Try local parser first for simple shorthand inputs.
                try:
                    local_result = LocalNLParser().parse(text)
                    if local_result and local_result.get('expression'):
                        expression = local_result['expression']
                except Exception:
                    expression = None

                # Fall back to Groq if local parsing did not produce an expression.
                if not expression:
                    parser_name = "Groq"
                    if GroqNLParser is None:
                        raise RuntimeError("Groq support is not installed in this environment.")
                    import os
                    api_key = os.getenv("GROQ_API_KEY")
                    if not api_key:
                        api_key, ok = QInputDialog.getText(
                            self, "Groq API Key", 
                            "Enter your free Groq API key:\n"
                            "Get it at: console.groq.com/keys\n\n"
                            "It's completely FREE and takes 30 seconds!"
                        )
                        if not ok or not api_key:
                            return
                        os.environ["GROQ_API_KEY"] = api_key
                    
                    parser = GroqNLParser(api_key)
                    expression = parser.parse(text)

                # Clean up smart quotes and spaces
                if expression:
                    # clean up smart quotes and special characters
                    expression = expression.replace('’', "'")  # fancy right quote
                    expression = expression.replace('‘', "'")  # fancy left quote
                    expression = expression.replace('”', '"')  # fancy double quote
                    expression = expression.replace('“', '"')  # fancy double quote
                    expression = expression.replace('"', '')   # remove any double quotes
                    expression = expression.replace('`', "'")  # backticks
                    expression = expression.replace('′', "'")  # prime symbol
                    expression = expression.replace('‛', "'")  # fancy quote
                    expression = expression.replace(' ', '')   # remove all spaces
                    
                    # Also fix any other potential issues
                    expression = expression.replace('&', '.')  # & to .
                    expression = expression.replace('|', '+')  # | to +
                    
                    print(f"Cleaned expression: {expression}")  # Debug print
                    
                    # Now set it
                    self.InsertExpressionEdit.setText(expression)
                
                if expression:
                    msg = f"{parser_name} converted your description:\n\n"
                    msg += f"'{text}'\n\n"
                    msg += f"→ {expression}\n\n"
                    msg += "Insert into expression field?"
                    
                    reply = QMessageBox.question(
                        self, f"{parser_name} Result", msg,
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes:
                        self.InsertExpressionEdit.setText(expression)
                        self.statusBar().showMessage('Expression ready - click Enter')
                    else:
                        self.statusBar().showMessage('Cancelled')
                else:
                    QMessageBox.critical(self, "Error", "Could not parse your request.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error:\n{str(e)}")

            def _local_natural_language_fallback(self, text):
                """Fallback to local NLP parser"""
                try:
                    from nlp_local import LocalNLParser
                    parser = LocalNLParser()
                    result = parser.parse(text)
                    
                    msg = f"Parsed with local parser!\n\n"
                    msg += f"Expression: {result['expression']}\n"
                    msg += f"Variables: {', '.join(result['variables'])}\n\n"
                    msg += "Insert into expression field?"
                    
                    reply = QMessageBox.question(
                        self, "Local Parser Result", msg,
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes:
                        self.InsertExpressionEdit.setText(result['expression'])
                        self.statusBar().showMessage('Expression ready - click Enter')
                        
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Local parser also failed:\n{str(e)}")

    # Database Check
    def checkDatabase(self):
        """Check parts against iGEM database"""
        if not CIRCUITS_FILE.exists():
            QMessageBox.warning(self, "Warning", "Generate circuits first")
            return
        
        self.statusBar().showMessage('Checking iGEM database...')
        
        try:
            db = GeneTechDatabase()
            report = db.analyze_circuits_file(CIRCUITS_FILE)
            results = [entry["availability"] for entry in report["parts"]]

            if not results:
                QMessageBox.information(self, "No Parts", "No parts found")
                return

            summary = report["summary"]
            buildable_text = "Yes" if summary["all_circuits_buildable"] else "No"

            msg = "Genetic Parts Availability Check\n\n"
            msg += f"Registries queried: {', '.join(report['providers'])}\n"
            msg += f"Total unique parts: {summary['total_parts']}\n"
            msg += f"Available parts: {summary['available_parts']}\n"
            msg += f"Missing parts: {summary['missing_parts']}\n"
            msg += f"Buildable circuits: {summary['buildable_circuits']}/{summary['total_circuits']}\n"
            msg += f"Requested functionality buildable: {buildable_text}\n\n"

            missing_parts = [entry for entry in report["parts"] if not entry["availability"]["available"]]
            if missing_parts:
                msg += "Missing or unmapped parts:\n"
                for entry in missing_parts:
                    availability = entry["availability"]
                    reason = availability.get("reason") or "Unavailable"
                    msg += f"  • {entry['part']} ({entry['part_type']}): {reason}\n"
                msg += "\n"

            unbuildable_circuits = [entry for entry in report["circuits"] if not entry["buildable"]]
            if unbuildable_circuits:
                msg += "Circuits blocked by unavailable parts:\n"
                for circuit in unbuildable_circuits:
                    missing_names = ", ".join(part["part"] for part in circuit["missing_parts"])
                    msg += f"  • Circuit {circuit['circuit_index']}: {missing_names}\n"
                msg += "\n"

            msg += f"Saved report: {report['report_file']}"

            QMessageBox.information(self, "Database Check", msg)
            self.statusBar().showMessage(
                f"Database check complete: {summary['buildable_circuits']}/{summary['total_circuits']} circuits buildable"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Database check failed:\n{str(e)}")

    #This function is to open the drawing canvas
    def DrawWindow(self):
        if CircuitBuilder is None:
            QMessageBox.warning(self, "Unavailable", "Circuit Builder dependencies are not installed in this environment.")
            return
        self.circuit_builder = CircuitBuilder(self)
        self.circuit_builder.show()
        self.hide()

    #Takes the boolean expression of the circuit drawn in the circuit canvas, processes it as before
    #and after performing all relevant functions lists the output circuits and SBOL files
    def processDrawEquation(self, bexp):
        if self.DelayRadioButton.isChecked():
            option = 0
        elif self.GatesRadioButton.isChecked():
            option = 1
        self.InsertExpressionEdit.setText(bexp)
        #self.ProgressBar.setVisible(True)
        #self.ProgressBar.setValue(0)
        self.result.append("a")

        if not self._run_expression_pipeline(bexp, option, include_sbol=True, update_progress=True):
            self.result.clear()
            return

        if not self._populate_truth_table(bexp):
            self.result.clear()
            return

        if len(self.result) > 0: #Call these functions only if there is an expression
            self.CreateCircuitList()
            self.CreateXMLList()
            self._load_first_sbol_file()
            self.result.clear()

    # This function reads the txt which of circuits and returns a list
    #with the number of generated circuits by the inserted boolean expression
    '''
    def ReadCircuitsFile(self):
        circuits = []
        try:
            with open("circuits.txt", "r") as f:
                lines = f.readlines()
            
            current_circuit = []
            for line in lines:
                if "*******************" in line:
                    if current_circuit:
                        circuits.append(current_circuit)
                        current_circuit = []
                else:
                    if line.strip():
                        current_circuit.append(line.strip())
            
            # Add the last circuit
            if current_circuit:
                circuits.append(current_circuit)
                
        except FileNotFoundError:
            print("circuits.txt not found")
            
        return circuits
    '''

    def ReadCircuitsFile(self):
        """Read circuits from circuits.txt"""
        circuits = []
        try:
            with open(CIRCUITS_FILE, 'r') as f:
                content = f.read()
            
            # Split by circuit headers
            blocks = content.split('*******************')
            
            for block in blocks:
                if not block.strip():
                    continue
                
                # Extract lines that are part of the circuit
                lines = []
                for line in block.strip().split('\n'):
                    line = line.strip()
                    # Skip header lines and empty lines
                    if line and not line.startswith('*') and 'Genetic Circuit' not in line:
                        lines.append(line)
                
                if lines:
                    circuits.append(lines)
            
            print(f"Read {len(circuits)} circuits from file")
            
        except FileNotFoundError:
            print("circuits.txt not found")
        except Exception as e:
            print(f"Error reading circuits: {e}")
        
        return circuits

    def viewCircuit(self):
        if self.CircuitList.currentItem():
            item_text = self.CircuitList.currentItem().text()
            
            # Extract circuit number
            import re
            numbers = re.findall(r'\d+', item_text)
            if numbers:
                circuit_num = numbers[0]
                
                # Determine which image to show
                if "SBOL Visual" in item_text:
                    img_path = USER_FILES_DIR / f'Circuit {circuit_num} SBOL Visual.png'
                elif "Logic" in item_text:
                    img_path = USER_FILES_DIR / f'Circuit {circuit_num} Logic.png'
                else:
                    img_path = USER_FILES_DIR / f'Circuit {circuit_num}.png'
                
                if os.path.exists(img_path):
                    img = Image.open(img_path)
                    img.show()
                else:
                    QMessageBox.warning(self, "Not Found", f"Image not found: {str(img_path)}")
            else:
                # Fallback to old method
                img_path = USER_FILES_DIR / f'{item_text}.png'
                if os.path.exists(img_path):
                    img = Image.open(img_path)
                    img.show()
                else:
                    QMessageBox.warning(self, "Not Found", f"Image not found: {item_text}")

    def SaveLabel(self):
        item = self.CircuitList.currentItem()
        self.saveImageDialog()

    # When the circuits are developed using the boolean expression
    #This function creates the list of the circuits by reading the
    # txt file of the circuits.
    '''
    def CreateCircuitList(self):
        circuits = self.ReadCircuitsFile()
        
        self.CircuitList.clear()
        self.checkList.clear()
        
        for i in range(len(circuits)):
            circuit_num = i + 1
            self.CircuitList.addItem(f"Circuit {circuit_num} Logic")
            self.CircuitList.addItem(f"Circuit {circuit_num} SBOL Visual")
            self.checkList.append("Check")
    '''

    def CreateCircuitList(self):
        """Create the circuit list display from actual circuits"""
        circuits = self.ReadCircuitsFile()
        
        self.CircuitList.clear()
        self.checkList.clear()
        
        if not circuits:
            print("No circuits found")
            self.statusBar().showMessage('No circuits found')
            return
        
        for i in range(len(circuits)):
            circuit_num = i + 1
            self.CircuitList.addItem(f"Circuit {circuit_num} Logic")
            self.CircuitList.addItem(f"Circuit {circuit_num} SBOL Visual")
            self.checkList.append("Check")
        
        print(f"Added {len(circuits)} circuits to display")
        self.statusBar().showMessage(f'Found {len(circuits)} circuits')

    #Code for importing a file in Notes
    def FileOpenDialog(self):
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog

            UserfileName, _ = QFileDialog.getOpenFileName(self,"Import File to Notes", "","All Files (*);;TxtFiles (*.txt)", options=options)
            if UserfileName:
                f = open(UserfileName,"r")
                data = f.read()
                self.Notes.setText(data)


    # When the circuits are developed using the boolean expression
    #This function creates the list of XML files of the
    #generated circuits by reading the
    # txt file of the circuits.
    def CreateXMLList(self):
        self.xmlList.clear()
        self.checkxmlList.clear()
        xml_files = sorted(
            USER_FILES_DIR.glob("SBOL File *.xml"),
            key=lambda path: int(re.search(r"(\d+)", path.stem).group(1)) if re.search(r"(\d+)", path.stem) else 0
        )
        for path in xml_files:
            self.xmlList.addItem(path.stem)
            self.checkxmlList.append("Check")

        if not xml_files:
            self.Notes.setText(
                "No SBOL files were generated for this expression.\n\n"
                "If circuit generation failed, this expression is not supported by the current gate library.\n"
                "Try another expression to populate the SBOL Data view."
            )
            self.statusBar().showMessage('No SBOL files generated')
        else:
            self.statusBar().showMessage(f'Loaded {len(xml_files)} SBOL files')

    #This function is created to save the xml file for the generated circuits.
    def FileSaveDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        UserfileName, _ = QFileDialog.getSaveFileName(self,"Save SBOL File","","All Files (*);;XML Files (*.xml)", options=options)
        if UserfileName:
            fileName = UserfileName.split("/")[-1]
            if (":" in fileName) or ("?" in fileName) or ("/" in fileName) or ("*" in fileName) or ("<" in fileName) or (">" in fileName) or ("|" in fileName) or ('"' in fileName):
                QMessageBox.about(self, "Alert", "A file name can't contain any of the following \n \ / : * ? < > |")
            else:
                f= open(UserfileName,"w+")
                item = self.xmlList.currentItem()
                if item is None:
                    QMessageBox.warning(self, "Warning", "No SBOL file selected")
                    f.close()
                    return
                source_path = self._resolve_sbol_file_path(str(item.text()))
                if not os.path.exists(source_path):
                    QMessageBox.warning(self, "Not Found", f"SBOL file not found: {source_path}")
                    f.close()
                    return
                fo = open(source_path)
                for i in fo:
                    f.write(i)

    def ReadXMLFile(self):
        item = self.xmlList.currentItem()
        if item is None:
            QMessageBox.warning(self, "Warning", "No SBOL file selected")
            return
        file = item.text()
        file_path = self._resolve_sbol_file_path(str(file))
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Not Found", f"SBOL file not found: {file_path}")
            self.statusBar().showMessage('SBOL file not found')
            return
        with open(file_path, "r") as f:
            data = f.read()
        self.Notes.setText(data)
        self.statusBar().showMessage(f'Loaded {os.path.basename(file_path)}')

    #THis functions save the text from the Notes Tab on Main window
    def SaveNotes(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        InputFile, _ = QFileDialog.getSaveFileName(self,"Save Notes","","All Files (*);;Txt Files (*.txt)", options=options)
        Text = self.Notes.toPlainText()
        if InputFile:
            f= open(InputFile+".xml","w+")
            f.write(Text)

    #This function is created to save an image file for the generated circuits.
    def saveImageDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        UserfileName, _ = QFileDialog.getSaveFileName(self,"Save Image File","","All Files (*);;Image Files (*.png)", options=options)
        if UserfileName:
            fileName = UserfileName.split("/")[-1]
            if (":" in fileName) or ("?" in fileName) or ("/" in fileName) or ("*" in fileName) or ("<" in fileName) or (">" in fileName) or ("|" in fileName) or ('"' in fileName):
                QMessageBox.about(self, "Alert", "A file name can't contain any of the following \n \ / : * ? < > |")
            else:
                item = self.CircuitList.currentItem()
                # Extract circuit number
                import re
                numbers = re.findall(r'\d+', item.text())
                if numbers:
                    circuit_num = numbers[0]
                    if "SBOL Visual" in item.text():
                        img_path = USER_FILES_DIR / f'Circuit {circuit_num} SBOL Visual.png'
                    elif "Logic" in item.text():
                        img_path = USER_FILES_DIR / f'Circuit {circuit_num} Logic.png'
                    else:
                        img_path = USER_FILES_DIR / f'Circuit {circuit_num}.png'
                    
                    if os.path.exists(img_path):
                        saveimg = Image.open(img_path)
                        saveimg.save(str(UserfileName)+".png")
                    else:
                        QMessageBox.warning(self, "Not Found", "Image file not found")
                else:
                    saveimg = Image.open(USER_FILES_DIR / (str(item.text()) + ".png"))
                    saveimg.save(str(UserfileName)+".png")

    #This function, upon clicking the reset button on main window,
    #clears all the generated/entered values on the main window
    def ResetAll(self):
        mBox = QMessageBox.question(self, "Warning!!", "Are you sure you want to clear?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if mBox == QMessageBox.Yes:
            self.InsertExpressionEdit.clear()
            self.spinBox.setValue(10)
            self.doubleSpinBox.setValue(100)
            self.CircuitSpinBox.setValue(10)
            self.xmlList.clear()
            self.CircuitList.clear()
            self.TruthList.clear()
            #self.ProgressBar.setValue(0)
            self.Notes.clear()

    def ResetBeforeNew(self):
        self.xmlList.clear()
        self.CircuitList.clear()
        self.TruthList.clear()
        #self.ProgressBar.setValue(0)
        self.Notes.clear()

    #This function is dedicated to close the main window
    def CloseApp(self):
        mBox = QMessageBox.question(self, "Warning!!", "Are you sure you want exit?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if mBox == QMessageBox.Yes:
            sys.exit()

    def About(self):
        about_path = BASE_DIR / 'AboutGenetech.txt'
        if sys.platform.startswith("darwin"):
            os.system(f'open "{about_path}"')
        elif os.name == "nt":
            os.startfile(str(about_path))
        else:
            os.system(f'xdg-open "{about_path}"')

    #This is the most important function of this code.
    ttList=[]
    List_TruthTable_Input =[]
    def EnterExp(self):
        if self.DelayRadioButton.isChecked():
            option = 0
        elif self.GatesRadioButton.isChecked():
            option = 1
        bexp = self.InsertExpressionEdit.text() #User expression
        
        # ===== ADD CLEANING RIGHT HERE =====
        # Replace all fancy quotes with straight quotes
        bexp = bexp.replace('’', "'")
        bexp = bexp.replace('‘', "'")
        bexp = bexp.replace('”', '"')
        bexp = bexp.replace('“', '"')
        bexp = bexp.replace('"', '')
        bexp = bexp.replace('`', "'")
        bexp = bexp.replace('′', "'")
        bexp = bexp.replace(' ', '')
        # ================================
            
        if bexp == "":
            mBox1 = QMessageBox.about(self, "Alert", "Please insert the expression")
        elif not bexp:
            bexp = 'a'
        else:
            bexp = bexp.replace(" ", "")
            #self.ProgressBar.setVisible(True)
            #self.ProgressBar.setValue(0)
            self.result.append("a")

            if not self._run_expression_pipeline(bexp, option, include_sbol=True):
                self.result.clear()
                return

            if not self._populate_truth_table(bexp):
                self.result.clear()
                return
        if len(self.result) > 0:
            self.CreateCircuitList()
            self.CreateXMLList()
            self._load_first_sbol_file()
            self.result.clear()

if __name__ == "__main__":
    app = QCoreApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    widget = MainPage()
    widget.show()
    sys.exit(app.exec_())
