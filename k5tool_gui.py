import sys
import threading
import shutil
import json
from queue import Queue
import os
import serial.tools.list_ports
from datetime import datetime
import html

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QProgressBar, QLabel, QLineEdit, QFileDialog,
    QComboBox, QMenuBar, QMenu, QMessageBox, QRadioButton,
    QButtonGroup, QGroupBox, QCompleter, QDialog, QTextBrowser
)
from PySide6.QtCore import (
    QProcess, Qt, QSettings, QByteArray, QTimer, QStringListModel, QUrl
)
from PySide6.QtGui import QTextCursor, QDesktopServices, QKeySequence, QAction

VERSION = "1.0"

# ---------------------------
# Потокобезопасное логирование
# ---------------------------
log_queue = Queue()
def log_writer():
    while True:
        record = log_queue.get()
        if record is None:
            break
        try:
            with open(settings.value('logfile', 'k5tool_gui.log'), 'a', encoding='utf-8') as f:
                f.write(record + '\n')
        except Exception:
            pass

log_thread = threading.Thread(target=log_writer, daemon=True)
log_thread.start()

# ---------------------------
# Настройки приложения
# ---------------------------
settings = QSettings('K5Tool', 'K5ToolGUI')

# ---------------------------
# Основной класс GUI
# ---------------------------
class K5ToolGUI(QMainWindow):
    HISTORY_KEY = 'args_history'
    LANGUAGE_KEY = 'language'
    TIMEOUT_MS = 120000  # 2 минуты

    def __init__(self):
        super().__init__()
        self.translations = {
            'ru': {
                'window_title': "K5Tool GUI",
                'menu_settings': "Настройки",
                'menu_theme': "Тема",
                'action_light': "Светлая",
                'action_dark': "Тёмная",
                'action_set_path': "Установить путь к k5tool",
                'action_check_updates': "Проверить обновления",
                'menu_help': "Help",
                'action_help': "Справка",
                'menu_about': "About",
                'action_about': "О программе",
                'menu_language': "Язык",
                'action_lang_ru': "Русский",
                'action_lang_en': "English",
                'label_port': "Порт:",
                'group_commands': "Команды",
                'btn_check': "Проверка",
                'btn_reboot': "Ребут",
                'btn_adc': "ADC",
                'btn_flash': "Прошивка",
                'btn_flash_raw': "Прошка RAW",
                'btn_unpack': "Распаковать",
                'btn_pack': "Упаковать",
                'btn_simula': "Симуляция",
                'btn_sniffer': "Сниффер",
                'group_read_eeprom': "Чтение EEPROM",
                'rb_read_full': "Read Full EEPROM Dump",
                'rb_read_cal': "Read Calibration Dump",
                'btn_read_eeprom': "Чтение EEPROM",
                'group_write_eeprom': "Запись EEPROM",
                'rb_write_full': "Write Full EEPROM Dump",
                'rb_write_cal': "Write Calibration Dump",
                'btn_write_eeprom': "Запись EEPROM",
                'args_placeholder': "Аргументы командной строки",
                'btn_start': "▶ Старт",
                'btn_stop': "■ Стоп",
                'status_ready': "Готов",
                'status_running': "Выполняется...",
                'msg_no_tool': "Путь к k5tool не задан или бинарник не найден",
                'msg_no_args': "Аргументы не заданы",
                'msg_no_port': "Порт не выбран",
                'dlg_timeout': "Время выполнения команды превысило лимит",
                'dlg_error_code': "Команда завершилась с кодом {code}",
                'help_text': """
<h3>Команды k5tool:</h3>
<ul>
  <li><b>-hello</b> — проверка соединения с радио</li>
  <li><b>-reboot</b> — перезагрузка радио</li>
  <li><b>-rdadc [output]</b> — чтение ADC и сохранение</li>
  <li><b>-wrflash &lt;file&gt;</b> — прошивка стандартного образа</li>
  <li><b>-wrflashraw &lt;file&gt;</b> — RAW прошивка без версии</li>
  <li><b>-unpack &lt;file&gt; [output]</b> — распаковка образа</li>
  <li><b>-pack &lt;file&gt; [output]</b> — упаковка образа</li>
  <li><b>-simula</b> — симуляция загрузчика</li>
  <li><b>-sniffer</b> — режим сниффера</li>
  <li><b>-rdee [offset] [size] [output]</b> — чтение EEPROM</li>
  <li><b>-wree [offset] [size] [file]</b> — запись EEPROM</li>
</ul>
""",
                'about_text': f"K5Tool GUI\nВерсия {VERSION}\n\nGUI для запуска k5tool с цветным логированием и историей аргументов.",
                'footer_text': "iwizard7 GitLab — v" + VERSION,
            },
            'en': {
                'window_title': "K5Tool GUI",
                'menu_settings': "Settings",
                'menu_theme': "Theme",
                'action_light': "Light",
                'action_dark': "Dark",
                'action_set_path': "Set k5tool Path",
                'action_check_updates': "Check Updates",
                'menu_help': "Help",
                'action_help': "Help",
                'menu_about': "About",
                'action_about': "About",
                'menu_language': "Language",
                'action_lang_ru': "Русский",
                'action_lang_en': "English",
                'label_port': "Port:",
                'group_commands': "Commands",
                'btn_check': "Check",
                'btn_reboot': "Reboot",
                'btn_adc': "ADC",
                'btn_flash': "Flash",
                'btn_flash_raw': "Flash RAW",
                'btn_unpack': "Unpack",
                'btn_pack': "Pack",
                'btn_simula': "Simulate",
                'btn_sniffer': "Sniffer",
                'group_read_eeprom': "Read EEPROM",
                'rb_read_full': "Read Full EEPROM Dump",
                'rb_read_cal': "Read Calibration Dump",
                'btn_read_eeprom': "Read EEPROM",
                'group_write_eeprom': "Write EEPROM",
                'rb_write_full': "Write Full EEPROM Dump",
                'rb_write_cal': "Write Calibration Dump",
                'btn_write_eeprom': "Write EEPROM",
                'args_placeholder': "Command-line arguments",
                'btn_start': "▶ Start",
                'btn_stop': "■ Stop",
                'status_ready': "Ready",
                'status_running': "Running...",
                'msg_no_tool': "k5tool path not set or binary not found",
                'msg_no_args': "No arguments specified",
                'msg_no_port': "Port not selected",
                'dlg_timeout': "Command execution time exceeded limit",
                'dlg_error_code': "Command exited with code {code}",
                'help_text': """
<h3>k5tool commands:</h3>
<ul>
  <li><b>-hello</b> — check connection to radio</li>
  <li><b>-reboot</b> — reboot radio</li>
  <li><b>-rdadc [output]</b> — read ADC and save</li>
  <li><b>-wrflash &lt;file&gt;</b> — flash standard image</li>
  <li><b>-wrflashraw &lt;file&gt;</b> — RAW flash without version</li>
  <li><b>-unpack &lt;file&gt; [output]</b> — unpack image</li>
  <li><b>-pack &lt;file&gt; [output]</b> — pack image</li>
  <li><b>-simula</b> — simulate bootloader</li>
  <li><b>-sniffer</b> — sniffer mode</li>
  <li><b>-rdee [offset] [size] [output]</b> — read EEPROM</li>
  <li><b>-wree [offset] [size] [file]</b> — write EEPROM</li>
</ul>
""",
                'about_text': f"K5Tool GUI\nVersion {VERSION}\n\nGUI to run k5tool with colored logging and argument history.",
                'footer_text': "iwizard7 GitLab — v" + VERSION,
            }
        }
        self.language = settings.value(self.LANGUAGE_KEY, 'ru')
        self.trans = self.translations[self.language]

        self.setWindowTitle(self.trans['window_title'])
        self.setFixedSize(700, 700)
        self.process = QProcess()
        self.restoreGeometry(settings.value("geometry", QByteArray()))

        self._setup_menu()
        self._setup_ui()
        self._connect_signals()
        self._load_history()

        self.set_theme(settings.value('theme', 'light'))

    # ---------------------------
    # Меню и темы
    # ---------------------------
    def _setup_menu(self):
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        # Настройки
        settings_menu = menubar.addMenu(self.trans['menu_settings'])
        theme_menu = QMenu(self.trans['menu_theme'], self)
        settings_menu.addMenu(theme_menu)
        light_act = QAction(self.trans['action_light'], self, triggered=lambda: self._change_theme('light'))
        dark_act = QAction(self.trans['action_dark'], self, triggered=lambda: self._change_theme('dark'))
        theme_menu.addAction(light_act)
        theme_menu.addAction(dark_act)
        path_act = QAction(self.trans['action_set_path'], self, triggered=self.set_k5tool_path)
        settings_menu.addAction(path_act)
        check_updates = QAction(self.trans['action_check_updates'], self, triggered=self.check_updates)
        settings_menu.addAction(check_updates)

        # Help
        help_menu = menubar.addMenu(self.trans['menu_help'])
        help_act = QAction(self.trans['action_help'], self, triggered=self.show_help)
        help_menu.addAction(help_act)

        # About
        about_menu = menubar.addMenu(self.trans['menu_about'])
        about_act = QAction(self.trans['action_about'], self, triggered=self.show_about)
        about_menu.addAction(about_act)

        # Language
        lang_menu = menubar.addMenu(self.trans['menu_language'])
        ru_act = QAction(self.trans['action_lang_ru'], self, triggered=lambda: self._change_language('ru'))
        en_act = QAction(self.trans['action_lang_en'], self, triggered=lambda: self._change_language('en'))
        lang_menu.addAction(ru_act)
        lang_menu.addAction(en_act)

    # ---------------------------
    # Создание виджетов
    # ---------------------------
    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Порт и LED-иконка
        port_layout = QHBoxLayout()
        self.port_label = QLabel(self.trans['label_port'])
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.setFixedWidth(200)
        self.led = QLabel()
        self.led.setFixedSize(12, 12)
        self.led.setStyleSheet("background-color: red; border-radius: 6px;")
        port_layout.addWidget(self.port_label)
        port_layout.addWidget(self.port_combo)
        port_layout.addWidget(self.led)
        port_layout.addStretch()
        main_layout.addLayout(port_layout)

        self._refresh_ports()
        self.port_timer = QTimer(self)
        self.port_timer.timeout.connect(self._refresh_ports)
        self.port_timer.start(2000)

        # Команды
        cmds_group = QGroupBox(self.trans['group_commands'])
        cmds_layout = QHBoxLayout(cmds_group)
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()
        self.buttons = []
        cmds = [
            (self.trans['btn_check'], "-hello", "Check connection", 'Ctrl+H'),
            (self.trans['btn_reboot'], "-reboot", "Reboot radio", 'Ctrl+R'),
            (self.trans['btn_adc'], "-rdadc [output]", "Read ADC and save", 'Ctrl+A'),
            (self.trans['btn_flash'], "-wrflash <file>", "Flash standard image", 'Ctrl+P'),
            (self.trans['btn_flash_raw'], "-wrflashraw <file>", "RAW flash without version", 'Ctrl+W'),
            (self.trans['btn_unpack'], "-unpack <file> [output]", "Unpack image", None),
            (self.trans['btn_pack'], "-pack <file> [output]", "Pack image", None),
            (self.trans['btn_simula'], "-simula", "Simulate bootloader", None),
            (self.trans['btn_sniffer'], "-sniffer", "Sniffer mode", None)
        ]
        for idx, (text, cmd, tip, shortcut) in enumerate(cmds):
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.setFixedWidth(110)
            if shortcut:
                btn.setShortcut(QKeySequence(shortcut))
            btn.clicked.connect(lambda _, c=cmd: self.prepare_command(c))
            (left_col if idx % 2 == 0 else right_col).addWidget(btn)
            self.buttons.append(btn)
        cmds_layout.addLayout(left_col)
        cmds_layout.addLayout(right_col)
        main_layout.addWidget(cmds_group)

        # Чтение EEPROM
        read_group = QGroupBox(self.trans['group_read_eeprom'])
        read_layout = QHBoxLayout(read_group)
        read_buttons = QButtonGroup(self)
        self.read_full_rb = QRadioButton(self.trans['rb_read_full'])
        self.read_cal_rb = QRadioButton(self.trans['rb_read_cal'])
        self.read_full_rb.setChecked(True)
        read_buttons.addButton(self.read_full_rb)
        read_buttons.addButton(self.read_cal_rb)
        self.read_eeprom_button = QPushButton(self.trans['btn_read_eeprom'])
        self.read_eeprom_button.setFixedWidth(150)
        read_template_full = "-rdee [output]"
        read_template_cal = "-rdee 0x1e00 0x0200 [output]"
        self.read_eeprom_button.clicked.connect(
            lambda: self.prepare_command(read_template_full if self.read_full_rb.isChecked() else read_template_cal)
        )
        read_layout.addWidget(self.read_full_rb)
        read_layout.addWidget(self.read_cal_rb)
        read_layout.addWidget(self.read_eeprom_button)
        main_layout.addWidget(read_group)

        # Запись EEPROM
        write_group = QGroupBox(self.trans['group_write_eeprom'])
        write_layout = QHBoxLayout(write_group)
        wg = QButtonGroup(self)
        self.write_full_rb = QRadioButton(self.trans['rb_write_full'])
        self.write_cal_rb = QRadioButton(self.trans['rb_write_cal'])
        self.write_full_rb.setChecked(True)
        wg.addButton(self.write_full_rb)
        wg.addButton(self.write_cal_rb)
        self.write_eeprom_button = QPushButton(self.trans['btn_write_eeprom'])
        self.write_eeprom_button.setFixedWidth(150)
        self.write_eeprom_button.clicked.connect(
            lambda: self.prepare_command("-wree <file>" if self.write_full_rb.isChecked() else "-wree 0x1e00 0x0200")
        )
        write_layout.addWidget(self.write_full_rb)
        write_layout.addWidget(self.write_cal_rb)
        write_layout.addWidget(self.write_eeprom_button)
        main_layout.addWidget(write_group)

        # Аргументы и история автозаполнения
        self.args_input = QLineEdit()
        self.args_input.setPlaceholderText(self.trans['args_placeholder'])
        self.args_input.setFixedWidth(300)
        main_layout.addWidget(self.args_input)

        self.history_model = QStringListModel()
        self.completer = QCompleter(self.history_model, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.args_input.setCompleter(self.completer)

        # Запуск/Остановка
        run_layout = QHBoxLayout()
        self.run_btn = QPushButton(self.trans['btn_start'])
        self.run_btn.setShortcut(QKeySequence("Ctrl+S"))
        self.run_btn.clicked.connect(self.run_command)
        self.stop_btn = QPushButton(self.trans['btn_stop'])
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_command)
        run_layout.addWidget(self.run_btn)
        run_layout.addWidget(self.stop_btn)
        run_layout.addStretch()
        main_layout.addLayout(run_layout)

        # Лог (без кнопки очистки)
        self.log_view = QTextEdit(readOnly=True)
        self.log_view.setStyleSheet(
            "QTextEdit { background-color: #fdfdfd; font-family: Menlo; font-size: 10pt; }"
        )
        main_layout.addWidget(self.log_view)

        # Статус
        status_layout = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setFixedHeight(16)
        self.step_label = QLabel("...")
        self.status = QLabel(self.trans['status_ready'])
        status_layout.addWidget(self.progress)
        status_layout.addWidget(self.step_label)
        status_layout.addWidget(self.status)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)

        # Ссылка на репо и версия
        self.footer = QLabel(f"<a href='https://github.com/iwizard7/k5toolGUI'>{self.trans['footer_text']}</a>")
        self.footer.setOpenExternalLinks(True)
        self.footer.setStyleSheet("color: gray; font-size: 10pt;")
        self.footer.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(self.footer)

    # ---------------------------
    # Сигналы и слоты
    # ---------------------------
    def _connect_signals(self):
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stdout)
        self.process.finished.connect(self.process_finished)
        self.port_combo.currentTextChanged.connect(self._update_led)

    # ---------------------------
    # Загрузка истории из настроек
    # ---------------------------
    def _load_history(self):
        hist = settings.value(self.HISTORY_KEY, [])
        if isinstance(hist, list):
            self.history = hist
        else:
            try:
                self.history = json.loads(hist)
            except Exception:
                self.history = []
        self.history_model.setStringList(self.history)

    def _save_to_history(self, args_str):
        if not args_str.strip():
            return
        if args_str not in self.history:
            self.history.insert(0, args_str)
            if len(self.history) > 20:
                self.history.pop()
            settings.setValue(self.HISTORY_KEY, json.dumps(self.history))
            self.history_model.setStringList(self.history)

    # ---------------------------
    # Обновление списка портов и LED
    # ---------------------------
    def _refresh_ports(self):
        current = self.port_combo.currentText()
        ports = serial.tools.list_ports.comports()
        port_names = sorted([port.device for port in ports])
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        self.port_combo.addItems(port_names)
        if current in port_names:
            self.port_combo.setCurrentText(current)
        self.port_combo.blockSignals(False)
        self._update_led()

    def _update_led(self):
        port = self.port_combo.currentText().strip()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if port and port in ports:
            self.led.setStyleSheet("background-color: green; border-radius: 6px;")
        else:
            self.led.setStyleSheet("background-color: red; border-radius: 6px;")

    # ---------------------------
    # Установка пути к k5tool
    # ---------------------------
    def set_k5tool_path(self):
        path, _ = QFileDialog.getOpenFileName(self, self.trans['action_set_path'])
        if path:
            if not os.access(path, os.X_OK):
                QMessageBox.warning(self, self.trans['action_set_path'], "Файл не является исполняемым")
                return
            settings.setValue('k5tool_path', path)
            self.log(f"k5tool path set to {path}")

    # ---------------------------
    # Смена темы
    # ---------------------------
    def _change_theme(self, theme):
        self.set_theme(theme)

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

    # ---------------------------
    # Смена языка
    # ---------------------------
    def _change_language(self, lang):
        if lang not in self.translations:
            return
        settings.setValue(self.LANGUAGE_KEY, lang)
        QMessageBox.information(self, self.trans['menu_language'],
                                "Перезапустите приложение для применения языка.")

    # ---------------------------
    # Подготовка аргументов для запуска
    # ---------------------------
    def prepare_command(self, cmd_template):
        parts = cmd_template.replace("[version]", "").split()
        filled = []
        try:
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
            if not port:
                QMessageBox.warning(self, self.trans['menu_settings'], self.trans['msg_no_port'])
                return
            filled.insert(0, port)
            filled.insert(0, "-port")
            settings.setValue('default_port', port)
            args_str = ' '.join(filled)
            self.args_input.setText(args_str)
        except Exception as e:
            QMessageBox.critical(self, self.trans['menu_settings'], f"Неверные данные: {e}")

    # ---------------------------
    # Запуск процесса
    # ---------------------------
    def run_command(self):
        command = settings.value('k5tool_path', shutil.which('k5tool') or '')
        if not command or not os.path.isfile(command):
            QMessageBox.warning(self, self.trans['menu_settings'], self.trans['msg_no_tool'])
            return
        args = self.args_input.text().split()
        if not args:
            QMessageBox.warning(self, self.trans['menu_settings'], self.trans['msg_no_args'])
            return

        self._set_ui_enabled(False)
        self.status.setText(self.trans['status_running'])
        self._set_progress_color("blue")
        self.progress.setRange(0, 0)

        try:
            self.process.start(command, args)
            self.kill_timer = QTimer(self)
            self.kill_timer.setSingleShot(True)
            self.kill_timer.timeout.connect(self._on_timeout)
            self.kill_timer.start(self.TIMEOUT_MS)
        except Exception as e:
            QMessageBox.critical(self, self.trans['menu_settings'], str(e))
            self._set_ui_enabled(True)

        self._save_to_history(self.args_input.text())

    def _on_timeout(self):
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.log("Перезапуск: превышен таймаут исполнения")
            QMessageBox.warning(self, self.trans['btn_start'], self.trans['dlg_timeout'])
            self._set_ui_enabled(True)
            self._set_progress_color("red")

    # ---------------------------
    # Остановка процесса
    # ---------------------------
    def stop_command(self):
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.status.setText(self.trans['status_ready'])
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self._set_ui_enabled(True)
            self._set_progress_color("red")

    # ---------------------------
    # Обработчик вывода
    # ---------------------------
    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode()
        self.log(data)
        self.step_label.setText(data.strip().split('\n')[-1])

        # Обновление прогресса по процентам
        for tok in data.split():
            if tok.endswith('%') and tok[:-1].isdigit():
                self.progress.setRange(0, 100)
                self.progress.setValue(int(tok[:-1]))
                self._set_progress_color("green")

    def process_finished(self):
        if hasattr(self, 'kill_timer') and self.kill_timer.isActive():
            self.kill_timer.stop()
        exit_code = self.process.exitCode()
        if exit_code != 0:
            QMessageBox.critical(self, self.trans['menu_settings'], self.trans['dlg_error_code'].format(code=exit_code))
            self._set_progress_color("red")
        else:
            self._set_progress_color("green")
        self.status.setText(self.trans['status_ready'])
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self._set_ui_enabled(True)

    # ---------------------------
    # Логирование с подсветкой
    # ---------------------------
    def log(self, message):
        log_queue.put(message)
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        highlight = {
            'Opening': 'blue', 'Handshake': 'orange', 'Firmware': 'green',
            'Error': 'red', 'Done': 'darkgreen', 'OK': 'darkcyan',
            'Reboot': 'purple', 'Read': 'navy', 'Write': 'maroon', '%': 'teal'
        }
        safe_msg = html.escape(message)
        html_line = f"<b style='color:gray'>{timestamp}</b> " + safe_msg
        for word, color in highlight.items():
            html_line = html_line.replace(word, f"<span style='color:{color}; font-weight:bold'>{word}</span>")
        self.log_view.append(html_line)
        self.log_view.moveCursor(QTextCursor.End)

    # ---------------------------
    # Изменение цвета прогресса
    # ---------------------------
    def _set_progress_color(self, color_name):
        self.progress.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color_name}; }}")

    # ---------------------------
    # Разрешаем/запрещаем UI
    # ---------------------------
    def _set_ui_enabled(self, enabled):
        for btn in self.buttons + [self.read_eeprom_button, self.write_eeprom_button]:
            btn.setEnabled(enabled)
        self.run_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(not enabled)
        self.port_combo.setEnabled(enabled)
        self.args_input.setEnabled(enabled)

    # ---------------------------
    # Проверка обновлений (открывает GitHub)
    # ---------------------------
    def check_updates(self):
        QDesktopServices.openUrl(QUrl("https://github.com/iwizard7/k5toolGUI/releases"))

    # ---------------------------
    # Справка и About
    # ---------------------------
    def show_help(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(self.trans['action_help'])
        layout = QVBoxLayout(dlg)
        browser = QTextBrowser()
        browser.setHtml(self.trans['help_text'])
        layout.addWidget(browser)
        dlg.setFixedSize(400, 300)
        dlg.exec()

    def show_about(self):
        QMessageBox.information(self, self.trans['action_about'], self.trans['about_text'])

    # ---------------------------
    # Сохранение геометрии при закрытии
    # ---------------------------
    def closeEvent(self, event):
        log_queue.put(None)
        settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = K5ToolGUI()
    window.show()
    sys.exit(app.exec())