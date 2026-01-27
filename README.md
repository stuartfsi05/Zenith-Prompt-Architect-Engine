# Zenith | Prompt Architect Engine (SOTA Edition 2.1)

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Architecture Modular](https://img.shields.io/badge/Architecture-Modular%20%26%20Decoupled-purple)
![AI Agnostic](https://img.shields.io/badge/AI-LLM%20Agnostic-orange)
![Tests Passing](https://img.shields.io/badge/Tests-Passing-brightgreen)

**Zenith** é um **Motor Cognitivo Polimórfico** de alta performance, desenhado para orquestrar fluxos de trabalho de IA complexos e autônomos.

Recentemente refatorado para a arquitetura **Modular SOTA 2.1**, o Zenith agora é desacoplado do provedor de LLM, possui uma base de conhecimento modular e conta com uma suíte de testes robusta.

---

## 💎 Diferenciais da Versão 2.1 (Refactor)

Além dos pilares originais (RAG Híbrido, Roteador Cognitivo, Chain-of-Thought), a nova versão introduz:

### 1. 🔌 LLM Provider Agnostic
O sistema foi desacoplado da API do Google. Através da nova camada de abstração `LLMProvider`, é possível integrar qualquer modelo (OpenAI, Anthropic, Ollama) implementando apenas uma classe. O sistema já vem com a implementação `GoogleGenAIProvider` nativa.

### 2. 🧩 Base de Conhecimento Modular
A antiga `StrategicKnowledgeBase` monolítica foi dividida em três componentes especializados:
- **Manager:** Orquestra o fluxo.
- **Retriever:** Cuida da busca bruta (Vetorial + BM25).
- **Reranker:** Reordena os resultados usando inteligência artificial.

### 3. 🛡️ Segurança & Bootstrap Robusto
- **Sem Pickle Inseguro:** O índice de palavras-chave (BM25) é reconstruído em memória ou carregado de forma segura, eliminando riscos de execução de código malicioso.
- **Fail-Safe Startup:** O novo `BootstrapService` garante que todos os diretórios, configurações e índices estejam íntegros antes do sistema iniciar.

### 4. 🧪 Infraestrutura de Testes
O projeto agora conta com cobertura de testes unitários (`pytest`) para os componentes críticos: Configuração, Bootstrap, Analisador de Intenção e o próprio Agente Central.

---

## 🛠 Arquitetura do Projeto

O código segue estritamente os princípios de **Clean Architecture**, **SOLID** e **Single Responsibility**:

```text
Zenith/
├── data/
│   ├── vector_store/    # Banco Vetorial (FAISS)
│   └── prompts/         # Instruções de Sistema
├── knowledge_base/      # Seus documentos (.md/.txt)
├── src/
│   ├── core/
│   │   ├── llm/         # Abstração de Provedores LLM
│   │   ├── knowledge/   # Package da Base de Conhecimento (Manager, Retriever, Reranker)
│   │   ├── agent.py     # Orquestrador Central
│   │   ├── analyzer.py  # Roteador Cognitivo
│   │   ├── bootstrap.py # Inicialização e Verificação do Sistema
│   │   ├── config.py    # Configuração Centralizada
│   │   ├── judge.py     # Auditor de Qualidade (Self-Healing)
│   │   └── memory.py    # Gestão de Memória de Longo Prazo
│   ├── utils/
│   └── main.py          # Entry Point Limpo
├── tests/               # Suíte de Testes Unitários
└── requirements.txt
```

---

## 🚀 Como Iniciar

### Pré-requisitos
- Python 3.10 ou superior
- Uma chave de API (Google AI Studio por padrão)

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
    - Crie um arquivo `.env` na raiz:
    ```env
    GOOGLE_API_KEY=sua_chave_aqui
    MODEL_NAME=gemini-2.5-flash
    TEMPERATURE=0.1
    ```

### ▶️ Executando

O sistema possui um sistema de **auto-ingestão**. Basta colocar seus arquivos na pasta `knowledge_base/` e rodar:

```bash
python -m src.main
```

O `BootstrapService` detectará novos arquivos, atualizará o banco vetorial e iniciará o chat automaticamente.

---

## 🧪 Desenvolvimento e Testes

Para garantir a estabilidade das modificações, execute a suíte de testes antes de qualquer commit:

```bash
python -m pytest tests/
```

---

## 📜 Licença
Proprietário e Confidencial. Todos os direitos reservados.
Desenvolvido como projeto de pesquisa em Agentes Autônomos Avançados.
