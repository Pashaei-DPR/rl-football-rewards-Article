################################
import pygame
import random
import math
import csv
import time
import subprocess
import sys
import os
import threading
############################
import blue_controller  # ایمپورت کردن فایل کنترلر جدید
import red_controller
#############################
# ---- Configuration ----   #
#############################
latest_actions = {"red": "", "blue": ""}

WIDTH, HEIGHT = 800, 500
FIELD_HEIGHT = 500
FPS = 60
GAME_DURATION = 5 * 60  # seconds
GOAL_WIDTH = 10
GOAL_HEIGHT = 150
GOAL_BOX_WIDTH = 80
GOAL_BOX_HEIGHT = 300
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 128, 0)
GOAL_COLOR = (200, 200, 0)
#########################
# ---- Initialize ----  #
#########################
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("2D Soccer Simulator")
font = pygame.font.SysFont("Arial", 24)
small_font = pygame.font.SysFont("Arial", 15)
clock = pygame.time.Clock()


#############################
# ---- Game State ----     #
#############################
score = [0, 0]
shots_on_target = {"red": 0, "blue": 0}
passes_completed = {"red": 0, "blue": 0}
pass_in_progress = {"active": False, "team": None, "target_player": None}
red_possession_time = blue_possession_time = 1
total_possession_time = 2 
last_possession_update = pygame.time.get_ticks()
last_shot_by = None
red_shot_flag = blue_shot_flag = 0
last_save_time = time.time()
#############################
# ---- Classes ----        #
#############################
class Agent:
    def __init__(self, x, y, color, controls=None, player_id=None):
        self.init_x = x
        self.init_y = y
        self.x = x
        self.y = y
        self.radius = 15
        self.color = color
        self.speed = 3
        self.controls = controls
        self.has_ball = False
        self.player_id = player_id
    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        if self.has_ball:
            pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), 5)
        label = self.player_id.replace("red", "R").replace("blue", "B").replace("_gk", "G")
        txt_col = (0, 0, 0) if self.color == RED else (255, 255, 255)
        text_surface = small_font.render(label, True, txt_col)
        rect = text_surface.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(text_surface, rect)
    def move_toward_ball_y(self, ball, x_fixed, margin=30):
        self.x = x_fixed
        self.y += self.speed * (1 if self.y < ball.y else -1 if self.y > ball.y else 0)
        min_y = HEIGHT // 2 - GOAL_HEIGHT // 2 + margin
        max_y = HEIGHT // 2 + GOAL_HEIGHT // 2 - margin
        self.y = max(min_y, min(max_y, self.y))
    def reset_position(self):
        self.x, self.y = self.init_x, self.init_y

