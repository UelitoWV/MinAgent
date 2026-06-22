
# MinAgent - Campo Minado Autônomo com Árvore de Comportamento e LLM - Wellington Viana

Este projeto implementa um agente autônomo capaz de jogar Campo Minado de forma inteligente. A tomada de decisão combina técnicas clássicas estruturadas através de uma Árvore de Comportamento (Behavior Tree) com a capacidade cognitiva de modelos de linguagem de grande porte (LLMs) como fallback para situações de alta incerteza.

A interface gráfica foi desenvolvida combinando Pygame (para a renderização veloz do tabuleiro de células) e Matplotlib (para exibição das estatísticas do jogo, log detalhado das decisões e árvore de execução).

---

## Estrutura do Projeto e Visualização de Arquivos

Abaixo está representada a estrutura de diretórios e arquivos presentes na raiz do projeto:

```text
RurAgent/
|-- .env                     (Arquivo local de credenciais, nao enviado ao git)
|-- .env.example             (Exemplo de configuracao das variaveis de ambiente)
|-- .gitignore               (Regras para ignorar arquivos no versionamento)
|-- behavior_tree.py         (Estrutura e execucao da Arvore de Comportamento)
|-- config.py                (Variaveis de configuracao do jogo e visual)
|-- game.py                  (Engine e regras do Campo Minado)
|-- llm_agent.py             (Agente e interface com a API da Hugging Face)
|-- main.py                  (Ponto de entrada do sistema e loop principal)
|-- README.md                (Este arquivo de documentacao)
|-- renderer.py              (Interface grafica mesclando Pygame e Matplotlib)
```

O papel detalhado de cada arquivo de código:

*   **main.py**: Ponto de entrada do programa. Coordena o fluxo do jogo, a inicialização automática do primeiro clique (para garantir um começo seguro), a execução de passos manuais ou automáticos e a interface gráfica principal.
*   **config.py**: Arquivo central de configurações. Permite ajustar o tamanho do tabuleiro (padrão: 12x12), a quantidade de minas (padrão: 32), configurações do modelo de LLM (tokens máximos, ID do modelo), cores da interface gráfica e velocidade de execução automática.
*   **game.py**: Implementa a engine e as regras do Campo Minado. Gerencia o estado das células (oculta, revelada, marcada com bandeira, explodida), a distribuição aleatória e segura de minas após a primeira jogada, o algoritmo de revelação em cascata (flood fill) e exportação do estado atual do jogo para o formato ASCII (usado pelo agente de LLM).
*   **behavior_tree.py**: Define a estrutura da Árvore de Comportamento utilizando o framework `py_trees`. Ela orquestra a execução de estratégias determinísticas de resolução antes de recorrer à LLM.
*   **llm_agent.py**: Gerencia a comunicação com a API de inferência da Hugging Face. Prepara o prompt descrevendo o tabuleiro atual em formato de caracteres (ASCII) e a lista de células de fronteira ativas, solicitando uma análise matemática em formato JSON para a tomada de decisão.
*   **renderer.py**: Constrói a janela gráfica principal integrando Pygame e Matplotlib. Contém a visualização interativa do tabuleiro, gráficos estatísticos e painéis de logs para acompanhar a tomada de decisão do agente passo a passo.

---

## Arquitetura de Decisão (Árvore de Comportamento)

<img width="8192" height="1527" alt="BehaviorTree MinAgent" src="https://github.com/user-attachments/assets/405c1210-dac0-41e2-95dd-24ef1040f615" />

O comportamento do agente segue uma prioridade estrita de regras executada recursivamente a cada turno (tick da árvore). A árvore está organizada sob um nó Selector principal que tenta executar as seguintes sequências por ordem de prioridade:

1.  **S1: Célula Segura Óbvia**
    *   **Regra**: Se um número revelado N possui exatamente N bandeiras marcadas ao redor, então todos os outros vizinhos ocultos desse número são seguros e podem ser revelados.
2.  **S2: Mina Óbvia**
    *   **Regra**: Se a quantidade de vizinhos ocultos ao redor de uma célula revelada N é exatamente igual à quantidade de minas restantes que faltam ser identificadas para aquele número, então todas essas células ocultas vizinhas são marcadas obrigatoriamente com bandeiras.
3.  **S3: Subconjuntos**
    *   **Regra**: Compara pares de células adjacentes na fronteira ativa. Se as células ocultas sob a influência da célula A forem um subconjunto estrito das células ocultas sob a influência da célula B:
        *   Caso a diferença de minas necessárias entre as duas células seja zero, as células extras exclusivas de B são seguras.
        *   Caso a diferença de minas necessárias seja igual ao número de células extras de B, essas células extras contêm minas obrigatoriamente.
4.  **S4: Agente LLM**
    *   **Regra**: Ativada somente quando nenhuma célula pode ser deduzida com 100% de certeza matemática pelas regras locais anteriores. A LLM recebe os dados das células da fronteira e calcula o risco relativo de cada candidata, executando a ação com o menor índice de risco estimado.

Se houver uma falha crítica na conexão ou na estruturação da resposta da LLM, o agente possui um mecanismo automático de fallback que executa uma jogada segura aleatória dentro da fronteira atual de modo a evitar o travamento da partida.

