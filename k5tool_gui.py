import sys
import subprocess
import logging
import threading
from queue import Queue
import os
import serial.tools.list_ports
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QProgressBar, QLabel, QLineEdit, QFileDialog,
    QTabWidget, QComboBox, QSizePolicy, QMenuBar, QMenu, QMessageBox, QRadioButton, QButtonGroup
)

from PySide6.QtCore import QProcess, Qt, QSettings, QByteArray, QTimer, QUrl
from PySide6.QtGui import QTextCursor, QAction, QDesktopServices

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

settings = QSettings('K5Tool', 'K5ToolGUI')

class K5ToolGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("K5Tool GUI")
        self.setFixedSize(700, 700)
        self.process = QProcess()
        self.restoreGeometry(settings.value("geometry", QByteArray()))

        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        settings_menu = menubar.addMenu("Настройки")
        theme_menu = QMenu("Тема", self)
        settings_menu.addMenu(theme_menu)
        light_act = QAction("Светлая", self, triggered=lambda: self.set_theme('light'))
        dark_act = QAction("Тёмная", self, triggered=lambda: self.set_theme('dark'))
        theme_menu.addAction(light_act)
        theme_menu.addAction(dark_act)
        path_act = QAction("Установить путь к k5tool", self, triggered=self.set_k5tool_path)
        settings_menu.addAction(path_act)

        menubar.addMenu("Help")
        menubar.addMenu("About")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Порт:"))
        self.port_combo = QComboBox()
        self.port_combo.setFixedWidth(150)
        self.port_combo.setEditable(True)
        self.port_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.port_combo.setInsertPolicy(QComboBox.NoInsert)
        self.port_combo.setCurrentText(settings.value('default_port', ''))
        port_layout.addWidget(self.port_combo)
        main_layout.addLayout(port_layout)

        self.refresh_ports()
        self.port_timer = QTimer(self)
        self.port_timer.timeout.connect(self.refresh_ports)
        self.port_timer.start(2000)

        cmd_layout = QVBoxLayout()
        btn_rows = [QVBoxLayout(), QVBoxLayout()]
        self.buttons = []
        cmds = [
            ("Проверка", "-hello", "Проверка соединения с радио"),
            ("Ребут", "-reboot", "Перезагрузка радио"),
            ("ADC", "-rdadc [output]", "Прочитать ADC и сохранить"),
            ("Прошивка", "-wrflash <file>", "Прошивка стандартного образа"),
            ("Прошка RAW", "-wrflashraw <file>", "RAW прошивка"),
            ("Распаковать", "-unpack <file> [output]", "Распаковка образа"),
            ("Упаковать", "-pack <file> [output]", "Упаковка образа"),
            ("Симуляция", "-simula", "Симуляция загрузчика"),
            ("Сниффер", "-sniffer", "Режим сниффера")
        ]
        for idx, (text, cmd, tip) in enumerate(cmds):
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.setFixedWidth(120)
            btn.clicked.connect(lambda _, c=cmd: self.prepare_command(c))
            btn_rows[idx % 2].addWidget(btn)
            self.buttons.append(btn)

        row_layout = QHBoxLayout()
        row_layout.addLayout(btn_rows[0])
        row_layout.addLayout(btn_rows[1])
        main_layout.addLayout(row_layout)

        eeprom_layout = QHBoxLayout()
        read_group = QButtonGroup(self)
        read_full = QRadioButton("Read Full EEPROM Dump")
        read_cal = QRadioButton("Read Calibration Dump")
        read_full.setChecked(True)
        read_group.addButton(read_full)
        read_group.addButton(read_cal)
        self.read_eeprom_button = QPushButton("Чтение EEPROM")
        self.read_eeprom_button.setFixedWidth(150)
        self.read_eeprom_button.clicked.connect(lambda: self.prepare_command("-rdee" if read_full.isChecked() else "-rdee 0x1e00 0x0200 [output]"))
        eeprom_layout.addWidget(read_full)
        eeprom_layout.addWidget(read_cal)
        eeprom_layout.addWidget(self.read_eeprom_button)
        main_layout.addLayout(eeprom_layout)

        write_layout = QHBoxLayout()
        write_group = QButtonGroup(self)
        write_full = QRadioButton("Write Full EEPROM Dump")
        write_cal = QRadioButton("Write Calibration Dump")
        write_full.setChecked(True)
        write_group.addButton(write_full)
        write_group.addButton(write_cal)
        self.write_eeprom_button = QPushButton("Запись EEPROM")
        self.write_eeprom_button.setFixedWidth(150)
        self.write_eeprom_button.clicked.connect(lambda: self.prepare_command("-wree <file>" if write_full.isChecked() else "-wree 0x1e00 0x0200"))
        write_layout.addWidget(write_full)
        write_layout.addWidget(write_cal)
        write_layout.addWidget(self.write_eeprom_button)
        main_layout.addLayout(write_layout)

        self.args_input = QLineEdit()
        self.args_input.setPlaceholderText("Аргументы командной строки")
        self.args_input.setFixedWidth(300)
        main_layout.addWidget(self.args_input)

        run_layout = QHBoxLayout()
        self.run_btn = QPushButton("▶ Старт")
        self.run_btn.clicked.connect(self.run_command)
        self.stop_btn = QPushButton("■ Стоп")
        self.stop_btn.clicked.connect(self.stop_command)
        self.stop_btn.setEnabled(False)
        run_layout.addWidget(self.run_btn)
        run_layout.addWidget(self.stop_btn)
        main_layout.addLayout(run_layout)

        self.log_view = QTextEdit(readOnly=True)
        self.log_view.setStyleSheet("QTextEdit { background-color: #fdfdfd; font-family: monospace; }")
        main_layout.addWidget(self.log_view)

        self.progress = QProgressBar()
        self.step_label = QLabel("...")
        self.status = QLabel("Готов")
        self.footer = QLabel()
        self.footer.setText(f"<a href='https://gitlab.com/qrp73/K5TOOL'>qrp73 GitLab</a>")
        self.footer.setOpenExternalLinks(True)
        self.footer.setStyleSheet("color: gray; font-size: 10pt;")
        self.footer.setAlignment(Qt.AlignLeft)
        bottom = QVBoxLayout()
        status_line = QHBoxLayout()
        status_line.addWidget(self.progress)
        status_line.addWidget(self.step_label)
        status_line.addWidget(self.status)
        bottom.addLayout(status_line)
        bottom.addWidget(self.footer)
        main_layout.addLayout(bottom)

        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stdout)  # STDERR отключено
        self.process.finished.connect(self.process_finished)

        self.set_theme(settings.value('theme', 'light'))

    def refresh_ports(self):
        current = self.port_combo.currentText()
        ports = serial.tools.list_ports.comports()
        port_names = sorted([port.device for port in ports])
        self.port_combo.clear()
        self.port_combo.addItems(port_names)
        if current in port_names:
            self.port_combo.setCurrentText(current)

    def set_k5tool_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Установить путь к k5tool")
        if path and os.access(path, os.X_OK):
            settings.setValue('k5tool_path', path)
            self.log(f"k5tool path set to {path}")
        else:
            QMessageBox.warning(self, "Ошибка", "Выбранный файл не является исполняемым")

    def set_theme(self, theme):
        if theme == 'dark':
            self.setStyleSheet("""
                QWidget { background: #2b2b2b; color: #f0f0f0; }
                QPushButton { background: #3c3c3c; border: 1px solid #555; padding: 5px; }
                QTextEdit, QLineEdit, QComboBox { background: #1e1e1e; color: #f0f0f0; }
            """)
        else:
            self.setStyleSheet("")
        settings.setValue('theme', theme)

    def prepare_command(self, cmd_template):
        if cmd_template == "-wrflashraw <file>":
            parts = cmd_template.replace("[version]", "").split()
        else:
            parts = cmd_template.split()
        filled = []
        for part in parts:
            if '<file>' in part or '[output]' in part:
                if '[output]' in part:
                    sel, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", filter="*.raw *.bin")
                else:
                    sel, _ = QFileDialog.getOpenFileName(self, "Выбрать файл", filter="*.raw *.bin")
                if not sel:
                    return
                filled.append(sel)
            else:
                filled.append(part)
        port = self.port_combo.currentText().strip()
        if port:
            filled.insert(0, port)
            filled.insert(0, "-port")
            settings.setValue('default_port', port)
        self.args_input.setText(' '.join(filled))

    def run_command(self):
        command = settings.value('k5tool_path', 'k5tool')
        if not command:
            QMessageBox.warning(self, "Ошибка", "Путь к k5tool не задан")
            return
        args = self.args_input.text().split()
        self.status.setText("Выполняется...")
        self.progress.setRange(0, 0)
        self.process.start(command, args)
        self.run_btn.setEnabled(False); self.stop_btn.setEnabled(True)

    def stop_command(self):
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.status.setText("Остановлено")
            self.progress.setRange(0, 100); self.progress.setValue(0)
            self.run_btn.setEnabled(True); self.stop_btn.setEnabled(False)

    def handle_stdout(self):
        text = self.process.readAllStandardOutput().data().decode()
        self.log(text)
        self.step_label.setText(text.strip().split('\n')[-1])
        for tok in text.split():
            if tok.endswith('%') and tok[:-1].isdigit():
                self.progress.setRange(0, 100); self.progress.setValue(int(tok[:-1]))

    def process_finished(self):
        self.status.setText("Завершено")
        self.progress.setRange(0, 100); self.progress.setValue(100)
        self.run_btn.setEnabled(True); self.stop_btn.setEnabled(False)

    def log(self, message):
        log_queue.put(message)
        timestamp = datetime.now().strftime("[%H:%M:%S]")

        highlight = {
            'Opening': 'blue',
            'Handshake': 'orange',
            'Firmware': 'green',
            'Error': 'red',
            'Done': 'darkgreen',
            'OK': 'darkcyan',
            'Reboot': 'purple',
            'Read': 'navy',
            'Write': 'maroon',
            '%': 'teal'
        }

        html = f"<b style='color:gray'>{timestamp}</b> " + message
        for word, color in highlight.items():
            html = html.replace(word, f"<span style='color:{color}; font-weight:bold'>{word}</span>")

        self.log_view.append(html)
        self.log_view.moveCursor(QTextCursor.End)

    def closeEvent(self, event):
        log_queue.put(None)
        settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = K5ToolGUI()
    window.show()
    sys.exit(app.exec())
