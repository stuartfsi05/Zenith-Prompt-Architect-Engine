# Zenith | Prompt Architect Engine

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-High%20Performance-009688)
![Supabase](https://img.shields.io/badge/Supabase-Vector%20Store-3ECF8E)
![Render](https://img.shields.io/badge/Render-Deployed-purple)

**Zenith** é um **Motor Cognitivo Headless** (sem interface visual) de alta performance. Ele foi projetado para atuar como o cérebro autônomo de aplicações complexas, operando via API para fornecer inteligência pura como serviço.

Este projeto está configurado para **Deploy Automático** via Render.

---

## 📚 Documentação da API

A documentação completa e interativa dos endpoints está disponível automaticamente via Swagger UI:

- **Local**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Produção (Render)**: `https://<seu-app>.onrender.com/docs`

Use essa interface para entender os contratos de dados e testar requisições em tempo real.

---

## 🧠 O Que é o Zenith?

O Zenith não é apenas um "chatbot". Ele é um **Orquestrador Cognitivo** que implementa um pipeline de raciocínio avançado:

1.  **Roteador Cognitivo**: Classifica a intenção do usuário (Planejamento, Raciocínio, Criatividade) antes de gerar resposta.
2.  **Memória Estratégica**: Persiste fatos importantes sobre o usuário a longo prazo (via Supabase), superando a janela de contexto limitada dos LLMs.
3.  **RAG Híbrido**: Recupera conhecimento técnico da base de dados vetorial para fundamentar respostas.
4.  **Auto-Auditoria ("O Juiz")**: Um segundo modelo avalia criticamente a resposta do primeiro antes de entregá-la ao usuário.

---

## 🚀 Como Executar (Localmente)

### 1. Pré-requisitos
*   Python 3.10+
*   Conta no Google AI Studio (Gemini API)
*   Projeto no Supabase (PostgreSQL + Vector)

### 2. Instalação
```bash
git clone https://github.com/stuartfsi05/Zenith-Prompt-Architect-Engine.git
cd Zenith-Prompt-Architect-Engine
pip install -r requirements.txt
```

### 3. Configuração (.env)
Crie um arquivo `.env` na raiz do projeto. 

> [!IMPORTANT]
> **Atenção à Chave da Supabase:**
> Não use a chave `sb_publishable...`. Você deve usar a chave **Legacy `anon` (JWT)**.
> No painel Supabase vá em: *Project Settings > API > Legacy anon, service_role API keys*.

```env
# Google Gemini
GOOGLE_API_KEY=sua_chave_do_aistudio_aqui
MODEL_NAME=gemini-2.5-flash
TEMPERATURE=0.1

# Supabase (Banco de Dados e Memória)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=eyJ... (Cole aqui a chave 'anon' JWT longa)

# Sistema
SYSTEM_PROMPT_PATH=data/prompts/system_instruction.md
```

### 4. Rodando o Servidor
Para iniciar a API localmente:
```bash
python src/run.py
```
O servidor iniciará em `http://0.0.0.0:8000`.

---

## ☁️ Deploy no Render

Este repositório já contém o arquivo de configuração `render.yaml` para deploy automático.

### Passo a Passo
1.  Crie uma conta no [Render](https://render.com).
2.  Conecte sua conta do GitHub.
3.  No painel do Render, clique em **"New"** > **"Web Service"**.
4.  Selecione este repositório.
5.  O Render detectará o `render.yaml` e configurará o ambiente automaticamente.

### Configuração de Ambiente (Environment Variables)
O arquivo `.env` **não** é enviado para o GitHub por segurança. Você deve configurar as variáveis manualmente no Render:

1.  Vá no Dashboard do seu serviço no Render.
2.  Clique em **Environment**.
3.  Adicione as mesmas variáveis do seu `.env` local (`GOOGLE_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, etc).

> [!NOTE]
> Sempre que você alterar uma senha ou chave, lembre-se de atualizar no painel do Render, pois isso não é sincronizado automaticamente pelo Git.

---

## 🛠️ Stack Tecnológico

*   **Linguagem**: Python 3.10
*   **Framework Web**: FastAPI + Uvicorn
*   **LLM Provider**: Google Gemini 2.5 Flash
*   **Banco Vetorial**: Supabase (pgvector)
*   **Arquitetura**: Transiente (Stateless) & Injeção de Dependência

---

## 📜 Licença
Projeto proprietário. Desenvolvido por Thiago Dias Precivalli.
