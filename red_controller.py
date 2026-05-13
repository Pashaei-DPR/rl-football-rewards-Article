# red_controller.py
import math
import random

def get_red_actions(game_state):
    """
    کنترلر هوشمند برای تیم قرمز (۳ بازیکن زمین + دروازه‌بان).
    استراتژی: پرسینگ هوشمند، پشتیبانی از مالک توپ و شوت منطقه‌ای.
    """
    # استخراج مختصات از game_state
    ball_x, ball_y = game_state.get("ball", (400, 250))
    red1_pos = game_state.get("red1", (150, 250))
    red2_pos = game_state.get("red2", (150, 170))
    red3_pos = game_state.get("red3", (150, 330))

    # ثابت‌های زمین
    WIDTH, HEIGHT = 800, 500
    GOAL_Y = HEIGHT // 2
    GOAL_WIDTH = 10

    # دیکشنری اکشن (همه صفر)
    actions = {
        # بازیکن ۱
        "red1_up": 0, "red1_down": 0, "red1_left": 0, "red1_right": 0,
        "red1_shoot": 0, "red1_pass_2": 0, "red1_pass_3": 0,
        # بازیکن ۲
        "red2_up": 0, "red2_down": 0, "red2_left": 0, "red2_right": 0,
        "red2_shoot": 0, "red2_pass_1": 0, "red2_pass_3": 0,
        # بازیکن ۳
        "red3_up": 0, "red3_down": 0, "red3_left": 0, "red3_right": 0,
        "red3_shoot": 0, "red3_pass_1": 0, "red3_pass_2": 0
    }

    # --- توابع کمکی ---
    def get_distance(p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def move_towards(agent_pos, target_pos, action_prefix):
        """حرکت عامل به سمت هدف (فقط یک محور فعال می‌شود)"""
        dx = target_pos[0] - agent_pos[0]
        dy = target_pos[1] - agent_pos[1]
        dist = math.hypot(dx, dy)

        if dist > 5:
            # جهت‌های ممکن
            if abs(dx) > abs(dy):
                actions[f"{action_prefix}_right"] = 1 if dx > 0 else 0
                actions[f"{action_prefix}_left"] = 1 if dx < 0 else 0
            else:
                actions[f"{action_prefix}_down"] = 1 if dy > 0 else 0
                actions[f"{action_prefix}_up"] = 1 if dy < 0 else 0

    def who_has_ball(threshold=20):
        """برمی‌گرداند کدام بازیکن قرمز توپ را در اختیار دارد (None اگر هیچ‌کس)"""
        dist1 = get_distance(red1_pos, (ball_x, ball_y))
        dist2 = get_distance(red2_pos, (ball_x, ball_y))
        dist3 = get_distance(red3_pos, (ball_x, ball_y))
        if dist1 < threshold:
            return "red1"
        if dist2 < threshold:
            return "red2"
        if dist3 < threshold:
            return "red3"
        return None

    ball_owner = who_has_ball()

    # --- بازیکن ۱ (مهاجم اصلی) ---
    if ball_owner == "red1":
        # مالک توپ: شوت در منطقه خطر، وگرنه پیشروی یا پاس
        if ball_x > WIDTH * 0.65:
            angle_to_goal = abs(math.atan2(GOAL_Y - ball_y, WIDTH - ball_x))
            if angle_to_goal < 0.78:   # زاویه خوب
                actions["red1_shoot"] = 1
            else:
                # پاس به بهترین گزینه (دورتر از خودش و نزدیک دروازه)
                best = "red2" if random.random() < 0.5 else "red3"
                actions[f"red1_pass_{best[-1]}"] = 1
        else:
            # پیشروی به سمت دروازه
            move_towards(red1_pos, (WIDTH - 50, GOAL_Y), "red1")
            if random.random() < 0.03:
                # پاس ناگهانی
                target = "red2" if random.random() < 0.5 else "red3"
                actions[f"red1_pass_{target[-1]}"] = 1
    else:
        # بدون توپ: اگر هم‌تیمی دارد، فضاسازی کن، وگرنه پرس یا برگشت
        if ball_owner in ("red2", "red3"):
            # هم‌تیمی مالک است → به منطقه حمله حرکت کن
            move_towards(red1_pos, (WIDTH - 120, GOAL_Y + random.randint(-60, 60)), "red1")
        else:
            # توپ آزاد یا حریف → پرس هوشمند
            if ball_x > red1_pos[0] - 60:
                move_towards(red1_pos, (ball_x, ball_y), "red1")
            else:
                # برگشت دفاعی
                move_towards(red1_pos, (WIDTH * 0.35, GOAL_Y), "red1")

    # --- بازیکن ۲ (هافبک میانی / همه‌کاره) ---
    if ball_owner == "red2":
        if ball_x > WIDTH * 0.75:
            # شوت با احتمال کمتر
            actions["red2_shoot"] = 1 if random.random() < 0.7 else 0
            if actions["red2_shoot"] == 0:
                # پاس به مهاجم
                actions["red2_pass_1"] = 1
        else:
            # پیشروی و پاس به بازیکنی که جلوتر است
            if red1_pos[0] > red2_pos[0] + 70:
                actions["red2_pass_1"] = 1
            elif red3_pos[0] > red2_pos[0] + 60:
                actions["red2_pass_3"] = 1
            else:
                move_towards(red2_pos, (WIDTH - 200, GOAL_Y), "red2")
                if random.random() < 0.04:
                    actions["red2_pass_1"] = 1
    else:
        if ball_owner in ("red1", "red3"):
            # پشتیبانی از صاحب توپ
            if ball_owner == "red1":
                support_x = max(red1_pos[0] - 100, 50)
                support_y = red1_pos[1] + random.randint(-40, 40)
            else:  # red3
                support_x = max(red3_pos[0] - 100, 50)
                support_y = red3_pos[1] + random.randint(-40, 40)
            move_towards(red2_pos, (support_x, support_y), "red2")
        else:
            # توپ آزاد یا با حریف: پرس در میانه زمین
            target_x = min(ball_x, WIDTH * 0.7)
            move_towards(red2_pos, (target_x, ball_y), "red2")

    # --- بازیکن ۳ (وینگر / هافبک چپ) ---
    if ball_owner == "red3":
        if ball_x > WIDTH * 0.7:
            angle = abs(math.atan2(GOAL_Y - ball_y, WIDTH - ball_x))
            if angle < 0.7:
                actions["red3_shoot"] = 1
            else:
                actions["red3_pass_1"] = 1  # پاس به مهاجم
        else:
            # پیشروی از کناره‌ها
            # تمایل به ماندن در عرض بالاتر (y کوچکتر)
            target_y = max(50, min(HEIGHT - 50, GOAL_Y - 80))
            move_towards(red3_pos, (WIDTH - 150, target_y), "red3")
            if random.random() < 0.03:
                actions["red3_pass_1"] = 1
    else:
        if ball_owner in ("red1", "red2"):
            # باز شدن در فضای خالی سمت چپ
            if ball_owner == "red1":
                flank_y = red1_pos[1] - 80
            else:
                flank_y = red2_pos[1] - 100
            flank_y = max(60, min(HEIGHT - 60, flank_y))
            flank_x = max(ball_x - 80, 80)
            move_towards(red3_pos, (flank_x, flank_y), "red3")
        else:
            # پرس از سمت چپ
            if ball_y < HEIGHT // 2 - 50:  # توپ در نیمه بالایی
                move_towards(red3_pos, (ball_x, ball_y), "red3")
            else:
                # برگشت به منطقه دفاعی
                move_towards(red3_pos, (WIDTH * 0.35, GOAL_Y - 100), "red3")

    return actions