import json
import logging
from typing import Any, Dict

from src.core.config import Config
from src.core.llm.google_genai import GoogleGenAIProvider


class StrategicAnalyzer:
    """
    Analyzes user intent to determine complexity and required strategy.
    """

    def __init__(self, config: Config):
        self.config = config

        # Initialize LLM Provider
        self.llm = GoogleGenAIProvider(
            model_name=self.config.MODEL_NAME,
            system_instruction=self._get_system_prompt(),
            temperature=0.1,  # Default, overriden in methods
        )
        self.llm.configure(self.config.GOOGLE_API_KEY)

        self.logger = logging.getLogger("StrategicAnalyzer")

    def _get_system_prompt(self) -> str:
        """
        Returns the system prompt for intent classification.
        """
        return """
        ATUE COMO: Um Roteador Cognitivo especialista.
        SUA MISSÃO: Analisar o input do usuário e classificar a intenção.

        RETORNE APENAS UM JSON VÁLIDO. NADA MAIS.
        
        ### ESTRUTURA DE ANÁLISE
        
        1. VETOR 1: NATUREZA DA TAREFA (natureza)
           - [G] Geração: Criatividade, escrita.
           - [R] Raciocínio: Lógica, análise crítica.
           - [P] Planejamento: Estruturação de passos.
           - [E] Extração: Resumo, formatação de dados.
           - [C] Codificação: Escrever código.
           - [I] Investigação: Busca factual.
        
        2. VETOR 2: COMPLEXIDADE (complexidade)
           - [S] Simples: Direto.
           - [C] Composta: Múltiplas variáveis.
           - [A] Abstrata: Subjetivo.
        
        3. VETOR 3: PRIORIDADE DE RECURSOS (prioridade)
           - [R] Rápida
           - [P] Padrão
           - [E] Exaustiva
        
        ### output_schema (JSON)
        {
            "natureza": "String (ex: Geração)",
            "complexidade": "String (ex: Composta)",
            "prioridade": "String (ex: Padrão)",
            "intencao_sintetizada": "Resumo de 1 linha",
            "strategy_selected": "Nome da estratégia sugerida"
        }
        
        Analise o input e gere o JSON.
        """

    async def analyze_intent_async(self, user_input: str) -> Dict[str, Any]:
        """
        Analyzes the user input and returns a structured classification.
        """
        self.logger.info("Executing Strategic Analysis...")

        max_retries = 2
        temperatures = [0.1, 0.4, 0.7]

        for attempt in range(max_retries + 1):
            current_temp = temperatures[attempt]

            try:
                response_text = await self.llm.generate_content_async(
                    f"INPUT DO USUÁRIO: {user_input}",
                    config={
                        "temperature": current_temp,
                        "response_mime_type": "application/json",
                    },
                )

                if not response_text:
                    raise ValueError("Empty response from Analyzer")

                analysis_json = json.loads(response_text)
                self.logger.info(
                    f"Analysis successful (Temp: {current_temp}): "
                    f"{analysis_json.get('natureza')}"
                )
                return analysis_json

            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(
                    f"Analysis Failed (Attempt {attempt + 1}/{max_retries + 1}) "
                    f"| Temp: {current_temp} | Error: {e}"
                )
            except Exception as e:
                self.logger.critical(f"Critical Analyzer Error: {e}")
                break

        self.logger.error("All retries failed. Activating Fallback Protocol.")
        return self._get_fallback_response(user_input)

    def _get_fallback_response(self, user_input: str) -> Dict[str, Any]:
        """
        Provides a safe default layout in case of failure.
        """
        return {
            "natureza": "Raciocínio",
            "complexidade": "Composta",
            "prioridade": "Padrão",
            "intencao_sintetizada": f"Fallback: '{user_input[:50]}...'",
            "strategy_selected": "Chain-of-Thought",
        }
