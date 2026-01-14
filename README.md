# Zenith | Prompt Architect Engine

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-Proprietary-red)
![Status](https://img.shields.io/badge/status-Active-green)
![RAG](https://img.shields.io/badge/RAG-Enabled-purple)

**Zenith** is a high-performance, modular autonomous agent engine designed to orchestrate complex generative AI workflows using Google's Gemini API. It has been evolved into a **Hybrid RAG Engine**, combining strict internal knowledge retrieval with grounded external search capabilities.

## 🧠 Core Capabilities

### 1. RAG (Retrieval-Augmented Generation)
Zenith is equipped with a dedicated "Knowledge Base". It can ingest authoritative documents (Markdown/Text) and use them as the primary source of truth for methodology and logic.
-   **Engine**: LangChain + ChromaDB
-   **Embeddings**: Google Generative AI Embeddings
-   **Ingestion**: Automated script to chunk and index documents.

### 2. Google Search Grounding (Strict Mode)
The engine implements a **Strict Grounding Protocol** to prevent hallucinations and maintain methodological integrity:
-   **External Search**: Used *exclusively* for verifying recent facts, new libraries, or current events.
-   **Internal Knowledge**: Used *exclusively* for core logic, prompt engineering methodology, and strategic reasoning.

### 3. Modular Architecture
The codebase follows strict **Clean Architecture** principles and is fully **PEP-8 Compliant**:
-   `src/core`: The brain (Agent, Analyzer, Knowledge Base).
-   `src/scripts`: Operational tools (Ingestion).
-   `src/utils`: Support systems (Logging, Security).

---

## 🛠 Project Structure

```text
Zenith/
├── data/
│   ├── chroma_db/       # Vector Database (The Memory)
│   └── prompts/         # System Instructions (The Personality)
├── knowledge_base/      # Drop your .md/.txt manuals here
├── src/
│   ├── core/
│   │   ├── agent.py     # Central Orchestrator
│   │   ├── knowledge.py # RAG Handler
│   │   └── ...
│   ├── scripts/
│   │   └── ingest.py    # Memory Builder
│   └── main.py          # Entry Point
└── requirements.txt
```

---

## 🚀 Getting Started

### Prerequisites
-   Python 3.10+
-   Google AI Studio API Key

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/stuartfsi05/Zenith-Prompt-Architect-Engine.git
    cd Zenith-Prompt-Architect-Engine
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    -   Create a `.env` file (see `.env.example`).
    -   Add your `GOOGLE_API_KEY`.
    -   Set `SYSTEM_PROMPT_PATH=data/prompts/system_instruction.txt` (or your preferred file).

### 🧠 Building the "Brain" (RAG)
Before running Zenith, you must teach it your manual:
1.  Place your `.md` or `.txt` files in the `knowledge_base/` folder.
2.  Run the ingestion script:
    ```bash
    python -m src.scripts.ingest
    ```
    *This creates the Vector Database in `data/chroma_db`.*

### ▶️ Usage
Run the main engine:
```bash
python -m src.main
```

---

## 🔒 Security & Grounding Rules

Zenith operates under the **TCRE-A Protocol** variants.
A hardcoded injection in `src/core/agent.py` ensures:
> "Use a Ferramenta de Busca APENAS para verificar fatos recentes... Para metodologia... use EXCLUSIVAMENTE sua Base de Conhecimento Interna."

---

## 📜 License
Copyright © 2025. All Rights Reserved.
This software is proprietary and confidential.
