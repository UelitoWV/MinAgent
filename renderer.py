'''
Código feito puramente por IA, mais especificamente o Claude 4.6 Sonnet
'''

import pygame
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Button
import numpy as np
from config import *
from game import HIDDEN, REVEALED, FLAGGED, EXPLODED


matplotlib.use("TkAgg")
pygame.font.init()
_FONT_NUM  = None
_FONT_SYM  = None

def _get_fonts():
    global _FONT_NUM, _FONT_SYM
    if _FONT_NUM is None:
        _FONT_NUM = pygame.font.SysFont("Arial", CELL_SIZE - 10, bold=True)
        _FONT_SYM = pygame.font.SysFont("Segoe UI Emoji", CELL_SIZE - 8)
    return _FONT_NUM, _FONT_SYM

HIGHLIGHT_COLORS = {
    "safe": (60,  200,  80, 120),
    "mine": (220,  50,  50, 140),
    "llm":  ( 80, 120, 220, 140),
}

def render_board(game) -> pygame.Surface:
    font_num, font_sym = _get_fonts()
    w = COLS * (CELL_SIZE + MARGIN) + MARGIN
    h = ROWS * (CELL_SIZE + MARGIN) + MARGIN
    surf = pygame.Surface((w, h))
    surf.fill(COLOR_BG)

    for r in range(ROWS):
        for c in range(COLS):
            cell = game.grid[r][c]
            x = MARGIN + c * (CELL_SIZE + MARGIN)
            y = MARGIN + r * (CELL_SIZE + MARGIN)
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)

            if cell.state == REVEALED:
                color = COLOR_REVEALED
            elif cell.state == EXPLODED:
                color = COLOR_EXPLODED
            else:
                color = COLOR_CELL_HIDDEN

            pygame.draw.rect(surf, color, rect, border_radius=4)

            if cell.highlight and cell.state == HIDDEN:
                hl_color = HIGHLIGHT_COLORS.get(cell.highlight, (255,255,0,80))
                hl_surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                hl_surf.fill(hl_color)
                surf.blit(hl_surf, (x, y))

                bc = {
                    "safe": (60, 220, 80),
                    "mine": (220, 60, 60),
                    "llm":  (80, 120, 240),
                }.get(cell.highlight, (255,255,0))
                pygame.draw.rect(surf, bc, rect, width=2, border_radius=4)

            cx = x + CELL_SIZE // 2
            cy = y + CELL_SIZE // 2

            if cell.state == FLAGGED:
                txt = font_sym.render("🚩", True, COLOR_FLAG)
                surf.blit(txt, txt.get_rect(center=(cx, cy)))

            elif cell.state in (REVEALED, EXPLODED):
                if cell.is_mine:
                    txt = font_sym.render("💣", True, (20, 20, 20))
                    surf.blit(txt, txt.get_rect(center=(cx, cy)))
                elif cell.number > 0:
                    color_n = NUMBER_COLORS.get(cell.number, (20, 20, 20))
                    txt = font_num.render(str(cell.number), True, color_n)
                    surf.blit(txt, txt.get_rect(center=(cx, cy)))

    return surf


STATUS_COLOR = {
    "SUCCESS": "#22c55e",
    "FAILURE": "#ef4444",
    "RUNNING": "#f59e0b",
    "INVALID": "#888888",
    "idle":    "#e0dedc",
}

