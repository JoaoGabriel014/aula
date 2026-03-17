import random
import threading
import tkinter as tk
from pathlib import Path

try:
    import winsound
except ImportError:
    winsound = None

CELL = 18
COLS = 10
ROWS = 20
BOARD_WIDTH = COLS * CELL
BOARD_HEIGHT = ROWS * CELL
PREVIEW_SIZE = 4 * CELL

BASE_DELAY = 720
MIN_DELAY = 120
LEVEL_LINES = 8

APP_BG = "#08111f"
PANEL_BG = "#101a2e"
PANEL_BORDER = "#22314d"
BOARD_BG = "#0b1528"
GRID_COLOR = "#182742"
TEXT_MAIN = "#f4f7fb"
TEXT_MUTED = "#98a6c0"
ACCENT = "#5eead4"
WARNING = "#fb7185"
JUMPSCARE_BG = "#120202"
JUMPSCARE_FLASH = "#f8fafc"

SHAPES = {
    "I": [[1, 1, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "S": [[0, 1, 1], [1, 1, 0]],
    "T": [[0, 1, 0], [1, 1, 1]],
    "Z": [[1, 1, 0], [0, 1, 1]],
}

COLORS = {
    "I": "#38bdf8",
    "J": "#4f46e5",
    "L": "#f97316",
    "O": "#facc15",
    "S": "#22c55e",
    "T": "#a855f7",
    "Z": "#ef4444",
}


def rotate(shape):
    return [list(row) for row in zip(*shape[::-1])]


def tint(color, factor):
    color = color.lstrip("#")
    rgb = [int(color[i : i + 2], 16) for i in (0, 2, 4)]
    if factor >= 1:
        mixed = [min(255, int(value + (255 - value) * (factor - 1))) for value in rgb]
    else:
        mixed = [max(0, int(value * factor)) for value in rgb]
    return "#" + "".join(f"{value:02x}" for value in mixed)


class Piece:
    def __init__(self, kind=None):
        self.kind = kind or random.choice(list(SHAPES))
        self.shape = [row[:] for row in SHAPES[self.kind]]
        self.color = COLORS[self.kind]
        self.x = COLS // 2 - len(self.shape[0]) // 2
        self.y = 0

    def cells(self, x=None, y=None, shape=None):
        x = self.x if x is None else x
        y = self.y if y is None else y
        shape = self.shape if shape is None else shape
        for row_index, row in enumerate(shape):
            for col_index, value in enumerate(row):
                if value:
                    yield x + col_index, y + row_index

    def collides(self, board, shape=None, x=None, y=None):
        for board_x, board_y in self.cells(x=x, y=y, shape=shape):
            if board_x < 0 or board_x >= COLS or board_y < 0 or board_y >= ROWS:
                return True
            if board[board_y][board_x] is not None:
                return True
        return False

    def move(self, dx, dy, board):
        new_x = self.x + dx
        new_y = self.y + dy
        if self.collides(board, x=new_x, y=new_y):
            return False
        self.x = new_x
        self.y = new_y
        return True

    def rotate(self, board):
        rotated = rotate(self.shape)
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)):
            if not self.collides(board, shape=rotated, x=self.x + dx, y=self.y + dy):
                self.shape = rotated
                self.x += dx
                self.y += dy
                return True
        return False

    def imprint(self, board):
        for board_x, board_y in self.cells():
            board[board_y][board_x] = self.color


class TetrisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tetris")
        self.root.configure(bg=APP_BG)
        self.root.resizable(False, False)

        self.record_path = Path(__file__).with_name("record.txt")
        self.record = self.load_record()
        self.after_id = None
        self.jumpscare_after_id = None
        self.jumpscare_used = False
        self.jumpscare_active = False
        self.jumpscare_bg = JUMPSCARE_BG
        self.jumpscare_fg = TEXT_MAIN
        self.jumpscare_origin = None

        self.score_var = tk.StringVar()
        self.lines_var = tk.StringVar()
        self.level_var = tk.StringVar()
        self.speed_var = tk.StringVar()
        self.record_var = tk.StringVar()
        self.status_var = tk.StringVar()

        self._build_layout()
        self.restart(initial=True)

        self.root.bind("<Key>", self.key_pressed)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_layout(self):
        outer = tk.Frame(self.root, bg=APP_BG, padx=10, pady=10)
        outer.pack()

        header = tk.Frame(outer, bg=APP_BG)
        header.pack(fill="x", pady=(0, 6))

        tk.Label(
            header,
            text="TETRIS",
            bg=APP_BG,
            fg=TEXT_MAIN,
            font=("Bahnschrift SemiBold", 15),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Niveis progressivos",
            bg=APP_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(4, 0))

        content = tk.Frame(outer, bg=APP_BG)
        content.pack()

        board_card = tk.Frame(
            content,
            bg=PANEL_BG,
            highlightthickness=1,
            highlightbackground=PANEL_BORDER,
            padx=6,
            pady=6,
        )
        board_card.grid(row=0, column=0, padx=(0, 10))

        self.board_canvas = tk.Canvas(
            board_card,
            width=BOARD_WIDTH,
            height=BOARD_HEIGHT,
            bg=BOARD_BG,
            highlightthickness=0,
        )
        self.board_canvas.pack()

        sidebar = tk.Frame(
            content,
            bg=PANEL_BG,
            width=185,
            highlightthickness=1,
            highlightbackground=PANEL_BORDER,
            padx=10,
            pady=10,
        )
        sidebar.grid(row=0, column=1, sticky="ns")
        sidebar.grid_propagate(False)

        self._create_stat_card(sidebar, "Pontuacao", self.score_var).pack(fill="x", pady=(0, 8))
        self._create_stat_card(sidebar, "Linhas", self.lines_var).pack(fill="x", pady=(0, 8))
        self._create_stat_card(sidebar, "Nivel", self.level_var).pack(fill="x", pady=(0, 8))
        self._create_stat_card(sidebar, "Velocidade", self.speed_var).pack(fill="x", pady=(0, 10))

        next_frame = tk.Frame(sidebar, bg="#0d1628", padx=8, pady=8)
        next_frame.pack(fill="x", pady=(0, 10))
        tk.Label(
            next_frame,
            text="Proxima peca",
            bg="#0d1628",
            fg=TEXT_MAIN,
            font=("Segoe UI Semibold", 9),
        ).pack(anchor="w")
        self.next_canvas = tk.Canvas(
            next_frame,
            width=PREVIEW_SIZE,
            height=PREVIEW_SIZE,
            bg="#09101d",
            highlightthickness=0,
        )
        self.next_canvas.pack(pady=(6, 0))

        self.status_label = tk.Label(
            sidebar,
            textvariable=self.status_var,
            bg=PANEL_BG,
            fg=ACCENT,
            font=("Segoe UI Semibold", 9),
        )
        self.status_label.pack(anchor="w", pady=(0, 10))

        controls = tk.Frame(sidebar, bg="#0d1628", padx=8, pady=8)
        controls.pack(fill="x", pady=(0, 10))
        tk.Label(
            controls,
            text="Controles",
            bg="#0d1628",
            fg=TEXT_MAIN,
            font=("Segoe UI Semibold", 9),
        ).pack(anchor="w")
        control_lines = [
            "Setas: mover",
            "Cima: girar",
            "Espaco: cair",
            "P: pausar",
            "R: reiniciar",
        ]
        for text in control_lines:
            tk.Label(
                controls,
                text=text,
                bg="#0d1628",
                fg=TEXT_MUTED,
                font=("Segoe UI", 7),
            ).pack(anchor="w", pady=1)

        actions = tk.Frame(sidebar, bg=PANEL_BG)
        actions.pack(fill="x")

        self.pause_btn = tk.Button(
            actions,
            text="Pausar",
            command=self.toggle_pause,
            bg=ACCENT,
            fg="#03111d",
            activebackground=tint(ACCENT, 0.9),
            activeforeground="#03111d",
            font=("Segoe UI Semibold", 8),
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
        )
        self.pause_btn.pack(fill="x", pady=(0, 6))

        tk.Button(
            actions,
            text="Novo jogo",
            command=self.restart,
            bg="#17243b",
            fg=TEXT_MAIN,
            activebackground="#22314d",
            activeforeground=TEXT_MAIN,
            font=("Segoe UI Semibold", 8),
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
        ).pack(fill="x")

        record_box = tk.Frame(sidebar, bg=PANEL_BG)
        record_box.pack(fill="x", pady=(10, 0))
        tk.Label(
            record_box,
            text="Recorde",
            bg=PANEL_BG,
            fg="#fcd34d",
            font=("Segoe UI Semibold", 9),
        ).pack(anchor="w")
        tk.Label(
            record_box,
            textvariable=self.record_var,
            bg=PANEL_BG,
            fg=TEXT_MAIN,
            font=("Bahnschrift SemiBold", 14),
        ).pack(anchor="w", pady=(2, 0))

    def _create_stat_card(self, parent, title, variable):
        card = tk.Frame(parent, bg="#0d1628", padx=8, pady=8)
        tk.Label(
            card,
            text=title,
            bg="#0d1628",
            fg=TEXT_MUTED,
            font=("Segoe UI", 7),
        ).pack(anchor="w")
        tk.Label(
            card,
            textvariable=variable,
            bg="#0d1628",
            fg=TEXT_MAIN,
            font=("Bahnschrift SemiBold", 13),
        ).pack(anchor="w", pady=(2, 0))
        return card

    def load_record(self):
        try:
            return int(self.record_path.read_text(encoding="utf-8").strip())
        except (FileNotFoundError, ValueError):
            return 0

    def save_record(self):
        if self.score > self.record:
            self.record = self.score
            self.record_path.write_text(str(self.record), encoding="utf-8")

    def restart(self, initial=False):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.jumpscare_after_id is not None:
            self.root.after_cancel(self.jumpscare_after_id)
            self.jumpscare_after_id = None

        self.board = [[None] * COLS for _ in range(ROWS)]
        self.piece = Piece()
        self.next_piece = Piece()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.drop_delay = BASE_DELAY
        self.gameover = False
        self.paused = False
        self.jumpscare_used = False
        self.jumpscare_active = False
        self.jumpscare_bg = JUMPSCARE_BG
        self.jumpscare_fg = TEXT_MAIN
        self.jumpscare_origin = None
        self.pause_btn.configure(text="Pausar")

        self._update_progress()
        self._refresh_ui()
        self._schedule_tick()

        if not initial:
            self.board_canvas.focus_set()

    def close(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        if self.jumpscare_after_id is not None:
            self.root.after_cancel(self.jumpscare_after_id)
        self.root.destroy()

    def _schedule_tick(self):
        self.after_id = self.root.after(self.drop_delay, self._tick)

    def _tick(self):
        self.after_id = None
        if not self.paused and not self.gameover:
            if not self.piece.move(0, 1, self.board):
                self.lock_piece()

        self._refresh_ui()

        if not self.gameover:
            self._schedule_tick()

    def key_pressed(self, event):
        key = event.keysym.lower()

        if key == "r":
            self.restart()
            return
        if key in {"p", "escape"}:
            self.toggle_pause()
            return
        if self.gameover or self.paused or self.jumpscare_active:
            return

        moved = False
        if key in {"left", "a"}:
            moved = self.piece.move(-1, 0, self.board)
        elif key in {"right", "d"}:
            moved = self.piece.move(1, 0, self.board)
        elif key in {"down", "s"}:
            moved = self.piece.move(0, 1, self.board)
            if moved:
                self.score += 1
            else:
                self.lock_piece()
        elif key in {"up", "w", "x"}:
            moved = self.piece.rotate(self.board)
        elif key == "space":
            drop_distance = 0
            while self.piece.move(0, 1, self.board):
                drop_distance += 1
            self.score += drop_distance * 2
            self.lock_piece()
            moved = True

        if moved:
            self._refresh_ui()

    def toggle_pause(self):
        if self.gameover:
            return
        self.paused = not self.paused
        self.pause_btn.configure(text="Continuar" if self.paused else "Pausar")
        self._refresh_ui()

    def lock_piece(self):
        self.piece.imprint(self.board)
        cleared = self.clear_lines()
        if cleared:
            self.lines += cleared
            self.score += {1: 100, 2: 300, 3: 500, 4: 800}[cleared] * self.level
            if not self.jumpscare_used:
                self._trigger_jumpscare()

        self._update_progress()
        self.piece = self.next_piece
        self.next_piece = Piece()

        if self.piece.collides(self.board):
            self.gameover = True
            self.pause_btn.configure(text="Pausar")
            self.save_record()
            self.record_var.set(str(self.record))

    def clear_lines(self):
        remaining_rows = [row for row in self.board if any(cell is None for cell in row)]
        cleared = ROWS - len(remaining_rows)
        for _ in range(cleared):
            remaining_rows.insert(0, [None] * COLS)
        self.board = remaining_rows
        return cleared

    def _update_progress(self):
        self.level = self.lines // LEVEL_LINES + 1
        scaled_delay = int(BASE_DELAY * (0.88 ** (self.level - 1)))
        self.drop_delay = max(MIN_DELAY, scaled_delay)

    def _refresh_ui(self):
        self.score_var.set(str(self.score))
        self.lines_var.set(str(self.lines))
        self.level_var.set(str(self.level))
        self.speed_var.set(f"{self.drop_delay} ms")
        self.record_var.set(str(max(self.record, self.score)))

        if self.jumpscare_active:
            self.status_var.set("")
            self.status_label.configure(fg=WARNING)
        elif self.gameover:
            self.status_var.set("Fim de jogo - pressione R para recomecar")
            self.status_label.configure(fg=WARNING)
        elif self.paused:
            self.status_var.set("Jogo pausado")
            self.status_label.configure(fg="#fbbf24")
        else:
            self.status_var.set("Ritmo subindo a cada nivel")
            self.status_label.configure(fg=ACCENT)

        self._draw_board()
        self._draw_next_piece()

    def _draw_board(self):
        self.board_canvas.delete("all")

        for row in range(ROWS + 1):
            y = row * CELL
            self.board_canvas.create_line(0, y, BOARD_WIDTH, y, fill=GRID_COLOR)
        for col in range(COLS + 1):
            x = col * CELL
            self.board_canvas.create_line(x, 0, x, BOARD_HEIGHT, fill=GRID_COLOR)

        for row_index, row in enumerate(self.board):
            for col_index, color in enumerate(row):
                if color:
                    self._draw_block(self.board_canvas, col_index * CELL, row_index * CELL, color)

        ghost_y = self._ghost_y()
        for board_x, board_y in self.piece.cells(y=ghost_y):
            self._draw_block(
                self.board_canvas,
                board_x * CELL,
                board_y * CELL,
                tint(self.piece.color, 1.1),
                ghost=True,
            )

        for board_x, board_y in self.piece.cells():
            self._draw_block(self.board_canvas, board_x * CELL, board_y * CELL, self.piece.color)

        self.board_canvas.create_rectangle(
            1,
            1,
            BOARD_WIDTH - 1,
            BOARD_HEIGHT - 1,
            outline=PANEL_BORDER,
            width=2,
        )

        if self.jumpscare_active:
            self.board_canvas.create_rectangle(
                0,
                0,
                BOARD_WIDTH,
                BOARD_HEIGHT,
                fill=self.jumpscare_bg,
                outline="",
            )
            self.board_canvas.create_text(
                BOARD_WIDTH // 2,
                BOARD_HEIGHT // 2 - 8,
                text="BOO!",
                fill=self.jumpscare_fg,
                font=("Bahnschrift SemiBold", 26),
            )
            self.board_canvas.create_text(
                BOARD_WIDTH // 2,
                BOARD_HEIGHT // 2 + 22,
                text="",
                fill=self.jumpscare_fg,
                font=("Segoe UI", 8),
            )
        elif self.paused or self.gameover:
            self.board_canvas.create_rectangle(
                0,
                0,
                BOARD_WIDTH,
                BOARD_HEIGHT,
                fill="#06101d",
                outline="",
                stipple="gray50",
            )
            title = "PAUSADO" if self.paused else "GAME OVER"
            subtitle = "Pressione P para voltar" if self.paused else "Pressione R para tentar de novo"
            self.board_canvas.create_text(
                BOARD_WIDTH // 2,
                BOARD_HEIGHT // 2 - 18,
                text=title,
                fill=TEXT_MAIN if self.paused else WARNING,
                font=("Bahnschrift SemiBold", 17),
            )
            self.board_canvas.create_text(
                BOARD_WIDTH // 2,
                BOARD_HEIGHT // 2 + 16,
                text=subtitle,
                fill=TEXT_MUTED,
                font=("Segoe UI", 8),
            )

    def _draw_next_piece(self):
        self.next_canvas.delete("all")
        self.next_canvas.create_rectangle(
            0, 0, PREVIEW_SIZE, PREVIEW_SIZE, fill="#09101d", outline=""
        )

        shape = self.next_piece.shape
        width = len(shape[0]) * CELL
        height = len(shape) * CELL
        offset_x = (PREVIEW_SIZE - width) / 2
        offset_y = (PREVIEW_SIZE - height) / 2

        for row_index, row in enumerate(shape):
            for col_index, value in enumerate(row):
                if value:
                    x = offset_x + col_index * CELL
                    y = offset_y + row_index * CELL
                    self._draw_block(self.next_canvas, x, y, self.next_piece.color)

    def _ghost_y(self):
        ghost_y = self.piece.y
        while not self.piece.collides(self.board, y=ghost_y + 1):
            ghost_y += 1
        return ghost_y

    def _draw_block(self, canvas, x, y, color, ghost=False):
        x0 = x + 1
        y0 = y + 1
        x1 = x + CELL - 1
        y1 = y + CELL - 1

        if ghost:
            canvas.create_rectangle(
                x0 + 4,
                y0 + 4,
                x1 - 4,
                y1 - 4,
                outline=color,
                width=2,
                dash=(4, 3),
            )
            return

        canvas.create_rectangle(x0, y0, x1, y1, fill=tint(color, 0.58), outline="")
        canvas.create_rectangle(
            x0 + 2,
            y0 + 2,
            x1 - 2,
            y1 - 2,
            fill=color,
            outline=tint(color, 0.35),
            width=1,
        )
        canvas.create_line(
            x0 + 4,
            y0 + 4,
            x1 - 4,
            y0 + 4,
            fill=tint(color, 1.18),
            width=2,
        )
        canvas.create_line(
            x0 + 4,
            y0 + 4,
            x0 + 4,
            y1 - 4,
            fill=tint(color, 1.08),
            width=2,
        )

    def _trigger_jumpscare(self):
        self.jumpscare_used = True
        self.jumpscare_active = True
        self.root.update_idletasks()
        self.jumpscare_origin = (self.root.winfo_x(), self.root.winfo_y())
        self._play_jumpscare_sound()
        self._run_jumpscare_frame(0)

    def _run_jumpscare_frame(self, step):
        frames = [
            (JUMPSCARE_FLASH, "#111827", 4),
            ("#050816", TEXT_MAIN, 6),
            ("#8b0000", "#fff5f5", 14),
            (JUMPSCARE_FLASH, "#111827", 10),
            (JUMPSCARE_BG, "#fff5f5", 16),
        ]

        if step >= len(frames):
            self.jumpscare_active = False
            self.jumpscare_bg = JUMPSCARE_BG
            self.jumpscare_fg = TEXT_MAIN
            if self.jumpscare_origin is not None:
                origin_x, origin_y = self.jumpscare_origin
                self.root.geometry(f"+{origin_x}+{origin_y}")
            self.jumpscare_origin = None
            self.jumpscare_after_id = None
            self._refresh_ui()
            return

        self.jumpscare_bg, self.jumpscare_fg, shake = frames[step]
        self._shake_window(shake)
        self._refresh_ui()
        self.jumpscare_after_id = self.root.after(70, lambda: self._run_jumpscare_frame(step + 1))

    def _shake_window(self, force):
        if self.jumpscare_origin is None:
            return
        origin_x, origin_y = self.jumpscare_origin
        offset_x = random.randint(-force, force)
        offset_y = random.randint(-force, force)
        self.root.geometry(f"+{origin_x + offset_x}+{origin_y + offset_y}")

    def _play_jumpscare_sound(self):
        if winsound is None:
            for delay in (0, 80, 160):
                self.root.after(delay, self.root.bell)
            return

        def worker():
            for frequency, duration in ((1700, 70), (900, 90), (2100, 120)):
                try:
                    winsound.Beep(frequency, duration)
                except RuntimeError:
                    break

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = TetrisApp(root)
    root.mainloop()
