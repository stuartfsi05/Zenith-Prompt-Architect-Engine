import asyncio
import json
import os
from typing import Any, List

from google import genai
from google.genai import types

from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("StrategicMemory")


class StrategicMemory:
    """
    Implements Progressive Semantic Memory.
    Features Master Summary and Entity Extraction.
    """

    def __init__(self, config: Config):
        self.config = config
        self.memory_path = os.path.join(os.getcwd(), "data", "memory.json")

        self.master_summary = ""
        self.user_profile = {}

        self.load_memory()

        self.client = genai.Client(api_key=self.config.GOOGLE_API_KEY)
        self.system_instruction = (
            "You are a Background Memory Processor. "
            "Your job is to compress information and extract facts."
        )

    def load_memory(self):
        """Loads semantic memory from JSON."""
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.master_summary = data.get("master_summary", "")
                    self.user_profile = data.get("user_profile", {})
                logger.info("Semantic Memory loaded.")
            except Exception as e:
                logger.error(f"Failed to load memory: {e}")
        else:
            logger.info("No existing memory found. Starting fresh.")

    def save_memory(self):
        """Saves semantic memory to JSON."""
        data = {
            "master_summary": self.master_summary,
            "user_profile": self.user_profile,
        }
        try:
            os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info("Semantic Memory saved.")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    async def consolidate_memory_async(self, old_messages: List[Any]):
        """
        Integrates old messages into the Master Summary.
        """
        if not old_messages:
            return

        logger.info(f"Consolidating {len(old_messages)} old messages into Summary...")

        conversation_text = ""
        for msg in old_messages:
            role = msg.role if hasattr(msg, "role") else "unknown"
            content = ""
            if hasattr(msg, "parts"):
                for part in msg.parts:
                    content += part.text
            else:
                content = str(msg)

            conversation_text += f"{role}: {content}\n"

        prompt = f"""
        TAREFA: Compressão Semântica (Atualização de Resumo Mestre)

        RESUMO MESTRE ATUAL:
        {self.master_summary}

        NOVAS MENSAGENS ARQUIVADAS:
        {conversation_text}

        INSTRUÇÃO:
        Reescreva o RESUMO MESTRE para incorporar as informações vitais.
        - Mantenha fatos importantes, decisões, nomes e preferências.
        - Descarte cumprimentos e banalidades.
        - O texto deve ser um parágrafo denso.

        NOVO RESUMO MESTRE:
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.config.MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction
                )
            )
            if response.text:
                self.master_summary = response.text
                self.save_memory()
                logger.info("Master Summary updated.")
        except Exception as e:
            logger.error(f"Memory Consolidation Failed: {e}")

    async def extract_entities_async(self, user_input: str, model_output: str):
        """
        Analyzes the latest interaction to extract persistent facts.
        """
        if len(user_input) < 10:
            return

        logger.info("Extracting Entities & Facts...")

        prompt = f"""
        TAREFA: Extração de Entidades e Fatos (User Profile)

        PERFIL DE USUÁRIO ATUAL (JSON):
        {json.dumps(self.user_profile, ensure_ascii=False)}

        INTERAÇÃO RECENTE:
        User: {user_input}
        AI: {model_output}

        INSTRUÇÃO:
        Analise a interação. Se houver NOVOS fatos sobre o usuário
        (nome, projeto, stack, preferências), atualize o JSON.
        Se não houver nada novo, retorne o JSON original.

        Retorne APENAS o JSON válido.
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.config.MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    response_mime_type="application/json"
                )
            )

            updated_profile = json.loads(response.text)

            if updated_profile != self.user_profile:
                self.user_profile = updated_profile
                self.save_memory()
                logger.info(f"User Profile updated: {self.user_profile.keys()}")
            else:
                logger.info("No new entities found.")

        except Exception as e:
            logger.warning(f"Entity Extraction Failed: {e}")

    def get_context_injection(self) -> str:
        """Returns the formatted string to be injected into the LLM context."""
        context = ""

        if self.user_profile:
            facts = "\n".join([f"- {k}: {v}" for k, v in self.user_profile.items()])
            context += (
                f"--- [MEMÓRIA SEMÂNTICA: PERFIL DO USUÁRIO] ---\n" f"{facts}\n\n"
            )

        if self.master_summary:
            context += (
                f"--- [MEMÓRIA SEMÂNTICA: RESUMO MESTRE] ---\n"
                f"{self.master_summary}\n\n"
            )

        return context
