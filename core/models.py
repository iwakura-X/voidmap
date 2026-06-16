# core/models.py
import json
import os
import random
from time import sleep
from .sounds import play_ping, play_error

class SignalSource:
    def __init__(self, name, data, process_level=0):
        self.name = name
        self.freq = data.get("freq")
        self.stren = data.get("stren")
        self.pol = data.get("pol")
        self.info_levels = data.get("info_levels", {})
        self.process_level = process_level

    def emit(self):
        lines = []
        # Уровень 0: базовые параметры (всегда есть)
        lines.append(f"Frequency: {self.freq} MHz, Polarity: {self.pol}, Strength: {self.stren}")
        if self.process_level >= 1:
            lines.append(f"Identified as: {self.name}")
        if self.process_level >= 2:
            lines.append(self.info_levels.get('2', 'No additional info'))
        if self.process_level >= 3:
            lines.append(self.info_levels.get('3', 'No further info'))
        return "\n".join(lines)

    def upgrade(self, world):
        if self.process_level >= world.max_process_level:
            print(f"Cannot upgrade '{self.name}' further. Need higher experience (current max level: {world.max_process_level}/3).")
            return False
        self.process_level += 1
        if self.process_level == 1:
            world.add_exp(self.name)
        print(f"Upgraded signal to level {self.process_level}.")
        return True


class Telescope:
    def __init__(self):
        self.current_freq = 0.0
        self.current_pol = ""
        self.is_on = True
        self.unprocessed = []

    def tune(self, freq, pol):
        self.current_freq = freq
        self.current_pol = pol
        print(f"Telescope's frequency is set to {freq} MHz, Polarity is set to {pol}")

    def listen(self, source):
        if abs(source.freq - self.current_freq) < 0.5 and source.pol == self.current_pol:
            return {
                "freq": source.freq,
                "stren": source.stren,
                "pol": source.pol
            }
        else:
            return None


class World:
    def __init__(self):
        self.sources = []
        self.telescope = Telescope()
        self.all_signals = []   # будет загружено через load_signals_db
        self.processed_signal_names = set()
        self.max_process_level = 1

    def update_max_process_level(self):
        count = len(self.processed_signal_names)
        if count >= 10:
            self.max_process_level = 3
        elif count >= 3:
            self.max_process_level = 2
        else:
            self.max_process_level = 1

    def add_exp(self, signal_name):
        if signal_name not in self.processed_signal_names:
            self.processed_signal_names.add(signal_name)
            self.update_max_process_level()
            print(f"New signal identified! Total unique: {len(self.processed_signal_names)}.")
            print(f"Max processing level now: {self.max_process_level}/3.")

    def update(self):
        self.telescope.unprocessed = []
        for src in self.all_signals:
            raw = self.telescope.listen(src)
            if raw is not None:
                self.telescope.unprocessed.append(raw)
        if not self.telescope.unprocessed:
            print("No signals detected.")
            play_error()
        else:
            print(f"Detected {len(self.telescope.unprocessed)} signal(s). Use 'list' to see them.")
            play_ping()
    def find_nearest_signal(self):
        if not self.all_signals:
            return None, None
        current = self.telescope.current_freq
        nearest = min(self.all_signals, key=lambda src: abs(src.freq - current))
        distance = abs(nearest.freq - current)
        return nearest, distance