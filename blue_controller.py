# blue_controller.py
import pygame

######################
# ---- Reward ----   #
#####################
def get_blue_reward(game_state):
    """
    محاسبه امتیاز (Reward) اختصاصی برای تیم آبی.
    
    فرمول:
    پاس = 1 امتیاز
    شوت در چارچوب = 3 امتیاز
    گل زده = 20 امتیاز
    گل خورده = -10 امتیاز
    """
    shots = game_state.get("blue_shots", 0)
    passes = game_state.get("blue_passes", 0)
    current_score = game_state.get("score", [0, 0])
    blue_goals_scored = current_score[0]
    blue_goals_conceded = current_score[1]

    reward_passes = passes * 1
    reward_shots = shots * 3
    reward_goals = blue_goals_scored * 20
    reward_conceded = blue_goals_conceded * (-10)

    return reward_passes + reward_shots + reward_goals + reward_conceded


def get_blue_actions(game_state):
    """
    کنترل دستی تیم آبی (۳ بازیکن) با صفحه‌کلید.
    
    بازیکن ۱ : WASD (حرکت)         Z (شوت)  X (پاس به ۲)  C (پاس به ۳)
    بازیکن ۲ : T بالا، F چپ، G پائین، H راست  V (شوت)  B (پاس به ۱)  N (پاس به ۳)
    بازیکن ۳ : I بالا، J چپ، K پائین، L راست   M (شوت)  , (پاس به ۱)  . (پاس به ۲)
    """
    keys = pygame.key.get_pressed()

    actions = {
        # blue1
        "blue1_up": 0, "blue1_down": 0, "blue1_left": 0, "blue1_right": 0,
        "blue1_shoot": 0, "blue1_pass_2": 0, "blue1_pass_3": 0,
        # blue2
        "blue2_up": 0, "blue2_down": 0, "blue2_left": 0, "blue2_right": 0,
        "blue2_shoot": 0, "blue2_pass_1": 0, "blue2_pass_3": 0,
        # blue3
        "blue3_up": 0, "blue3_down": 0, "blue3_left": 0, "blue3_right": 0,
        "blue3_shoot": 0, "blue3_pass_1": 0, "blue3_pass_2": 0
    }

    # ---------- blue1 ----------
    if keys[pygame.K_w]: actions["blue1_up"] = 1
    if keys[pygame.K_s]: actions["blue1_down"] = 1
    if keys[pygame.K_a]: actions["blue1_left"] = 1
    if keys[pygame.K_d]: actions["blue1_right"] = 1

    if keys[pygame.K_z]: actions["blue1_shoot"] = 1
    if keys[pygame.K_x]: actions["blue1_pass_2"] = 1
    if keys[pygame.K_c]: actions["blue1_pass_3"] = 1

    # ---------- blue2 ----------
    if keys[pygame.K_t]: actions["blue2_up"] = 1
    if keys[pygame.K_g]: actions["blue2_down"] = 1
    if keys[pygame.K_f]: actions["blue2_left"] = 1
    if keys[pygame.K_h]: actions["blue2_right"] = 1

    if keys[pygame.K_v]: actions["blue2_shoot"] = 1
    if keys[pygame.K_b]: actions["blue2_pass_1"] = 1
    if keys[pygame.K_n]: actions["blue2_pass_3"] = 1

    # ---------- blue3 ----------
    if keys[pygame.K_i]: actions["blue3_up"] = 1
    if keys[pygame.K_k]: actions["blue3_down"] = 1
    if keys[pygame.K_j]: actions["blue3_left"] = 1
    if keys[pygame.K_l]: actions["blue3_right"] = 1

    if keys[pygame.K_m]: actions["blue3_shoot"] = 1
    if keys[pygame.K_COMMA]: actions["blue3_pass_1"] = 1
    if keys[pygame.K_PERIOD]: actions["blue3_pass_2"] = 1

    return actions