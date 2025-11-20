# Zenith | Prompt Architect Engine

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-Proprietary-red)
![Status](https://img.shields.io/badge/status-Active-green)

**Zenith** is a high-performance, modular autonomous agent engine designed to orchestrate complex generative AI workflows using Google's Gemini API. It serves as the foundational runtime for the **TCRE-A Protocol**, providing a secure and robust environment for prompt engineering, execution, and evaluation.

---

## 🏗 Project Architecture

Zenith is built on **Clean Architecture** principles, utilizing a modular **Orchestrator Pattern** to manage the lifecycle of generative tasks. The system is designed to be deterministic, auditable, and secure by default.

### Workflow Pipeline

The engine follows a strict execution protocol for every request:

`Input` → **Strategic Analysis** (FDU) → **Semantic Validation** (SIC) → **Execution** (LLM) → **Self-Correction** (The Judge) → `Output`

### Core Components

- **`src/core/agent.py` (The Orchestrator):**
  Acts as a **Facade**. It abstracts the complexity of the underlying subsystems, managing the flow of data between analysis, validation, and execution modules. It ensures that no raw input is processed without passing through the strategic layer.

- **`src/core/analyzer.py` (Strategic Module):**
  Implements the **Unified Decision Framework (FDU)**. It decomposes raw user intent into structured task vectors (Nature, Complexity, Quality Requirements) before any generation begins.

- **`src/core/validator.py` (Guardrails):**
  Enforces **Semantic Integrity Constraints (SIC)**. A logical gatekeeper that validates the alignment of the intended strategy against safety protocols and analytical depth requirements.

- **`src/core/judge.py` (Constitutional AI):**
  An internal feedback loop implementation. It evaluates the generated output against a strict quality rubric (Fidelity, Safety, Clarity, Efficiency) to simulate self-reflection and continuous improvement.

- **`src/core/config.py`:**
  A Singleton-based configuration manager using Python `dataclasses`. It enforces strict environment variable validation.

- **`src/utils/loader.py` (Security Core):**
  Implements a **Secure Fallback Protocol**. It specifically checks for the existence of the proprietary production prompt (`data/prompts/*`). If not found, it seamlessly degrades to "Demo Mode" using sanitized samples, ensuring IP is never exposed in unauthorized environments.

- **`src/utils/logger.py`:**
  Centralized logging infrastructure using `rich.logging`. It provides structured logs for debugging and beautiful console output for runtime monitoring.

---

## 🧩 Design Patterns

- **Facade Pattern:** The `ZenithAgent` provides a simplified interface to a complex subsystem of analyzers, validators, and judges.
- **Strategy Pattern:** The analysis module allows for dynamic selection of optimal prompting strategies (e.g., CoT, Step-Back) based on input complexity.
- **Dependency Injection:** System instructions and configurations are injected into the Agent, facilitating easy mocking and testing.
- **Fallback/Circuit Breaker:** The Loader implements a robust fallback mechanism to ensure business continuity (in demo mode) even when secure assets are unavailable.

---

## 🔒 Security & IP Protection

Zenith is designed with IP protection as a first-class citizen.

1.  **Environment Isolation:** All sensitive keys and configuration toggles are managed via `.env` files, which are strictly excluded from version control.
2.  **Sanitized Fallback:** The `loader.py` module specifically checks for the existence of the production system prompt. If not found, it seamlessly degrades to a "Demo Mode" using a sanitized sample prompt (`data/prompts/system_instruction.sample.md`), ensuring that the proprietary logic is never exposed in unauthorized environments.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- A Google Cloud Project with the Gemini API enabled
- An API Key

### Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/zenith-engine.git](https://github.com/your-username/zenith-engine.git)
    cd zenith-engine
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    Copy the example configuration and add your API key.
    ```bash
    cp .env.example .env
    ```
    Edit `.env` and set `GOOGLE_API_KEY`.

### Usage

Run the application via the CLI entry point:

```bash
python -m src.main

You will be greeted by the Zenith Interface. Type your query to interact with the agent. Type `exit` or `quit` to terminate the session.

## 📜 License

Copyright © 2025. All Rights Reserved.
This software is proprietary and confidential. Unauthorized copying, transfer, or reproduction is strictly prohibited.
