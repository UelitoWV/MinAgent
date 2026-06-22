import sys
import os
import pygame
import matplotlib.pyplot as plt
from config import ROWS, COLS, NUM_MINES, FIRST_CLICK
from game import MinesweeperGame
from behavior_tree import build_tree, run_tree, collect_node_status
from llm_agent import LLMAgent
from renderer import MainWindow


sys.path.insert(0, os.path.dirname(__file__))
pygame.init()

game       = MinesweeperGame()
llm_agent  = LLMAgent()
bt_tree    = build_tree(game, llm_agent)

node_status  = {}
last_action  = None
step_pending = False

# ─── Primeiro clique automático (garante tabuleiro seguro) ─
def do_first_click():
    r, c = FIRST_CLICK
    game.reveal(r, c)

do_first_click()

# ═══════════════════════════════════════════════════════════
# EXECUTA UM PASSO DA BT
# ═══════════════════════════════════════════════════════════
def do_step() -> bool:
    """
    Executa um tick da BT e aplica a ação.
    Retorna True se o jogo terminou (para parar o auto).
    """
    global last_action, node_status

    if game.game_over:
        window.stop_auto()
        return True

    # Roda a BT
    action = run_tree(bt_tree, game)
    node_status = collect_node_status(bt_tree)

    if action is None:
        print("[WARN] BT não produziu ação")
        window.refresh(game, node_status, llm_agent, last_action)
        return game.game_over

    last_action = action

    # Aplica highlight e redesenha ANTES da ação (para visualizar)
    window.refresh(game, node_status, llm_agent, last_action)
    plt.pause(0.15)

    # Executa a ação no jogo
    r, c = action["row"], action["col"]
    if action["type"] == "reveal":
        success = game.reveal(r, c)
        src_label = {
            "bt_safe": "BT-Segura", "llm": "LLM", "llm_fallback": "LLM-Fallback"
        }.get(action["source"], action["source"])
        status = "V" if success else " ** MINA!"
        print(f"[{src_label:12}] REVEAL ({r:2},{c:2}) → {status}  | {action['reasoning'][:60]}")
    elif action["type"] == "flag":
        game.flag(r, c)
        src_label = {
            "bt_mine": "BT-Mina", "bt_subset_safe": "BT-Subset", "llm": "LLM"
        }.get(action["source"], action["source"])
        print(f"[{src_label:12}] FLAG   ({r:2},{c:2})           | {action['reasoning'][:60]}")

    # Redesenha após ação
    node_status = collect_node_status(bt_tree)
    window.refresh(game, node_status, llm_agent, last_action)

    if game.game_over:
        if game.won:
            print(f"\n // VITÓRIA! {game.moves} jogadas, {llm_agent.call_count} chamadas LLM //")
        else:
            print(f"\n** Explodiu em ({r},{c}) após {game.moves} jogadas **")
        window.stop_auto()
        return True

    return False


# RESET
def do_reset():
    global game, llm_agent, bt_tree, node_status, last_action
    game        = MinesweeperGame()
    llm_agent   = LLMAgent()
    bt_tree     = build_tree(game, llm_agent)
    node_status = {}
    last_action = None
    do_first_click()
    window.refresh(game, node_status, llm_agent, last_action)
    print("\n[RESET] Novo jogo iniciado\n")



# JANELA PRINCIPAL
window = MainWindow(
    on_step  = do_step,
    on_auto  = do_step,
    on_reset = do_reset,
)

# Render inicial
window.refresh(game, node_status, llm_agent, last_action)

print("=" * 60)
print(f"  Campo Minado {ROWS}×{COLS} — {NUM_MINES} minas")
print(f"  BT + LLM Agent ({llm_agent.__class__.__name__})")
print(f"  Primeiro clique em {FIRST_CLICK} (centro seguro)")
print()

plt.show()
pygame.quit()
