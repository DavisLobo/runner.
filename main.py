import json
import os
import sys
import time
import math
import array
import pygame

# Pygame and audio initialization (44.1kHz, 16-bit mono)
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

# --- SCREEN SETTINGS (NATIVE 320x180, 1280x720 SCALE 4x) ---
SCREEN_WIDTH, SCREEN_HEIGHT = 320, 180
SCALE = 4
WINDOW_WIDTH, WINDOW_HEIGHT = SCREEN_WIDTH * SCALE, SCREEN_HEIGHT * SCALE

display = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
game_icon = pygame.image.load("runner.png")
pygame.display.set_icon(game_icon)
pygame.display.set_caption("runner.")

clock = pygame.time.Clock()
FPS = 60

font_small = pygame.font.Font(None, 12)
font = pygame.font.Font(None, 16)
font_large = pygame.font.Font(None, 32)

# Strict Monochromatic Palette
COLOR_BG = (15, 20, 15)          
COLOR_FG = (210, 230, 210)       
COLOR_MID = (80, 100, 80)        
COLOR_DARK = (40, 50, 40)        
COLOR_WHITE = (240, 255, 240)    

DATA_FILE = "data.json"

# --- DEFAULT CONTROLS AND SETTINGS ---
DEFAULT_SETTINGS = {
    "sfx_volume": 20,
    "music_volume": 20,
    "key_jump": pygame.K_SPACE,
    "key_left": pygame.K_a,
    "key_right": pygame.K_d,
    "key_run": pygame.K_LSHIFT
}

current_settings = DEFAULT_SETTINGS.copy()

# --- SYNTHESIZED 8-BIT SOUND GENERATOR ---
def generate_sound(wave_type="square", start_freq=440, end_freq=440, duration=0.1, max_amp=6000):
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    buffer = array.array('h')
    
    for i in range(num_samples):
        t = i / sample_rate
        progress = i / num_samples
        freq = start_freq + (end_freq - start_freq) * progress
        
        if wave_type == "square":
            val = 1.0 if (t * freq) % 1.0 < 0.5 else -1.0
        elif wave_type == "sawtooth":
            val = 2.0 * ((t * freq) % 1.0) - 1.0
        elif wave_type == "sine":
            val = math.sin(2 * math.pi * freq * t)
        elif wave_type == "noise":
            val = ((i * 1103515245 + 12345) & 0x7FFFFFFF) / 0x3FFFFFFF - 1.0
        else:
            val = math.sin(2 * math.pi * freq * t)

        envelope = max(0.0, 1.0 - progress)
        sample_val = int(val * envelope * max_amp)
        buffer.append(sample_val)

    return pygame.mixer.Sound(buffer=buffer)

# Game Sounds
sound_damage = generate_sound("sawtooth", start_freq=120, end_freq=30, duration=0.25, max_amp=5000)
sound_win = generate_sound("square", start_freq=440, end_freq=880, duration=0.35, max_amp=4000)

# Menu Sounds
# 1. Selection (Navigation): Opaque, short, and discreet (low sine wave)
# 2. Choice (Confirm): Upbeat, bright, and ascending (fast upward square wave)
# 3. Back (Cancel): Subdued and descending (falling low sawtooth wave)
sound_menu_move = generate_sound("sine", start_freq=220, end_freq=200, duration=0.04, max_amp=2500)
sound_menu_select = generate_sound("square", start_freq=350, end_freq=700, duration=0.10, max_amp=4000)
sound_menu_back = generate_sound("sawtooth", start_freq=240, end_freq=110, duration=0.12, max_amp=3500)

def play_sfx(sound, volume_percentage):
    sound.set_volume(volume_percentage / 100.0)
    sound.play()