class MainWindow:
    def __init__(self, on_step, on_auto, on_reset):
        self.on_step  = on_step
        self.on_auto  = on_auto
        self.on_reset = on_reset

        self.fig = plt.figure(figsize=(14, 10), facecolor="#1e1e1e")
        self.fig.canvas.manager.set_window_title("Campo Minado — BT + LLM Agent")

        gs = gridspec.GridSpec(
            3, 2, figure=self.fig,
            left=0.02, right=0.98, top=0.92, bottom=0.12,
            wspace=0.25, hspace=0.40,
        )
        self.ax_board = self.fig.add_subplot(gs[:, 0])
        self.ax_log   = self.fig.add_subplot(gs[0:2, 1])
        self.ax_stats = self.fig.add_subplot(gs[2, 1])

        for ax in [self.ax_board, self.ax_log, self.ax_stats]:
            ax.set_facecolor("#1e1e1e")

        self._build_buttons()
        self.auto_timer = None
        self._auto_running = False

    def _build_buttons(self):
        ax_step  = self.fig.add_axes([0.02, 0.03, 0.10, 0.06])
        ax_auto  = self.fig.add_axes([0.13, 0.03, 0.10, 0.06])
        ax_reset = self.fig.add_axes([0.24, 0.03, 0.10, 0.06])

        self.btn_step  = Button(ax_step,  "Step ▶",  color="#1c3a5e", hovercolor="#2a5080")
        self.btn_auto  = Button(ax_auto,  "Auto ▷",  color="#1a4a2a", hovercolor="#266638")
        self.btn_reset = Button(ax_reset, "Resetar", color="#4a1a1a", hovercolor="#6a2222")

        for btn in [self.btn_step, self.btn_auto, self.btn_reset]:
            btn.label.set_color("#ddd")
            btn.label.set_fontsize(10)

        self.btn_step.on_clicked(lambda e: self.on_step())
        self.btn_auto.on_clicked(self._toggle_auto)
        self.btn_reset.on_clicked(lambda e: self.on_reset())

    def _toggle_auto(self, e):
        if self._auto_running:
            if self.auto_timer:
                self.auto_timer.stop()
                self.auto_timer = None
            self._auto_running = False
            self.btn_auto.label.set_text("Auto ▷")
            self.btn_auto.color = "#1a4a2a"
        else:
            self._auto_running = True
            self.btn_auto.label.set_text("Parar ◼")
            self.btn_auto.color = "#4a1a1a"
            self.auto_timer = self.fig.canvas.new_timer(interval=AUTO_STEP_MS)
            self.auto_timer.add_callback(self._auto_cb)
            self.auto_timer.start()
        self.fig.canvas.draw_idle()

    def _auto_cb(self):
        stop = self.on_auto()
        if stop:
            self._toggle_auto(None)

    def stop_auto(self):
        if self._auto_running:
            self._toggle_auto(None)

    def render_board(self, game):
        surf = render_board(game)
        arr  = pygame.surfarray.array3d(surf)
        arr  = np.transpose(arr, (1, 0, 2))

        self.ax_board.cla()
        self.ax_board.set_facecolor("#1e1e1e")
        self.ax_board.imshow(arr)
        self.ax_board.axis("off")

        state = game.get_state()
        status = "💥 EXPLODIU" if (game.game_over and not game.won) else \
                 "🏆 VITÓRIA!" if game.won else "🎮 Jogando"
        self.ax_board.set_title(
            f"{status}  |  🚩 {game.flags_placed}/{NUM_MINES}  |  "
            f"⬜ {state['cells_hidden']}  |  🎯 {game.moves} jogadas",
            fontsize=10, color="#ddd", pad=6,
        )

    def render_log(self, llm_agent, last_action: dict | None):
        ax = self.ax_log
        ax.cla()
        ax.set_facecolor("#141414")
        ax.axis("off")
        ax.set_title(f"Log do Agente  (LLM calls: {llm_agent.call_count})",
                     fontsize=9, color="#aaa", pad=3)

        y = 0.97
        dy = 0.075

        if last_action:
            src_colors = {
                "bt_safe":    "#22c55e",
                "bt_mine":    "#ef4444",
                "llm":        "#60a5fa",
                "llm_fallback": "#f59e0b",
            }
            src = last_action.get("source", "")
            col = src_colors.get(src, "#ccc")
            src_label = {
                "bt_safe": "🟢 BT-Segura",
                "bt_mine": "🔴 BT-Mina",
                "llm":     "🔵 LLM",
                "llm_fallback": "🟡 LLM-Fallback",
            }.get(src, src)
            act_type = last_action.get("type", "?")
            pos = (last_action.get("row"), last_action.get("col"))
            ax.text(0.02, y, f"▶ {src_label}  {act_type.upper()}  {pos}",
                    fontsize=9, color=col, fontweight="bold",
                    transform=ax.transAxes, va="top")
            y -= dy
            reason = last_action.get("reasoning", "")
            if reason:
                words = reason.split()
                line, lines = "", []
                for w in words:
                    if len(line) + len(w) > 50:
                        lines.append(line); line = w
                    else:
                        line = (line + " " + w).strip()
                if line: lines.append(line)
                for l in lines[:3]:
                    ax.text(0.04, y, l, fontsize=7.5, color="#aaa",
                            transform=ax.transAxes, va="top",
                            fontfamily="monospace")
                    y -= dy * 0.75
            y -= dy * 0.5

        ax.text(0.02, y, "─── Histórico LLM ───",
                fontsize=7.5, color="#555", transform=ax.transAxes, va="top")
        y -= dy * 0.8

        for entry in llm_agent.history[:10]:
            if y < 0.02: break
            ok_col = "#22c55e" if entry["ok"] else "#ef4444"
            pos_str = str(entry["pos"]) if entry["pos"] else "—"
            line = f"#{entry['call']}  {entry['type'].upper():6}  {pos_str:8}  {entry['reasoning'][:40]}"
            ax.text(0.02, y, line, fontsize=6.5, color=ok_col,
                    transform=ax.transAxes, va="top", fontfamily="monospace")
            y -= dy * 0.72

    def render_stats(self, game, node_status):
        ax = self.ax_stats
        ax.cla()
        ax.set_facecolor("#141414")
        ax.axis("off")

        state = game.get_state()
        pct_revealed = game.cells_revealed / (ROWS * COLS - NUM_MINES) * 100 if not game.won else 100

        cards = [
            ("Mines\nrestantes", str(state["mines_remaining"]), "#f59e0b"),
            ("Células\nocultas",  str(state["cells_hidden"]),   "#60a5fa"),
            ("Reveladas",  f"{pct_revealed:.0f}%",              "#22c55e"),
            ("Jogadas",    str(game.moves),                     "#a78bfa"),
        ]
        for i, (label, val, color) in enumerate(cards):
            cx = 0.05 + (i % 2) * 0.50
            cy = 0.80 - (i // 2) * 0.42

            ax.add_patch(mpatches.FancyBboxPatch(
                (cx, cy - 0.20), 0.42, 0.35,
                boxstyle="round,pad=0.02",
                facecolor="#252525", edgecolor="#333", linewidth=0.7,
                transform=ax.transAxes,
            ))
            ax.text(cx + 0.21, cy + 0.05, label, ha="center", va="center",
                    fontsize=7, color="#777", transform=ax.transAxes)
            ax.text(cx + 0.21, cy - 0.10, val, ha="center", va="center",
                    fontsize=14, color=color, fontweight="bold",
                    transform=ax.transAxes)

    def refresh(self, game, node_status, llm_agent, last_action):
        self.render_board(game)
        self.render_log(llm_agent, last_action)
        self.render_stats(game, node_status)
        self.fig.canvas.draw_idle()
        plt.pause(0.001)