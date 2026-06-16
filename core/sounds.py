# core/sounds.py
import os
import threading
from time import sleep

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide'
import pygame
import numpy as np

pygame.mixer.init(frequency=44100, size=-16, channels=1)

def play_ambience(ambience_file="sounds/ambience.wav"):
    """Запускает фоновую музыку с зацикливанием."""
    path = resource_path(os.path.join("core", ambience_file))
    if os.path.exists(path):
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(loops=-1)
        return True
    else:
        print(f"Ambience file not found: {ambience_file}")
        return False

def _generate_tone(freq, duration, volume=0.3):
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave = np.sin(2 * np.pi * freq * t) * volume
    wave = (wave * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(wave)

def play_ping():
    _generate_tone(1200, 0.15).play()

def play_fake():
    _generate_tone(600, 0.2).play()
    sleep(0.1)
    _generate_tone(400, 0.1).play()

def play_save():
    _generate_tone(1000, 0.1).play()
    sleep(0.1)
    _generate_tone(1200, 0.1).play()

def play_process():
    _generate_tone(800, 0.15).play()
    sleep(0.05)
    _generate_tone(1000, 0.15).play()
    sleep(0.05)
    _generate_tone(1200, 0.2).play()

def play_error():
    _generate_tone(300, 0.3).play()

def play_success():
    _generate_tone(880, 0.1).play()
    sleep(0.08)
    _generate_tone(1100, 0.15).play()

def play_level_up():
    _generate_tone(600, 0.1).play()
    sleep(0.07)
    _generate_tone(900, 0.1).play()
    sleep(0.07)
    _generate_tone(1200, 0.15).play()