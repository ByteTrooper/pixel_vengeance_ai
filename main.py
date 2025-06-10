import pygame
import sys
import random
import time
import math
import ollama
import threading

# --- Sound Initialization ---
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.init()

# --- AI Model Selection ---
AI_MODEL = 'phi3:mini'

# --- OLLAMA AI Configuration ---
try:
    client = ollama.Client()
    client.show(AI_MODEL)
    print(f"Ollama client connected successfully. Model '{AI_MODEL}' is available.")
    LOCAL_AI_ENABLED = True
except Exception as e:
    print(f"Error connecting to Ollama or finding model: {e}")
    print(f"AI functionality disabled. Ensure Ollama is running and '{AI_MODEL}' is downloaded.")
    LOCAL_AI_ENABLED = False

# --- Constants & Colors ---
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
WHITE, BLACK, RED, GREEN, YELLOW = (255, 255, 255), (0, 0, 0), (255, 0, 0), (0, 255, 0), (255, 255, 0)
PURPLE, BRIGHT_PURPLE, ORANGE, CYAN = (128, 0, 128), (220, 120, 255), (255, 165, 0), (0, 255, 255)
GREY = (128, 128, 128)
NUM_STARS = 100
WAVE_COOLDOWN = 3000

# --- Caching & Asset Generation ---
FONT_CACHE = {}

