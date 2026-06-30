import py_trees
from game import MinesweeperGame, REVEALED, HIDDEN, FLAGGED

'''
Itens importantes para cada ação:
- "action": dict {type: "reveal"|"flag", row, col, source, reasoning}
- "game": O jogo propriamente dito
'''


'''
## S1: CÉLULA SEGURA ÓBVIA ##
Regra: se o número N == quantidade de bandeiras ao redor, Então todos os outros vizinhos ocultos da células são SEGUROS
'''
class ExisteCelulaSegura(py_trees.behaviour.Behaviour):
    def __init__(self, game: MinesweeperGame):
        super().__init__("Existe Célula\nSegura Óbvia?")
        self.game = game
        self.bb   = py_trees.blackboard.Client(name=self.name)
        self.bb.register_key("action", access=py_trees.common.Access.WRITE)

    def update(self):
        g = self.game

        # Varrer todo o tabuleiro: de cima pra baixo, da esquerda para a direita
        for r in range(g.rows):
            for c in range(g.cols):
                if g.get_cell_state(r, c) != REVEALED:
                    continue

                # Ele vai pegar o número da célula
                num = g.get_number(r, c)
                # Caso for 0, ele pula pra outra análise
                if num == 0:
                    continue
                # A partir do número da célula, ele compara com as flags vizinhas e não flags
                flags  = g.count_flags_around(r, c)
                hidden = g.hidden_neighbors(r, c)

                # Se o número já bateu, então os vizinhos estão seguros
                if flags == num and hidden:
                    target = hidden[0]
                    self.bb.action = {
                        "type":      "reveal",
                        "row":       target[0],
                        "col":       target[1],
                        "source":    "bt_safe",
                        "reasoning": f"({r},{c}) tem {num} bandeiras ao redor — vizinhos ocultos são seguros",
                    }
                    # True na Behavior Tree
                    return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE


'''
## S2: MINA ÓBVIA ##
Regra: se o número N == quantidade de vizinhos ocultos, Então todos os TODOS os vizinhos ocultos são minas
'''
class ExisteMina(py_trees.behaviour.Behaviour):
    def __init__(self, game: MinesweeperGame):
        super().__init__("Existe Mina\nÓbvia?")
        self.game = game
        self.bb   = py_trees.blackboard.Client(name=self.name)
        self.bb.register_key("action", access=py_trees.common.Access.WRITE)

    def update(self):
        g = self.game
        # Varrer todo o tabuleiro: de cima pra baixo, da esquerda para a direita
        for r in range(g.rows):
            for c in range(g.cols):
                if g.get_cell_state(r, c) != REVEALED:
                    continue
                # Mesma coisa da parte de cima
                num    = g.get_number(r, c)
                if num == 0:
                    continue
                flags  = g.count_flags_around(r, c)
                hidden = g.hidden_neighbors(r, c)
                remaining = num - flags
                # células ocultas restantes == minas restantes
                if remaining > 0 and remaining == len(hidden):
                    target = hidden[0]
                    self.bb.action = {
                        "type":      "flag",
                        "row":       target[0],
                        "col":       target[1],
                        "source":    "bt_mine",
                        "reasoning": f"({r},{c}) precisa de {remaining} minas e tem {len(hidden)} ocultas",
                    }
                    return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE

'''
## S3: Subconjuntos ##
Regra: Nessa parte, a gente vai comparar células em pares e com base nisso vamos observar se os vizinhos ocultos de uma célula A são um subconjunto dos vizinhos ocultos da célula B, a partir disso temos dois pontos:
    1. Diferença == 0 -> A célula A já pegou todas as minas, logo todas células que só a B possui são seguras.
    2. Diferença == Quantidade de células extras -> A Célula A tem suas X minas, e a Célula B precisa exatamente do restante, logo, as células extras de B são MINAS.
'''
class Subconjuntos(py_trees.behaviour.Behaviour):
    def __init__(self, game):
        super().__init__("Subconjuntos")
        self.game = game
        self.bb = py_trees.blackboard.Client(name=self.name)
        self.bb.register_key("action", access=py_trees.common.Access.WRITE)

    def update(self):
        g = self.game
        # Coletar todas as células ativas, ou seja, precisam de definição dos vizinhos
        active_cells = []
        # Varrer todo o tabuleiro: de cima pra baixo, da esquerda para a direita
        for r in range(g.rows):
            for c in range(g.cols):
                if g.get_cell_state(r, c) == REVEALED:
                    # Número da célula analisada
                    num = g.get_number(r, c)
                    if num > 0:
                        # Fazer um set ao invés da função pura para fazer operações no futuro
                        hidden = set(g.hidden_neighbors(r, c))
                        flags = g.count_flags_around(r, c)
                        rem_mines = num - flags

                        if hidden and rem_mines > 0:

                            # Pra identificar melhor, eu coloquei nas células a identificação de posição (coordenada), quais estão escondidas e quais são minas
                            active_cells.append({
                                "pos": (r, c),
                                "hidden": hidden,
                                "mines": rem_mines
                            })
        
        # Comparar pares de células (A e B)
        for cell_A in active_cells:
            for cell_B in active_cells:
                if cell_A["pos"] == cell_B["pos"]:
                    continue
                
                set_A = cell_A["hidden"]
                set_B = cell_B["hidden"]
                
                # Se A é um subconjunto estrito de B (B engloba A, mas B tem mais casas)
                if set_A.issubset(set_B) and set_A != set_B:
                    diff_hidden = list(set_B - set_A)
                    diff_mines  = cell_B["mines"] - cell_A["mines"]
                    
                    target = diff_hidden[0] # Pega a primeira casa que sobrou para agir
                    
                    # Cénario 1: As casas restantes são SEGURAS
                    if diff_mines == 0:
                        self.bb.action = {
                            "type":      "reveal",
                            "row":       target[0],
                            "col":       target[1],
                            "source":    "bt_subset_safe",
                            "reasoning": f"Subconjunto: {cell_A['pos']} anula {cell_B['pos']} -> ({target[0]},{target[1]}) é segura",
                        }
                        return py_trees.common.Status.SUCCESS
                        
                    # Cenário 2: As casas restantes são MINAS
                    elif diff_mines == len(diff_hidden):
                        self.bb.action = {
                            "type":      "flag",
                            "row":       target[0],
                            "col":       target[1],
                            "source":    "bt_subset_mine",
                            "reasoning": f"Subconjunto: Resto de {cell_B['pos']} contra {cell_A['pos']} força mina em ({target[0]},{target[1]})",
                        }
                        return py_trees.common.Status.SUCCESS

        return py_trees.common.Status.FAILURE