class Ball:
    def __init__(self, x, y):
        self.init_pos = (x, y)
        self.x, self.y = x, y
        self.radius = 10
        self.color = WHITE
        self.x_velocity = self.y_velocity = 0
        self.owner = None
        self.possession_cooldown = 0
        self.pass_target = None
    def reset(self, x=None, y=None):
        self.x, self.y = x or self.init_pos[0], y or self.init_pos[1]
        self.x_velocity = self.y_velocity = 0
        self.owner = None
        self.possession_cooldown = 0
        self.pass_target = None
    def update(self):
        if self.owner:
            self.x, self.y = self.owner.x, self.owner.y
        else:
            self.x += self.x_velocity
            self.y += self.y_velocity
            self.x_velocity *= 0.98
            self.y_velocity *= 0.98
        if self.possession_cooldown > 0:
            self.possession_cooldown -= 1
    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        if self.pass_target and not self.owner:
            pygame.draw.line(surface, (100, 100, 100), (int(self.x), int(self.y)),
                             (int(self.pass_target.x), int(self.pass_target.y)), 1)
    def handle_possession(self, agents):
        if self.possession_cooldown > 0:
            return
        agents_near_ball = [a for a in agents if math.hypot(self.x - a.x, self.y - a.y) < self.radius + a.radius]
        if self.pass_target in agents_near_ball and not self.owner:
            self.owner = self.pass_target
            self.owner.has_ball = True
            self.pass_target = None
            if self.owner.color == RED: passes_completed["red"] += 1
            if self.owner.color == BLUE: passes_completed["blue"] += 1
            return
        if len(agents_near_ball) == 2:
            self.owner = random.choice(agents_near_ball)
        elif agents_near_ball:
            self.owner = agents_near_ball[0]
        else:
            if self.owner: self.owner.has_ball = False
            self.owner = None
        if self.owner: self.owner.has_ball = True
    def shoot(self, direction, force=15):
        if not self.owner:
            return  
        self.x_velocity, self.y_velocity = math.cos(direction) * force, math.sin(direction) * force
        if self.owner: self.owner.has_ball = False
        self.owner, self.pass_target, self.possession_cooldown = None, None, 20
    def pass_to(self, target_player, force=9):
        if not self.owner:
            return False
        if not self.owner: return False
        dx, dy = target_player.x - self.x, target_player.y - self.y
        distance = math.hypot(dx, dy)
        if distance < 1: return False
        angle = math.atan2(dy, dx) + random.uniform(-0.1, 0.1)
        adjusted_force = min(force * (distance/200 + 0.5), force * 1.5)
        self.x_velocity, self.y_velocity = math.cos(angle) * adjusted_force, math.sin(angle) * adjusted_force
        self.pass_target = target_player
        if self.owner: self.owner.has_ball = False
        self.owner, self.possession_cooldown = None, 10
        return True
    