def generate_sound(frequency, duration_ms):
    sample_rate = pygame.mixer.get_init()[0]
    max_amp = 2 ** (pygame.mixer.get_init()[1] * -1 - 1) - 1
    length = int(sample_rate * (duration_ms / 1000.0))
    buf = bytearray(length * 2)
    for i in range(length):
        wave = max_amp if (i // (sample_rate // frequency // 2)) % 2 == 0 else -max_amp
        wave = int(wave * ((length - i) / length))
        packed_wave = wave.to_bytes(2, byteorder='little', signed=True)
        buf[i*2] = packed_wave[0]
        buf[i*2+1] = packed_wave[1]
    return pygame.mixer.Sound(buffer=buf)

laser_charge_sound = generate_sound(200, 1000)
laser_fire_sound = generate_sound(800, 200)
bomb_sound = generate_sound(100, 1500)
player_hit_sound = generate_sound(150, 500)

def draw_text(surf, text, size, x, y, color=WHITE, align="midtop"):
    if size not in FONT_CACHE:
        FONT_CACHE[size] = pygame.font.Font(pygame.font.match_font('arial'), size)
    font = FONT_CACHE[size]
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    setattr(text_rect, align, (x, y))
    surf.blit(text_surface, text_rect)

# --- Art Functions ---
def create_enemy_sprite():
    sprite = pygame.Surface([32, 24], pygame.SRCALPHA)
    pygame.draw.ellipse(sprite, RED, (0, 0, 32, 20))
    pygame.draw.rect(sprite, YELLOW, (13, 4, 6, 12))
    return sprite

def create_boss_sprite():
    sprite = pygame.Surface([160, 80], pygame.SRCALPHA)
    pygame.draw.rect(sprite, PURPLE, (0, 10, 160, 60))
    pygame.draw.rect(sprite, BRIGHT_PURPLE, (10, 20, 140, 40), 4)
    pygame.draw.polygon(sprite, YELLOW, [(0, 10), (20, 40), (0, 70)])
    pygame.draw.polygon(sprite, YELLOW, [(160, 10), (140, 40), (160, 70)])
    pygame.draw.rect(sprite, RED, (70, 0, 20, 15))
    return sprite

def create_interceptor_sprite():
    sprite = pygame.Surface([40, 40], pygame.SRCALPHA)
    pygame.draw.polygon(sprite, WHITE, [(20, 0), (0, 35), (20, 25), (40, 35)])
    pygame.draw.rect(sprite, CYAN, (17, 20, 6, 10))
    return sprite

def create_striker_sprite():
    sprite = pygame.Surface([40, 40], pygame.SRCALPHA)
    pygame.draw.polygon(sprite, (200, 200, 255), [(20, 0), (0, 35), (40, 35)])
    pygame.draw.rect(sprite, CYAN, (10, 20, 6, 10))
    pygame.draw.rect(sprite, CYAN, (24, 20, 6, 10))
    return sprite

def create_tank_sprite():
    sprite = pygame.Surface([40, 40], pygame.SRCALPHA)
    pygame.draw.rect(sprite, GREY, (5, 5, 30, 30))
    pygame.draw.polygon(sprite, WHITE, [(20, 0), (0, 35), (20, 25), (40, 35)], 2)
    pygame.draw.rect(sprite, CYAN, (17, 20, 6, 10))
    return sprite

def create_wraith_sprite():
    sprite = pygame.Surface([40, 40], pygame.SRCALPHA)
    pygame.draw.polygon(sprite, YELLOW, [(20, 0), (5, 40), (35, 40)])
    pygame.draw.polygon(sprite, WHITE, [(20, 5), (10, 35), (30, 35)])
    pygame.draw.rect(sprite, CYAN, (17, 20, 6, 10))
    return sprite

JET_TYPES = {
    "Interceptor": {"sprite_func": create_interceptor_sprite, "speed": 8, "bullet_type": "single", "lives": 1, "bombs": 3, "description": "A balanced, all-around fighter."},
    "Striker": {"sprite_func": create_striker_sprite, "speed": 7, "bullet_type": "double", "lives": 1, "bombs": 1, "description": "High firepower."},
    "Tank": {"sprite_func": create_tank_sprite, "speed": 6, "bullet_type": "single", "lives": 3, "bombs": 2, "description": "Heavily armored."},
    "Wraith": {"sprite_func": create_wraith_sprite, "speed": 11, "bullet_type": "single", "lives": 1, "bombs": 2, "description": "A high-speed jet."}
}

# --- Game Object Classes ---
class Starfield:
    def __init__(self, num_stars=NUM_STARS):
        self.stars = [[random.randrange(0, SCREEN_WIDTH), random.randrange(0, SCREEN_HEIGHT), random.randint(1, 3)] for _ in range(num_stars)]
    def update(self):
        for star in self.stars:
            star[1] += star[2] * 0.5
            if star[1] > SCREEN_HEIGHT:
                star[1] = 0
                star[0] = random.randrange(0, SCREEN_WIDTH)
    def draw(self, surface):
        for x, y, size in self.stars:
            pygame.draw.rect(surface, WHITE, (x, y, size, size))

class Player(pygame.sprite.Sprite):
    def __init__(self, jet_type):
        super().__init__()
        stats = JET_TYPES[jet_type]
        self.image = stats["sprite_func"]()
        self.rect = self.image.get_rect(centerx=SCREEN_WIDTH / 2, bottom=SCREEN_HEIGHT - 10)
        self.speed_x, self.bullet_type, self.lives, self.bombs = stats["speed"], stats["bullet_type"], stats["lives"], stats["bombs"]
        self.power = 1
        self.invincible, self.invincible_timer, self.invincible_duration = False, 0, 3000
    def shoot(self, all_sprites, bullets):
        if self.bullet_type == 'single':
            b = Bullet(self.rect.centerx, self.rect.top, self.power)
            all_sprites.add(b)
            bullets.add(b)
        elif self.bullet_type == 'double':
            b1 = Bullet(self.rect.left + 10, self.rect.top, self.power)
            b2 = Bullet(self.rect.right - 10, self.rect.top, self.power)
            all_sprites.add(b1, b2)
            bullets.add(b1, b2)
    def shoot_super_laser(self, all_sprites, player_lasers):
        l = PlayerLaser(self.rect.centerx, self.rect.top)
        all_sprites.add(l)
        player_lasers.add(l)
    def use_bomb(self, repulsors):
        if self.bombs > 0:
            self.bombs -= 1
            bomb_sound.play()
            r = Repulsor(self.rect.center)
            repulsors.add(r)
    def powerup(self, type):
        if type == 'speed':
            self.speed_x += 1
        elif type == 'power':
            self.power = min(self.power + 1, 5)
    def get_hit(self):
        if not self.invincible:
            player_hit_sound.play()
            self.lives -= 1
            self.power = max(1, self.power - 1)
            if self.lives > 0:
                self.invincible = True
                self.invincible_timer = pygame.time.get_ticks()
                self.rect.centerx = SCREEN_WIDTH / 2
    def update(self, playable_left, playable_right):
        if self.invincible and pygame.time.get_ticks() - self.invincible_timer > self.invincible_duration:
            self.invincible = False
        h_speed = 0
        keystate = pygame.key.get_pressed()
        if keystate[pygame.K_LEFT]:
            h_speed -= self.speed_x
        if keystate[pygame.K_RIGHT]:
            h_speed += self.speed_x
        self.rect.x += h_speed
        self.rect.right = min(self.rect.right, playable_right)
        self.rect.left = max(self.rect.left, playable_left)
        self.image.set_alpha(128 if self.invincible and (pygame.time.get_ticks() // 100) % 2 == 0 else 255)

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, power=1):
        super().__init__()
        self.image = pygame.Surface([4 + (power * 2), 12])
        self.image.fill(CYAN)
        self.rect = self.image.get_rect(centerx=x, bottom=y)
        self.speed_y = -10
        self.damage = 10 * power
    def update(self):
        self.rect.y += self.speed_y
        if self.rect.bottom < 0:
            self.kill()

class PlayerLaser(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface([20, SCREEN_HEIGHT])
        self.image.fill(CYAN)
        self.rect = self.image.get_rect(centerx=x, bottom=y)
        self.spawn_time = pygame.time.get_ticks()
    def update(self):
        if pygame.time.get_ticks() - self.spawn_time > 500:
            self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = create_enemy_sprite()
        self.rect = self.image.get_rect(x=random.randrange(SCREEN_WIDTH - 32), y=random.randrange(-150, -50))
        self.speed_y = random.randrange(1, 5)
        self.health = 10
    def update(self):
        self.rect.y += self.speed_y
        if self.rect.top > SCREEN_HEIGHT + 20:
            self.kill()

class BossBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, speed_x=0, speed_y=6):
        super().__init__()
        self.image = pygame.Surface([12, 12], pygame.SRCALPHA)
        pygame.draw.circle(self.image, ORANGE, (6, 6), 6)
        self.rect = self.image.get_rect(centerx=x, top=y)
        self.speed_x, self.speed_y = speed_x, speed_y
    def update(self):
        self.rect.x += self.speed_x
        self.rect.y += self.speed_y
        if not screen.get_rect().colliderect(self.rect):
            self.kill()

class Mine(pygame.sprite.Sprite):
    def __init__(self, center):
        super().__init__()
        self.image = pygame.Surface([20, 20], pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=center)
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = 8000  # 8 seconds
        self.warn_time = 1000 # 1 second warning period
        self.warn_color = YELLOW
        self.active_color = ORANGE

    def update(self):
        now = pygame.time.get_ticks()
        time_alive = now - self.spawn_time

        if time_alive > self.lifetime:
            self.kill()
            return

        self.image.fill((0,0,0,0)) # Clear previous frame
        if time_alive < self.warn_time:
            if (now // 150) % 2 == 0:
                pygame.draw.circle(self.image, self.warn_color, (10, 10), 10)
        else:
            color = self.active_color if (now // 250) % 2 == 0 else RED
            pygame.draw.circle(self.image, color, (10, 10), 10)

class Laser(pygame.sprite.Sprite):
    def __init__(self, boss_rect):
        super().__init__()
        self.boss_rect = boss_rect
        self.image = pygame.Surface([10, SCREEN_HEIGHT - boss_rect.bottom])
        self.image.fill(BRIGHT_PURPLE)
        self.rect = self.image.get_rect(centerx=self.boss_rect.centerx, top=self.boss_rect.bottom)
        self.spawn_time = pygame.time.get_ticks()
        self.state = "charging"
        laser_charge_sound.play()
    def update(self):
        self.rect.centerx = self.boss_rect.centerx
        now = pygame.time.get_ticks()
        if self.state == "charging" and now - self.spawn_time > 1000:
            self.state = "firing"
            center_pos = self.rect.center
            self.image = pygame.Surface([80, SCREEN_HEIGHT - self.rect.top])
            self.image.fill(RED)
            self.rect = self.image.get_rect(center=center_pos)
            laser_charge_sound.stop()
            laser_fire_sound.play()
        if now - self.spawn_time > 2000:
            self.kill()

class HomingMissile(pygame.sprite.Sprite):
    def __init__(self, x, y, player_ref):
        super().__init__()
        self.original_image = pygame.Surface([10, 20], pygame.SRCALPHA)
        pygame.draw.polygon(self.original_image, ORANGE, [(5, 0), (0, 20), (10, 20)])
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x,y))
        self.player = player_ref
        self.pos = pygame.Vector2(x, y)
        self.speed = 3
        self.update_counter = 0
    def update(self):
        self.update_counter += 1
        if not self.player.alive():
            self.kill()
            return
        direction_to_player = pygame.Vector2(self.player.rect.center) - self.pos
        if direction_to_player.length_squared() > 0:
            if self.update_counter % 3 == 0:
                angle = direction_to_player.angle_to(pygame.Vector2(0, -1))
                self.image = pygame.transform.rotate(self.original_image, angle)
                self.rect = self.image.get_rect(center=self.pos)
            self.pos += direction_to_player.normalize() * self.speed
            self.rect.center = self.pos
        if not screen.get_rect().colliderect(self.rect):
            self.kill()

class PowerUp(pygame.sprite.Sprite):
    def __init__(self, center):
        super().__init__()
        self.type = random.choice(['speed', 'power'])
        self.image = pygame.Surface([30, 30], pygame.SRCALPHA)
        color = GREEN if self.type == 'speed' else YELLOW
        pygame.draw.rect(self.image, color, self.image.get_rect(), 0, 5)
        draw_text(self.image, 'S' if self.type == 'speed' else 'P', 24, 15, 2, BLACK, align="midtop")
        self.rect = self.image.get_rect(center=center)
        self.speed_y = 3
    def update(self):
        self.rect.y += self.speed_y
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

class Repulsor(pygame.sprite.Sprite):
    def __init__(self, center):
        super().__init__()
        self.center = center
        self.radius = 10
        self.max_radius = SCREEN_WIDTH
        self.growth_rate = 30
        self.rect = pygame.Rect(center[0] - self.radius, center[1] - self.radius, self.radius * 2, self.radius * 2)
    def update(self):
        self.radius += self.growth_rate
        self.rect.center = self.center
        self.rect.size = (self.radius * 2, self.radius * 2)
        if self.radius > self.max_radius:
            self.kill()

class Boss(pygame.sprite.Sprite):
    def __init__(self, player_ref):
        super().__init__()
        self.image = create_boss_sprite()
        self.rect = self.image.get_rect(centerx=SCREEN_WIDTH / 2, top=50)
        self.speed_x, self.max_health, self.health = 3, 2500, 2500
        self.ai_client = client if LOCAL_AI_ENABLED else None
        self.is_thinking = False
        self.ai_thread = None
        self.action_sequence = []
        self.next_action_sequence = None
        self.fallback_sequence = ["SPREAD_SHOT", "MOVE_RIGHT", "CIRCLE_SHOT", "MOVE_LEFT", "SINGLE_SHOT"]
        self.ai_request_cooldown = 10000
        self.last_ai_request_time = -self.ai_request_cooldown
        self.enraged = False
        self.desperation_mode = False
        self.dialogue_text = ""
        self.dialogue_timer = 0
        self.final_stand_activated = False
        self.player = player_ref
        self.current_move_direction = "MOVE_RIGHT"
        self.move_timer = 0
        self.move_interval = 2000
        self.is_shielded = False
        self.shield_timer = 0
        self.shield_duration = 4000
        self.shield_health_thresholds = [0.75, 0.50, 0.25]
        self.health_to_regain_on_disable = self.max_health * 0.05
        self.last_minion_summon_time = pygame.time.get_ticks()
        self.minion_summon_interval = 30000
        self.action_cooldown = 250
        self.last_action_time = 0
        self.passive_attack_timer = pygame.time.get_ticks()
        self.passive_attack_interval = random.randint(1500, 2500)
    def set_dialogue(self, text, duration_ms):
        self.dialogue_text = text
        self.dialogue_timer = pygame.time.get_ticks() + duration_ms
    def request_new_ai_sequence(self, player_bullets_group, num_minions):
        current_time = pygame.time.get_ticks()
        if not self.is_thinking and self.ai_client and (current_time - self.last_ai_request_time > self.ai_request_cooldown):
            self.is_thinking = True
            self.last_ai_request_time = current_time
            self.ai_thread = threading.Thread(target=self.get_ai_action, args=(player_bullets_group, num_minions))
            self.ai_thread.start()
            print("AI is thinking...")
    def get_ai_action(self, player_bullets_group, num_minions):
        final_action_sequence = self.fallback_sequence.copy()
        try:
            health_pct = int((self.health / self.max_health) * 100)
            available_actions = "SINGLE_SHOT, SPREAD_SHOT, VOLLEY_SHOT, CIRCLE_SHOT, DODGE, MOVE_LEFT, MOVE_RIGHT, HOMING_MISSILE, LAY_MINES"
            if self.enraged:
                available_actions += ", LASER_SWEEP"
            system_prompt = f"""You are a game boss AI. Your goal is to be aggressive. Your only valid actions are: {available_actions}. RULES: 1. Respond with a comma-separated sequence of 3 to 4 actions. 2. The sequence must contain at least two attack actions. 3. Your response MUST be ONLY the comma-separated list. Example: SPREAD_SHOT,MOVE_LEFT,HOMING_MISSILE"""
            user_prompt = f"My Health: {health_pct}%. Enraged? {'Yes' if self.enraged else 'No'}."
            response = self.ai_client.chat(model=AI_MODEL, messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_prompt}])
            raw_response = response['message']['content'].strip().upper()
            valid_actions_list = [action.strip() for action in available_actions.split(',')]
            potential_actions = [action.strip() for action in raw_response.split(',')]
            validated_actions = [action for action in potential_actions if action in valid_actions_list]
            if validated_actions and len(validated_actions) >= 2:
                final_action_sequence = validated_actions
                print(f"AI decided: {final_action_sequence}")
            else:
                print(f"AI Warning: Invalid sequence '{raw_response}'. Using fallback.")
        except Exception as e:
            print(f"Ollama AI error: {e}")
        finally:
            self.next_action_sequence = final_action_sequence
            self.is_thinking = False
    def single_shot(self, all_sprites, boss_bullets):
        b = BossBullet(self.rect.centerx, self.rect.bottom, speed_y=8)
        all_sprites.add(b)
        boss_bullets.add(b)
    def spread_shot(self, all_sprites, boss_bullets):
        for i in range(-1, 2):
            b = BossBullet(self.rect.centerx, self.rect.bottom, speed_x=(i * 3), speed_y=5)
            all_sprites.add(b)
            boss_bullets.add(b)
    def volley_shot(self, all_sprites, boss_bullets):
        for i in range(3):
            b = BossBullet(self.rect.centerx, self.rect.bottom + (i * 40), speed_y=7)
            all_sprites.add(b)
            boss_bullets.add(b)
    def circle_shot(self, all_sprites, boss_bullets):
        print("Boss: CIRCLE SHOT!")
        num_bullets = 12
        for i in range(num_bullets):
            angle = i * (360 / num_bullets)
            speed_x = 4 * math.cos(math.radians(angle))
            speed_y = 4 * math.sin(math.radians(angle))
            b = BossBullet(self.rect.centerx, self.rect.centery, speed_x, speed_y)
            all_sprites.add(b)
            boss_bullets.add(b)
    def laser_sweep(self, all_sprites, boss_bullets):
        print("Boss: LASER!")
        l = Laser(self.rect)
        all_sprites.add(l)
        boss_bullets.add(l)
    def homing_missile(self, all_sprites, boss_bullets):
        print("Boss: MISSILE!")
        m = HomingMissile(self.rect.centerx, self.rect.bottom, self.player)
        all_sprites.add(m)
        boss_bullets.add(m)
    def lay_mines(self, all_sprites, boss_bullets):
        print("Boss: LAYING MINES!")
        self.set_dialogue("Watch your step!", 2000)
        for _ in range(random.randint(3, 5)):
            mine_x = self.rect.centerx + random.randint(-250, 250)
            mine_y = self.rect.bottom + random.randint(50, 250)
            mine_x = max(20, min(SCREEN_WIDTH - 20, mine_x))
            mine_y = max(150, min(SCREEN_HEIGHT - 100, mine_y))
            m = Mine(center=(mine_x, mine_y))
            all_sprites.add(m)
            boss_bullets.add(m)
    def summon_minions(self, all_sprites, enemies_group):
        if len(enemies_group) > 30:
            print("Boss: Too many minions.")
            return
        print("Boss: SUMMON!")
        self.set_dialogue("My servants will destroy you!", 3000)
        for _ in range(random.randint(8, 12)):
            e = Enemy()
            all_sprites.add(e)
            enemies_group.add(e)
    def update(self, all_sprites, bullets, boss_bullets, enemies_group):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_minion_summon_time > self.minion_summon_interval:
            if not self.is_shielded:
                self.summon_minions(all_sprites, enemies_group)
            self.last_minion_summon_time = current_time
        health_percent = self.health / self.max_health
        if self.shield_health_thresholds and health_percent < self.shield_health_thresholds[0] and not self.is_shielded:
            self.is_shielded = True
            self.shield_timer = current_time + self.shield_duration
            self.shield_health_thresholds.pop(0)
            self.set_dialogue("You cannot pierce this barrier!", 3000)
            self.action_sequence = []
        if self.is_shielded:
            if current_time > self.shield_timer:
                self.is_shielded = False
                self.health = min(self.max_health, self.health + self.health_to_regain_on_disable)
            return
        if not self.final_stand_activated and health_percent < 0.10:
            self.final_stand_activated = True
            print("BOSS: FINAL STAND!")
            self.set_dialogue("I WILL NOT BE DEFEATED!", 4000)
            self.desperation_mode = True
            self.summon_minions(all_sprites, enemies_group)
            self.summon_minions(all_sprites, enemies_group)
            self.action_sequence.clear()
            self.action_sequence.insert(0, "LASER_SWEEP")
        if not self.enraged and health_percent < 0.5:
            self.enraged = True
            print("BOSS IS ENRAGED!")
            self.set_dialogue("ENOUGH! FEEL MY WRATH!", 3000)
            self.action_sequence.insert(0, "LASER_SWEEP")
        if not self.action_sequence:
            if self.next_action_sequence:
                self.action_sequence = self.next_action_sequence
                self.next_action_sequence = None
            else:
                self.request_new_ai_sequence(bullets, len(enemies_group))
                if not self.is_thinking:
                    self.action_sequence = self.fallback_sequence.copy()
        if self.action_sequence and current_time - self.last_action_time > self.action_cooldown:
            self.last_action_time = current_time
            action = self.action_sequence.pop(0)
            action_map = {"SINGLE_SHOT":self.single_shot, "SPREAD_SHOT":self.spread_shot, "VOLLEY_SHOT":self.volley_shot, "CIRCLE_SHOT":self.circle_shot, "LASER_SWEEP":self.laser_sweep, "HOMING_MISSILE":self.homing_missile, "LAY_MINES":self.lay_mines}
            if action in action_map:
                action_map[action](all_sprites, boss_bullets)
            elif action == "DODGE":
                self.rect.x += random.choice([-90, 90])
            elif action in ["MOVE_LEFT", "MOVE_RIGHT"]:
                self.current_move_direction = action
        if current_time - self.move_timer > self.move_interval:
            self.move_timer = current_time
            self.current_move_direction = random.choice(["MOVE_LEFT", "MOVE_RIGHT"])
        self.rect.x += self.speed_x * (1 if self.current_move_direction == "MOVE_RIGHT" else -1)
        if self.rect.left < 0:
            self.rect.left = 0
            self.current_move_direction = "MOVE_RIGHT"
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.current_move_direction = "MOVE_LEFT"
        if not self.is_shielded and current_time - self.passive_attack_timer > self.passive_attack_interval:
            self.passive_attack_timer = current_time
            self.passive_attack_interval = random.randint(1500, 2500)
            random.choice([self.single_shot, self.spread_shot])(all_sprites, boss_bullets)
            print("Boss: Passive Attack!")

