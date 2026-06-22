import random
from config import ROWS, COLS, NUM_MINES

# Estado de cada célula
HIDDEN    = "hidden"
REVEALED  = "revealed"
FLAGGED   = "flagged"
EXPLODED  = "exploded"

class Cell:
    def __init__(self):
        self.state    = HIDDEN
        self.is_mine  = False
        self.number   = 0       # 0 = vazia, 1-8 = adjacências
        self.highlight = None   # "safe" | "mine" | "llm" | None

class MinesweeperGame:
    def __init__(self):
        self.rows      = ROWS
        self.cols      = COLS
        self.num_mines = NUM_MINES
        self.grid      = [[Cell() for _ in range(COLS)] for _ in range(ROWS)]
        self.initialized = False   # minas colocadas só após 1º clique (Para não dar aquele erro ruim de iniciar já perdendo)
        self.game_over   = False
        self.won         = False
        self.moves       = 0
        self.flags_placed = 0
        self.cells_revealed = 0

    ## Inicialização
    # Coloca minas evitando a célula do primeiro clique e seus vizinhos.
    def place_mines(self, safe_row, safe_col):
        safe = set()
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                r, c = safe_row + dr, safe_col + dc
                if 0 <= r < self.rows and 0 <= c < self.cols:
                    safe.add((r, c))

        candidates = [(r, c) for r in range(self.rows)
                              for c in range(self.cols)
                              if (r, c) not in safe]
        mines = random.sample(candidates, self.num_mines)
        for r, c in mines:
            self.grid[r][c].is_mine = True

        # Calcula números
        for r in range(self.rows):
            for c in range(self.cols):
                if not self.grid[r][c].is_mine:
                    self.grid[r][c].number = sum(
                        1 for nr, nc in self._neighbors(r, c)
                        if self.grid[nr][nc].is_mine
                    )
        self.initialized = True

    def _neighbors(self, r, c):
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    yield nr, nc

    # Ações do minesweeper
    # Revela célula. Retorna True se OK, False se explodiu.
    def reveal(self, row, col):
        if self.game_over:
            return False
        cell = self.grid[row][col]
        if cell.state != HIDDEN:
            return False

        if not self.initialized:
            self.place_mines(row, col)

        self.clear_highlights()

        # Condição de Derrota (Game Over)
        if cell.is_mine:
            cell.state = EXPLODED
            self.game_over = True
            self._reveal_all_mines()
            return False

        self._flood_reveal(row, col)
        self.moves += 1
        self._check_win()
        return True

    # Marca/desmarca bandeira.
    def flag(self, row, col):

        if self.game_over:
            return
        
        cell = self.grid[row][col]

        if cell.state == HIDDEN:
            cell.state = FLAGGED
            self.flags_placed += 1

        elif cell.state == FLAGGED:
            cell.state = HIDDEN
            self.flags_placed -= 1

        self.clear_highlights()
        self.moves += 1

    # Revelação iterativa para todas as células vazias.
    def _flood_reveal(self, row, col):

        stack = [(row, col)]
        visited = set()

        while stack:
            r, c = stack.pop()
            if (r, c) in visited:
                continue
            visited.add((r, c))
            cell = self.grid[r][c]

            if cell.state != HIDDEN:
                continue
            cell.state = REVEALED
            self.cells_revealed += 1

            if cell.number == 0:
                for nr, nc in self._neighbors(r, c):
                    if (nr, nc) not in visited:
                        stack.append((nr, nc))

    # Revela todas as minas, caso se vc erre alguma coisa, aí mostra
    def _reveal_all_mines(self):
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.grid[r][c]
                if cell.is_mine and cell.state == HIDDEN:
                    cell.state = REVEALED

    # Checa se acertou tudo
    def _check_win(self):
        total = self.rows * self.cols
        if self.cells_revealed == total - self.num_mines:
            self.won = True
            self.game_over = True

    # Highlights 
    def clear_highlights(self):
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c].highlight = None

    def set_highlight(self, row, col, kind):
        self.grid[row][col].highlight = kind

    # Estado para ajudar a LLM a entender qual a situação do ambiente em que ele vai precisar atuar.
    # A partir daqui, a maioria das coisas vai ser utilizado para enriquecer a LLM
    def get_state(self):
        """Retorna estrutura com tudo que a BT e o LLM precisam."""
        hidden, flagged, revealed = [], [], []
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.grid[r][c]
                if cell.state == HIDDEN:
                    hidden.append((r, c))
                elif cell.state == FLAGGED:
                    flagged.append((r, c))
                elif cell.state == REVEALED:
                    revealed.append((r, c, cell.number))

        return {
            "hidden":          hidden,
            "flagged":         flagged,
            "revealed":        revealed,
            "mines_remaining": self.num_mines - self.flags_placed,
            "cells_hidden":    len(hidden),
            "moves":           self.moves,
            "initialized":     self.initialized,
        }

    def get_number(self, r, c):
        return self.grid[r][c].number

    def get_cell_state(self, r, c):
        return self.grid[r][c].state

    def count_flags_around(self, r, c):
        return sum(1 for nr, nc in self._neighbors(r, c)
                   if self.grid[nr][nc].state == FLAGGED)

    def count_hidden_around(self, r, c):
        return sum(1 for nr, nc in self._neighbors(r, c)
                   if self.grid[nr][nc].state == HIDDEN)

    def hidden_neighbors(self, r, c):
        return [(nr, nc) for nr, nc in self._neighbors(r, c)
                if self.grid[nr][nc].state == HIDDEN]

    # Células reveladas com número ao redor de (r,c).
    def number_neighbors(self, r, c):
        return [(nr, nc) for nr, nc in self._neighbors(r, c)
                if self.grid[nr][nc].state == REVEALED and self.grid[nr][nc].number > 0]

    def to_ascii(self):
        """Grid em ASCII para o LLM. (FEITA POR IA - Claude)"""
        header = "   " + " ".join(f"{c:2}" for c in range(self.cols))
        lines  = [header, "   " + "─" * (self.cols * 3)]
        for r in range(self.rows):
            row_chars = []
            for c in range(self.cols):
                cell = self.grid[r][c]
                if cell.state == HIDDEN:
                    row_chars.append(" .")
                elif cell.state == FLAGGED:
                    row_chars.append(" F")
                elif cell.state == REVEALED:
                    row_chars.append(f" {cell.number if cell.number > 0 else '□'}")
                else:
                    row_chars.append(" X")
            lines.append(f"{r:2} |" + "".join(row_chars))
        return "\n".join(lines)

    # Células ocultas adjacentes a pelo menos um número revelado.
    def frontier_cells(self):
        frontier = set()
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c].state == HIDDEN:
                    for nr, nc in self._neighbors(r, c):
                        if (self.grid[nr][nc].state == REVEALED
                                and self.grid[nr][nc].number > 0):
                            frontier.add((r, c))
                            break
        return sorted(frontier)
