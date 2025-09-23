import tkinter as tk
import random, os

# Configurações
CELL, COLS, ROWS = 30, 10, 20
WIDTH, HEIGHT = COLS*CELL, ROWS*CELL
BASE_DELAY = 500  # velocidade inicial

# Peças do Tetris
SHAPES = {
    'I': [[1,1,1,1]],
    'J': [[1,0,0],[1,1,1]],
    'L': [[0,0,1],[1,1,1]],
    'O': [[1,1],[1,1]],
    'S': [[0,1,1],[1,1,0]],
    'T': [[0,1,0],[1,1,1]],
    'Z': [[1,1,0],[0,1,1]]
}
COLORS = {'I':'#00ffff','J':'#0000ff','L':'#ff7f00',
          'O':'#ffff00','S':'#00ff00','T':'#800080','Z':'#ff0000'}

def rotate(shape): return [list(r) for r in zip(*shape[::-1])]

class Piece:
    def __init__(self, kind=None):
        self.kind = kind or random.choice(list(SHAPES))
        self.shape = [r[:] for r in SHAPES[self.kind]]
        self.color = COLORS[self.kind]
        self.x, self.y = COLS//2 - len(self.shape[0])//2, 0

    def rotate(self, board):
        new_shape = rotate(self.shape)
        if not self._collides(new_shape, self.x, self.y, board): self.shape = new_shape

    def move(self, dx, dy, board):
        if not self._collides(self.shape, self.x+dx, self.y+dy, board):
            self.x, self.y = self.x+dx, self.y+dy
            return True
        return False

    def _collides(self, shape, x, y, board):
        for r,row in enumerate(shape):
            for c,val in enumerate(row):
                if val:
                    bx, by = x+c, y+r
                    if bx<0 or bx>=COLS or by<0 or by>=ROWS or board[by][bx] is not None:
                        return True
        return False

    def imprint(self, board):
        for r,row in enumerate(self.shape):
            for c,val in enumerate(row):
                if val: board[self.y+r][self.x+c] = self.color

class TetrisApp:
    def __init__(self, root):
        self.root = root
        self.canvas = tk.Canvas(root, width=WIDTH+150, height=HEIGHT, bg='black')
        self.canvas.grid(row=0, column=0, rowspan=2)

        # Botão de reinício
        self.restart_btn = tk.Button(root, text="Recomeçar", command=self.restart)
        self.restart_btn.grid(row=0, column=1, padx=10, pady=10)

        # Estado inicial
        self.board = [[None]*COLS for _ in range(ROWS)]
        self.piece, self.next_piece = Piece(), Piece()
        self.score, self.lines, self.level = 0, 0, 1
        self.gameover, self.paused = False, False
        self.record = self.load_record()

        # Interface
        self._create_ui_texts()
        root.bind("<Key>", self.key_pressed)
        self._draw_frame()
        self._tick()

    # ===== Recorde =====
    def load_record(self): return int(open("record.txt").read()) if os.path.exists("record.txt") else 0
    def save_record(self):
        if self.score > self.record:
            with open("record.txt","w") as f: f.write(str(self.score))
            self.record = self.score

    # ===== Teclas =====
    def key_pressed(self, e):
        if self.gameover: return
        if e.keysym == "Left": self.piece.move(-1,0,self.board)
        elif e.keysym == "Right": self.piece.move(1,0,self.board)
        elif e.keysym == "Down": 
            if not self.piece.move(0,1,self.board): self.lock_piece()
        elif e.keysym == "Up": self.piece.rotate(self.board)
        elif e.keysym == "space":
            while self.piece.move(0,1,self.board): pass
            self.lock_piece()
        self._draw_frame()

    # ===== Lógica =====
    def _tick(self):
        if not self.paused and not self.gameover:
            if not self.piece.move(0,1,self.board): self.lock_piece()
        self._draw_frame()

        # velocidade aumenta com a pontuação
        self.level = self.score // 1000 + 1
        delay = max(100, BASE_DELAY - (self.level-1)*50)  # nunca menor que 100ms
        self.root.after(delay, self._tick)

    def lock_piece(self):
        self.piece.imprint(self.board)
        cleared = self.clear_lines()
        if cleared:
            self.lines += cleared
            self.score += [0,100,300,500,800][cleared]
        self.piece, self.next_piece = self.next_piece, Piece()
        if self.piece._collides(self.piece.shape, self.piece.x, self.piece.y, self.board):
            self.gameover = True
            self.save_record()

    def clear_lines(self):
        new_board = [row for row in self.board if any(cell is None for cell in row)]
        cleared = ROWS - len(new_board)
        for _ in range(cleared): new_board.insert(0,[None]*COLS)
        self.board = new_board
        return cleared

    def restart(self):
        self.board = [[None]*COLS for _ in range(ROWS)]
        self.piece, self.next_piece = Piece(), Piece()
        self.score, self.lines, self.level = 0,0,1
        self.gameover = False
        self._draw_frame()

    # ===== Interface =====
    def _create_ui_texts(self):
        self.score_text = self.canvas.create_text(WIDTH+75,40,fill='white',font=('Helvetica',12))
        self.level_text = self.canvas.create_text(WIDTH+75,100,fill='white',font=('Helvetica',12))
        self.record_text = self.canvas.create_text(WIDTH+75,160,fill='gold',font=('Helvetica',12))

    def _draw_frame(self):
        self.canvas.delete("board")
        for r in range(ROWS):
            for c in range(COLS):
                x0,y0 = c*CELL,r*CELL
                x1,y1 = x0+CELL,y0+CELL
                color = self.board[r][c]
                self.canvas.create_rectangle(x0,y0,x1,y1,fill=color or "",outline="#1a1a1a",tags="board")

        for r,row in enumerate(self.piece.shape):
            for c,val in enumerate(row):
                if val:
                    x0,y0=(self.piece.x+c)*CELL,(self.piece.y+r)*CELL
                    self.canvas.create_rectangle(x0,y0,x0+CELL,y0+CELL,fill=self.piece.color,outline="white",tags="board")

        # Atualiza textos
        self.canvas.itemconfigure(self.score_text, text=f"Pontuação:\n{self.score}")
        self.canvas.itemconfigure(self.level_text, text=f"Nível:\n{self.level}")
        self.canvas.itemconfigure(self.record_text, text=f"Recorde:\n{self.record}")

        if self.gameover:
            self.canvas.create_text(WIDTH//2, HEIGHT//2, text="GAME OVER", fill="red", font=("Helvetica",24,"bold"),tags="board")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Tetris — João")
    app = TetrisApp(root)
    root.mainloop()