---

## Requisitos e Dependências

Para executar este projeto, você precisará ter instalado o Python 3.10 ou superior. As principais dependências externas do ecossistema Python utilizadas são:

*   **pygame**: Renderização visual do tabuleiro de blocos.
*   **matplotlib**: Estruturação dos painéis, logs, botões e dados estatísticos.
*   **numpy**: Processamento eficiente dos arrays visuais gerados pelo Pygame para inserção no Matplotlib.
*   **py_trees**: Biblioteca para estruturação e execução da Árvore de Comportamento.
*   **huggingface_hub**: Comunicação direta com os Inference Providers da Hugging Face para consulta da LLM.
*   **python-dotenv**: Carregamento de variáveis de ambiente a partir do arquivo `.env`.

---

## Como Inicializar e Executar o Projeto

Siga os passos descritos abaixo para configurar seu ambiente local e iniciar o jogo.

### 1. Clonar ou Acessar a Pasta do Projeto
Certifique-se de que está na raiz do diretório do projeto onde os arquivos listados acima se encontram.

### 2. Criar e Ativar um Ambiente Virtual
É altamente recomendado criar um ambiente virtual dedicado para evitar conflitos de pacotes:

No Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

No Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar as Dependências
Com o ambiente virtual ativo, execute o comando abaixo para instalar todos os pacotes necessários:
```bash
pip install pygame matplotlib numpy py-trees huggingface_hub python-dotenv
```

### 4. Configurar as Variáveis de Ambiente e Requisitos do Token Hugging Face
O agente de LLM requer acesso à API da Hugging Face para obter as previsões lógicas quando a árvore determinística de comportamento não consegue resolver o cenário.

#### Requisitos Importantes do Token de Acesso (HF_TOKEN)
Para que as chamadas ao modelo de inferência funcionem de forma correta, o token gerado na sua conta da Hugging Face deve seguir regras estritas de permissão:
1.  **Tipo de Token**: O token gerado deve ser do tipo **Fine-grained (Grão Fino)**. Não utilize tokens de escrita genéricos ou antigos sem escopo definido.
2.  **Permissões e Escopos (Inference Provider)**: No momento da criação do token, você deve habilitar especificamente as permissões voltadas à inferência de modelos:
    *   Marque a permissão de **Inference** (especificamente **Make calls to the serverless Inference API** ou permissões associadas a **Inference Providers**).
    *   Isso garante que o `InferenceClient` possa autenticar e encaminhar os dados para o modelo definido na variável `LLM_MODEL`.

#### Passos de Configuração do Ambiente:
1.  Crie uma cópia do arquivo `.env.example` e salve-a com o nome `.env` no mesmo diretório:
    ```bash
    copy .env.example .env
    ```
    *(No Linux ou macOS, utilize `cp .env.example .env`)*

2.  Abra o arquivo `.env` em um editor de texto e insira o seu token pessoal fine-grained com escopo de Inference na variável `HF_TOKEN`:
    ```env
    HF_TOKEN=seu_token_real_da_huggingface_aqui_sem_aspas
    LLM_MODEL=meta-llama/Meta-Llama-3-70B-Instruct:novita
    LLM_MAX_TOKENS=512
    ```
    *Nota: Você pode modificar a variável `LLM_MODEL` para apontar para outro modelo de instrução compatível com a API se assim desejar.*

### 5. Executar o Aplicativo
Com as configurações do arquivo `.env` preenchidas, inicie o sistema executando:
```bash
python main.py
```

### 6. Controles da Interface Gráfica
Uma janela com título "Campo Minado — BT + LLM Agent" será exibida contendo três botões interativos na base esquerda della:

*   **Step**: Executa exatamente uma única jogada do agente autônomo (seja resolvendo por regras determinísticas da Árvore de Comportamento ou consultando a LLM).
*   **Auto**: Inicia a reprodução contínua e automática do jogo com o intervalo de tempo configurado no arquivo `config.py`. Pressione o mesmo botão (que mudará de nome para "Parar") a qualquer momento para pausar.
*   **Resetar**: Reinicia o tabuleiro atualizando todas as variáveis de jogo, permitindo começar um novo jogo do zero mantendo os mesmos agentes.

---

## Disclaimer sobre o Uso de Inteligência Artificial

Este projeto contou com assistência de Inteligência Artificial (especificamente os modelos Claude Sonnet 4.6) para a codificação de componentes específicos:

*   **Interface Gráfica e Visualização (renderer.py)**: O módulo visual completo integrando Pygame e Matplotlib para renderização do tabuleiro e atualização em tempo real do log e das estatísticas foi implementado a partir de assistência de IA.
*   **Lógica de Tradução Textual (game.py)**: A função `to_ascii` responsável por converter a matriz em grade textual estruturada foi projetada com IA para garantir a precisão dos dados enviados no contexto do modelo de linguagem.
*   **Estruturação de Prompts e Tratamento de Respostas**: O refinamento e correção de erros na desserialização de dados JSON em `llm_agent.py` foram aprimorados via ferramentas de inteligência artificial de modo a assegurar que as jogadas do agente de LLM fossem devidamente integradas na Árvore de Comportamento.