def show_controls_screen(surface):
    starfield = Starfield()
    clock = pygame.time.Clock()
    start_time = pygame.time.get_ticks()
    duration = 5000

    while pygame.time.get_ticks() - start_time < duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        starfield.update()
        surface.fill(BLACK)
        starfield.draw(surface)

        draw_text(surface, "PIXEL VENGEANCE AI", 64, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4)
        draw_text(surface, "Arrow Keys: Dodge the cosmic storm!", 22, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        draw_text(surface, "Spacebar: Unleash pixelated fury!", 22, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40)
        draw_text(surface, "Left Shift: Charge the SUPER LASER!", 22, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 80)
        draw_text(surface, "C Key: Drop a reality-warping bomb!", 22, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 120)

        remaining_time = max(0, (duration - (pygame.time.get_ticks() - start_time)) // 1000 + 1)
        draw_text(surface, f"Get ready in {remaining_time}...", 18, SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.75, YELLOW)

        pygame.display.flip()
        clock.tick(60)

def show_jet_selection_screen(surface):
    starfield = Starfield()
    jet_names = list(JET_TYPES.keys())
    selected_index = 0
    selecting = True
    clock = pygame.time.Clock()
    while selecting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    selected_index = (selected_index + 1) % len(jet_names)
                if event.key == pygame.K_LEFT:
                    selected_index = (selected_index - 1) % len(jet_names)
                if event.key == pygame.K_RETURN:
                    return jet_names[selected_index]

        starfield.update()
        surface.fill(BLACK)
        starfield.draw(surface)

        draw_text(surface, "CHOOSE YOUR JET", 50, SCREEN_WIDTH / 2, 50)
        jet_stats = JET_TYPES[jet_names[selected_index]]
        jet_sprite = jet_stats["sprite_func"]()
        surface.blit(jet_sprite, jet_sprite.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50)))
        draw_text(surface, jet_names[selected_index].upper(), 36, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50)
        draw_text(surface, jet_stats["description"], 20, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 100, YELLOW)
        stats_text = f"Lives: {jet_stats['lives']} | Bombs: {jet_stats['bombs']} | Speed: {jet_stats['speed']}"
        draw_text(surface, stats_text, 20, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 150)
        draw_text(surface, "Use Arrow Keys to Navigate, Enter to Select", 18, SCREEN_WIDTH / 2, SCREEN_HEIGHT - 50, GREY)
        pygame.display.flip()
        clock.tick(60)

