import os
from dotenv import load_dotenv

load_dotenv()

# CONFIGURAÇÕES DE AMBIENTE E JOGO
# LLM
HF_TOKEN       = os.getenv("HF_TOKEN")
LLM_MODEL      = os.getenv("LLM_MODEL", "meta-llama/Meta-Llama-3-70B-Instruct:novita")
LLM_MAX_TOKENS = os.getenv("LLM_MAX_TOKENS", "1024")

# Tabuleiro
ROWS           = 12
COLS           = 12
NUM_MINES      = 32

## VISUAL DO JOGO
# Visual pygame (célula)
CELL_SIZE      = 36
MARGIN         = 2

# BT / jogo
AUTO_STEP_MS   = 800
FIRST_CLICK    = (ROWS // 2, COLS // 2)


# CORES PYGAME
COLOR_BG          = (30,  30,  30)
COLOR_CELL_HIDDEN = (70,  70,  80)
COLOR_CELL_HOVER  = (90,  90, 110)
COLOR_CELL_SAFE   = (50, 120,  50)
COLOR_CELL_MINE   = (180,  40,  40)
COLOR_CELL_LLM    = ( 60,  90, 180)
COLOR_REVEALED    = (200, 200, 210)
COLOR_EXPLODED    = (220,  50,  50)
COLOR_FLAG        = (230, 160,  30)
COLOR_GRID_LINE   = ( 20,  20,  20)
COLOR_TEXT        = ( 20,  20,  20)
COLOR_WHITE       = (255, 255, 255)

NUMBER_COLORS = {
    1: ( 30,  80, 200),
    2: ( 30, 140,  60),
    3: (210,  40,  40),
    4: ( 20,  20, 140),
    5: (140,  20,  20),
    6: ( 20, 140, 140),
    7: ( 20,  20,  20),
    8: (100, 100, 100),
}