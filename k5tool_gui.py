import sys
import subprocess
import logging
import threading
from queue import Queue
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QProgressBar, QLabel, QLineEdit, QFileDialog,
    QInputDialog, QTabWidget, QListWidget, QSplitter, QMenu, QMenuBar
)
from PySide6.QtGui import QTextCursor, QColor, QAction
from PySide6.QtCore import QProcess, Qt, QSettings

# Async logger thread
log_queue = Queue()
def log_writer():
    while True:
        record = log_queue.get()
        if record is None:
            break
        with open(settings.value('logfile', 'k5tool_gui.log'), 'a', encoding='utf-8') as f:
            f.write(record + '\n')
log_thread = threading.Thread(target=log_writer, daemon=True)
log_thread.start()

# Load settings
settings = QSettings('K5Tool', 'K5ToolGUI')

class K5ToolGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("K5Tool GUI")
        self.resize(1000, 700)
        self.process = QProcess()

        # Menubar & Themes
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        settings_menu = menubar.addMenu("Settings")
        theme_menu = QMenu("Theme", self)
        settings_menu.addMenu(theme_menu)
        light_act = QAction("Light", self, triggered=lambda: self.set_theme('light'))
        dark_act = QAction("Dark", self, triggered=lambda: self.set_theme('dark'))
        theme_menu.addAction(light_act)
        theme_menu.addAction(dark_act)
        path_act = QAction("Set k5tool Path", self, triggered=self.set_k5tool_path)
        settings_menu.addAction(path_act)

        # Central splitter for history and main
        splitter = QSplitter(Qt.Horizontal)
        self.history = QListWidget()
        self.history.setToolTip("История ранее выполненных команд")
        self.history.itemClicked.connect(self.load_history)
        splitter.addWidget(self.history)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Buttons with tooltips
        cmd_layout = QHBoxLayout()
        self.buttons = []
        cmds = [
            ("Check Connection", "-hello", "Проверка соединения с радио"),
            ("List Ports", "-port", "Список доступных COM-портов"),
            ("Reboot Radio", "-reboot", "Перезагрузка радио"),
            ("Read ADC", "-rdadc [output]", "Прочитать ADC и сохранить в файл"),
            ("Read EEPROM", "-rdee [offset] [size] [output]", "Чтение EEPROM с опциями"),
            ("Write EEPROM", "-wree [offset] <file>", "Запись EEPROM из файла"),
            ("Flash Firmware", "-wrflash <file>", "Прошивка стандартного образа"),
            ("Flash Raw FW", "-wrflashraw [version] <file>", "Прошивка RAW образа"),
            ("Unpack Image", "-unpack <file> [output]", "Распаковка образа"),
            ("Pack Image", "-pack <version> <file> [output]", "Упаковка образа"),
            ("Simulator", "-simula", "Симуляция загрузчика"),
            ("Sniffer Mode", "-sniffer", "Режим сниффера"),
            ("Parse Hex", "-parse <data>", "Парсинг hex-пакета"),
            ("Parse Plain", "-parse-plain <data>", "Парсинг plain-пакета")
        ]
        for text, cmd, tip in cmds:
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda _, c=cmd: self.prepare_command(c))
            cmd_layout.addWidget(btn)
            self.buttons.append(btn)
        main_layout.addLayout(cmd_layout)

        # Args input
        self.args_input = QLineEdit()
        self.args_input.setPlaceholderText("Аргументы командной строки")
        main_layout.addWidget(self.args_input)

        # Run/Stop layout
        run_layout = QHBoxLayout()
        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self.run_command)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_command)
        self.stop_btn.setEnabled(False)
        run_layout.addWidget(self.run_btn)
        run_layout.addWidget(self.stop_btn)
        main_layout.addLayout(run_layout)

        # Tabs for stdout/stderr/log
        tabs = QTabWidget()
        self.stdout_view = QTextEdit(readOnly=True)
        self.stderr_view = QTextEdit(readOnly=True)
        self.log_view = QTextEdit(readOnly=True)
        tabs.addTab(self.stdout_view, "STDOUT")
        tabs.addTab(self.stderr_view, "STDERR")
        tabs.addTab(self.log_view, "Log File")
        main_layout.addWidget(tabs)

        # Progress & status
        self.progress = QProgressBar()
        self.status = QLabel("Ready")
        bottom = QHBoxLayout()
        bottom.addWidget(self.progress)
        bottom.addWidget(self.status)
        main_layout.addLayout(bottom)

        splitter.addWidget(main_widget)
        self.setCentralWidget(splitter)

        # QProcess signals
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        # apply stored theme
        self.set_theme(settings.value('theme', 'light'))

    def set_k5tool_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Set k5tool Path")
        if path:
            settings.setValue('k5tool_path', path)
            self.log(f"k5tool path set to {path}")

    def set_theme(self, theme):
        if theme == 'dark':
            self.setStyleSheet("QWidget { background: #2b2b2b; color: #f0f0f0; }")
        else:
            self.setStyleSheet("")
        settings.setValue('theme', theme)

    def prepare_command(self, cmd_template):
        parts = cmd_template.split()
        filled = []
        for part in parts:
            if '<file>' in part or '[output]' in part:
                sel = QFileDialog.getSaveFileName(self, "Select File")[0] if '[output]' in part else QFileDialog.getOpenFileName(self, "Select File")[0]
                if not sel:
                    return
                filled.append(sel)
            else:
                filled.append(part)
        self.args_input.setText(' '.join(filled))

    def run_command(self):
        command = settings.value('k5tool_path', 'k5tool')
        args = self.args_input.text().split()
        self.history.addItem(command + ' ' + ' '.join(args))
        self.status.setText("Running...")
        self.progress.setRange(0, 0)
        self.stdout_view.clear(); self.stderr_view.clear()
        self.process.start(command, args)
        self.run_btn.setEnabled(False); self.stop_btn.setEnabled(True)

    def stop_command(self):
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.status.setText("Stopped")
            self.progress.setRange(0, 100); self.progress.setValue(0)
            self.run_btn.setEnabled(True); self.stop_btn.setEnabled(False)

    def handle_stdout(self):
        text = self.process.readAllStandardOutput().data().decode()
        self.stdout_view.moveCursor(QTextCursor.End)
        self.stdout_view.insertHtml(f"<span>{text}</span>")
        self.log(text)
        for tok in text.split():
            if tok.endswith('%') and tok[:-1].isdigit():
                self.progress.setRange(0, 100); self.progress.setValue(int(tok[:-1]))

    def handle_stderr(self):
        text = self.process.readAllStandardError().data().decode()
        self.stderr_view.moveCursor(QTextCursor.End)
        self.stderr_view.insertHtml(f"<span style='color:red;'>{text}</span>")
        self.log(text)

    def process_finished(self):
        self.status.setText("Done")
        self.progress.setRange(0, 100); self.progress.setValue(100)
        self.run_btn.setEnabled(True); self.stop_btn.setEnabled(False)

    def load_history(self, item):
        self.args_input.setText(item.text().split(' ', 1)[1])

    def log(self, message):
        log_queue.put(message)
        self.log_view.append(message)

    def closeEvent(self, event):
        log_queue.put(None)
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = K5ToolGUI()
    window.show()
    sys.exit(app.exec())
