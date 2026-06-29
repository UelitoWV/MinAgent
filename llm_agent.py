import json
import random
import re, ast
from smolagents import CodeAgent, LiteLLMModel

from config import HF_TOKEN, LLM_MODEL, LLM_MAX_TOKENS
from game import HIDDEN, FLAGGED, REVEALED


model = LiteLLMModel(
    model_id=LLM_MODEL,
    api_key=HF_TOKEN,
    max_tokens=LLM_MAX_TOKENS,
)

'''
Agente LLM com paradigma CodeAct (smolagents):
Em vez de responder em JSON, o modelo gera e executa código Python para calcular probabilidades de mina e decidir a jogada mais segura. (Sugestão do professor)
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

        # Função auxiliares do arquivo 'game.py' para facilitar o entendimento da LLM
        frontier = game.frontier_cells()
        
        frontier_data = {}

        for r, c in frontier[:12]:
            vizinhos_info = []
            for nr, nc in self._number_neighbors(game, r, c):
                num = game.get_number(nr, nc)
                flags = game.count_flags_around(nr, nc)
                hid = game.count_hidden_around(nr, nc)
                
                vizinhos_info.append({
                    "minas_restantes": num - flags,
                    "ocultas_restantes": hid
                })
            
            if vizinhos_info:
                frontier_data[f"{r},{c}"] = vizinhos_info

        # Se não há dados na fronteira, aciona o fallback imediatamente
        if not frontier_data:
            return self._fallback(game, "Sem dados estruturados na fronteira para analisar.")

        candidates = []

        for r, c in frontier[:12]:
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

        prompt = f"""Você é um especialista em análise de Campo Minado.
A variável 'dados_fronteira' JÁ ESTÁ CARREGADA na sua memória. ELA É UM DICIONÁRIO.
NÃO TENTE DECLARAR OU REESCREVER a variável 'dados_fronteira' no seu código. Use-a diretamente.

Regras do seu script:
1. Itere sobre dados_fronteira.items().
2. Para cada restrição de uma coordenada, calcule o risco: (minas_restantes / ocultas_restantes).
3. O risco da coordenada é o MAIOR risco entre os vizinhos.
4. Encontre a coordenada com o MENOR risco.
5. Use a ferramenta final_answer() passando EXATAMENTE um dicionário com a sua resposta.

EXEMPLO OBRIGATÓRIO DE SAÍDA:
final_answer({{
    "row": 4,
    "col": 5,
    "action": "reveal",
    "reasoning": "Risco calculado: 25%"
}})
"""

        self.last_prompt = prompt

        try:
            # CodeAgent entregando o modelo que definimos acima e rodando o prompt acima
            agent1 = CodeAgent(tools=[], model=model, add_base_tools=False, max_steps=2)
            raw = agent1.run(prompt, additional_args={"dados_fronteira": frontier_data})
            print(raw)

            # Puxa tudo pra string
            self.last_response = str(raw)

            if isinstance(raw, dict):
                data = raw
            elif isinstance(raw, str):
                try:
                    data = json.loads(raw.replace("'", '"'))
                except json.JSONDecodeError:
                    match = re.search(r"\{.*\}", 
                                    raw, 
                                    re.DOTALL)
                    if not match:
                        self._log_error("JSON não encontrado na string", raw)
                        
                        return self._fallback(game, "JSON não encontrado na string")
                    
                    data = json.loads(match.group())

            # Aqui pegamos o que a LLM gerou e colocamos no nosso jogo como uma ação
            row = int(data["row"])
            col = int(data["col"])

            action = (
                data.get("action", "reveal")
                .lower()
                .strip()
            )

            if action not in ("reveal", "flag"):
                action = "reveal"

            reasoning = data.get("reasoning", "")

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


            state_cell = game.get_cell_state(row, col)

            if state_cell not in (HIDDEN,FLAGGED):
                self._log_error(
                    f"Célula já revelada ({row},{col})",
                    raw,
                )
                return self._fallback(game,
                    "célula já revelada",
                )

            # Resultado final
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

        # Tratamento de Erros
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
            try:
                # Caso chegue no máximo de etapas, a gente pega o último resultado válido gerado pelo CodeAct
                for step in agent1.memory.steps:
                    # O output dos códigos executados fica salvo nas observações
                    if hasattr(step, 'observations') and step.observations:
                        match = re.search(r"(\{.*'row'.*'col'.*\})", str(step.observations), re.DOTALL)
                        if match:
                            data = ast.literal_eval(match.group(1))
                            row, col = int(data["row"]), int(data["col"])
                            action = data.get("action", "reveal").lower()
                            
                            result = {"type": action, "row": row, "col": col, "source": "llm_codeact_recuperado", "reasoning": "Resgatado da memória com sucesso!"}
                            self._log_success(result)
                            return result
            except:
                pass # Se até o roubo de memória falhar, desiste e vai pro fallback

            self._log_error(f"Erro no CodeAgent: {e}", str(e))
            return self._fallback(game, "Falha total do agente")

    # Funções auxiliares
    def _number_neighbors(self, game, r, c):

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

 

