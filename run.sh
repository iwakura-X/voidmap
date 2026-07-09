#!/bin/bash

# Переходим в директорию скрипта (на случай запуска из другого места)
cd "$(dirname "$0")"

# Проверяем, установлен ли cool-retro-term
if command -v cool-retro-term &> /dev/null; then
    # Запускаем cool-retro-term с профилем Voidmap (если есть) и выполняем main.py
    cool-retro-term -e python3 main.py
else
    echo "cool-retro-term is not found. Running in current terminal emulator..."
    python3 main.py
fi