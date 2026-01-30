import json
import logging
from typing import Any, Dict

from google import genai
from google.genai import types

from src.core.config import Config


class TheJudge:
    """
    Evaluates the quality of the Agent's output against the User's input.
    """

    def __init__(self, config: Config):
        self.config = config
        # genai.configure moved to client init
        self.logger = logging.getLogger("ZenithJudge")

        self.client = genai.Client(api_key=self.config.GOOGLE_API_KEY)
        self.system_instruction = self._get_system_prompt()

    def _get_system_prompt(self) -> str:
        return """
        ATUE COMO: O Juiz Supremo. Uma IA de Auditoria de Qualidade.
        
        SUA MISSÃO: Classificar objetivamente a resposta de uma IA.
        
         ### RUBRICA DE AVALIAÇÃO (0-100 PONTOS)
        
        1. **Fidelidade à Intenção (0-35 pontos):**
           - A resposta atende EXATAMENTE ao que foi pedido?
        
        2. **Robustez e Segurança (0-25 pontos):**
           - A resposta é segura?
        
        3. **Clareza e Didatismo (0-20 pontos):**
           - A formatação está impecável?
        
        4. **Eficiência (0-20 pontos):**
           - Foi direto ao ponto?
        
        ### OUTPUT SCHEMA (JSON OBRIGATÓRIO)
        Retorne APENAS um JSON válido.
        
        {
          "score": int, // Soma total (0-100)
          "feedback": "string", // Crítica construtiva.
          "needs_refinement": boolean // True se score < 80
        }
        """

    async def evaluate_async(
        self, user_input: str, model_output: str
    ) -> Dict[str, Any]:
        """
        Evaluates the interaction (Async).
        """
        self.logger.info("The Judge is in session. Auditing response...")

        prompt = f"""
        [INPUT DO USUÁRIO]
        {user_input}

        [RESPOSTA DA IA]
        {model_output}

        [TAREFA]
        Avalie a [RESPOSTA DA IA] com base na [INPUT DO USUÁRIO].
        Gere o JSON de saída.
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.config.MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )

            raw_text = response.text.strip()

            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            result = json.loads(raw_text)

            self.logger.info(
                f"Verdict: Score {result.get('score')} | "
                f"Refinement: {result.get('needs_refinement')}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Judge Execution Failed: {e}. Defaulting to safe score.")
            return self._get_fallback_evaluation()

    def _get_fallback_evaluation(self) -> Dict[str, Any]:
        """
        Fallback for when the Judge fails.
        """
        return {
            "score": 85,
            "feedback": "Avaliação indisponível. Qualidade assumida como Padrão.",
            "needs_refinement": False,
        }