def start_new_wave(wave_num):
    global is_wave_active, enemies_to_spawn_this_wave, enemies_spawned_this_wave, enemy_spawn_interval
    is_wave_active = True
    enemies_to_spawn_this_wave = 10 + (wave_num * 5)
    enemies_spawned_this_wave = 0
    enemy_spawn_interval = max(100, 500 - (wave_num * 80))
    print(f"--- WAVE {wave_num} INCOMING! ({enemies_to_spawn_this_wave} enemies, spawning every {enemy_spawn_interval}ms) ---")

def draw_health_bar(surf, x, y, pct):
    BAR_LENGTH, BAR_HEIGHT = 150, 20
    fill = (pct / 100) * BAR_LENGTH
    outline_rect = pygame.Rect(x, y, BAR_LENGTH, BAR_HEIGHT)
    fill_rect = pygame.Rect(x, y, max(0, fill), BAR_HEIGHT)
    pygame.draw.rect(surf, GREEN, fill_rect)
    pygame.draw.rect(surf, WHITE, outline_rect, 2)

def draw_charge_bar(surf, x, y, pct):
    BAR_LENGTH, BAR_HEIGHT = 150, 20
    fill = (min(100, max(0, pct)) / 100) * BAR_LENGTH
    outline_rect = pygame.Rect(x, y, BAR_LENGTH, BAR_HEIGHT)
    fill_rect = pygame.Rect(x, y, fill, BAR_HEIGHT)
    pygame.draw.rect(surf, YELLOW, fill_rect)
    pygame.draw.rect(surf, WHITE, outline_rect, 2)

