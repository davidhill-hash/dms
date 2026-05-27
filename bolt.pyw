"""
Bolt — a cute little desktop robot that walks along your Windows taskbar.

He strolls back and forth on top of the taskbar, stays above every window,
chatters now and then, and naps on his own. Click him for a menu of tricks
(wave, dance, jump, joke, nap, wake) or to quit.

Run:  double-click this file, or  > pythonw bolt.pyw
Needs: Python 3.x on Windows (Tkinter is included with the standard installer).
On macOS/Linux it still runs, but the transparent background and exact
taskbar placement are Windows features and may differ.
"""

import math
import random
import tkinter as tk

# ---- Windows niceties (safe no-ops elsewhere) ------------------------------
try:
    import ctypes
    import ctypes.wintypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # crisp on high-DPI
except Exception:
    ctypes = None


def taskbar_top(screen_h):
    """Y coordinate of the top edge of the Windows taskbar (work-area bottom)."""
    try:
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
        if 0 < rect.bottom <= screen_h:
            return rect.bottom
    except Exception:
        pass
    return screen_h - 48  # sensible fallback


# ---- palette ---------------------------------------------------------------
TRANS   = "#010101"   # key color -> fully transparent + click-through on Windows
BODY    = "#cfd8e3"
BODY_HI = "#eef3f9"
EDGE    = "#6c7889"
LIMB    = "#9aa7b8"
DARK    = "#3a4250"
SCREEN  = "#11151f"
EYE     = "#4cc2ff"
ACCENT  = "#ffd166"
WHITE   = "#ffffff"
INK     = "#1b2030"

W, H = 170, 210          # window / canvas size
CX   = W // 2            # robot center x
FPS_MS = 33              # ~30 fps

THOUGHTS = [
    "Just stretching my legs...", "Beep boop. ", "Lovely day up here!",
    "Patrolling... all clear.", "Anyone need a hand?", "Step, step, step...",
]
JOKES = [
    "Why was the robot tired?\nIt had a hard drive!",
    "I only speak binary.\n01001000 01101001!",
    "I never byte off more\nthan I can chew.",
    "I'd tell you a UDP joke,\nbut you might not get it.",
    "My favorite music?\nHeavy metal!",
]


