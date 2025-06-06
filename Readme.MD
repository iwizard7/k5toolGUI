# 🛠️ k5toolUI — Графическая оболочка для `k5tool`

![PySide6](https://img.shields.io/badge/built%20with-PySide6-6D9BC3.svg?style=for-the-badge)
![Version](https://img.shields.io/badge/version-1.1-blue.svg?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge)

Графический интерфейс на Python для работы с CLI-утилитой [`k5tool`](https://github.com/dmitrijsibanov/k5tool), обеспечивающий удобную визуальную работу с EEPROM и другими функциями микроконтроллеров или устройств.

---

## 🚀 Возможности

- 📥 **Чтение EEPROM** с выбором имени и места сохранения
- 📤 **Запись EEPROM** с указанием пути к hex-файлу
- ⚙️ **Запуск любой команды** `k5tool` с аргументами
- 📜 **Лог командной строки** с автоматическим логированием
- 🔄 **Автообновление списка COM-портов**
- ✅ **LED-индикатор** состояния выбранного порта
- 📊 **Прогресс-бар** для визуализации выполнения команд
- 🗑️ **Очистка лога**
- 🌍 **Поддержка локализации** (🇷🇺 Русский / 🇬🇧 English)
- 🔎 **Проверка обновлений** (ссылка на GitHub релизы)
- 💾 **Сохранение настроек** и истории аргументов между сессиями

---

## 📸 Скриншот

![screenshot](https://raw.githubusercontent.com/dmitrijsibanov/k5toolUI/main/assets/screenshot.png)  
> Современный и компактный интерфейс

---

## 🧰 Установка и запуск

### 1. Клонируй репозиторий:
```bash
git clone https://github.com/dmitrijsibanov/k5toolUI.git
cd k5toolUI
```
2. Создай виртуальное окружение:
```bash
python -m venv .venv
source .venv/bin/activate  # для Linux/macOS
.venv\Scripts\activate     # для Windows
```
3. Установи зависимости:
```bash
pip install -r requirements.txt
```
4. Запусти приложение:
```bash
python k5tool_gui.py

```
⸻

🖥️ Требования
	•	Python 3.8+
	•	PySide6
	•	CLI-утилита k5tool должна быть в PATH

⸻

📂 Структура проекта

k5toolUI/
├── k5tool_gui.py         # основной GUI-скрипт
├── k5tool_gui.log        # лог-файл (автоматически создается)
├── requirements.txt      # зависимости
├── README.md             # этот файл
├── assets/
│   └── screenshot.png    # скриншот приложения


⸻

🌐 Локализация

Приложение поддерживает два языка:
	•	🇷🇺 Русский
	•	🇬🇧 English

Изменение языка происходит через меню «Язык». Требуется перезапуск приложения для применения изменений.

⸻

📝 История изменений

Полный список изменений смотри в CHANGELOG.md
---