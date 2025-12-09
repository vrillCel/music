import pygame
import librosa
import numpy as np
import random
import json
from collections import deque

pygame.init()
WIDTH, HEIGHT = 600, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Music Visualizer Game")

FONT = pygame.font.SysFont("Arial", 32)
BIG_FONT = pygame.font.SysFont("Arial", 48)

# ============================
# LINKED LIST (Notes)
# ============================
class NoteNode:
    def __init__(self, x, y, lane, duration):
        self.x = x
        self.y = y
        self.lane = lane
        self.duration = duration
        self.next = None

class NoteLinkedList:
    def __init__(self):
        self.head = None

    def add(self, x, y, lane, duration):
        new = NoteNode(x, y, lane, duration)
        if self.head is None:
            self.head = new
        else:
            cur = self.head
            while cur.next:
                cur = cur.next
            cur.next = new

    def remove_first(self):
        if self.head:
            self.head = self.head.next

    def __iter__(self):
        cur = self.head
        while cur:
            yield cur
            cur = cur.next

# ============================
# Explosion Particle
# ============================
class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.life = random.randint(10, 20)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self):
        if self.life > 0:
            pygame.draw.circle(screen, (255, 255, 255), (int(self.x), int(self.y)), 3)


# ============================
# Load music + beat detection
# ============================
def load_beats(path):
    y, sr = librosa.load(path)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beats, sr=sr)
    return beat_times


# ============================
# High Score System
# ============================
def load_scores():
    try:
        with open("scores.json", "r") as f:
            return json.load(f)
    except:
        return {"song.mp3": 0, "song1.mp3": 0, "song2.mp3": 0}

def save_scores(scores):
    with open("scores.json", "w") as f:
        json.dump(scores, f, indent=4)


# ============================
# Menu Screen
# ============================
def song_menu():
    running = True
    while running:
        screen.fill((20, 20, 20))

        title = BIG_FONT.render("Select a Song", True, (255, 255, 255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))

        options = ["song.mp3", "song1.mp3", "song2.mp3"]
        y = 250
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()[0]

        for song in options:
            text = FONT.render(song, True, (255, 255, 0))
            rect = text.get_rect(center=(WIDTH//2, y))

            # Highlight
            if rect.collidepoint(mouse):
                pygame.draw.rect(screen, (70, 70, 70), rect.inflate(40, 20))
                if click:
                    return song

            screen.blit(text, rect)
            y += 120

        pygame.display.update()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                exit()


# ============================
# Main Game
# ============================
def game(song_path):
    # Load background depending on song
    if song_path == "song.mp3":
        background = pygame.image.load("background.png").convert()
    elif song_path == "song1.mp3":
        background = pygame.image.load("background1.png").convert()
    elif song_path == "song2.mp3":
        background = pygame.image.load("background2.png").convert()
    else:
        background = None

    # Load beats
    beat_times = load_beats(song_path)
    beat_queue = deque(beat_times)

    # Start audio
    pygame.mixer.music.load(song_path)
    pygame.mixer.music.play()

    # Notes list
    notes = NoteLinkedList()

    # Stack for undo
    action_stack = []

    # Particles
    particles = []

    # Lanes
    lane_x = [100, 250, 400]
    lane_colors = [(255, 50, 50), (50, 255, 50), (50, 50, 255)]

    keys = {pygame.K_a: 0, pygame.K_s: 1, pygame.K_d: 2}

    score = 0
    combo = 0
    max_combo = 0

    clock = pygame.time.Clock()
    running = True
    fall_speed = 5

    judgement_line = HEIGHT - 150
    hit_window = 60

    start_time = pygame.time.get_ticks() / 1000.0

    while running:
        dt = clock.tick(60)
        t = pygame.time.get_ticks() / 1000.0 - start_time

        # Draw background
        if background:
            screen.blit(background, (0, 0))
        else:
            screen.fill((0, 0, 0))

        # Spawn notes exactly on beats
        if beat_queue and t >= beat_queue[0]:
            lane = random.randint(0, 2)
            notes.add(lane_x[lane], -50, lane, 0.3)
            beat_queue.popleft()

        # Update and draw notes
        for note in list(notes):
            note.y += fall_speed
            pygame.draw.rect(screen, lane_colors[note.lane],
                             pygame.Rect(note.x - 40, note.y - 40, 80, 80))

            # Missed
            if note.y > judgement_line + hit_window:
                notes.remove_first()
                combo = 0

        # Draw judgement line
        pygame.draw.line(screen, (255, 255, 255), (0, judgement_line), (WIDTH, judgement_line), 4)

        # Particles
        for p in particles[:]:
            p.update()
            p.draw()
            if p.life <= 0:
                particles.remove(p)

        # Text (score/combo)
        score_text = FONT.render(f"Score: {score}", True, (255, 255, 255))
        combo_text = FONT.render(f"Combo: {combo}", True, (255, 255, 255))
        screen.blit(score_text, (20, 20))
        screen.blit(combo_text, (20, 70))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit()
            if event.type == pygame.KEYDOWN:

                if event.key in keys:
                    lane = keys[event.key]

                    # Find closest note in lane
                    hit_note = None
                    closest_dist = 999

                    for note in notes:
                        if note.lane == lane:
                            dist = abs(note.y - judgement_line)
                            if dist < closest_dist:
                                closest_dist = dist
                                hit_note = note

                    if hit_note and closest_dist < hit_window:
                        # Perfect / Good
                        if closest_dist < 20:
                            score += 300
                        else:
                            score += 100

                        combo += 1
                        max_combo = max(combo, max_combo)

                        # Explosion
                        for i in range(15):
                            particles.append(Particle(hit_note.x, judgement_line))

                        notes.remove_first()
                    else:
                        combo = 0

        pygame.display.update()

        # End when music stops
        if not pygame.mixer.music.get_busy():
            running = False

    # Save high score
    scores = load_scores()
    if score > scores[song_path]:
        scores[song_path] = score
        save_scores(scores)

    return score


# ============================
# MAIN LOOP
# ============================
while True:
    song = song_menu()
    final_score = game(song)

    # Score summary
    showing = True
    while showing:
        screen.fill((0, 0, 0))
        txt = BIG_FONT.render(f"Score: {final_score}", True, (255, 255, 0))
        screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 50))

        txt2 = FONT.render("Press ENTER to continue", True, (255, 255, 255))
        screen.blit(txt2, (WIDTH//2 - txt2.get_width()//2, HEIGHT//2 + 50))

        pygame.display.update()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                showing = False
