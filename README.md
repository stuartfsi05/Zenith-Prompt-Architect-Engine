# Zenith | Prompt Architect Engine (SOTA Edition)

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Architecture SOTA](https://img.shields.io/badge/Architecture-SOTA%20FDU%202.0-purple)
![AI Powered](https://img.shields.io/badge/AI-Gemini%20Flash%202.0-orange)
![Status Active](https://img.shields.io/badge/Status-Operational-green)

**Zenith** não é apenas um chatbot. É um **Motor Cognitivo Polimórfico** de alta performance, desenhado para orquestrar fluxos de trabalho de IA complexos e autônomos.

Recentemente atualizado para a arquitetura **FDU 2.0 (State-of-the-Art)**, o Zenith combina o melhor da recuperação de informação (RAG Híbrido) com raciocínio profundo (Structured Chain-of-Thought) e autogestão (Self-Healing).

---

## 💎 O Que Torna o Zenith "SOTA"? (State-of-the-Art)

Diferente de agentes tradicionais que "alucinam" ou perdem o contexto, o Zenith opera sobre 5 pilares fundamentais:

### 1. 🧠 Hybrid Search (RAG 2.0)
O sistema não depende apenas de vetores. Ele utiliza uma **Busca Híbrida** para garantir que nenhuma informação seja perdida:
- **BM25 (Palavras-Chave):** Encontra termos exatos e técnicos rapidamente (cache persistente para performance).
- **Vetores (Semântica):** Entende o conceito e o significado por trás da pergunta.
- **Reciprocal Rank Fusion (RRF):** Funde os resultados dos dois mundos matematicamente.
- **LLM Reranking:** Um "segundo cérebro" (Cross-Encoder) relê os top-10 resultados e escolhe apenas os 3 mais relevantes para o contexto atual.

### 2. 🎭 Motor Polimórfico (Single Persistent Session)
O Zenith "muda de pele" sem perder a memória.
- Ele pode ser um **Investigador** em um turno, um **Programador Sênior** no próximo e um **Estrategista** no fim.
- Tudo isso acontece dentro de uma **Sessão Persistente Única**, garantindo que o contexto da conversa flua natural e continuamente.

### 3. 🚦 Roteador Cognitivo Resiliente
Antes de responder, um sub-agente (Router) analisa sua intenção:
- **Natureza:** É código? É texto? É planejamento?
- **Complexidade:** Precisa de RAG? Precisa de CoT (Chain-of-Thought)?
- **Resiliência:** Se o roteador falhar, ele aumenta a temperatura (criatividade) e tenta novamente antes de desistir.

### 4. 🔗 Structured Chain-of-Thought (CoT)
O Zenith é **forçado** a pensar antes de agir.
Todas as respostas complexas são precedidas por tags `<thinking>...</thinking>`, onde o agente planeja, critica a si mesmo e verifica fatos antes de gerar a resposta final para o usuário.

### 5. ❤️‍🩹 Self-Healing Loop (Autocorreção)
Um módulo "Juiz" (The Judge) avalia silenciosamente cada resposta gerada.
- Se a nota for baixa (< 80/100), o Zenith **auto-rejeita** a resposta, lê o feedback do juiz e tenta gerar uma versão melhorada, *antes* de mostrar qualquer coisa ao usuário.

### 6. 🖼️ Janela Deslizante de Contexto (Optimization)
Para evitar custos explosivos e erros de token, o Zenith mantém na memória ativa apenas as últimas **20 trocas de mensagens**, descartando automaticamente o que for irrelevante ("Sliding Window").

---

## 🛠 Arquitetura do Projeto

O código segue os princípios de **Clean Architecture** e **PEP-8**:

```text
Zenith/
├── data/
│   ├── chroma_db/       # Memória Vetorial (Semântica)
│   ├── bm25_index.pkl   # Memória de Palavras-chave (Rápida)
│   └── prompts/         # Instruções de Sistema
├── knowledge_base/      # Seus Manuais (.md/.txt) vão aqui
├── src/
│   ├── core/
│   │   ├── agent.py     # Orquestrador SOTA (O Cérebro)
│   │   ├── analyzer.py  # Roteador Cognitivo
│   │   ├── knowledge.py # Motor de Busca Híbrida
│   │   ├── validation.py# Guardrails de Segurança
│   │   └── judge.py     # Módulo de Autoavaliação
│   ├── scripts/
│   │   └── ingest.py    # Ingestão de Dados Automatizada
│   └── main.py          # Ponto de Entrada
└── requirements.txt
```

---

## 🚀 Como Iniciar

### Pré-requisitos
- Python 3.10 ou superior
- Uma chave de API do Google AI Studio (`GOOGLE_API_KEY`)

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

3.  **Configure o Ambiente:**
    - Crie um arquivo `.env` na raiz.
    - Adicione: `GOOGLE_API_KEY=sua_chave_aqui`
    - (Opcional) Ajuste o `MODEL_NAME` para `gemini-3-flash-preview` para máxima performance.

### 🧠 Treinando o Cérebro (Ingestão)

1.  Coloque seus arquivos de conhecimento (`.pdf`, `.md`, `.txt`) na pasta `knowledge_base/`.
2.  Inicie o programa. O sistema detectará mudanças e fará a ingestão **automaticamente**:
    ```bash
    python -m src.main
    ```
    *(Nota: Isso criará o banco vetorial e o índice BM25 otimizado).*

---

## 🛡️ Segurança e Guardrails

O Zenith implementa o protocolo **Semantic Validator**:
- **Bloqueio de PII:** Tenta detectar chaves de API ou cartões de crédito vazados.
- **Estrutura:** Garante que o Roteador sempre responda em JSON válido.
- **Grounding:** Prioriza a Base de Conhecimento Interna sobre alucinações.

---

## 📜 Licença
Proprietário e Confidencial. Todos os direitos reservados.
Desenvolvido como projeto de pesquisa em Agentes Autônomos Avançados.
