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
SMALL_FONT = pygame.font.SysFont("Arial", 24)


# ============================
# LINKED LIST (Notes)
# ============================
class NoteNode:
    def __init__(self, x, y, lane, duration, note_type="normal"):
        self.x = x
        self.y = y
        self.lane = lane
        self.duration = duration
        self.note_type = note_type  # "normal", "long"
        self.is_holding = False
        self.hold_start_y = None
        self.next = None


class NoteLinkedList:
    def __init__(self):
        self.head = None

    def add(self, x, y, lane, duration, note_type="normal"):
        new = NoteNode(x, y, lane, duration, note_type)
        if self.head is None:
            self.head = new
        else:
            cur = self.head
            while cur.next:
                cur = cur.next
            cur.next = new

    def remove(self, node):
        if self.head == node:
            self.head = self.head.next
            return
        cur = self.head
        while cur and cur.next != node:
            cur = cur.next
        if cur and cur.next:
            cur.next = cur.next.next

    def __iter__(self):
        cur = self.head
        while cur:
            yield cur
            cur = cur.next


# ============================
# BINARY SEARCH TREE for High Scores
# (Nonlinear Data Structure)
# ============================
class ScoreNode:
    def __init__(self, song, score):
        self.song = song
        self.score = score
        self.left = None
        self.right = None


class ScoreBST:
    def __init__(self):
        self.root = None

    def insert(self, song, score):
        if self.root is None:
            self.root = ScoreNode(song, score)
        else:
            self._insert_recursive(self.root, song, score)

    def _insert_recursive(self, node, song, score):
        if song < node.song:
            if node.left is None:
                node.left = ScoreNode(song, score)
            else:
                self._insert_recursive(node.left, song, score)
        elif song > node.song:
            if node.right is None:
                node.right = ScoreNode(song, score)
            else:
                self._insert_recursive(node.right, song, score)
        else:
            node.score = max(node.score, score)

    def search(self, song):
        return self._search_recursive(self.root, song)

    def _search_recursive(self, node, song):
        if node is None:
            return 0
        if song == node.song:
            return node.score
        elif song < node.song:
            return self._search_recursive(node.left, song)
        else:
            return self._search_recursive(node.right, song)

    def inorder_traversal(self):
        result = []
        self._inorder_recursive(self.root, result)
        return result

    def _inorder_recursive(self, node, result):
        if node:
            self._inorder_recursive(node.left, result)
            result.append((node.song, node.score))
            self._inorder_recursive(node.right, result)


# ============================
# Explosion Particle
# ============================
class Particle:
    def __init__(self, x, y, color=(255, 255, 255)):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.life = random.randint(10, 20)
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self):
        if self.life > 0:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 3)


# ============================
# Feedback Text
# ============================
class FeedbackText:
    def __init__(self, text, x, y, color):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.life = 30
        self.font = BIG_FONT

    def update(self):
        self.y -= 2
        self.life -= 1

    def draw(self):
        if self.life > 0:
            alpha = min(255, self.life * 8)
            txt = self.font.render(self.text, True, self.color)
            screen.blit(txt, (self.x - txt.get_width() // 2, self.y))


# ============================
# Approach Circle
# ============================
class ApproachCircle:
    def __init__(self, x, y, max_radius=60):
        self.x = x
        self.y = y
        self.max_radius = max_radius
        self.current_radius = max_radius

    def update(self, target_y, judgement_line, hit_window):
        distance = abs(target_y - judgement_line)
        self.current_radius = max(40, (distance / hit_window) * self.max_radius)

    def draw(self):
        pygame.draw.circle(screen, (255, 255, 255), (int(self.x), int(self.y)), int(self.current_radius), 2)


# ============================
# Load music + beat detection
# ============================
def load_beats(path):
    y, sr = librosa.load(path)

    # Use onset detection for more accurate rhythm tracking
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)

    # Detect beats with better parameters
    tempo, beats = librosa.beat.beat_track(
        onset_envelope=onset_env,
        y=y,
        sr=sr,
        start_bpm=120,
        units='frames',
        hop_length=512,
        tightness=200  # Very strict beat tracking
    )

    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=512)

    return beat_times


# ============================
# High Score System with BST
# ============================
def load_scores():
    bst = ScoreBST()
    try:
        with open("scores.json", "r") as f:
            data = json.load(f)
            for song, score in data.items():
                bst.insert(song, score)
    except:
        bst.insert("song.mp3", 0)
        bst.insert("song1.mp3", 0)
        bst.insert("song2.mp3", 0)
    return bst


def save_scores(bst):
    scores = {}
    for song, score in bst.inorder_traversal():
        scores[song] = score
    with open("scores.json", "w") as f:
        json.dump(scores, f, indent=4)


