import asyncio
import json
import os
from typing import Dict, List, Any

import google.generativeai as genai

from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("StrategicMemory")


class StrategicMemory:
    """
    Implements Progressive Semantic Memory (SOTA Memory Management).
    Features:
    1. Recursive Summarization (Master Summary) to cure "Mechanical Amnesia".
    2. Entity Extraction (User Profile) for persistent personalization.
    """

    def __init__(self, config: Config):
        self.config = config
        self.memory_path = os.path.join(os.getcwd(), "data", "memory.json")
        
        # Initialize Memory Components
        self.master_summary = ""
        self.user_profile = {}
        
        # Load existing memory
        self.load_memory()

        # Initialize LLM for backend memory operations
        # We use a cheaper/faster model or the same model depending on config.
        # Assuming usage of the main model for quality.
        self.model = genai.GenerativeModel(
            model_name=self.config.MODEL_NAME,
            system_instruction="You are a Background Memory Processor. Your job is to compress information and extract facts without losing context."
        )

    def load_memory(self):
        """Loads semantic memory from JSON."""
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.master_summary = data.get("master_summary", "")
                    self.user_profile = data.get("user_profile", {})
                logger.info("🧠 Semantic Memory loaded.")
            except Exception as e:
                logger.error(f"Failed to load memory: {e}")
        else:
            logger.info("🧠 No existing memory found. Starting fresh.")

    def save_memory(self):
        """Saves semantic memory to JSON."""
        data = {
            "master_summary": self.master_summary,
            "user_profile": self.user_profile
        }
        try:
            os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info("💾 Semantic Memory saved.")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    async def consolidate_memory_async(self, old_messages: List[Any]):
        """
        Takes a list of old messages (about to be pruned) and integrates them 
        into the Master Summary.
        """
        if not old_messages:
            return

        logger.info(f"📉 Consolidating {len(old_messages)} old messages into Master Summary...")

        # Format messages for the model
        conversation_text = ""
        for msg in old_messages:
            role = msg.role if hasattr(msg, 'role') else "unknown"
            # content might be a list of parts or a string
            content = ""
            if hasattr(msg, 'parts'):
                for part in msg.parts:
                    content += part.text
            else:
                content = str(msg)
            
            conversation_text += f"{role}: {content}\n"

        prompt = f"""
        TAREFA: Compressão Semântica (Atualização de Resumo Mestre)
        
        RESUMO MESTRE ATUAL:
        {self.master_summary}
        
        NOVAS MENSAGENS ARQUIVADAS (Que serão deletadas da Short-Term Memory):
        {conversation_text}
        
        INSTRUÇÃO:
        Reescreva o RESUMO MESTRE para incorporar as informações vitais das NOVAS MENSAGENS ARQUIVADAS.
        - Mantenha fatos importantes, decisões, nomes e preferências.
        - Descarte cumprimentos e banalidades.
        - O texto deve ser um parágrafo denso e progressivo.
        
        NOVO RESUMO MESTRE:
        """

        try:
            response = await self.model.generate_content_async(prompt)
            if response.text:
                self.master_summary = response.text
                self.save_memory()
                logger.info("✅ Master Summary updated.")
        except Exception as e:
            logger.error(f"Memory Consolidation Failed: {e}")

    async def extract_entities_async(self, user_input: str, model_output: str):
        """
        Analyzing the latest interaction to extract permanent facts about the user/project.
        Updates self.user_profile.
        """
        # Heuristic: Only run if input/output is substantial or contains key terms, 
        # but for now we can run it on every turn or check length to save valid tokens.
        if len(user_input) < 10: 
            return

        logger.info("🕵️ extracting Entities & Facts...")

        prompt = f"""
        TAREFA: Extração de Entidades e Fatos (User Profile)
        
        PERFIL DE USUÁRIO ATUAL (JSON):
        {json.dumps(self.user_profile, ensure_ascii=False)}
        
        INTERAÇÃO RECENTE:
        User: {user_input}
        AI: {model_output}
        
        INSTRUÇÃO:
        Analise a interação. Se houver NOVOS fatos sobre o usuário (nome, cargo, projeto, stack tecnológica, preferências, família), atualize o JSON.
        Se não houver nada novo, retorne o JSON original.
        
        Retorne APENAS o JSON válido.
        """

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            updated_profile = json.loads(response.text)
            
            if updated_profile != self.user_profile:
                self.user_profile = updated_profile
                self.save_memory()
                logger.info(f"👤 User Profile updated: {self.user_profile.keys()}")
            else:
                logger.info("👤 No new entities found.")
                
        except Exception as e:
            logger.warning(f"Entity Extraction Failed: {e}")

    def get_context_injection(self) -> str:
        """Returns the formatted string to be injected into the LLM context."""
        context = ""
        
        if self.user_profile:
            facts = "\n".join([f"- {k}: {v}" for k, v in self.user_profile.items()])
            context += f"--- [MEMÓRIA SEMÂNTICA: PERFIL DO USUÁRIO] ---\n{facts}\n\n"
            
        if self.master_summary:
            context += f"--- [MEMÓRIA SEMÂNTICA: RESUMO MESTRE] ---\n{self.master_summary}\n\n"
            
        return context