#############################
# ---- Game Logic ----      #
#############################
def draw_field():
    screen.fill(GREEN)
    pygame.draw.rect(screen, WHITE, (0, 0, WIDTH, HEIGHT), 4)
    pygame.draw.line(screen, WHITE, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 2)
    pygame.draw.circle(screen, WHITE, (WIDTH // 2, HEIGHT // 2), 70, 2)
    pygame.draw.rect(screen, WHITE, (0, HEIGHT // 2 - GOAL_BOX_HEIGHT // 2, GOAL_BOX_WIDTH, GOAL_BOX_HEIGHT), 2)
    pygame.draw.rect(screen, WHITE, (WIDTH - GOAL_BOX_WIDTH, HEIGHT // 2 - GOAL_BOX_HEIGHT // 2, GOAL_BOX_WIDTH, GOAL_BOX_HEIGHT), 2)
    pygame.draw.rect(screen, GOAL_COLOR, (0, HEIGHT // 2 - GOAL_HEIGHT // 2, GOAL_WIDTH, GOAL_HEIGHT))
    pygame.draw.rect(screen, GOAL_COLOR, (WIDTH - GOAL_WIDTH, HEIGHT // 2 - GOAL_HEIGHT // 2, GOAL_WIDTH, GOAL_HEIGHT))
    score_text = font.render(f"Red {score[1]} - {score[0]} Blue", True, WHITE)
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 10))

    owner_text = small_font.render(f"Owner: {ball.owner.player_id if ball.owner else 'None'}", True, WHITE)
    screen.blit(owner_text, (10, 10))
    # ===== نمایش اکشن‌های بازیکنان =====
    action_text_red = small_font.render(f"Red Actions: {latest_actions['red']}", True, RED)
    action_text_blue = small_font.render(f"Blue Actions: {latest_actions['blue']}", True, BLUE)
    screen.blit(action_text_red, (10, HEIGHT - 30))
    screen.blit(action_text_blue, (WIDTH - action_text_blue.get_width() - 10, HEIGHT - 30))

def check_goal(ball):
    if (ball.x - ball.radius <= GOAL_WIDTH and HEIGHT // 2 - GOAL_HEIGHT // 2 < ball.y < HEIGHT // 2 + GOAL_HEIGHT // 2):
        return "blue"
    if (ball.x + ball.radius >= WIDTH - GOAL_WIDTH and HEIGHT // 2 - GOAL_HEIGHT // 2 < ball.y < HEIGHT // 2 + GOAL_HEIGHT // 2):
        return "red"
    return None

def check_goalkeeper_block(ball, keeper):
    global last_shot_by
    dist = math.hypot(ball.x - keeper.x, ball.y - keeper.y)
    if dist < ball.radius + keeper.radius:
        dx, dy = ball.x - keeper.x, ball.y - keeper.y
        angle = math.atan2(dy, dx)
        speed = math.hypot(ball.x_velocity, ball.y_velocity)
        ball.x_velocity, ball.y_velocity = math.cos(angle) * speed * 0.7, math.sin(angle) * speed * 0.7
        if keeper == blue_keeper and last_shot_by == "red":
            shots_on_target["red"] += 1
            last_shot_by = None
        elif keeper == red_keeper and last_shot_by == "blue":
            shots_on_target["blue"] += 1
            last_shot_by = None
        ball.x = keeper.x + (ball.radius + keeper.radius + 1) * math.cos(angle)
        ball.y = keeper.y + (ball.radius + keeper.radius + 1) * math.sin(angle)

### تغییر یافته: تابع خواندن از دیتابیس حذف شد ###
# def read_actions_from_db(...): ...

def move_by_db_action(agent, action_dict, prefix):
    up, down, left, right = (action_dict.get(f"{prefix}_up", 0), action_dict.get(f"{prefix}_down", 0),
                             action_dict.get(f"{prefix}_left", 0), action_dict.get(f"{prefix}_right", 0))
    # Conflict resolution
    if up and down: up = down = 0
    if left and right: left = right = 0
    agent.y += (-agent.speed if up else agent.speed if down else 0)
    agent.x += (-agent.speed if left else agent.speed if right else 0)
    agent.x = max(agent.radius, min(WIDTH - agent.radius, agent.x))
    agent.y = max(agent.radius, min(HEIGHT - agent.radius, agent.y))

def handle_shoot_and_pass(agent, action_dict, team_prefix, teammates, ball):
    if not agent.has_ball or ball.owner != agent:
        return
    global red_shot_flag, blue_shot_flag, last_shot_by
    if not agent.has_ball: return
    pass_flags = {t: action_dict.get(f"{agent.player_id}_pass_{t.player_id[-1]}", 0) for t in teammates if t != agent}
    shoot_flag = action_dict.get(f"{agent.player_id}_shoot", 0)
    if shoot_flag and any(pass_flags.values()): return
    for teammate, flag in pass_flags.items():
        if flag: ball.pass_to(teammate); return
    if shoot_flag:
        angle = math.atan2(HEIGHT // 2 - ball.y,
                           (WIDTH - GOAL_WIDTH - ball.x) if agent.color == RED else (GOAL_WIDTH - ball.x))
        if agent.color == RED:
            red_shot_flag = 1; last_shot_by = "red"
        else:
            blue_shot_flag = 1; last_shot_by = "blue"
        ball.shoot(angle, force=15)

#############################
# ---- Setup Players ----   #
#############################
red_agent = Agent(150, HEIGHT // 2, RED, player_id="red1")
blue_agent = Agent(WIDTH - 150, HEIGHT // 2, BLUE, player_id="blue1")
red_agent2 = Agent(150, HEIGHT // 2 - 80, RED, player_id="red2")
blue_agent2 = Agent(WIDTH - 150, HEIGHT // 2 + 80, BLUE, player_id="blue2")
red_agent3 = Agent(150, HEIGHT // 2 + 80, RED, player_id="red3")
blue_agent3 = Agent(WIDTH - 150, HEIGHT // 2 - 80, BLUE, player_id="blue3")

ball = Ball(WIDTH // 2, HEIGHT // 2)
red_keeper = Agent(40, HEIGHT // 2, RED, player_id="red_gk"); red_keeper.speed = 0.9
blue_keeper = Agent(WIDTH - 40, HEIGHT // 2, BLUE, player_id="blue_gk"); blue_keeper.speed = 0.9
red_team = [red_agent, red_agent2,red_agent3]
blue_team = [blue_agent, blue_agent2,blue_agent3]
all_field_players = red_team + blue_team
all_players = all_field_players + [red_keeper, blue_keeper]


#############################
# ---- Main Game Loop ----  #
#############################
start_time = time.time()
running = True

# متغیر برای مدیریت تایمر وقتی گل می‌شود
goal_scored_timer = 0 

while running:
    # ۱. بررسی وضعیت پنجره (برای جلوگیری از هنگ کردن)
    if not pygame.display.get_init():
        running = False
        break

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # ۲. بررسی مجدد شرط خروج
    if not running:
        break

    # محاسبه زمان سپری شده
    elapsed_time = time.time() - start_time
    
    # اگر گل شده باشد، وارد حالت انتظار می‌شویم
    if goal_scored_timer > 0:
        # بررسی اینکه آیا زمان انتظار (۲ ثانیه) تمام شده است
        if time.time() - goal_scored_timer > 2:
            goal_scored_timer = 0  # پایان انتظار
            ball.reset()
            [p.reset_position() for p in all_field_players]
        else:
            # در حالت انتظار، فقط صفحه را آپدیت می‌کنیم و دکمه ضربدر چک می‌شود
            pygame.display.flip()
            clock.tick(FPS)
            continue  # از ادامه دستورات بازی در این فریم صرف‌نظر می‌کنیم

    # پایان بازی
    if elapsed_time >= GAME_DURATION:
        running = False
        
    # Draw everything
    draw_field()
    
    # --- Controller Calls ---
    # --- Controller Calls ---
    
    # محاسبه درصد مالکیت برای ارسال به کنترلرها
    total_possession = total_possession_time
    red_pct = int((red_possession_time / total_possession) * 100) if total_possession else 0
    blue_pct = int((blue_possession_time / total_possession) * 100) if total_possession else 0
    
    # تعیین مالک توپ
    ball_owner_id = ball.owner.player_id if ball.owner else None
    
    game_state_snapshot = {
        "ball": (ball.x, ball.y),
        "red1": (red_agent.x, red_agent.y),
        "red2": (red_agent2.x, red_agent2.y),
        "red3": (red_agent3.x, red_agent3.y),
        "blue1": (blue_agent.x, blue_agent.y),
        "blue2": (blue_agent2.x, blue_agent2.y),
        "blue3": (blue_agent3.x, blue_agent3.y),
        "score": score,
    
        "red_passes": passes_completed["red"],
        "blue_passes": passes_completed["blue"],
        "red_shots": shots_on_target["red"],
        "blue_shots": shots_on_target["blue"],
        "red_possession": red_pct,
        "blue_possession": blue_pct,

        "ball_owner": ball_owner_id
    }
    
    # فراخوانی کنترلرها
    red_action_dict = red_controller.get_red_actions(game_state_snapshot)
    blue_action_dict = blue_controller.get_blue_actions(game_state_snapshot)
    

    
    if red_action_dict:
        latest_actions["red"] = ", ".join([k for k, v in red_action_dict.items() if v and k != "time_sec"])
    if blue_action_dict:
        latest_actions["blue"] = ", ".join([k for k, v in blue_action_dict.items() if v and k != "time_sec"])
        
    if blue_action_dict:
        move_by_db_action(blue_agent, blue_action_dict, "blue1")
        handle_shoot_and_pass(blue_agent, blue_action_dict, "blue", blue_team, ball)
        move_by_db_action(blue_agent2, blue_action_dict, "blue2")
        handle_shoot_and_pass(blue_agent2, blue_action_dict, "blue", blue_team, ball)
        move_by_db_action(blue_agent3, blue_action_dict, "blue3")
        handle_shoot_and_pass(blue_agent3, blue_action_dict, "blue", blue_team, ball)
    if red_action_dict:
        move_by_db_action(red_agent, red_action_dict, "red1")
        handle_shoot_and_pass(red_agent, red_action_dict, "red", red_team, ball)
        move_by_db_action(red_agent2, red_action_dict, "red2")
        handle_shoot_and_pass(red_agent2, red_action_dict, "red", red_team, ball)
        move_by_db_action(red_agent3, red_action_dict, "red3")
        handle_shoot_and_pass(red_agent3, red_action_dict, "red", red_team, ball)
    # --- Stats Display ---
    minutes, seconds = int(elapsed_time) // 60, int(elapsed_time) % 60
    timer_text = font.render(f"Time: {minutes:02}:{seconds:02}", True, WHITE)
    shot_text = font.render(f"Shots On Target - Red: {shots_on_target['red']+score[1]}  Blue: {shots_on_target['blue']+score[0]}", True, WHITE)
    pass_text = font.render(f"Passes - Red: {passes_completed['red']}  Blue: {passes_completed['blue']}", True, WHITE)
    
    total_possession = total_possession_time
    red_pct = int((red_possession_time / total_possession) * 100) if total_possession else 0
    blue_pct = int((blue_possession_time / total_possession) * 100) if total_possession else 0
    
    poss_text = font.render(f"Possession - Red: {red_pct}%  Blue: {blue_pct}%", True, WHITE)
    for i, surf in enumerate([timer_text, shot_text, pass_text, poss_text]):
        screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, 40 + i*30))
        
    # --- Possession Update ---
    current_time_tick = pygame.time.get_ticks()
    delta_time = (current_time_tick - last_possession_update) / 1000
    last_possession_update = current_time_tick
    total_possession_time += delta_time  
    if ball.owner:
        if ball.owner.color == RED:
            red_possession_time += delta_time
        elif ball.owner.color == BLUE:
            blue_possession_time += delta_time
            
    # --- Goalkeeper & Physics ---
    red_keeper.move_toward_ball_y(ball, x_fixed=40)
    blue_keeper.move_toward_ball_y(ball, x_fixed=WIDTH - 40)
    
    ball.handle_possession(all_players)
    ball.update()
    
    # Boundaries
    if ball.x - ball.radius < 0: ball.x = ball.radius; ball.x_velocity *= -0.8
    if ball.x + ball.radius > WIDTH: ball.x = WIDTH - ball.radius; ball.x_velocity *= -0.8
    if ball.y - ball.radius < 0: ball.y = ball.radius; ball.y_velocity *= -0.8
    if ball.y + ball.radius > HEIGHT: ball.y = HEIGHT - ball.radius; ball.y_velocity *= -0.8
    
    check_goalkeeper_block(ball, red_keeper)
    check_goalkeeper_block(ball, blue_keeper)
    
    # --- Goal Check ---
    goal = check_goal(ball)
    if goal == "blue":
        if last_shot_by == "red": shots_on_target["red"] += 1
        score[0] += 1; last_shot_by = None
        # به جای sleep، تایمر را ست می‌کنیم
        goal_scored_timer = time.time() 
    elif goal == "red":
        if last_shot_by == "blue": shots_on_target["blue"] += 1
        score[1] += 1; last_shot_by = None
        # به جای sleep، تایمر را ست می‌کنیم
        goal_scored_timer = time.time()
        
    # Draw Agents & Ball
    for agent in all_players: agent.draw(screen)
    ball.draw(screen)
    
    # --- Save Loop ---
    now = time.time()
    if now - last_save_time >= 0.1:
        red_shot_flag = blue_shot_flag = 0
        last_save_time = now

    pygame.display.flip()
    clock.tick(FPS)

####################
# Game Over display (با حلقه برای جلوگیری از هنگ کردن)
####################
game_over_start = time.time()
waiting_exit = True
while waiting_exit:
    # بررسی خروج در صفحه پایانی
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            waiting_exit = False
            
    final_text = font.render("Match Over", True, WHITE)
    screen.blit(final_text, (WIDTH // 2 - final_text.get_width() // 2, HEIGHT // 2))
    pygame.display.flip()
    
    # بعد از ۳ ثانیه یا با بستن پنجره خارج می‌شود
    if time.time() - game_over_start > 3:
        waiting_exit = False
        
    clock.tick(FPS)

pygame.quit()

#############################
# ---- Save Results to CSV ---- #
#############################

# ۱. ساخت یک اسنپ‌شات نهایی از وضعیت بازی برای دسترسی به آمارها
final_game_state = {
    "ball": (ball.x, ball.y),
    "red1": (red_agent.x, red_agent.y),
    "red2": (red_agent2.x, red_agent2.y),
    "blue1": (blue_agent.x, blue_agent.y),
    "blue2": (blue_agent2.x, blue_agent2.y),
    "score": score,
    "red_passes": passes_completed["red"],
    "blue_passes": passes_completed["blue"],
    "red_shots": shots_on_target["red"],
    "blue_shots": shots_on_target["blue"],
    "red_possession": int((red_possession_time / total_possession_time) * 100) if total_possession_time else 0,
    "blue_possession": int((blue_possession_time / total_possession_time) * 100) if total_possession_time else 0
}

# ۲. محاسبه ریوارد نهایی تیم آبی
try:
    final_blue_reward = blue_controller.get_blue_reward(final_game_state)
except AttributeError:
    b_shots = final_game_state["blue_shots"]
    b_passes = final_game_state["blue_passes"]
    b_score = final_game_state["score"][0]
    r_score = final_game_state["score"][1]
    final_blue_reward = (b_passes * 1) + (b_shots * 3) + (b_score * 20) + (r_score * -10)

# ۳. دریافت مدت زمان و فریم بر ثانیه
# مدت زمان بازی (ثانیه) - از متغیر موجود در حلقه اصلی استفاده می‌کنیم
# اگر بازی تمام شده باشد، elapsed_time برابر با کل زمان بازی است
game_duration_sec = elapsed_time 

# دریافت میانگین FPS از آبجکت clock
# این دستور میانگین فریم‌ها را از آخرین بار فراخوانی tick برمی‌گرداند
current_fps = clock.get_fps()

# ۴. تعریف نام فایل و داده‌ها
csv_filename = "match_results.csv"
file_exists = os.path.isfile(csv_filename)

# هدرهای فایل CSV (با اضافه شدن Duration و FPS)
headers = [
    "Date", "Time", 
    "Red Score", "Red Shots", "Red Passes", "Red Possession %",
    "Blue Score", "Blue Shots", "Blue Passes", "Blue Possession %",
    "Blue Final Reward",
    "Duration (sec)", "FPS"
]

# داده‌های ردیف فعلی
from datetime import datetime
now = datetime.now()
row_data = [
    now.strftime("%Y-%m-%d"),
    now.strftime("%H:%M:%S"),
    score[1],                              # Red Score
    final_game_state["red_shots"],         # Red Shots
    final_game_state["red_passes"],        # Red Passes
    final_game_state["red_possession"],    # Red Possession
    score[0],                              # Blue Score
    final_game_state["blue_shots"],        # Blue Shots
    final_game_state["blue_passes"],       # Blue Passes
    final_game_state["blue_possession"],   # Blue Possession
    final_blue_reward,                     # Blue Reward
    f"{game_duration_sec:.2f}",            # Duration (با دو رقم اعشار)
    f"{current_fps:.2f}"                   # FPS (با دو رقم اعشار)
]

# ۵. نوشتن در فایل
try:
    with open(csv_filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # اگر فایل وجود نداشت، هدرها را بنویس
        if not file_exists:
            writer.writerow(headers)
            
        writer.writerow(row_data)
    print(f"Results saved to {csv_filename}")
except Exception as e:
    print(f"Error saving CSV: {e}")

#############################
# ---- End Save Results ---- #
#############################




sys.exit()


