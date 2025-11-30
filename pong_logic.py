import math
import random

FIELD_WIDTH = 800
FIELD_HEIGHT = 400
PADDLE_WIDTH = 10
PADDLE_HEIGHT = 80
BALL_SIZE = 12

BALL_SPEED = 320
PADDLE_SPEED = 320

def limit(v, a, b):
    return max(a, min(b, v))

class GameState:
    def __init__(self):
        self.width = FIELD_WIDTH
        self.height = FIELD_HEIGHT
        self.paddle_h = PADDLE_HEIGHT
        self.ball_size = BALL_SIZE

        self.paddles = [self.height / 2, self.height / 2]
        self.paddle_x = [10, self.width - 10 - PADDLE_WIDTH]

        self.ball_x = self.width / 2
        self.ball_y = self.height / 2
        self.ball_vx = 0.0
        self.ball_vy = 0.0

        self.scores = [0, 0]
        self.playing = False

        self.win_score = 10
        self.winner = None

    def velocity_ball(self, dt=1):
        self.ball_x = self.width / 2
        self.ball_y = self.height / 2
        speed = BALL_SPEED
        angle = random.uniform(-0.5, 0.5) * math.pi / 6 # наклон траектории
        self.ball_vx = speed * dt
        self.ball_vy = speed * math.sin(angle)

    def to_dict(self):
        return {
            'width': self.width,
            'height': self.height,
            'paddles': self.paddles,
            'paddle_x': self.paddle_x,
            'ball': {'x': self.ball_x, 'y': self.ball_y},
            'scores': self.scores,
            'playing': self.playing,
            'paddle_h': self.paddle_h,
            'win_score': self.win_score,
            'winner': self.winner
        }

    def update(self, dt, inputs):
        for i in (0, 1):
            d = inputs.get(i, "stop")
            if d == "up":
                self.paddles[i] -= PADDLE_SPEED * dt
            elif d == "down":
                self.paddles[i] += PADDLE_SPEED * dt

            half = self.paddle_h / 2
            self.paddles[i] = limit(self.paddles[i], half, self.height - half)

        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt

        half_b = self.ball_size / 2

        if self.ball_y - half_b < 0:
            self.ball_y = half_b
            self.ball_vy = -self.ball_vy
        if self.ball_y + half_b > self.height:
            self.ball_y = self.height - half_b
            self.ball_vy = -self.ball_vy

        px = self.paddle_x[0]
        py = self.paddles[0]
        if self.ball_x - half_b <= px + PADDLE_WIDTH:
            if abs(self.ball_y - py) <= self.paddle_h/2:
                self.ball_x = px + PADDLE_WIDTH + half_b
                self.ball_vx = abs(self.ball_vx)
            else:
                self.scores[1] += 1
                self.velocity_ball(1)

        px = self.paddle_x[1]
        py = self.paddles[1]
        if self.ball_x + half_b >= px:
            if abs(self.ball_y - py) <= self.paddle_h/2:
                self.ball_x = px - half_b
                self.ball_vx = -abs(self.ball_vx)
            else:
                self.scores[0] += 1
                self.velocity_ball(-1)

        if self.scores[0] >= self.win_score:
            self.playing = False
            self.winner = 0
        elif self.scores[1] >= self.win_score:
            self.playing = False
            self.winner = 1
