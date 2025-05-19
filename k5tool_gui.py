import sys
import subprocess
import logging
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QProgressBar, QLabel, QLineEdit, QFileDialog
)
from PySide6.QtCore import QProcess, Qt

# Configure logging
logging.basicConfig(
    filename='k5tool_gui.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class K5ToolGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("K5Tool GUI")
        self.resize(900, 600)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout
        main_layout = QHBoxLayout(central)

        # Command buttons panel
        cmd_panel = QWidget()
        cmd_layout = QVBoxLayout(cmd_panel)
        cmd_layout.setAlignment(Qt.AlignTop)

        # Define buttons for each command
        commands = [
            ("Check Connection", ["-hello"]),
            ("List Ports", ["-port"]),
            ("Set Port", ["-port", "<port>"]),
            ("Reboot Radio", ["-reboot"]),
            ("Read ADC", ["-rdadc", "[output]"]),
            ("Read EEPROM", ["-rdee", "[offset]", "[size]", "[output]"]),
            ("Write EEPROM", ["-wree", "[offset]", "<file>"]),
            ("Flash Firmware", ["-wrflash", "<file>"]),
            ("Flash Raw FW", ["-wrflashraw", "[version]", "<file>"]),
            ("Unpack Image", ["-unpack", "<file>", "[output]"]),
            ("Pack Image", ["-pack", "<version>", "<file>", "[output]"]),
            ("Simulator", ["-simula"]),
            ("Sniffer Mode", ["-sniffer"]),
            ("Parse Hex", ["-parse", "<data>"]),
            ("Parse Plain", ["-parse-plain", "<data>"])
        ]

        for label, args in commands:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, a=args: self.prepare_command(a))
            cmd_layout.addWidget(btn)

        # Right panel: args input, run/stop, output, progress
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Arguments input
        self.args_label = QLabel("Arguments:")
        self.args_input = QLineEdit()
        self.args_input.setPlaceholderText("Enter arguments separated by spaces or choose via buttons")

        # Run and Stop buttons
        btn_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Command")
        self.run_button.clicked.connect(self.run_command)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_command)
        self.stop_button.setEnabled(False)
        btn_layout.addWidget(self.run_button)
        btn_layout.addWidget(self.stop_button)

        # Output display
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        # Assemble right layout
        right_layout.addWidget(self.args_label)
        right_layout.addWidget(self.args_input)
        right_layout.addLayout(btn_layout)
        right_layout.addWidget(self.output)
        right_layout.addWidget(self.progress)

        main_layout.addWidget(cmd_panel)
        main_layout.addWidget(right_panel, stretch=1)

        # QProcess for async execution
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

    def prepare_command(self, args_template):
        args_filled = []
        for arg in args_template:
            if arg == "<file>":
                path, _ = QFileDialog.getOpenFileName(self, "Select File to Open")
                if not path:
                    return
                args_filled.append(path)
            elif arg == "[output]":
                path, _ = QFileDialog.getSaveFileName(self, "Select Output File")
                if not path:
                    return
                args_filled.append(path)
            else:
                args_filled.append(arg)
        self.args_input.setText(' '.join(args_filled))

    def run_command(self):
        args = self.args_input.text().split()
        full_cmd = ["k5tool"] + args
        logging.info(f"Running: {' '.join(full_cmd)}")

        self.output.clear()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.setValue(0)
        self.process.start(full_cmd[0], full_cmd[1:])
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_command(self):
        if self.process.state() == QProcess.Running:
            self.process.kill()
            logging.info("Process killed by user.")
            self.output.append("<b>Process stopped by user.</b>")
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.run_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode()
        self.output.append(data)
        logging.info(data.strip())
        for part in data.split():
            if part.endswith('%') and part[:-1].isdigit():
                self.progress.setRange(0, 100)
                self.progress.setValue(int(part[:-1]))

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode()
        self.output.append(f"<span style='color:red;'>{data}</span>")
        logging.error(data.strip())

    def process_finished(self):
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.output.append("<b>Done</b>")
        logging.info("Process finished.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = K5ToolGUI()
    window.show()
    sys.exit(app.exec())
