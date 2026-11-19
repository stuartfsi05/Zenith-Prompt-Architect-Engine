import asyncio
import json
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from src.core.config import Config
from src.core.database import PersistenceLayer
from src.core.llm.google_genai import is_modern_gemini_model
from src.utils.json_utils import parse_llm_json
from src.utils.logger import setup_logger

logger = setup_logger("StrategicMemory")


class StrategicMemory:
    """
    Implements Progressive Semantic Memory strictly isolated per user_id.
    Features per-user Master Summary and Entity Extraction.
    """

    def __init__(
        self,
        config: Config,
        db: Optional[PersistenceLayer] = None,
        api_key: Optional[str] = None,
    ):
        self.config = config
        self.db = db
        self._cache: Dict[str, Dict[str, Any]] = {}

        effective_key = api_key or self.config.GOOGLE_API_KEY.get_secret_value()
        self.client = genai.Client(api_key=effective_key)
        self.system_instruction = (
            "You are a Background Memory Processor. "
            "Your job is to compress information and extract facts."
        )

    def _build_config(self, json_output: bool = False) -> types.GenerateContentConfig:
        """Builds generation config compatible with modern Gemini 3+/4+ models."""
        config_kwargs: Dict[str, Any] = {
            "system_instruction": self.system_instruction,
        }
        if json_output:
            config_kwargs["response_mime_type"] = "application/json"
        if is_modern_gemini_model(self.config.AUX_MODEL_NAME):
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level=self.config.AUX_THINKING_LEVEL
            )
        return types.GenerateContentConfig(**config_kwargs)

    def load_user_memory(self, user_id: str) -> Dict[str, Any]:
        """Loads semantic memory strictly scoped to user_id."""
        if not user_id:
            return {"master_summary": "", "user_profile": {}}

        if user_id in self._cache:
            return self._cache[user_id]

        if self.db is not None:
            loaded = self.db.get_user_memory(user_id)
            mem = {
                "master_summary": loaded.get("master_summary") or "",
                "user_profile": dict(loaded.get("user_profile") or {}),
            }
        else:
            mem = {"master_summary": "", "user_profile": {}}

        self._cache[user_id] = mem
        return mem

    def save_user_memory(
        self, user_id: str, master_summary: str, user_profile: Dict[str, Any]
    ) -> None:
        """Saves semantic memory strictly scoped to user_id."""
        if not user_id:
            return

        mem = {
            "master_summary": master_summary,
            "user_profile": dict(user_profile),
        }
        self._cache[user_id] = mem

        if self.db is not None:
            try:
                self.db.save_user_memory(user_id, master_summary, mem["user_profile"])
            except Exception as e:
                logger.error(f"Failed to persist memory for user {user_id}: {e}")

    async def consolidate_memory_async(
        self, user_id: str, old_messages: List[Any]
    ) -> None:
        """Integrates old messages into the user's Master Summary."""
        if not user_id or not old_messages:
            return

        logger.info(
            f"Consolidating {len(old_messages)} old messages for user {user_id}..."
        )
        mem = self.load_user_memory(user_id)

        conversation_text = ""
        for msg in old_messages:
            role = msg.role if hasattr(msg, "role") else "unknown"
            content = ""
            if hasattr(msg, "parts"):
                for part in msg.parts:
                    content += getattr(part, "text", "") or ""
            else:
                content = str(msg)
            conversation_text += f"{role}: {content}\n"

        prompt = f"""
        TAREFA: Compressão Semântica (Atualização de Resumo Mestre)

        RESUMO MESTRE ATUAL:
        {mem["master_summary"]}

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
                model=self.config.AUX_MODEL_NAME,
                contents=prompt,
                config=self._build_config(),
            )
            if response.text:
                self.save_user_memory(
                    user_id, response.text.strip(), mem["user_profile"]
                )
                logger.info(f"Master Summary updated for user {user_id}.")
        except Exception as e:
            logger.error(f"Memory Consolidation Failed: {e}")

    async def manage_history(
        self, chat_session: Any, user_id: str, max_history: int = 20
    ) -> None:
        """
        Checks chat history length and triggers consolidation if needed.
        Acts as a background maintenance task scoped to user_id.
        """
        if not hasattr(chat_session, "history"):
            return

        current_history = chat_session.history
        history_len = len(current_history)

        if history_len > max_history:
            prune_count = history_len - max_history
            items_to_prune = current_history[:prune_count]

            logger.info(
                f"Pruning History (Current: {history_len}). "
                f"Archiving {len(items_to_prune)} items for user {user_id}."
            )

            chat_session.history = current_history[prune_count:]
            asyncio.create_task(self.consolidate_memory_async(user_id, items_to_prune))

    async def extract_entities_async(
        self, user_id: str, user_input: str, model_output: str
    ) -> None:
        """Analyzes the latest interaction to extract persistent facts for user_id."""
        if not user_id or len(user_input) < 10:
            return

        logger.info(f"Extracting Entities & Facts for user {user_id}...")
        mem = self.load_user_memory(user_id)
        current_profile = mem["user_profile"]

        prompt = f"""
        TAREFA: Extração de Entidades e Fatos (User Profile)

        PERFIL DE USUÁRIO ATUAL (JSON):
        {json.dumps(current_profile, ensure_ascii=False)}

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
                model=self.config.AUX_MODEL_NAME,
                contents=prompt,
                config=self._build_config(json_output=True),
            )

            updated_profile = parse_llm_json(response.text)
            if not isinstance(updated_profile, dict):
                return

            if updated_profile != current_profile:
                self.save_user_memory(user_id, mem["master_summary"], updated_profile)
                logger.info(
                    f"User Profile updated for {user_id}: {list(updated_profile.keys())}"
                )
            else:
                logger.info("No new entities found.")

        except Exception as e:
            logger.warning(f"Entity Extraction Failed: {e}")

    def get_context_injection(self, user_id: str) -> str:
        """Returns the formatted memory string strictly for user_id."""
        mem = self.load_user_memory(user_id)
        user_profile = mem["user_profile"]
        master_summary = mem["master_summary"]
        context = ""

        if user_profile:
            facts = "\n".join([f"- {k}: {v}" for k, v in user_profile.items()])
            context += f"--- [MEMÓRIA SEMÂNTICA: PERFIL DO USUÁRIO] ---\n{facts}\n\n"

        if master_summary:
            context += (
                f"--- [MEMÓRIA SEMÂNTICA: RESUMO MESTRE] ---\n{master_summary}\n\n"
            )

        return context
