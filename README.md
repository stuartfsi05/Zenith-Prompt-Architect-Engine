# Zenith | Prompt Architect Engine

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Architecture Modular](https://img.shields.io/badge/Architecture-Modular%20%26%20Decoupled-purple)
![AI Agnostic](https://img.shields.io/badge/AI-LLM%20Agnostic-orange)
![Tests Passing](https://img.shields.io/badge/Tests-Passing-brightgreen)

**Zenith** é um **Motor Cognitivo Polimórfico** desenvolvido para orquestrar fluxos de trabalho de inteligência artificial complexos e autônomos. Projetado sob os princípios de Clean Architecture e SOLID, o Zenith oferece uma plataforma robusta, modular e segura para a criação de agentes inteligentes.

Sua arquitetura permite que o sistema adapte sua "persona" e estratégia de execução dinamicamente com base na intenção do usuário, variando entre modos de raciocínio lógico, codificação técnica e investigação factual.

---

## 🔥 Funcionalidades Principais

### 🧠 Motor Polimórfico
O Zenith analisa cada solicitação e seleciona a estratégia cognitiva ideal:
*   **Arquitetura de Prompt Dinâmica:** O sistema constrói prompts contextuais em tempo real, injetando diretrizes específicas (Code Engineer, Researcher, Prompt Architect).
*   **Roteamento de Intenção:** Um módulo analisador classifica a complexidade e a natureza da tarefa (Raciocínio, Geração, Planejamento) para alocar os recursos adequados.

### 🔌 LLM Provider Agnostic
O núcleo do sistema é desacoplado de provedores específicos. Através da abstração `LLMProvider`, o Zenith é capaz de integrar diferentes modelos. Atualmente, possui implementação nativa robusta para **Google Gemini 2.5 Flash**, otimizada para velocidade e eficiência.

### 📚 RAG Híbrido Avançado
O sistema de recuperação de informações (RAG) combina o melhor de dois mundos:
*   **Busca Vetorial:** Para capturar similaridade semântica profunda.
*   **Busca por Palavras-Chave (BM25):** Para precisão terminológica.
*   **Reranking:** Um passo final de reordenação inteligente para garantir que apenas o contexto mais relevante chegue ao modelo.

### ⚖️ The Judge (Self-Correction)
O sistema possui um módulo de auditoria interna ("O Juiz") que avalia a qualidade das respostas geradas antes de entregá-las ao usuário. Se a resposta não atingir os critérios de qualidade, o sistema inicia um loop de auto-correção autônomo.

### 💾 Memória e Persistência
*   **Memória Semântica Progressiva:** O sistema mantém um resumo mestre e um perfil de usuário que evoluem com o tempo.
*   **Banco de Dados SQLite:** Todas as sessões e interações são persistidas localmente de forma estruturada, permitindo auditoria e continuidade.

---

## 🛠 Arquitetura do Projeto

O projeto segue uma estrutura modular clara:

```text
Zenith/
├── data/
│   ├── vector_store/    # Índices Vetoriais e BM25
│   └── zenith.db        # Banco SQLite de Histórico e Sessões
├── knowledge_base/      # Documentos para ingestão (.md/.txt)
├── src/
│   ├── core/
│   │   ├── agent.py     # Orquestrador Central
│   │   ├── analyzer.py  # Roteador de Intenção
│   │   ├── database.py  # Gerenciador de Persistência SQLite
│   │   ├── judge.py     # Módulo de Auto-Avaliação
│   │   ├── memory.py    # Memória Semântica
│   │   ├── personas.py  # Definições de Personas do Sistema
│   │   ├── llm/         # Abstração e Implementação de LLMs
│   │   └── knowledge/   # RAG Manager, Retriever e Reranker
│   ├── scripts/         # Scripts utilitários (ex: verify_db.py)
│   └── main.py          # Ponto de Entrada
├── tests/               # Suíte de Testes (pytest)
└── requirements.txt
```

---

## 🚀 Como Iniciar

### Pré-requisitos
- Python 3.10 ou superior
- Uma chave de API do Google AI Studio

### Instalação

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/stuartfsi05/Zenith-Prompt-Architect-Engine.git
    cd Zenith-Prompt-Architect-Engine
    ```

2.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuração:**
    Crie um arquivo `.env` na raiz do projeto com suas credenciais:
    ```env
    GOOGLE_API_KEY=sua_chave_aqui
    MODEL_NAME=gemini-2.5-flash
    TEMPERATURE=0.1
    ```

### ▶️ Executando

Para iniciar o agente interativo:

```bash
python -m src.main
```

O sistema irá automaticamente:
1. Validar a configuração e ambiente (`BootstrapService`).
2. Indexar novos documentos encontrados na pasta `knowledge_base/`.
3. Iniciar a interface de chat no terminal.

---

## 🧪 Testes

O projeto mantém uma alta cobertura de testes para garantir a estabilidade. Para rodar a suíte de testes:

```bash
python -m pytest
```

---

## 📜 Licença

Proprietário e Confidencial. Todos os direitos reservados.
Desenvolvido como projeto de pesquisa em Agentes Autônomos Avançados.
