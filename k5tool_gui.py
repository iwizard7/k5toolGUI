import sys
import subprocess
import logging
import threading
from queue import Queue
import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QProgressBar, QLabel, QLineEdit, QFileDialog,
    QInputDialog, QTabWidget, QListWidget, QSplitter, QMenu, QMenuBar,
    QMessageBox, QComboBox, QSizePolicy
)

from PySide6.QtCore import QProcess, Qt, QSettings, QByteArray
from PySide6.QtGui import QTextCursor, QColor, QAction, QKeySequence

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

        self.restoreGeometry(settings.value("geometry", QByteArray()))

        # Меню и тема
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

        # Основной сплиттер
        splitter = QSplitter(Qt.Horizontal)
        self.history = QListWidget()
        self.history.setToolTip("История ранее выполненных команд")
        self.history.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.history.setMinimumWidth(400)
        self.history.itemClicked.connect(self.load_history)
        splitter.addWidget(self.history)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Порт
        port_layout = QHBoxLayout()
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("Укажите порт (например, COM3 или /dev/ttyUSB0)")
        self.port_input.setText(settings.value('default_port', ''))
        port_layout.addWidget(QLabel("Порт:"))
        port_layout.addWidget(self.port_input)
        main_layout.addLayout(port_layout)

        # Кнопки
        cmd_layout = QHBoxLayout()
        self.buttons = []
        cmds = [
            ("Проверка", "-hello", "Проверка соединения с радио"),
            ("Порты", "-port", "Список доступных COM-портов"),
            ("Ребут", "-reboot", "Перезагрузка радио"),
            ("ADC", "-rdadc [output]", "Прочитать ADC и сохранить"),
            ("Чтение EEPROM", "-rdee [offset] [size] [output]", "Чтение EEPROM"),
            ("Запись EEPROM", "-wree [offset] <file>", "Запись EEPROM из файла"),
            ("Прошивка", "-wrflash <file>", "Прошивка стандартного образа"),
            ("RAW FW", "-wrflashraw [version] <file>", "RAW прошивка"),
            ("Распаковать", "-unpack <file> [output]", "Распаковка образа"),
            ("Упаковать", "-pack <version> <file> [output]", "Упаковка образа"),
            ("Симуляция", "-simula", "Симуляция загрузчика"),
            ("Сниффер", "-sniffer", "Режим сниффера"),
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

        # Комбобокс истории + строка ввода
        self.args_input = QLineEdit()
        self.args_input.setPlaceholderText("Аргументы командной строки")
        self.history_box = QComboBox()
        self.history_box.setEditable(True)
        self.history_box.setInsertPolicy(QComboBox.NoInsert)
        self.history_box.activated.connect(lambda idx: self.args_input.setText(self.history_box.itemText(idx)))

        args_layout = QHBoxLayout()
        args_layout.addWidget(self.args_input)
        args_layout.addWidget(self.history_box)
        main_layout.addLayout(args_layout)

        # Run / Stop
        run_layout = QHBoxLayout()
        self.run_btn = QPushButton("▶ Старт (Ctrl+R / F5)")
        self.run_btn.clicked.connect(self.run_command)
        self.run_btn.setShortcut(QKeySequence("Ctrl+R"))
        self.run_btn.setShortcut(QKeySequence(Qt.Key_F5))
        self.stop_btn = QPushButton("■ Стоп (Ctrl+S / Esc)")
        self.stop_btn.clicked.connect(self.stop_command)
        self.stop_btn.setShortcut(QKeySequence("Ctrl+S"))
        self.stop_btn.setShortcut(QKeySequence(Qt.Key_Escape))
        self.stop_btn.setEnabled(False)
        run_layout.addWidget(self.run_btn)
        run_layout.addWidget(self.stop_btn)
        main_layout.addLayout(run_layout)

        # Tabs
        tabs = QTabWidget()
        self.stdout_view = QTextEdit(readOnly=True)
        self.stderr_view = QTextEdit(readOnly=True)
        self.log_view = QTextEdit(readOnly=True)
        tabs.addTab(self.stdout_view, "STDOUT")
        tabs.addTab(self.stderr_view, "STDERR")
        tabs.addTab(self.log_view, "Лог")
        main_layout.addWidget(tabs)

        # Статус и нижняя панель
        self.progress = QProgressBar()
        self.step_label = QLabel("...")
        self.status = QLabel("Готов")
        self.footer = QLabel("iwizard7 | Версия 0.2 | https://github.com/iwizard7/k5toolGUI")
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

        splitter.addWidget(main_widget)
        self.setCentralWidget(splitter)
        self.splitter = splitter
        self.splitter.restoreState(settings.value("splitter_state", QByteArray()))

        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        self.set_theme(settings.value('theme', 'light'))

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
        parts = cmd_template.split()
        filled = []
        for part in parts:
            if '<file>' in part or '[output]' in part:
                sel = QFileDialog.getSaveFileName(self, "Выберите файл")[0] if '[output]' in part else QFileDialog.getOpenFileName(self, "Выберите файл")[0]
                if not sel:
                    return
                filled.append(sel)
            else:
                filled.append(part)
        port = self.port_input.text().strip()
        if port:
            filled.insert(0, f"-port={port}")
            settings.setValue('default_port', port)
        self.args_input.setText(' '.join(filled))

    def run_command(self):
        command = settings.value('k5tool_path', 'k5tool')
        if not command:
            QMessageBox.warning(self, "Ошибка", "Путь к k5tool не задан")
            return

        args = self.args_input.text().split()
        port = self.port_input.text().strip()
        if port and f"-port={port}" not in args:
            args.insert(0, f"-port={port}")
            settings.setValue('default_port', port)

        cmdline = command + ' ' + ' '.join(args)
        self.history.addItem(cmdline)
        if self.args_input.text() not in [self.history_box.itemText(i) for i in range(self.history_box.count())]:
            self.history_box.addItem(self.args_input.text())
        self.status.setText("Выполняется...")
        self.progress.setRange(0, 0)
        self.stdout_view.clear(); self.stderr_view.clear()
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
        self.stdout_view.moveCursor(QTextCursor.End)
        self.stdout_view.insertHtml(f"<span>{text}</span>")
        self.log(text)
        self.step_label.setText(text.strip().split('\n')[-1])
        for tok in text.split():
            if tok.endswith('%') and tok[:-1].isdigit():
                self.progress.setRange(0, 100); self.progress.setValue(int(tok[:-1]))

    def handle_stderr(self):
        text = self.process.readAllStandardError().data().decode()
        self.stderr_view.moveCursor(QTextCursor.End)
        self.stderr_view.insertHtml(f"<span style='color:red;'>" + text + "</span>")
        self.log(text)

    def process_finished(self):
        self.status.setText("Завершено")
        self.progress.setRange(0, 100); self.progress.setValue(100)
        self.run_btn.setEnabled(True); self.stop_btn.setEnabled(False)

    def load_history(self, item):
        self.args_input.setText(item.text().split(' ', 1)[1])

    def log(self, message):
        log_queue.put(message)
        self.log_view.append(message)

    def closeEvent(self, event):
        log_queue.put(None)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("splitter_state", self.splitter.saveState())
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = K5ToolGUI()
    window.show()
    sys.exit(app.exec())
