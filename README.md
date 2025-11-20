# Zenith | Prompt Architect Engine

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-Proprietary-red)
![Status](https://img.shields.io/badge/status-Active-green)

**Zenith** is a high-performance, modular autonomous agent engine designed to orchestrate complex generative AI workflows using Google's Gemini API. It serves as the foundational runtime for the **TCRE-A Protocol**, providing a secure and robust environment for prompt engineering and execution.

## 🏗️ Project Architecture

Zenith is built on **Clean Architecture** principles, ensuring separation of concerns, testability, and maintainability.

### Core Components

- **`src/core/agent.py`**: The brain of the operation. Encapsulates the Gemini `GenerativeModel` and manages chat sessions. It handles API interactions with robust error handling and retry logic (via the underlying library).
- **`src/core/config.py`**: A Singleton-based configuration manager using Python `dataclasses`. It enforces strict environment variable validation, ensuring the application never runs in an undefined state.
- **`src/utils/loader.py`**: A security-focused file loader. It implements a "Fallback Protocol" that protects Intellectual Property by defaulting to a sanitized "Demo Mode" if the proprietary system prompt is missing.
- **`src/utils/logger.py`**: Centralized logging infrastructure using `rich.logging`. It provides structured logs for debugging and beautiful console output for runtime monitoring.

### Design Patterns

- **Dependency Injection**: Configuration and System Instructions are injected into the Agent, allowing for easy mocking and testing.
- **Singleton**: The Configuration manager ensures a single source of truth for application settings.
- **Strategy/Fallback**: The Loader implements a fallback strategy to ensure business continuity (in demo mode) even when secure assets are unavailable.

## 🔒 Security & IP Protection

Zenith is designed with IP protection as a first-class citizen.

1.  **Environment Isolation**: All sensitive keys and configuration toggles are managed via `.env` files, which are strictly excluded from version control.
2.  **Sanitized Fallback**: The `loader.py` module specifically checks for the existence of the production system prompt. If not found, it seamlessly degrades to a "Demo Mode" using a sanitized sample prompt (`data/prompts/system_instruction.sample.md`), ensuring that the proprietary logic is never exposed in unauthorized environments.

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- A Google Cloud Project with the Gemini API enabled
- An API Key

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-org/zenith-engine.git
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
```

You will be greeted by the Zenith Interface. Type your query to interact with the agent. Type `exit` or `quit` to terminate the session.

## 📜 License

Copyright © 2024. All Rights Reserved.
This software is proprietary and confidential. Unauthorized copying, transfer, or reproduction is strictly prohibited.