# --- Game Setup ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pixel Vengeance AI")
clock = pygame.time.Clock()
show_controls_screen(screen)
chosen_jet = show_jet_selection_screen(screen)
all_sprites = pygame.sprite.Group()
enemies = pygame.sprite.Group()
bullets = pygame.sprite.Group()
boss_bullets = pygame.sprite.Group()
player_lasers = pygame.sprite.Group()
powerups = pygame.sprite.Group()
repulsors = pygame.sprite.Group()
boss_group = pygame.sprite.GroupSingle()
player = Player(chosen_jet)
all_sprites.add(player)
score = 0
starfield = Starfield()
player_laser_charge = 0
PLAYER_LASER_MAX_CHARGE = 1000
running, game_over_message, current_wave, max_waves = True, "", 0, 3
playable_left, playable_right = 0, SCREEN_WIDTH
wave_clear_time = 0

is_wave_active = False
enemies_to_spawn_this_wave = 0
enemies_spawned_this_wave = 0
last_enemy_spawn_time = 0
enemy_spawn_interval = 500

wave_clear_time = pygame.time.get_ticks()

# --- MAIN GAME LOOP ---
while running:
    dt = clock.tick(60)
    current_time = pygame.time.get_ticks()
    if player.alive() and player_laser_charge < PLAYER_LASER_MAX_CHARGE:
        player_laser_charge += 1
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_q):
            running = False
        elif event.type == pygame.KEYDOWN and player.alive():
            if event.key == pygame.K_SPACE:
                player.shoot(all_sprites, bullets)
            if event.key == pygame.K_LSHIFT and player_laser_charge >= PLAYER_LASER_MAX_CHARGE:
                player.shoot_super_laser(all_sprites, player_lasers)
                player_laser_charge = 0
            if event.key == pygame.K_c:
                player.use_bomb(repulsors)

    # --- UPDATE SECTION ---
    # This is the corrected update logic.
    # Update components that don't need special arguments first.
    starfield.update()
    repulsors.update()
    enemies.update()
    bullets.update()
    boss_bullets.update()
    player_lasers.update()
    powerups.update()

    # Now, update the Player and Boss with their required arguments.
    if player.alive():
        player.update(playable_left, playable_right)

    boss = boss_group.sprite
    if boss:
        boss.update(all_sprites, bullets, boss_bullets, enemies)
        if boss.desperation_mode:
            shrink_speed = 0.5
            playable_left = min(playable_left + shrink_speed, SCREEN_WIDTH / 2 - 50)
            playable_right = max(playable_right - shrink_speed, SCREEN_WIDTH / 2 + 50)
            if playable_left >= playable_right:
                game_over_message = "CRUSHED!"
                running = False

    # --- GAME LOGIC SECTION ---
    if is_wave_active and enemies_spawned_this_wave < enemies_to_spawn_this_wave:
        if current_time - last_enemy_spawn_time > enemy_spawn_interval:
            last_enemy_spawn_time = current_time
            for _ in range(random.randint(1, 2)):
                if enemies_spawned_this_wave < enemies_to_spawn_this_wave:
                    e = Enemy()
                    all_sprites.add(e)
                    enemies.add(e)
                    enemies_spawned_this_wave += 1

    if not boss:
        if is_wave_active and enemies_spawned_this_wave >= enemies_to_spawn_this_wave and not enemies and wave_clear_time == 0:
            is_wave_active = False
            wave_clear_time = current_time

        if not is_wave_active and wave_clear_time != 0 and current_time - wave_clear_time > WAVE_COOLDOWN:
            if current_wave < max_waves:
                current_wave += 1
                start_new_wave(current_wave)
            elif current_wave == max_waves:
                current_wave += 1
                new_boss = Boss(player)
                all_sprites.add(new_boss)
                boss_group.add(new_boss)
                new_boss.set_dialogue("I am powered by a vast intelligence...", 5000)
            wave_clear_time = 0

    enemy_hits = pygame.sprite.groupcollide(enemies, bullets, False, True)
    for enemy, hit_bullets in enemy_hits.items():
        for bullet in hit_bullets:
            enemy.health -= bullet.damage
        if enemy.health <= 0:
            score += 100
            enemy.kill()
            if random.random() > 0.9:
                p = PowerUp(enemy.rect.center)
                all_sprites.add(p)
                powerups.add(p)

    if player.alive():
        player_is_hit = False
        if pygame.sprite.spritecollide(player, enemies, True) or pygame.sprite.spritecollide(player, boss_bullets, True):
            player_is_hit = True
        if boss and not player.invincible and pygame.sprite.spritecollide(player, boss_group, False):
            player_is_hit = True
        if player_is_hit:
            player.get_hit()

        for p_up in pygame.sprite.spritecollide(player, powerups, True):
            player.powerup(p_up.type)

        if player.lives <= 0:
            game_over_message = "GAME OVER"
            running = False
            player.kill()

    for repulsor in repulsors:
        pygame.sprite.groupcollide(boss_bullets, repulsors, True, False, pygame.sprite.collide_circle)
        for enemy in enemies:
            if pygame.sprite.collide_circle(enemy, repulsor):
                enemy.kill()
                score += 100

    if player_lasers:
        score += len(pygame.sprite.groupcollide(enemies, player_lasers, True, False)) * 100
        if boss and not boss.is_shielded and pygame.sprite.spritecollide(boss, player_lasers, False):
            boss.health -= 1.5
            if boss.health <= 0 and boss.alive():
                boss.kill()
                score += 5000
                game_over_message = "YOU WIN!"
                running = False
    if boss and not boss.is_shielded:
        hits = pygame.sprite.groupcollide(boss_group, bullets, False, True)
        if hits:
            for hit_bullet in hits[boss]:
                boss.health -= hit_bullet.damage
            if boss.health <= 0 and boss.alive():
                boss.kill()
                score += 5000
                game_over_message = "YOU WIN!"
                running = False

    # --- DRAW SECTION ---
    screen.fill(BLACK)
    starfield.draw(screen)
    all_sprites.draw(screen)
    for r in repulsors:
        pygame.draw.circle(screen, CYAN, r.center, int(r.radius), 10)
    if boss and boss.desperation_mode:
        pygame.draw.rect(screen, BLACK, (0, 0, playable_left, SCREEN_HEIGHT))
        pygame.draw.rect(screen, BLACK, (playable_right, 0, SCREEN_WIDTH - playable_right, SCREEN_HEIGHT))

    draw_text(screen, f"SCORE: {score}", 24, SCREEN_WIDTH / 2, 10)
    draw_text(screen, f"BOMBS: {player.bombs}", 22, SCREEN_WIDTH - 10, 10, align="topright")
    draw_text(screen, f"LIVES: {player.lives}", 22, 10, 10, align="topleft")
    if boss:
        draw_text(screen, "AI BOSS", 18, 5, 35, RED, align="topleft")
        draw_health_bar(screen, 5, 55, (boss.health / boss.max_health) * 100)
        if boss.dialogue_timer > current_time:
            draw_text(screen, boss.dialogue_text, 36, SCREEN_WIDTH / 2, 140, ORANGE)
        if boss.is_shielded:
            shield_surf = pygame.Surface(boss.rect.size, pygame.SRCALPHA)
            pygame.draw.ellipse(shield_surf, (0, 200, 255, 100), (0, 0, boss.rect.width, boss.rect.height))
            scaled_shield = pygame.transform.scale(shield_surf, (int(boss.rect.width * 1.3), int(boss.rect.height * 1.5)))
            screen.blit(scaled_shield, scaled_shield.get_rect(center=boss.rect.center))
        if boss.is_thinking:
            draw_text(screen, "AI: Analyzing...", 22, SCREEN_WIDTH / 2, 80, YELLOW, align="center")

    if wave_clear_time != 0 and not is_wave_active and not boss and current_wave > 0:
        draw_text(screen, f"WAVE {current_wave} CLEAR!", 48, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, RED)

    draw_charge_bar(screen, 5, SCREEN_HEIGHT - 25, (player_laser_charge / PLAYER_LASER_MAX_CHARGE) * 100)
    draw_text(screen, "Laser [L-SHIFT]", 18, 175, SCREEN_HEIGHT - 28, align="topleft")
    draw_text(screen, "Bomb [C]", 18, 280, SCREEN_HEIGHT - 28, align="topleft")

    pygame.display.flip()

if game_over_message:
    final_score_text = f"FINAL SCORE: {score}"
    color = RED if "OVER" in game_over_message or "CRUSHED" in game_over_message else GREEN
    draw_text(screen, game_over_message, 64, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50, color)
    draw_text(screen, final_score_text, 32, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 20, WHITE)
    pygame.display.flip()
    time.sleep(5)

pygame.quit()
sys.exit()