# core/models.py
import json
import os
import random
from time import sleep
from .sounds import play_ping, play_error, play_alien_bad, play_alien_good, play_alien_neutral

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
            print(f"Cannot process '{self.name}' further. Need higher experience (current max level: {world.max_process_level}/3).")
            return False
        self.process_level += 1
        if self.process_level == 1:
            world.add_exp(self.name)
        print("Processing signal...")
        sleep(3)
        print(f"Processed signal to level {self.process_level}.")
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
        # Gameplay things
        self.sources = []
        self.telescope = Telescope()
        self.all_signals = []   # будет загружено через load_signals_db
        self.processed_signal_names = set()
        self.max_process_level = 1
        # Lore things
        self.alien_reputation = 0          # от -10 до +10
        self.alien_contact_stage = 0       # 0 - нет контакта, 1 - первый контакт установлен
        self.last_alien_message = None     # текст последнего сообщения
        self.alien_cooldown = 0            # счётчик для ограничения частоты сообщений
        self.username = None

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
        saved_names = {src.name for src in self.sources}  # множество имён сохранённых сигналов
        for src in self.all_signals:
            if src.name in saved_names:
                continue  # пропускаем уже найденные
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
        saved_names = {src.name for src in self.sources}
        available = [src for src in self.all_signals if src.name not in saved_names]
        if not available:
            return None, None
        current = self.telescope.current_freq
        nearest = min(available, key=lambda src: abs(src.freq - current))
        distance = abs(nearest.freq - current)
        return nearest, distance

    def trigger_alien_event(self):
        """Вызывается после каждой команды с шансом 5%."""
        if self.alien_contact_stage == 0:
            return
        if random.random() > 0.05:  # 5% шанс
            return
        
        # В зависимости от репутации выбираем сообщение
        if self.alien_reputation > 0:
            msg, desc = self._get_good_message()
        elif self.alien_reputation < 0:
            msg, desc = self._get_bad_message()
        else:
            msg, desc = self._get_neutral_message()
        
        self.last_alien_message = msg
        print(msg)
        print(f"({desc})")
        # Здесь можно добавить звук

    def _get_good_message(self):
        messages = [
            ("'We appreciate your trust. We will share our knowledge with you.'",
             "A warm glow emanates from the console."),
            ("'Your music is chaotic, but we like it. It reminds us of our home star.'",
             "A strange, uplifting melody seems to play in the background.")
        ]
        play_alien_good()
        return random.choice(messages)

    def _get_bad_message(self):
        messages = [
            ("'mankind is fragile.'",
             "The screen flickers briefly."),
            ("'do not be afraid of your own faith.'",
             "A low hum vibrates through the observatory.")
        ]
        return random.choice(messages)
        play_alien_bad()

    def _get_neutral_message(self):
        messages = [
            ("'We are still observing you. Your actions will determine our relationship.'",
             "Static."),
            ("'We cannot decide if you are friend or foe. Perhaps you need more time.'",
             "The silence stretches.")
        ]
        play_alien_neutral()
        return random.choice(messages)