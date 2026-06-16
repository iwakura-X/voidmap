import json
import os
from .models import SignalSource

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_signals_db(filename="signals_db.json"):
    """Загружает БД сигналов из JSON и возвращает список объектов SignalSource."""
    path = resource_path(os.path.join("core", filename))
    with open(path, 'r') as f:
        data = json.load(f)
    sources = []
    for name, attrs in data.items():
        src = SignalSource(name, attrs, process_level=0)
        sources.append(src)
    return sources

def save_progress(world, filename="savegame.json"):
    """Сохраняет текущий прогресс в файл."""
    save_data = {
        "signals": {src.name: src.process_level for src in world.sources},
        "max_process_level": world.max_process_level
    }
    with open(filename, 'w') as f:
        json.dump(save_data, f, indent=4)

def load_progress(world, filename="savegame.json"):
    """Загружает прогресс из файла и восстанавливает состояние."""
    if not os.path.exists(filename):
        print("No save file found.")
        return
    with open(filename, 'r') as f:
        save_data = json.load(f)
    world.sources = []
    world.processed_signal_names.clear()
    for name, saved_level in save_data.get("signals", {}).items():
        original = None
        for src in world.all_signals:
            if src.name == name:
                original = src
                break
        if original is None:
            print(f"Warning: signal '{name}' not found in database. Skipping.")
            continue
        data_copy = {
            "freq": original.freq,
            "stren": original.stren,
            "pol": original.pol,
            "info_levels": original.info_levels
        }
        new_src = SignalSource(name, data_copy, process_level=saved_level)
        world.sources.append(new_src)
    world.max_process_level = save_data.get("max_process_level", 1)
    world.processed_signal_names = {src.name for src in world.sources if src.process_level >= 1}
    world.update_max_process_level()