'''
## S4: LLM ##
Regra: Aqui, a gente vai pro famoso "pergunta para os universitários" :). Dado que nenhuma outra célula deu certo, chamamos a LLM para tomar a melhor decisão com base no seu pensamento.
'''
class NenhumaCelulaObvia(py_trees.behaviour.Behaviour):
    def __init__(self):
        super().__init__("Nenhuma\nCélula Óbvia?")

    def update(self):
        return py_trees.common.Status.SUCCESS


class ChamarLLM(py_trees.behaviour.Behaviour):
    def __init__(self, game: MinesweeperGame, llm_agent):
        super().__init__("Chamar LLM\n(Incerteza)")
        self.game      = game
        self.llm_agent = llm_agent
        self.bb        = py_trees.blackboard.Client(name=self.name)
        self.bb.register_key("action", access=py_trees.common.Access.WRITE)

    def update(self):
        # Chamamos o LLM Agent e a partir do resultado, entregamos a resposta.
        # Caso queira ver mais, o arquivo 'llm_agent.py' está abordando mais sobre.
        result = self.llm_agent.decide(self.game)
        if result:
            self.bb.action = result
            r, c = result["row"], result["col"]
            self.game.set_highlight(r, c, "llm")
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE


## Classe auxiliar para mostrar no jogo se é flag OU se é reveal (mais fácil de modular do que duas classes, uma que revela ou uma que dá flag).
class ExecutarAcaoBB(py_trees.behaviour.Behaviour):
    def __init__(self, game):
        super().__init__("Executar\nAção")
        self.game = game
        self.bb = py_trees.blackboard.Client(name=self.name)
        self.bb.register_key("action", access=py_trees.common.Access.READ)

    def update(self):
        act = self.bb.action
        
        # Puxa o tipo de ação que o nó anterior (S1, S2 ou S3) decidiu
        if act["type"] == "reveal":
            self.game.set_highlight(act["row"], act["col"], "safe")
        elif act["type"] == "flag":
            self.game.set_highlight(act["row"], act["col"], "mine")
            
        return py_trees.common.Status.SUCCESS    
    

# CONSTRUÇÃO DA ÁRVORE
def build_tree(game: MinesweeperGame, llm_agent) -> py_trees.behaviour.Behaviour:
    root = py_trees.composites.Selector(name="Raiz ?", memory=False)

    # S1 — célula segura
    s1 = py_trees.composites.Sequence(name="S1: Segura", memory=False)
    s1.add_children([ExisteCelulaSegura(game), ExecutarAcaoBB(game)])

    # S2 — mina óbvia
    s2 = py_trees.composites.Sequence(name="S2: Mina", memory=False)
    s2.add_children([ExisteMina(game), ExecutarAcaoBB(game)])

    # S3 - teste de subconjuntos
    s3 =  py_trees.composites.Sequence(name="S3: Subconjuntos", memory=False)
    s3.add_children([Subconjuntos(game), ExecutarAcaoBB(game)])

    # S3 — LLM
    s4 = py_trees.composites.Sequence(name="S4: LLM", memory=False)
    s4.add_children([NenhumaCelulaObvia(), ChamarLLM(game, llm_agent)])

    root.add_children([s1, s2, s3, s4])
    root.setup_with_descendants()
    return root



# EXECUTOR: roda a BT e retorna a ação decidida
def run_tree(tree: py_trees.behaviour.Behaviour,
             game: MinesweeperGame) -> dict | None:
    # Limpa action no blackboard antes do tick
    client = py_trees.blackboard.Client(name="Runner")
    try:
        client.register_key("action", access=py_trees.common.Access.WRITE)
    except Exception:
        pass
    try:
        client.action = None
    except Exception:
        pass
    
    # Tick para passar pela decisão da BT
    tree.tick_once()

    # Lê a ação resultante
    reader = py_trees.blackboard.Client(name="Reader")
    try:
        reader.register_key("action", access=py_trees.common.Access.READ)
    except Exception:
        pass
    try:
        return reader.action
    except Exception:
        return None

# HELPER: coleta status de todos os nós para exibição
def collect_node_status(tree) -> dict:
    status = {}
    def walk(node):
        status[node.name] = node.status.value if node.status else "idle"
        if hasattr(node, "children"):
            for child in node.children:
                walk(child)
    walk(tree)
    return status