# --- RETROWAVE CHIPTUNE MUSIC ---
def generate_synthwave_track():
    sample_rate = 44100
    bpm = 110
    beat_duration = 60 / bpm
    total_beats = 32
    duration = total_beats * beat_duration
    num_samples = int(sample_rate * duration)
    buffer = array.array('h')

    chords = [
        [220.0, 261.63, 329.63], # Am
        [174.61, 220.0, 261.63], # F
        [130.81, 164.81, 196.0],  # C
        [146.83, 185.0, 220.0]   # G
    ]
    bass_notes = [110.0, 87.31, 65.41, 73.42]

    for i in range(num_samples):
        t = i / sample_rate
        beat = (t / beat_duration) % total_beats
        chord_idx = int(beat // 8) % 4
        
        arp_step = int((t / (beat_duration / 4)) % 3)
        arp_freq = chords[chord_idx][arp_step] * 2.0
        arp_val = 1.0 if (t * arp_freq) % 1.0 < 0.3 else -0.3

        bass_freq = bass_notes[chord_idx]
        bass_pulse = 1.0 - ((t / (beat_duration / 2)) % 1.0)
        bass_val = (2.0 * ((t * bass_freq) % 1.0) - 1.0) * bass_pulse

        mixed = (arp_val * 0.3) + (bass_val * 0.5)
        sample_val = int(mixed * 2500)
        buffer.append(sample_val)

    return pygame.mixer.Sound(buffer=buffer)

music_track = generate_synthwave_track()
music_channel = None

def update_music_volume(settings):
    global music_channel
    if music_channel is None:
        music_channel = music_track.play(loops=-1)
    if music_channel:
        music_channel.set_volume(settings["music_volume"] / 100.0)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data.json: {e}")

def load_best_time():
    data = load_data()
    return data.get("best_time", None)

def save_best_time(new_best_time):
    data = load_data()
    data["best_time"] = round(new_best_time, 3)
    save_data(data)

def format_time(seconds):
    if seconds is None:
        return "--:--.---"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{mins:02d}:{secs:02d}.{millis:03d}"

def create_scanline_surface():
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for y in range(0, SCREEN_HEIGHT, 2):
        pygame.draw.line(surface, (0, 0, 0, 40), (0, y), (SCREEN_WIDTH, y))
    return surface

scanlines = create_scanline_surface()


# --- PLAYER ---
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 12, 12)
        self.vel_x = 0.0
        self.vel_y = 0.0

        self.base_speed = 2.0
        self.run_multiplier = 2.0
        self.gravity = 0.3
        self.jump_force = -5.5
        self.variable_jump_multiplier = 0.5

        self.air_drag = 0.03

        self.on_ground = False
        self.is_running = False
        self.facing_right = True
        self.coyote_timer = 0
        self.COYOTE_TIME_MAX = 6
        self.jump_buffer_timer = 0
        self.JUMP_BUFFER_MAX = 6

        self.max_hp = 2
        self.hp = self.max_hp
        self.invincible_timer = 0
        self.INVINCIBLE_TIME_MAX = 45

    def take_damage(self, damage=1):
        if self.invincible_timer <= 0:
            self.hp -= damage
            self.invincible_timer = self.INVINCIBLE_TIME_MAX
            self.vel_y = -3.5
            return True
        return False

    def update(self, keys, settings, tiles):
        if self.invincible_timer > 0:
            self.invincible_timer -= 1

        move_dir = 0
        if keys[settings["key_left"]] or keys[pygame.K_LEFT]:
            move_dir -= 1
            self.facing_right = False
        if keys[settings["key_right"]] or keys[pygame.K_RIGHT]:
            move_dir += 1
            self.facing_right = True

        if self.on_ground:
            self.is_running = (keys[settings["key_run"]] or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and move_dir != 0
            target_speed = self.base_speed * (self.run_multiplier if self.is_running else 1.0)
            self.vel_x = move_dir * target_speed
        else:
            if move_dir != 0:
                if abs(self.vel_x) <= self.base_speed:
                    self.vel_x = move_dir * self.base_speed
            else:
                self.vel_x = 0

            if abs(self.vel_x) > self.base_speed:
                if self.vel_x > 0:
                    self.vel_x = max(self.base_speed, self.vel_x - self.air_drag)
                elif self.vel_x < 0:
                    self.vel_x = min(-self.base_speed, self.vel_x + self.air_drag)

        self.rect.x += int(self.vel_x)
        self.check_collisions_x(tiles)

        if self.on_ground:
            self.coyote_timer = self.COYOTE_TIME_MAX
        else:
            self.coyote_timer = max(0, self.coyote_timer - 1)

        self.jump_buffer_timer = max(0, self.jump_buffer_timer - 1)

        jump_pressed = keys[settings["key_jump"]] or keys[pygame.K_UP]
        if not jump_pressed and self.vel_y < 0:
            self.vel_y *= self.variable_jump_multiplier

        if self.jump_buffer_timer > 0 and self.coyote_timer > 0:
            self.vel_y = self.jump_force
            self.coyote_timer = 0
            self.jump_buffer_timer = 0

        self.vel_y += self.gravity
        if self.vel_y > 7:
            self.vel_y = 7

        self.on_ground = False
        self.rect.y += int(self.vel_y)
        self.check_collisions_y(tiles)

    def trigger_jump_request(self):
        self.jump_buffer_timer = self.JUMP_BUFFER_MAX

    def check_collisions_x(self, tiles):
        for tile in tiles:
            if self.rect.colliderect(tile):
                if self.vel_x > 0:
                    self.rect.right = tile.left
                    self.vel_x = 0
                elif self.vel_x < 0:
                    self.rect.left = tile.right
                    self.vel_x = 0

    def check_collisions_y(self, tiles):
        for tile in tiles:
            if self.rect.colliderect(tile):
                if self.vel_y > 0:
                    self.rect.bottom = tile.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = tile.bottom
                    self.vel_y = 0

    def draw(self, surface, camera_x):
        if self.invincible_timer > 0 and (self.invincible_timer // 4) % 2 == 0:
            return

        draw_rect = self.rect.copy()
        draw_rect.x -= camera_x

        pygame.draw.rect(surface, COLOR_FG, draw_rect)
        
        eye_offset = 7 if self.facing_right else 2
        pygame.draw.rect(surface, COLOR_BG, (draw_rect.x + eye_offset, draw_rect.y + 3, 3, 3))


# --- LEVEL ---
LEVEL_MAP = [
    "............................................................",
    "...........................................................F",
    "....................................................PPPPPPPP",
    ".......................................PPPP.PPPP............",
    "............................PPPPP...........................",
    "...................PPPP.....................................",
    "...............PP...........................................",
    "........PPPP................................................",
    "...................SSSS............SSSSSS...................",
    "X.PP.......SSSS...PPPPPP...PPPP...PPPPPPPPPP................",
    "PPPP...PPPPPPPP.............................PPPP.............",
]

TILE_SIZE = 16

def build_level(map_data):
    tiles, spikes = [], []
    finish_line, spawn_pos = None, (30, 100)

    for row_idx, row in enumerate(map_data):
        for col_idx, cell in enumerate(row):
            x, y = col_idx * TILE_SIZE, row_idx * TILE_SIZE
            if cell == "P":
                tiles.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
            elif cell == "S":
                spikes.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
            elif cell == "F":
                finish_line = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
            elif cell == "X":
                spawn_pos = (x, y)

    map_width = len(map_data[0]) * TILE_SIZE
    return tiles, spikes, finish_line, spawn_pos, map_width


def draw_tile(surface, rect, camera_x):
    draw_rect = rect.copy()
    draw_rect.x -= camera_x
    pygame.draw.rect(surface, COLOR_MID, draw_rect)
    pygame.draw.rect(surface, COLOR_FG, draw_rect, 1)


def draw_spike(surface, rect, camera_x):
    x = rect.x - camera_x
    p1 = (x, rect.bottom)
    p2 = (x + TILE_SIZE // 2, rect.top + 2)
    p3 = (x + TILE_SIZE, rect.bottom)
    pygame.draw.polygon(surface, COLOR_FG, [p1, p2, p3])


def draw_finish_line(surface, rect, camera_x):
    sub_size = TILE_SIZE // 2
    for r in range(2):
        for c in range(2):
            color = COLOR_FG if (r + c) % 2 == 0 else COLOR_BG
            pygame.draw.rect(surface, color, (rect.x - camera_x + c * sub_size, rect.y + r * sub_size, sub_size, sub_size))


def draw_hud(surface, player_hp, elapsed_time, best_time, is_running):
    for i in range(2):
        color = COLOR_FG if i < player_hp else COLOR_DARK
        pygame.draw.rect(surface, color, (6 + (i * 10), 6, 7, 7))
        pygame.draw.rect(surface, COLOR_FG, (6 + (i * 10), 6, 7, 7), 1)

    if is_running:
        run_txt = font.render("RUN", True, COLOR_WHITE)
        surface.blit(run_txt, (30, 4))

    time_txt = font.render(format_time(elapsed_time), True, COLOR_FG)
    surface.blit(time_txt, (SCREEN_WIDTH - time_txt.get_width() - 6, 6))

    best_txt = font.render(f"PB: {format_time(best_time)}", True, COLOR_MID)
    surface.blit(best_txt, (SCREEN_WIDTH - best_txt.get_width() - 6, 18))


def draw_animated_bg(surface, frame_count):
    surface.fill(COLOR_BG)
    offset = (frame_count * 0.5) % 16
    for x in range(0, SCREEN_WIDTH + 16, 16):
        pygame.draw.line(surface, COLOR_DARK, (x - offset, 0), (x - offset, SCREEN_HEIGHT))
    for y in range(0, SCREEN_HEIGHT + 16, 16):
        pygame.draw.line(surface, COLOR_DARK, (0, y), (SCREEN_WIDTH, y))


def show_credits(surface):
    start_t = time.time()
    while time.time() - start_t < 2.5:
        surface.fill(COLOR_BG)
        
        t1 = font_large.render("runner.", True, COLOR_WHITE)
        t2 = font.render("by DavisLobo", True, COLOR_FG)
        t3 = font.render("Thanks for Playing!", True, COLOR_MID)

        surface.blit(t1, (SCREEN_WIDTH // 2 - t1.get_width() // 2, 45))
        surface.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, 85))
        surface.blit(t3, (SCREEN_WIDTH // 2 - t3.get_width() // 2, 110))

        surface.blit(scanlines, (0, 0))
        scaled = pygame.transform.scale(surface, (WINDOW_WIDTH, WINDOW_HEIGHT))
        window.blit(scaled, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)


# --- MODAL DE TUTORIAL (EM INGLÊS) ---
def show_tutorial_modal(surface, settings, frame_count):
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                play_sfx(sound_menu_select, settings["sfx_volume"])
                waiting = False

        draw_animated_bg(surface, frame_count)
        
        pulse = math.sin(frame_count * 0.08) * 2
        title_txt = font_large.render("RUNNER.", True, COLOR_WHITE)
        surface.blit(title_txt, (SCREEN_WIDTH // 2 - title_txt.get_width() // 2, 28 + int(pulse)))

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 15, 10, 200))
        surface.blit(overlay, (0, 0))

        modal_w, modal_h = 260, 140
        modal_x = (SCREEN_WIDTH - modal_w) // 2
        modal_y = (SCREEN_HEIGHT - modal_h) // 2

        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(surface, COLOR_BG, modal_rect)
        pygame.draw.rect(surface, COLOR_FG, modal_rect, 2)

        t_title = font_large.render("HOW TO PLAY", True, COLOR_WHITE)
        surface.blit(t_title, (SCREEN_WIDTH // 2 - t_title.get_width() // 2, modal_y + 10))

        key_j = pygame.key.name(settings["key_jump"]).upper()
        key_l = pygame.key.name(settings["key_left"]).upper()
        key_r = pygame.key.name(settings["key_right"]).upper()
        key_run = pygame.key.name(settings["key_run"]).upper()

        lines = [
            f"MOVE : [{key_l}] / [{key_r}] or ARROWS",
            f"JUMP : [{key_j}] or UP ARROW",
            f"RUN  : Hold [{key_run}]",
            "",
            "Avoid spikes and reach the goal fast!",
            "",
            "Press ANY KEY to Start"
        ]

        for idx, line in enumerate(lines):
            c = COLOR_WHITE if idx == 6 else (COLOR_MID if idx == 4 else COLOR_FG)
            txt = font.render(line, True, c)
            surface.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, modal_y + 36 + idx * 13))

        surface.blit(scanlines, (0, 0))
        scaled = pygame.transform.scale(surface, (WINDOW_WIDTH, WINDOW_HEIGHT))
        window.blit(scaled, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)

    return True


# --- TELA DE OPÇÕES (OPTIONS) ---
def run_options_menu(surface, settings):
    options = ["SFX Volume", "Music Volume", "Jump Key", "Left Key", "Right Key", "Run Key", "BACK"]
    selected = 0
    remapping_idx = None

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

            if remapping_idx is not None:
                if event.type == pygame.KEYDOWN:
                    key_map_keys = ["key_jump", "key_left", "key_right", "key_run"]
                    settings[key_map_keys[remapping_idx - 2]] = event.key
                    play_sfx(sound_menu_select, settings["sfx_volume"])
                    remapping_idx = None
                continue

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(options)
                    play_sfx(sound_menu_move, settings["sfx_volume"])
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(options)
                    play_sfx(sound_menu_move, settings["sfx_volume"])

                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if selected == 0:
                        settings["sfx_volume"] = max(0, settings["sfx_volume"] - 10)
                        play_sfx(sound_menu_move, settings["sfx_volume"])
                    elif selected == 1:
                        settings["music_volume"] = max(0, settings["music_volume"] - 10)
                        update_music_volume(settings)
                        play_sfx(sound_menu_move, settings["sfx_volume"])

                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if selected == 0:
                        settings["sfx_volume"] = min(100, settings["sfx_volume"] + 10)
                        play_sfx(sound_menu_move, settings["sfx_volume"])
                    elif selected == 1:
                        settings["music_volume"] = min(100, settings["music_volume"] + 10)
                        update_music_volume(settings)
                        play_sfx(sound_menu_move, settings["sfx_volume"])

                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if selected == 6:  # BACK
                        play_sfx(sound_menu_back, settings["sfx_volume"])
                        return
                    elif 2 <= selected <= 5:
                        play_sfx(sound_menu_select, settings["sfx_volume"])
                        remapping_idx = selected

                elif event.key == pygame.K_ESCAPE:
                    play_sfx(sound_menu_back, settings["sfx_volume"])
                    return

        surface.fill(COLOR_BG)

        t_title = font_large.render("OPTIONS", True, COLOR_WHITE)
        surface.blit(t_title, (SCREEN_WIDTH // 2 - t_title.get_width() // 2, 12))

        key_names = [
            f"< {settings['sfx_volume']}% >",
            f"< {settings['music_volume']}% >",
            pygame.key.name(settings["key_jump"]).upper(),
            pygame.key.name(settings["key_left"]).upper(),
            pygame.key.name(settings["key_right"]).upper(),
            pygame.key.name(settings["key_run"]).upper(),
            ""
        ]

        for i, opt in enumerate(options):
            color = COLOR_WHITE if i == selected else COLOR_MID
            prefix = "> " if i == selected else "  "
            
            if remapping_idx == i:
                val_str = "PRESS ANY KEY..."
            else:
                val_str = key_names[i]

            label = f"{prefix}{opt}"
            txt_lbl = font.render(label, True, color)
            txt_val = font.render(val_str, True, COLOR_FG if i == selected else COLOR_MID)

            y_pos = 42 + i * 18
            surface.blit(txt_lbl, (25, y_pos))
            if val_str:
                surface.blit(txt_val, (SCREEN_WIDTH - txt_val.get_width() - 25, y_pos))

        surface.blit(scanlines, (0, 0))
        scaled = pygame.transform.scale(surface, (WINDOW_WIDTH, WINDOW_HEIGHT))
        window.blit(scaled, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)


# --- MAIN LOOP AND INITIAL MENU ---
def main():
    frame_count = 0
    menu_options = ["PLAY", "OPTIONS", "QUIT"]
    selected_option = 0

    update_music_volume(current_settings)

    while True:
        frame_count += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                show_credits(display)
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected_option = (selected_option - 1) % len(menu_options)
                    play_sfx(sound_menu_move, current_settings["sfx_volume"])
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected_option = (selected_option + 1) % len(menu_options)
                    play_sfx(sound_menu_move, current_settings["sfx_volume"])

                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if selected_option == 0:  # PLAY
                        play_sfx(sound_menu_select, current_settings["sfx_volume"])
                        if show_tutorial_modal(display, current_settings, frame_count):
                            run_game(current_settings)

                    elif selected_option == 1:  # OPTIONS
                        play_sfx(sound_menu_select, current_settings["sfx_volume"])
                        run_options_menu(display, current_settings)

                    elif selected_option == 2:  # QUIT
                        play_sfx(sound_menu_back, current_settings["sfx_volume"])
                        pygame.time.delay(150)
                        show_credits(display)
                        pygame.quit()
                        sys.exit()

        draw_animated_bg(display, frame_count)

        pulse = math.sin(frame_count * 0.08) * 2
        title_txt = font_large.render("runner.", True, COLOR_WHITE)
        display.blit(title_txt, (SCREEN_WIDTH // 2 - title_txt.get_width() // 2, 32 + int(pulse)))

        sub_txt = font_small.render("run. fast. win.", True, COLOR_MID)
        display.blit(sub_txt, (SCREEN_WIDTH // 2 - sub_txt.get_width() // 2, 60))

        for idx, opt in enumerate(menu_options):
            color = COLOR_WHITE if idx == selected_option else COLOR_MID
            prefix = "> " if idx == selected_option else "  "
            txt = font.render(f"{prefix}{opt}", True, color)
            display.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, 95 + idx * 20))

        display.blit(scanlines, (0, 0))
        scaled = pygame.transform.scale(display, (WINDOW_WIDTH, WINDOW_HEIGHT))
        window.blit(scaled, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)


# --- GAME LOOP ---
def run_game(settings):
    tiles, spikes, finish_line, spawn_pos, map_width = build_level(LEVEL_MAP)
    best_time = load_best_time()

    player = Player(spawn_pos[0], spawn_pos[1])
    start_time = time.time()
    completed = False
    final_time = 0.0
    is_new_record = False
    flash_screen_timer = 0

    in_game = True
    while in_game:
        if not completed:
            current_run_time = time.time() - start_time
        else:
            current_run_time = final_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                show_credits(display)
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key in (settings["key_jump"], pygame.K_UP):
                    player.trigger_jump_request()

                if event.key == pygame.K_r:
                    player = Player(spawn_pos[0], spawn_pos[1])
                    start_time = time.time()
                    completed = False
                    is_new_record = False

                if event.key == pygame.K_ESCAPE:
                    play_sfx(sound_menu_back, settings["sfx_volume"])
                    in_game = False

        keys = pygame.key.get_pressed()

        if not completed:
            player.update(keys, settings, tiles)

            if player.rect.top > SCREEN_HEIGHT:
                play_sfx(sound_damage, settings["sfx_volume"])
                player = Player(spawn_pos[0], spawn_pos[1])
                start_time = time.time()

            for spike in spikes:
                spike_hitbox = pygame.Rect(spike.x + 2, spike.y + 4, TILE_SIZE - 4, TILE_SIZE - 4)
                if player.rect.colliderect(spike_hitbox):
                    if player.take_damage(1):
                        play_sfx(sound_damage, settings["sfx_volume"])
                        flash_screen_timer = 3
                    break

            if player.hp <= 0:
                player = Player(spawn_pos[0], spawn_pos[1])
                start_time = time.time()

            if finish_line and player.rect.colliderect(finish_line):
                completed = True
                final_time = time.time() - start_time
                play_sfx(sound_win, settings["sfx_volume"])

                if best_time is None or final_time < best_time:
                    best_time = final_time
                    save_best_time(best_time)
                    is_new_record = True

        # Câmera
        camera_x = player.rect.centerx - (SCREEN_WIDTH // 2)
        camera_x = max(0, min(camera_x, map_width - SCREEN_WIDTH))

        # Renderização
        if flash_screen_timer > 0:
            display.fill(COLOR_FG)
            flash_screen_timer -= 1
        else:
            display.fill(COLOR_BG)

        for tile in tiles:
            draw_tile(display, tile, camera_x)

        for spike in spikes:
            draw_spike(display, spike, camera_x)

        if finish_line:
            draw_finish_line(display, finish_line, camera_x)

        player.draw(display, camera_x)
        draw_hud(display, player.hp, current_run_time, best_time, player.is_running)

        display.blit(scanlines, (0, 0))

        if completed:
            overlay = pygame.Surface((180, 75))
            overlay.fill(COLOR_BG)
            pygame.draw.rect(overlay, COLOR_FG, (0, 0, 180, 75), 1)

            title_str = "NEW BEST TIME!" if is_new_record else "VICTORY!"
            title_txt = font_large.render(title_str, True, COLOR_WHITE)

            t_str = f"Time: {format_time(final_time)}"
            t_txt = font.render(t_str, True, COLOR_FG)

            restart_txt = font.render("Press 'R' to Restart", True, COLOR_MID)
            esc_txt = font_small.render("ESC to Main Menu", True, COLOR_MID)

            overlay.blit(title_txt, (180 // 2 - title_txt.get_width() // 2, 6))
            overlay.blit(t_txt, (180 // 2 - t_txt.get_width() // 2, 30))
            overlay.blit(restart_txt, (180 // 2 - restart_txt.get_width() // 2, 46))
            overlay.blit(esc_txt, (180 // 2 - esc_txt.get_width() // 2, 60))

            display.blit(overlay, (SCREEN_WIDTH // 2 - 90, SCREEN_HEIGHT // 2 - 37))

        scaled_surface = pygame.transform.scale(display, (WINDOW_WIDTH, WINDOW_HEIGHT))
        window.blit(scaled_surface, (0, 0))

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()