class Bolt:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-transparentcolor", TRANS)
        except tk.TclError:
            pass
        self.root.config(bg=TRANS)

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.bar_top = taskbar_top(self.screen_h)
        self.win_y = self.bar_top - H + 4  # feet rest just on the taskbar

        self.canvas = tk.Canvas(self.root, width=W, height=H, bg=TRANS,
                                highlightthickness=0, bd=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)

        self._build_menu()

        # ---- state ----
        self.x = float(self.screen_w * 0.4)
        self.dir = 1
        self.speed = 1.3
        self.mode = "walk"            # walk | sleep | pause | trick:wave|dance|jump
        self.t = 0
        self.jump_start = 0
        self.blink_until = 0
        self.bubble = None            # (text, until_frame)
        self.resume_id = None

        self.place()
        self.root.after(900, lambda: self.say("Hi, I'm Bolt! Click me.", 3000))
        self.loop()

    # ---------------------------------------------------------------- menu
    def _build_menu(self):
        m = tk.Menu(self.root, tearoff=0, bg="#1f2533", fg="#e7ecf3",
                    activebackground="#33405a", activeforeground=WHITE,
                    font=("Segoe UI", 10), bd=0)
        m.add_command(label="  Wave hello", command=lambda: self.wave())
        m.add_command(label="  Bust a move", command=lambda: self.dance())
        m.add_command(label="  Jump!", command=lambda: self.jump())
        m.add_command(label="  Tell a joke", command=self.joke)
        m.add_separator()
        m.add_command(label="  Take a nap", command=self.sleep)
        m.add_command(label="  Wake up", command=self.wake)
        m.add_separator()
        m.add_command(label="  Quit Bolt", command=self.root.destroy)
        self.menu = m

    # ------------------------------------------------------------ placement
    def place(self):
        self.root.geometry(f"{W}x{H}+{int(self.x)}+{int(self.win_y)}")

    # ------------------------------------------------------------- helpers
    def set_mode(self, m):
        self.mode = m

    def say(self, text, ms):
        self.bubble = (text, self.t + ms // FPS_MS)

    def trick(self, cls, ms, msg=None):
        prev = "sleep" if self.mode == "sleep" else "walk"
        if cls == "jump":
            self.jump_start = self.t
        self.set_mode("trick:" + cls)
        if msg:
            self.say(msg, ms)
        self.root.after(ms, lambda: self.set_mode(prev))

    # actions
    def wave(self):  self.trick("wave", 1700, "Hello there!")
    def dance(self): self.trick("dance", 2600, "woo!")
    def jump(self):  self.trick("jump", 650, "Wheee!")

    def joke(self):
        self.wake()
        self.set_mode("pause")
        self.say(random.choice(JOKES), 4000)
        self._schedule_resume(4200)

    def sleep(self):
        self.set_mode("sleep")
        self.say("Powering down...", 1500)

    def wake(self):
        if self.mode != "walk":
            self.set_mode("walk")
            self.say("Good morning!", 1500)

    def _schedule_resume(self, ms):
        if self.resume_id:
            self.root.after_cancel(self.resume_id)
        self.resume_id = self.root.after(ms, self._resume)

    def _resume(self):
        self.resume_id = None
        if self.mode == "pause":
            self.set_mode("walk")

    def on_click(self, e):
        if self.mode == "sleep":
            self.set_mode("walk")
            self.say("*yawn*... who clicked me?", 2000)
            return
        self.set_mode("pause")
        self._schedule_resume(4000)
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()

    # ------------------------------------------------------------- drawing
    def rrect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2,
               x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def limb(self, px, py, length, ang_deg, width, color):
        a = math.radians(ang_deg)
        ex = px + length * math.sin(a)
        ey = py + length * math.cos(a)
        self.canvas.create_line(px, py, ex, ey, width=width, fill=color,
                                capstyle="round")
        return ex, ey

    def draw(self):
        c = self.canvas
        c.delete("all")

        m = self.mode
        ph = math.sin(self.t * 0.35)        # walk oscillator
        yoff = 0.0
        wig = 0.0
        legL = legR = 0.0
        armL = armR = 0.0
        eyes_open = True

        if m == "walk":
            legL = 17 * ph; legR = -17 * ph
            armL = -14 * ph; armR = 14 * ph
            yoff = abs(ph) * 2
        elif m == "sleep":
            yoff = math.sin(self.t * 0.08) * 1.5
            eyes_open = False
        elif m.startswith("trick:"):
            sub = m.split(":")[1]
            if sub == "wave":
                armR = 142 + 22 * math.sin(self.t * 0.8)
                armL = -8
            elif sub == "dance":
                d = math.sin(self.t * 0.6)
                armL = -125 + 35 * d
                armR = 125 + 35 * d
                wig = d * 5
                yoff = abs(d) * 5
                legL = 8 * d; legR = -8 * d
            elif sub == "jump":
                frames = max(1, 650 // FPS_MS)
                prog = min(1.0, (self.t - self.jump_start) / frames)
                yoff = 46 * math.sin(math.pi * prog)
                armL = -150; armR = 150
                legL = 10; legR = -10

        # blink
        if self.t > self.blink_until and random.random() < 0.02:
            self.blink_until = self.t + 4
        blinking = self.t < self.blink_until and eyes_open

        cx = CX + wig
        base = -yoff      # negative y = upward

        # geometry (y grows downward; 'base' lifts everything when jumping/bobbing)
        feet_y = H - 4 + base
        hip_y  = feet_y - 18
        body_b = hip_y
        body_t = body_b - 36
        head_b = body_t + 3
        head_t = head_b - 30

        # legs (behind body)
        lx = self.limb(cx - 8, hip_y, 18, legL, 6, EDGE)
        rx = self.limb(cx + 8, hip_y, 18, legR, 6, EDGE)
        for fx, fy in (lx, rx):
            c.create_oval(fx - 6, fy - 3, fx + 5, fy + 3, fill=DARK, outline="")

        # arms (behind body)
        self.limb(cx - 19, body_t + 6, 17, armL, 5, LIMB)
        self.limb(cx + 19, body_t + 6, 17, armR, 5, LIMB)

        # body
        self.rrect(cx - 20, body_t, cx + 20, body_b, 10,
                   fill=BODY, outline=EDGE, width=1)
        self.rrect(cx - 20, body_t, cx + 20, body_t + 14, 10,
                   fill=BODY_HI, outline="")
        # little chest light
        c.create_oval(cx - 3, body_t + 20, cx + 3, body_t + 26,
                      fill=ACCENT, outline="")

        # head
        self.rrect(cx - 17, head_t, cx + 17, head_b, 9,
                   fill=BODY, outline=EDGE, width=1)
        # face screen
        self.rrect(cx - 13, head_t + 6, cx + 13, head_b - 4, 6,
                   fill=SCREEN, outline="")

        # antenna
        c.create_line(cx, head_t, cx, head_t - 11, fill=EDGE, width=2)
        ac = ACCENT if m != "sleep" else "#6b6440"
        c.create_oval(cx - 4, head_t - 17, cx + 4, head_t - 9,
                      fill=ac, outline="")

        # eyes + mouth
        ey = head_t + 13
        for ex in (cx - 7, cx + 7):
            if blinking or not eyes_open:
                c.create_line(ex - 3, ey, ex + 3, ey, fill=EYE if eyes_open else EDGE,
                              width=2, capstyle="round")
            else:
                c.create_oval(ex - 3, ey - 3, ex + 3, ey + 3, fill=EYE, outline="")
        if eyes_open:
            c.create_line(cx - 5, head_b - 8, cx + 5, head_b - 8,
                          fill=EYE, width=2, capstyle="round")

        # zzz while sleeping
        if m == "sleep":
            zp = (self.t % 60) / 60.0
            for i in range(3):
                p = (zp + i / 3.0) % 1.0
                zx = cx + 16 + p * 14
                zy = head_t - 2 - p * 28
                size = 9 + int(p * 5)
                c.create_text(zx, zy, text="z", fill=EYE,
                              font=("Segoe UI", size, "bold"))

        # speech bubble
        if self.bubble:
            text, until = self.bubble
            if self.t < until:
                self.draw_bubble(cx, head_t, text)
            else:
                self.bubble = None

    def draw_bubble(self, cx, head_t, text):
        c = self.canvas
        lines = text.split("\n")
        tw = max(len(s) for s in lines) * 6.2 + 18
        th = len(lines) * 15 + 12
        bx = min(W - tw - 4, max(4, cx - tw / 2))
        by = max(4, head_t - 22 - th)
        self.rrect(bx, by, bx + tw, by + th, 8, fill=WHITE, outline="")
        # little tail
        c.create_polygon(cx - 5, by + th, cx + 5, by + th, cx, by + th + 7,
                         fill=WHITE, outline="")
        c.create_text(bx + tw / 2, by + th / 2, text=text, fill=INK,
                      font=("Segoe UI", 9), justify="center")

    # ---------------------------------------------------------------- loop
    def loop(self):
        self.t += 1

        if self.mode == "walk":
            self.x += self.speed * self.dir
            left, right = 8, self.screen_w - W - 8
            if self.x >= right:
                self.x = right; self.dir = -1; self._maybe_chatter()
            elif self.x <= left:
                self.x = left; self.dir = 1; self._maybe_chatter()
            self.place()
            if self.t % 150 == 0 and random.random() < 0.4:
                self._maybe_chatter()

        self.draw()
        self.root.after(FPS_MS, self.loop)

    def _maybe_chatter(self):
        if self.mode == "walk" and not self.bubble:
            self.say(random.choice(THOUGHTS), 1800)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    Bolt().run()
