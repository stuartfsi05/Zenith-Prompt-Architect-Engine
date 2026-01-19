import json
import logging
import google.generativeai as genai
from typing import Dict, Any
from src.core.config import Config

# Constants for the Analyzer
ANALYZER_MODEL_NAME = "gemini-3-flash-preview"

class StrategicAnalyzer:
    """
    Implements the Cognitive Router (Strategic Analysis Module) following Framework FDU 2.0.
    Responsible for classifying user intent, complexity, and resource priority before execution.
    """

    def __init__(self):
        self.config = Config.load()
        genai.configure(api_key=self.config.GOOGLE_API_KEY)
        
        # Initialize a lightweight, fast model for routing
        self.model = genai.GenerativeModel(
            model_name=ANALYZER_MODEL_NAME,
            system_instruction=self._get_system_prompt()
        )
        self.logger = logging.getLogger("StrategicAnalyzer")

    def _get_system_prompt(self) -> str:
        """
        Returns the specific system prompt for the FDU 2.0 Framework classification.
        """
        return """
        ATUE COMO: Um Roteador Cognitivo (Cognitive Router) especialista no Framework FDU 2.0.
        SUA MISSÃO: Analisar o input do usuário e classificar a intenção para direcionar a execução correta.
        
        RETORNE APENAS UM JSON VÁLIDO. NADA MAIS.
        
        ### ESTRUTURA DE ANÁLISE (FRAMEWORK FDU 2.0)
        
        1. VETOR 1: NATUREZA DA TAREFA (natureza)
           - [G] Geração: Criatividade, escrita, storytelling, poemas, copywriting.
           - [R] Raciocínio: Lógica, análise crítica, debate, tomada de decisão, conselho.
           - [P] Planejamento: Estruturação de passos, cronogramas, roadmaps, gestão de projetos.
           - [E] Extração: Resumo, formatação de dados, parsing, retirar informações de texto.
           - [C] Codificação: Escrever código, scripts, debugging, arquitetura de software, SQL.
           - [I] Investigação: Busca factual, notícias, dados da Knowledge Base, perguntas sobre eventos.
        
        2. VETOR 2: COMPLEXIDADE (complexidade)
           - [S] Simples: Direto, Zero-Shot, sem necessidade de contexto profundo.
           - [C] Composta: Múltiplas variáveis, exige contexto ou múltiplos passos lógicos.
           - [A] Abstrata: Subjetivo, filosófico, ambíguo ou requer alta criatividade/nuance.
        
        3. VETOR 3: PRIORIDADE DE RECURSOS (prioridade)
           - [R] Rápida: Baixo custo, velocidade máxima, resposta concisa.
           - [P] Padrão: Equilíbrio entre custo e qualidade.
           - [E] Exaustiva: Alta qualidade, múltiplas revisões, precisão crítica, Deep Thinking.
        
        ### output_schema (JSON)
        {
            "natureza": "String (ex: Geração)",
            "complexidade": "String (ex: Composta)",
            "prioridade": "String (ex: Padrão)",
            "intencao_sintetizada": "Resumo de 1 linha do que o usuário quer",
            "strategy_selected": "Nome da estratégia sugerida (ex: Zero-Shot, Chain-of-Thought, ReAct, Tree-of-Thoughts)"
        }
        
        ### REGRAS DE ESTRATÉGIA
        - Se Complexidade == "Simples" -> strategy_selected: "Zero-Shot"
        - Se Complexidade == "Composta" -> strategy_selected: "Chain-of-Thought"
        - Se Complexidade == "Abstrata" OU Natureza == "Planejamento" -> strategy_selected: "Tree-of-Thoughts"
        - Se Natureza == "Investigação" -> strategy_selected: "ReAct" (Search/Action)
        
        Analise o input e gere o JSON.
        """

    def analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Analyzes the user input and returns a structured classification.
        """
        self.logger.info("Executing Strategic Analysis (Cognitive Router)...")
        
        try:
            # Generate the analysis
            response = self.model.generate_content(
                f"INPUT DO USUÁRIO: {user_input}",
                generation_config={"temperature": 0.0, "response_mime_type": "application/json"}
            )
            
            raw_text = response.text.strip()
            
            # Sanitize code blocks if present (though response_mime_type should handle it)
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            result = json.loads(raw_text)
            
            self.logger.info(f"Analysis complete: {result.get('natureza')} / {result.get('complexidade')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Analysis Failed: {str(e)}. Using Fallback.")
            return self._get_fallback_response(user_input)

    def _get_fallback_response(self, user_input: str) -> Dict[str, Any]:
        """
        Provides a safe default layout in case of model or parsing failure.
        """
        return {
            "natureza": "Raciocínio",  # Default safe assumption
            "complexidade": "Composta",
            "prioridade": "Padrão",
            "intencao_sintetizada": f"Fallback: Processar input '{user_input[:50]}...'",
            "strategy_selected": "Chain-of-Thought"
        }
