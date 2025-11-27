# Zenith | Prompt Architect Engine

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-Proprietary-red)
![Status](https://img.shields.io/badge/status-Active-green)

**Zenith** is a high-performance, modular autonomous agent engine designed to orchestrate complex generative AI workflows using Google's Gemini API. It serves as the foundational runtime for the **TCRE-A Protocol**, providing a secure and robust environment for prompt engineering, execution, and evaluation.

> ℹ️ **Open Core Edition:** This repository runs in **Demo Mode** by default. It utilizes a streamlined protocol (`v. Lite`) to demonstrate the engine's orchestration capabilities and architectural patterns without accessing the proprietary TCRE-A Knowledge Base reserved for the Enterprise edition.

---

## 🏗 Project Architecture

Zenith is built on **Clean Architecture** principles, utilizing a modular **Orchestrator Pattern** to manage the lifecycle of generative tasks. The system is designed to be deterministic, auditable, and secure by default.

### Workflow Pipeline

The engine follows a strict execution protocol for every request:

`Input` → **Strategic Analysis** (FDU) → **Semantic Validation** (SIC) → **Execution** (LLM) → **Self-Correction** (The Judge) → `Output`

### Core Components

- **`src/core/agent.py` (The Orchestrator):**
  Acts as a **Facade**. It abstracts the complexity of the underlying subsystems, managing the flow of data between analysis, validation, and execution modules.

- **`src/core/analyzer.py` (Strategic Module):**
  Implements the **Unified Decision Framework (FDU)**. It decomposes raw user intent into structured task vectors (Nature, Complexity, Quality Requirements).

- **`src/core/validator.py` (Guardrails):**
  Enforces **Semantic Integrity Constraints (SIC)**. A logical gatekeeper that validates the alignment of the intended strategy against safety protocols.

- **`src/core/judge.py` (Constitutional AI):**
  An internal feedback loop implementation. It evaluates the generated output against a strict quality rubric to simulate self-reflection.

- **`src/core/config.py`:**
  A Singleton-based configuration manager using Python `dataclasses`. It enforces strict environment variable validation (Fail-fast strategy).

- **`src/utils/loader.py` (Security Core):**
  Implements a **Secure Fallback Protocol**. It specifically checks for the existence of the proprietary production prompt (`data/prompts/*`). If not found, it seamlessly degrades to "Demo Mode", ensuring IP is never exposed.

- **`src/utils/logger.py`:**
  Centralized logging infrastructure using `rich.logging` for structured debugging and monitoring.

---

## 🧩 Design Patterns Used

- **Facade Pattern:** Simplifies the interface to the complex subsystem of agents.
- **Strategy Pattern:** Allows for dynamic selection of prompting strategies based on input.
- **Dependency Injection:** System instructions are injected, facilitating testing and modularity.
- **Circuit Breaker/Fallback:** The Loader ensures business continuity even when secure assets are missing.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- A Google Account (for Gemini API)

### Installation Guide

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/stuartfsi05/Zenith-Prompt-Architect-Engine.git
    cd Zenith-Prompt-Architect-Engine
    ```

2.  **Set up a Virtual Environment (Highly Recommended):**
    * **Windows:**
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    * **Mac/Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment:**
    * Copy the example configuration:
        ```bash
        cp .env.example .env
        ```
    * **Get your API Key:** Visit [Google AI Studio](https://aistudio.google.com/), generate a free API Key.
    * **Update `.env`:** Open the file and paste your key:
        ```ini
        GOOGLE_API_KEY=AIzaSy...YourKeyHere
        ```

### Usage

Run the application via the CLI entry point:

```bash
python -m src.main
```

You will be greeted by the Zenith Interface. Type your query to interact with the agent. The system will automatically detect the environment and load the appropriate protocol (Demo vs. Enterprise).

Type `exit` or `quit` to terminate the session.

---

## 🔒 Security & IP Protection

Zenith is designed with IP protection as a first-class citizen.

1.  **Environment Isolation:** All sensitive keys are managed via `.env` files, strictly excluded from version control.
2.  **Sanitized Fallback:** The `loader.py` module prevents `FileNotFoundError` by falling back to a sanitized sample prompt if the proprietary system instruction is missing.

---

## 📜 License

Copyright © 2025. All Rights Reserved.
This software is proprietary and confidential. Unauthorized copying, transfer, or reproduction is strictly prohibited.
