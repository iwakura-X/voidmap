# main.py
import sys
import os

# Добавляем core в путь поиска модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from core.console import Console
from core.models import World
from core.utils import load_signals_db
from core.sounds import play_ambience

ambience_path = os.path.join(os.path.dirname(__file__), "core", "sounds", "ambience.wav")
play_ambience(ambience_path)

if __name__ == "__main__":
    world = World()
    world.all_signals = load_signals_db()
    Console(world).cmdloop()