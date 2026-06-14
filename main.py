import cmd
import json
import random
import os
from time import sleep

class Console(cmd.Cmd):
    intro = "Voidmap Console. Type 'help' to list commands."
    prompt = "#: "

    def __init__(self, world):
        super().__init__()
        self.world = world

    def do_tune(self, arg):
        '''Tune the Telescope'''
        parts = arg.split()
        if len(parts) < 2:
            print("Usage: tune <freq> <pol>")
            return
        try:
            freq = float(parts[0])
            pol = parts[1]
            self.world.telescope.tune(freq, pol)
        except ValueError:
            print("Frequency must be a number")

    def do_scan(self, arg):
        '''Run one scan cycle'''
        print("Scanning bandwidth...")
        sleep(3)
        self.world.update()

    def do_q(self, arg):
        '''Exit the Console'''
        return True

    def do_list(self, arg):
        '''Print signals list'''
        if not self.world.telescope.unprocessed:
            print("No pending signals. Run 'scan' first.")
            return
        for i, sig in enumerate(self.world.telescope.unprocessed):
            print(f"{i}: Freq: {sig['freq']}MHz | Strength: {sig['stren']} | Pol: {sig['pol']}")

    def do_save(self, arg):
        '''Save detected signal by index: save 0'''
        if not arg:
            print("Usage: save <index>")
            return
        try:
            idx = int(arg)
            if idx < 0 or idx >= len(self.world.telescope.unprocessed):
                print("Index out of range.")
                return
            raw = self.world.telescope.unprocessed.pop(idx)
            '''
                Создаём объект SignalSource, но имя пока неизвестно
                Можно временно назвать "Unknown", потом при обработке определить.
                Для простоты будем искать в all_signals по частоте и полярности.
                В реальной игре нужно сопоставлять сырой сигнал с записью в БД.
                Сделаем так: ищем в all_signals источник с такими freq и pol.
            '''
            found = None
            for src in self.world.all_signals:
                if src.freq == raw['freq'] and src.pol == raw['pol']:
                    found = src
                    break
            if found is None:
                print("Unknown signal, cannot save.")
                return
            # Создаём копию с process_level = 0
            data_copy = {
                "freq": found.freq,
                "stren": found.stren,
                "pol": found.pol,
                "info_levels": found.info_levels
            }
            new_src = SignalSource(found.name, data_copy, process_level=0)
            self.world.sources.append(new_src)
            print(f"Signal from {found.freq} saved. Use 'catalog' to see saved signals.")
        except ValueError:
            print("Invalid index.")

    def do_catalog(self, arg):
        '''List saved signals with their process level and accumulated info'''
        if not self.world.sources:
            print("No saved signals.")
            return
        for i, src in enumerate(self.world.sources):
            print(f"--- Signal #{i} (Level {src.process_level}/3) ---")
            print(src.emit())
            print()

    def do_process(self, arg):
        '''Process saved signal by index: process 0'''
        if not arg:
            print("Usage: process <index>")
            return
        try:
            idx = int(arg)
            if idx < 0 or idx >= len(self.world.sources):
                print("Index out of range.")
            src = self.world.sources[idx]
            if src.process_level >= 3:
                print("Signal already fully processed.")
                return
            src.upgrade(self.world)
            print(src.emit())
            print(f"Processed signal to level {src.process_level}.")
            # Выводим новую инфу
            #print(src.emit())
        except ValueError:
            print("Invalid Index.")
        except IndexError:
            print("Index out of range.")

    def do_ping(self, arg):
        '''Works as a radar. Just type ping and u'll see'''
        nearest, dist = self.world.find_nearest_unsaved_signal()
        if nearest is None:
            print("""All signals discovered! Congratulation!
            You can add your own signals, or wait for updates.
            Thanks For Playing!
            By Iwakura, with love <3""")
            return
        
        is_noise = random.random() < 0.15
        if is_noise:
            print("Pinging...")
            sleep(5)
            print("Static noise. No clear signal detected.")
            return
        
        if dist < 50.0:
            accuracy = 50
        if dist < 200.0:
            accuracy = 100
        else:
            accuracy = 200

        error = random.uniform(-accuracy, accuracy)
        guessed_freq = nearest.freq + error
        guessed_freq = round(guessed_freq, 2)

        print("Pinging...")
        sleep(5)
        print(f"Possible signal near {guessed_freq}MHz.")
        if dist < 50:
            print("Source is close")
        elif dist < 100:
            print("Source is closer")
        else:
            print("Weak signal. Frequency may be inaccurate")

    def do_exp(self, arg):
        '''Shows exp'''
        count = len(self.world.processed_signal_names)
        max_level = self.world.max_process_level
        print(f"Unique signals processed: {count}")
        print(f"Current max processing level: {max_level}/3")
        if count < 3:
            need = 3 - count
            print(f"Need {need} more signal(s) to reach level 2.")
        elif count < 10:
            need = 10 - count
            print(f"Need {need} more signal(s) to reach level 3.")
        else:
            print("Maximum level reached! You are a true radio astronomer.")


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
        print(f"Upgraded '{self.name}' to level {self.process_level}.")
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
        self.all_signals = load_signals_db()
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
            print(f"New signal identified! Total unique: {len(self.processed_signal_names)}.\nMax processing level now: {self.max_process_level}.")

    def update(self):
        self.telescope.unprocessed = []
        for src in self.all_signals:
            raw = self.telescope.listen(src)
            if raw is not None:
                self.telescope.unprocessed.append(raw)
        if not self.telescope.unprocessed:
                print("No signals detected.")
        else:
            print(f"Detected {len(self.telescope.unprocessed)} signal(s). Use 'list' to see them.")

    def find_nearest_signal(self):
        if not self.all_signals:
            return None, None
        current = self.telescope.current_freq
        nearest = min(self.all_signals, key=lambda src: abs(src.freq - current))
        distance = abs(nearest.freq - current)
        return nearest, distance

    def find_nearest_unsaved_signal(self):
        """Возвращает ближайший по частоте сигнал, который ещё не добавлен в self.sources."""
        saved_names = {src.name for src in self.sources}   # имена уже сохранённых
        unsaved = [src for src in self.all_signals if src.name not in saved_names]
        if not unsaved:
            return None, None
        nearest = min(unsaved, key=lambda src: abs(src.freq - self.telescope.current_freq))
        distance = abs(nearest.freq - self.telescope.current_freq)
        return nearest, distance


def load_signals_db(filename = os.path.join(os.path.dirname(__file__), "signals_db.json")):
    with open(filename, 'r') as f:
        data = json.load(f)
    sources = []
    for name, attrs in data.items():
        src = SignalSource(name, attrs, process_level=0)
        sources.append(src)
    return sources

if __name__ == "__main__":
    world = World()
    #print("[DEBUG] world created")

    Console(world).cmdloop()