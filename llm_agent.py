import json
import random
import re

from huggingface_hub import InferenceClient

from config import HF_TOKEN, LLM_MODEL, LLM_MAX_TOKENS

client = InferenceClient(
    api_key=HF_TOKEN,
)

'''
Classe que possui a função de chamar a LLM (via Hugging Face COM Inference Providers**) para nos dar o resultado da próxima ação do agente
'''
class LLMAgent:
    def __init__(self):
        self.call_count = 0
        self.last_prompt = ""
        self.last_response = ""
        self.last_reasoning = ""
        self.history = []

    def decide(self, game) -> dict | None:
        self.call_count += 1

        # Funções auxiliares do arquivo 'game.py' para facilitar o entendimento da LLM
        state = game.get_state()
        ascii_grid = game.to_ascii() # FEITO POR IA - Claude
        frontier = game.frontier_cells()

        candidates = []

        for r, c in frontier[:30]:
            adj_nums = []

            for nr, nc in self._number_neighbors(game, r, c):
                num = game.get_number(nr, nc)
                flags = game.count_flags_around(nr, nc)
                hid = game.count_hidden_around(nr, nc)

                adj_nums.append(
                    f"  • ({nr},{nc}) = número {num}, "
                    f"{flags} bandeira(s), "
                    f"{hid} oculta(s)"
                )

            candidates.append(
                f"({r},{c}):\n" + "\n".join(adj_nums)
            )

        cand_text = (
            "\n".join(candidates)
            if candidates
            else "Nenhuma célula na fronteira."
        )

        if not frontier and state["hidden"]:
            non_frontier = state["hidden"][:10]

            cand_text = (
                "Sem fronteira. Candidatas aleatórias:\n"
                + ", ".join(str(x) for x in non_frontier)
            )

        prompt = f"""
Você é um especialista em Campo Minado.

GRID {game.rows}x{game.cols}

Minas restantes: {state['mines_remaining']}
Células ocultas: {state['cells_hidden']}
Jogadas: {state['moves']}

TABULEIRO:

{ascii_grid}

Legenda:
. = oculta
F = bandeira
□ = vazia revelada
1-8 = número
X = explodida

CANDIDATAS:

{cand_text}

SUA TAREFA E REGRAS ESTRITAS:
1. ALVO RESTRITO: A sua coordenada final (row, col) DEVE OBRIGATORIAMENTE ser extraída da lista de CANDIDATAS. Nunca escolha a coordenada de um número.
2. CÁLCULO DE RISCO: Calcule o risco cruzando os vizinhos. Risco = (Minas pendentes do vizinho) / (Células ocultas ao redor do vizinho).
3. AÇÃO 'flag': USO RESTRITO. Só use se o cálculo provar 100% de risco matemático (Minas pendentes == Células ocultas restantes).
4. AÇÃO 'reveal': Escolha a CANDIDATA com a MENOR porcentagem de risco.
5. DESEMPATE: Se várias candidatas tiverem o mesmo risco (ex: 50%), escolha a que toca no menor número de outras células ocultas.

IMPORTANTE:
- Responda SOMENTE JSON válido.
- Não utilize markdown.
- Não utilize blocos ```json.
- Não escreva texto antes ou depois do JSON.

Formato obrigatório:

{{
  "reasoning": "Prove a matemática. Ex: 'O 3 em (2,2) já tem 1 flag. Faltam 2 minas. Ele toca em exatamente 2 ocultas. Logo, (2,3) é flag obrigatório.' Se não houver prova assim, use reveal.",
  "action": "reveal | flag",
  "row": 0,
  "col": 0
}}


"""

        self.last_prompt = prompt

        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.1, # Dar menos aleatoriedade pra LLM
                max_tokens=LLM_MAX_TOKENS,
            )
            raw = response.choices[0].message.content.strip()

            self.last_response = raw

            match = re.search(
                r"\{.*\}",
                raw,
                re.DOTALL,
            )

            # Alguns tratamentos de erros
            if not match:
                self._log_error(
                    "JSON não encontrado",
                    raw,
                )
                print("\n===== RAW =====")
                print(raw)
                print("===============")  
                return self._fallback(
                    game,
                    "JSON não encontrado",
                )

            data = json.loads(match.group())

            row = int(data["row"])
            col = int(data["col"])

            action = (
                data.get("action", "reveal")
                .lower()
                .strip()
            )

            if action not in ("reveal", "flag"):
                action = "reveal"

            reasoning = data.get(
                "reasoning",
                "",
            )

            if not (
                0 <= row < game.rows
                and 0 <= col < game.cols
            ):
                self._log_error(
                    f"Posição inválida ({row},{col})",
                    raw,
                )
                return self._fallback(
                    game,
                    "posição inválida",
                )

            from game import HIDDEN, FLAGGED

            state_cell = game.get_cell_state(
                row,
                col,
            )

            if state_cell not in (
                HIDDEN,
                FLAGGED,
            ):
                self._log_error(
                    f"Célula já revelada ({row},{col})",
                    raw,
                )
                return self._fallback(
                    game,
                    "célula já revelada",
                )

            result = {
                "type": action,
                "row": row,
                "col": col,
                "source": "llm",
                "reasoning": reasoning,
            }

            self.last_reasoning = reasoning

            self._log_success(result)

            return result

        except json.JSONDecodeError as e:
            self._log_error(
                f"JSON inválido: {e}",
                self.last_response,
            )

            return self._fallback(
                game,
                "JSON inválido",
            )

        except Exception as e:
            self._log_error(
                f"Erro API: {e}",
                "",
            )

            return self._fallback(
                game,
                str(e),
            )

    def _number_neighbors(
        self,
        game,
        r,
        c,
    ):
        from game import REVEALED

        for dr in range(-1, 2):
            for dc in range(-1, 2):

                if dr == 0 and dc == 0:
                    continue

                nr = r + dr
                nc = c + dc

                if (
                    0 <= nr < game.rows
                    and 0 <= nc < game.cols
                    and game.get_cell_state(nr, nc)
                    == REVEALED
                    and game.get_number(nr, nc) > 0
                ):
                    yield nr, nc


    def _log_success(
        self,
        result,
    ):
        self.history.insert(
            0,
            {
                "call": self.call_count,
                "type": result["type"],
                "pos": (
                    result["row"],
                    result["col"],
                ),
                "source": result["source"],
                "reasoning": result["reasoning"],
                "ok": True,
            },
        )

        self.history = self.history[:50]

    def _log_error(
        self,
        msg,
        raw,
    ):
        self.history.insert(
            0,
            {
                "call": self.call_count,
                "type": "error",
                "pos": None,
                "source": "hf_llm",
                "reasoning": msg,
                "raw": raw[:500],
                "ok": False,
            },
        )

        self.history = self.history[:50]


    
     # Caso dê fallback (a IA não respondeu bem, ou foi alguma célula que já estava revelada ou marcada), no pior dos casos, a gente aleatoriza
     # Eu fiz isso por conta que principalmente quando a IA não respondia corretamente, o jogo parava
    def _fallback(
        self,
        game,
        reason,
    ):
        from game import HIDDEN

        frontier = game.frontier_cells()

        pool = (
            frontier
            if frontier
            else [
                (r, c)
                for r in range(game.rows)
                for c in range(game.cols)
                if game.get_cell_state(r, c)
                == HIDDEN
            ]
        )

        if not pool:
            return None

        r, c = random.choice(pool)

        result = {
            "type": "reveal",
            "row": r,
            "col": c,
            "source": "fallback",
            "reasoning": f"Fallback ({reason})",
        }

        self._log_success(result)

        return result

 