# ============================
# Menu Screen
# ============================
def song_menu(score_bst):
    running = True
    while running:
        screen.fill((20, 20, 20))

        title = BIG_FONT.render("Select a Song", True, (255, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))

        options = ["song.mp3", "song1.mp3", "song2.mp3"]
        y = 250
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()[0]

        for song in options:
            high_score = score_bst.search(song)
            text = FONT.render(f"{song}", True, (255, 255, 0))
            score_text = SMALL_FONT.render(f"Best: {high_score}", True, (150, 150, 150))

            rect = text.get_rect(center=(WIDTH // 2, y))

            # Highlight
            if rect.collidepoint(mouse):
                pygame.draw.rect(screen, (70, 70, 70), rect.inflate(40, 40))
                if click:
                    pygame.time.wait(200)
                    return song

            screen.blit(text, rect)
            screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, y + 30))
            y += 120

        pygame.display.update()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                exit()


# ============================
# Main Game
# ============================
def game(song_path, score_bst):
    # Load background depending on song
    try:
        if song_path == "song.mp3":
            background = pygame.image.load("background.png").convert()
        elif song_path == "song1.mp3":
            background = pygame.image.load("background1.png").convert()
        elif song_path == "song2.mp3":
            background = pygame.image.load("background2.png").convert()
        else:
            background = None
    except:
        background = None

    # Load beats
    beat_times = load_beats(song_path)
    beat_queue = deque(beat_times)

    # Start audio
    pygame.mixer.music.load(song_path)

    # Notes list
    notes = NoteLinkedList()

    # Particles
    particles = []
    feedback_texts = []

    # 4 Lanes
    lane_x = [75, 225, 375, 525]
    lane_colors = [(255, 50, 50), (50, 255, 50), (50, 50, 255), (255, 255, 50)]
    lane_flash = [0, 0, 0, 0]

    # 4 keys for 4 lanes
    keys = {pygame.K_a: 0, pygame.K_s: 1, pygame.K_j: 2, pygame.K_k: 3}

    score = 0
    combo = 0
    max_combo = 0
    total_notes = 0
    perfect_hits = 0
    good_hits = 0
    missed_notes = 0
    health = 100

    clock = pygame.time.Clock()
    running = True
    paused = False
    fall_speed = 3

    judgement_line = HEIGHT - 150
    hit_window = 60

    # Countdown
    countdown_active = True
    countdown_start = pygame.time.get_ticks()

    while countdown_active:
        screen.fill((0, 0, 0))
        elapsed = (pygame.time.get_ticks() - countdown_start) / 1000.0

        if elapsed < 1:
            text = BIG_FONT.render("3", True, (255, 255, 255))
        elif elapsed < 2:
            text = BIG_FONT.render("2", True, (255, 255, 255))
        elif elapsed < 3:
            text = BIG_FONT.render("1", True, (255, 255, 255))
        elif elapsed < 4:
            text = BIG_FONT.render("GO!", True, (0, 255, 0))
        else:
            countdown_active = False
            pygame.mixer.music.play()
            start_time = pygame.time.get_ticks() / 1000.0
            break

        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2))
        pygame.display.update()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                exit()

        clock.tick(60)

    while running:
        dt = clock.tick(60)

        if paused:
            screen.fill((0, 0, 0, 128))
            pause_text = BIG_FONT.render("PAUSED", True, (255, 255, 255))
            screen.blit(pause_text, (WIDTH // 2 - pause_text.get_width() // 2, HEIGHT // 2 - 50))
            continue_text = SMALL_FONT.render("Press ESC to continue", True, (200, 200, 200))
            screen.blit(continue_text, (WIDTH // 2 - continue_text.get_width() // 2, HEIGHT // 2 + 20))
            exit_text = SMALL_FONT.render("Press Q to quit to menu", True, (200, 200, 200))
            screen.blit(exit_text, (WIDTH // 2 - exit_text.get_width() // 2, HEIGHT // 2 + 50))

            pygame.display.update()

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    exit()
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        paused = False
                        pygame.mixer.music.unpause()
                    elif e.key == pygame.K_q:
                        pygame.mixer.music.stop()
                        return None
            continue

        t = pygame.time.get_ticks() / 1000.0 - start_time

        # Draw background
        if background:
            screen.blit(background, (0, 0))
        else:
            screen.fill((0, 0, 0))

        # Spawn notes exactly on beats
        if beat_queue and t >= beat_queue[0]:
            lane = random.randint(0, 3)
            notes.add(lane_x[lane], -50, lane, 0.3, "normal")
            total_notes += 1
            beat_queue.popleft()

        # Update and draw notes
        for note in list(notes):
            if not paused:
                note.y += fall_speed

            # Draw note
            pygame.draw.rect(screen, lane_colors[note.lane],
                             pygame.Rect(note.x - 40, note.y - 40, 80, 80), border_radius=5)

            # Missed
            if note.y > judgement_line + hit_window:
                notes.remove(note)
                combo = 0
                health = max(0, health - 10)
                missed_notes += 1

                # Miss feedback
                feedback_texts.append(FeedbackText("MISS", note.x, judgement_line, (255, 0, 0)))
                for i in range(10):
                    particles.append(Particle(note.x, judgement_line, (255, 0, 0)))

        # Draw lane highlights
        for i in range(4):
            if lane_flash[i] > 0:
                s = pygame.Surface((100, HEIGHT))
                s.set_alpha(lane_flash[i])
                s.fill(lane_colors[i])
                screen.blit(s, (lane_x[i] - 50, 0))
                lane_flash[i] = max(0, lane_flash[i] - 15)

        # Draw lane separators
        for i in range(5):
            x = i * 150
            pygame.draw.line(screen, (100, 100, 100), (x, 0), (x, HEIGHT), 2)

        # Draw judgement line
        pygame.draw.line(screen, (255, 255, 255), (0, judgement_line), (WIDTH, judgement_line), 4)

        # Particles
        for p in particles[:]:
            p.update()
            p.draw()
            if p.life <= 0:
                particles.remove(p)

        # Feedback texts
        for ft in feedback_texts[:]:
            ft.update()
            ft.draw()
            if ft.life <= 0:
                feedback_texts.remove(ft)

        # Text (score/combo/health)
        score_text = FONT.render(f"Score: {score}", True, (255, 255, 255))
        combo_text = FONT.render(f"Combo: {combo}", True, (255, 255, 255))

        # Combo color based on milestones
        combo_color = (255, 255, 255)
        if combo >= 50:
            combo_color = (255, 0, 255)
        elif combo >= 20:
            combo_color = (255, 215, 0)
        elif combo >= 10:
            combo_color = (0, 255, 255)

        combo_text = FONT.render(f"Combo: {combo}", True, combo_color)

        # Health bar
        pygame.draw.rect(screen, (100, 0, 0), (20, 120, 200, 20))
        pygame.draw.rect(screen, (0, 255, 0), (20, 120, health * 2, 20))
        pygame.draw.rect(screen, (255, 255, 255), (20, 120, 200, 20), 2)

        screen.blit(score_text, (20, 20))
        screen.blit(combo_text, (20, 70))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    paused = not paused
                    if paused:
                        pygame.mixer.music.pause()
                    else:
                        pygame.mixer.music.unpause()
                elif event.key in keys and not paused:
                    lane = keys[event.key]
                    lane_flash[lane] = 100

                    # Find closest note in lane using LINEAR SEARCH ALGORITHM
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
                            perfect_hits += 1
                            feedback_texts.append(FeedbackText("PERFECT!", hit_note.x, judgement_line, (0, 255, 255)))
                        else:
                            score += 100
                            good_hits += 1
                            feedback_texts.append(FeedbackText("GOOD", hit_note.x, judgement_line, (255, 255, 0)))

                        combo += 1
                        max_combo = max(combo, max_combo)

                        # Explosion
                        for i in range(15):
                            particles.append(Particle(hit_note.x, judgement_line, lane_colors[lane]))

                        notes.remove(hit_note)

        pygame.display.update()

        # Game over
        if health <= 0:
            pygame.mixer.music.stop()
            running = False

        # End when music stops
        if not pygame.mixer.music.get_busy():
            running = False

    # Calculate accuracy
    total_hits = perfect_hits + good_hits
    accuracy = (total_hits / total_notes * 100) if total_notes > 0 else 0

    # Save high score
    if score > score_bst.search(song_path):
        score_bst.insert(song_path, score)
        save_scores(score_bst)

    return {
        "score": score,
        "max_combo": max_combo,
        "accuracy": accuracy,
        "perfect": perfect_hits,
        "good": good_hits,
        "missed": missed_notes
    }


# ============================
# MAIN LOOP
# ============================
score_bst = load_scores()

while True:
    song = song_menu(score_bst)
    result = game(song, score_bst)

    if result is None:
        continue

    # Score summary
    showing = True
    while showing:
        screen.fill((0, 0, 0))

        y_pos = 150

        txt = BIG_FONT.render(f"Score: {result['score']}", True, (255, 255, 0))
        screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, y_pos))
        y_pos += 70

        txt2 = FONT.render(f"Max Combo: {result['max_combo']}", True, (255, 255, 255))
        screen.blit(txt2, (WIDTH // 2 - txt2.get_width() // 2, y_pos))
        y_pos += 50

        txt3 = FONT.render(f"Accuracy: {result['accuracy']:.1f}%", True, (0, 255, 255))
        screen.blit(txt3, (WIDTH // 2 - txt3.get_width() // 2, y_pos))
        y_pos += 50

        txt4 = SMALL_FONT.render(f"Perfect: {result['perfect']} | Good: {result['good']} | Missed: {result['missed']}",
                                 True, (200, 200, 200))
        screen.blit(txt4, (WIDTH // 2 - txt4.get_width() // 2, y_pos))
        y_pos += 80

        txt5 = FONT.render("Press ENTER to continue", True, (255, 255, 255))
        screen.blit(txt5, (WIDTH // 2 - txt5.get_width() // 2, y_pos))

        pygame.display.update()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                showing = False