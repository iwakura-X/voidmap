# core/console.py

import cmd
import random
import json
import os
from time import sleep

from .models import World, SignalSource, Telescope
from .utils import load_signals_db, save_progress, load_progress
from .sounds import play_ping, play_fake, play_save, play_process, play_error, play_success, play_level_up

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
            play_success()
        except Exception as e:
            print(f"Error saving game: {e}")
            play_error()

    def do_load_game(self, arg):
        '''Load progress from savegame.json'''
        if not os.path.exists("savegame.json"):
            print("No save file found. Use 'save_game' first.")
            play_error()
            return
        try:
            with open("savegame.json", "r") as f:
                save_data = json.load(f)
                play_process()
        except Exception as e:
            print(f"Error loading save file: {e}")
            play_error()
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
                print("Polarity must be 'R' or 'L' (right or left)")
                return
            print("Tuning...")
            sleep(3)
            self.world.telescope.tune(freq, pol)
            play_success()
        except ValueError:
            print("Frequency must be a number")
            play_error()

    def do_scan(self, arg):
        '''Run one scan cycle'''
        print("Scanning bandwidth...")
        sleep(3)
        self.world.update()

    def do_q(self, arg):
        '''Exit the Console'''
        print("Thanks for playing!!!")
        play_success()
        return True

    def do_list(self, arg):
        '''Print signals list'''
        if not self.world.telescope.unprocessed:
            print("No pending signals. Run 'scan' first.")
            play_error()
            return
        for i, sig in enumerate(self.world.telescope.unprocessed):
            print(f"{i}: Freq: {sig['freq']}MHz | Strength: {sig['stren']} | Pol: {sig['pol']}")
            play_success()

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
                play_fake()
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
                play_error()
                return

            data_copy = {
                "freq": found.freq,
                "stren": found.stren,
                "pol": found.pol,
                "info_levels": found.info_levels
            }
            new_src = SignalSource(found.name, data_copy, process_level=0)
            self.world.sources.append(new_src)
            print("Saving signal...")
            sleep(2)
            play_save()
            print(f"Signal from {found.freq} MHz saved. Use 'catalog' to see saved signals.")
        except ValueError:
            print("Invalid index.")
            play_error()
        except IndexError:
            print("Index out of range.")
            play_error()

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
                play_error()
            src = self.world.sources[idx]
            if src.process_level >= 3:
                print("Signal already fully processed.")
                play_success()
                return
            src.upgrade(self.world)
            print(src.emit())
            print(f"Processed signal to level {src.process_level}.")
            play_process()
            ## Выводим новую инфу
            #print(src.emit())
        except ValueError:
            print("Invalid Index.")
            play_error()
        except IndexError:
            print("Index out of range.")
            play_error()

    def do_ping(self, arg):
        '''Works as a radar. Just type ping and u'll see'''
        nearest, dist = self.world.find_nearest_signal()
        if nearest is None:
            print("""All signals discovered! Congratulations!
            You can add your own signals, or wait for updates.
            Thanks For Playing!
            By Iwakura, made with love <3""")
            play_level_up()
            return

        is_noise = random.random() < 0.15
        if is_noise:
            print("Pinging...")
            sleep(5)
            play_fake()
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
        play_ping()
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