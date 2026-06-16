import cmd, json, random, os, threading, time, pygame
import simpleaudio as sa

pygame.mixer.init()

def play_ambience(ambience_file):
    pygame.mixer.music.load(ambience_file)
    pygame.mixer.music.play(loops=-1)
    while True:
        time.sleep(1)

ambience_path = 'sounds/ambience.wav'
if os.path.exists(ambience_path):
    ambience_thread = threading.Thread(target=play_ambience, args=(ambience_path,), daemon=True)
    ambience_thread.start()

class Console(cmd.Cmd):
    intro = "Welcome to Voidmap! Hope you'll enjoy playing my game! Type 'help' to list commands."
    prompt = "root@RT-64~#: "

    def __init__(self, world):
        super().__init__()
        self.world = world

    def do_sound_off(self, arg):
        '''Toggle sound on/off'''
        pygame.mixer.music.pause()

    def do_sound_on(self, arg):
        '''Start sound'''
        pygame.mixer.music.unpause()

    def do_fastfetch(self, arg):
        '''shows in-game machine info'''
        art = r"""
                                                 _.oo.
                         _.u[[/;:,.         .odMMMMMM'
                      .o888UU[[[/;:-.  .o@P^    MMM^
                     oN88888UU[[[/;::-.        dP^
                    dNMMNN888UU[[[/;:--.   .o@P^
                   ,MMMMMMN888UU[[/;::-. o@^
                   NNMMMNN888UU[[[/~.o@P^
                   888888888UU[[[/o@^-..
                  oI8888UU[[[/o@P^:--..
               .@^  YUU[[[/o@^;::---..
             oMP     ^/o@P^;:::---..
          .dMMM    .o@^ ^;::---...
         dMMMMMMM@^`       `^^^^
        YMMMUP^
         ^^
        """
        print(art)
        print()
        print("  OS: THA-1500 Linux v6.7-release")
        print(f"  Host: {self.world.telescope.current_freq:g} MHz | Polarity: {self.world.telescope.current_pol or 'N/A'}")
        print("  Uptime: 42 days, 7 hours, 23 minutes (cosmic time)")
        print("  Shell: astrosh 5.2")
        print("  CPU: Neutron Star Pulsar Core (12 quantum threads @ 1.21 NHz)")
        print("  RAM: 13.37 PB of cosmic noise (used: 42%)")
        print("  Storage: 128 ZB (radio‑buffer, 73% free)")
        print("  Signal processor: RT‑64 MK‑II")
        print("  Noise floor: -189 dBm")
        print("  Bandwidth: 1.6MHz")
        print("  Active filters: bandpass, notch, wavelet denoise")
        print()
        print("  “The universe is not only stranger than we imagine, it is stranger than we can imagine.”")

    def do_save_game(self, arg):
        '''Save current progress to savegame.json'''
        save_data = {
            "signals": {src.name: src.process_level for src in self.world.sources},
            "max_process_level": self.world.max_process_level
        }
        try:
            with open("savegame.json", "w") as f:
                json.dump(save_data, f, indent=4)
            print("Game saved to savegame.json")
        except Exception as e:
            print(f"Error saving game: {e}")

    def do_load_game(self, arg):
        '''Load progress from savegame.json'''
        if not os.path.exists("savegame.json"):
            print("No save file found. Use 'save_game' first.")
            return
        try:
            with open("savegame.json", "r") as f:
                save_data = json.load(f)
        except Exception as e:
            print(f"Error loading save file: {e}")
            return

        # Очищаем текущие данные
        self.world.sources = []
        self.world.processed_signal_names.clear()

        # Восстанавливаем сигналы
        signals_from_save = save_data.get("signals", {})
        for name, saved_level in signals_from_save.items():
            # Ищем оригинальные данные о сигнале в базе all_signals
            original = None
            for src in self.world.all_signals:
                if src.name == name:
                    original = src
                    break
            if original is None:
                print(f"Warning: signal '{name}' not found in database. Skipping.")
                continue
            # Создаём копию с сохранённым уровнем обработки
            data_copy = {
                "freq": original.freq,
                "stren": original.stren,
                "pol": original.pol,
                "info_levels": original.info_levels
            }
            new_src = SignalSource(name, data_copy, process_level=saved_level)
            self.world.sources.append(new_src)

        # Восстанавливаем max_process_level (или пересчитываем)
        self.world.max_process_level = save_data.get("max_process_level", 1)
        # Обновляем множество обработанных сигналов (опыт) на основе загруженных
        self.world.processed_signal_names = {src.name for src in self.world.sources if src.process_level >= 1}
        # Пересчитываем max_process_level (на всякий случай)
        self.world.update_max_process_level()
        print(f"Game loaded. Found {len(self.world.sources)} saved signals.")
        print(f"Max processing level: {self.world.max_process_level}/3")

    def do_tune(self, arg):
        '''Tune the Telescope'''
        parts = arg.split()
        if len(parts) < 2:
            print("Usage: tune <freq> <pol>")
            return
        try:
            freq = float(parts[0])
            pol = parts[1]
            if pol not in ("L", "R"):
                print("Polarity must be 'R' or 'L' (right or left)ю")
                return
            print("Tuning...")
            sleep(3)
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
        print("Thanks for playing!!!")
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

            # Проверка на ложный сигнал
            if raw.get("is_fake", False):
                print("Signal dissolved into static... It was a false alarm.")
                return

            # Поиск соответствия в базе (реальный сигнал)
            found = None
            for src in self.world.all_signals:
                if src.freq == raw['freq'] and src.pol == raw['pol']:
                    found = src
                    break
            if found is None:
                print("Unknown signal, cannot save.")
                return

            data_copy = {
                "freq": found.freq,
                "stren": found.stren,
                "pol": found.pol,
                "info_levels": found.info_levels
            }
            new_src = SignalSource(found.name, data_copy, process_level=0)
            self.world.sources.append(new_src)
            print(f"Signal from {found.freq} MHz saved. Use 'catalog' to see saved signals.")
        except ValueError:
            print("Invalid index.")
        except IndexError:
            print("Index out of range.")

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
            print("""All signals discovered! Congratulations!
            You can add your own signals, or wait for updates.
            Thanks For Playing!
            By Iwakura, made with love <3""")
            return

        is_noise = random.random() < 0.15
        if is_noise:
            print("Pinging...")
            sleep(5)
            print("Static noise. No clear signal detected.")
            return

        # Ошибка тем больше, чем дальше источник, но не слишком огромная
        # Максимальная ошибка — 10% от расстояния, но не менее 0.5 и не более 8 МГц
        max_error = max(0.5, min(8.0, dist * 0.1))
        error = random.uniform(-max_error, max_error)
        guessed_freq = nearest.freq + error
        guessed_freq = round(guessed_freq, 2)

        print("Pinging...")
        sleep(5)
        print(f"Possible signal near {guessed_freq} MHz.")

        # Подсказка о расстоянии (чем ближе, тем точнее)
        if dist < 5:
            print("Very close! Almost caught it.")
        elif dist < 20:
            print("Getting warm, keep tuning.")
        elif dist < 50:
            print("Signal is somewhere around.")
        else:
            print("Weak and distant. Frequency may be very inaccurate.")

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
        # Сначала реальные сигналы
        for src in self.all_signals:
            raw = self.telescope.listen(src)
            if raw is not None:
                self.telescope.unprocessed.append(raw)

        # Ложные сигналы-обманки (вероятность 35%)
        if random.random() < 0.10:
            num_fake = random.randint(1, 3)
            for _ in range(num_fake):
                fake_freq = random.uniform(100.0, 5000.0)
                fake_stren = random.uniform(0.1, 0.9)
                fake_pol = random.choice(["R", "L"])
                fake_raw = {
                    "freq": fake_freq,
                    "stren": fake_stren,
                    "pol": fake_pol,
                    "is_fake": True
                }
                self.telescope.unprocessed.append(fake_raw)

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