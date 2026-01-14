## **Guia de Técnicas Avançadas: Self-Critique e Step-Back**

### **Introdução: Propósito e Escopo**

Este guia detalha as técnicas avançadas de prompting *Self-Critique* e *Step-Back*. Para garantir uma aplicação precisa e consistente, ideal tanto para engenheiros quanto para sistemas de IA, as técnicas são organizadas dentro de um framework de decisão robusto. Este documento serve como uma referência completa para analisar um problema, selecionar a estratégia ideal e construir um prompt de alta performance.

### ---

**Seção 1: O Framework de Decisão (FDD-IA)**

Este framework é o processo central a ser seguido para cada tarefa de otimização de prompt.

#### **Passo 1: Análise de Vetores da Tarefa**

Para cada prompt de entrada, a tarefa deve ser decomposta nos seguintes vetores de análise:

1. **Natureza da Tarefa (NT):** Qual é o verbo principal da solicitação?  
   * \[NT-G\] **Geração:** Criar conteúdo novo (texto, código, ideias).  
   * \[NT-R\] **Raciocínio:** Resolver problemas lógicos, matemáticos, ou de causa e efeito.  
   * \[NT-P\] **Planejamento:** Estruturar passos para atingir um objetivo.  
   * \[NT-E\] **Extração/Síntese:** Resumir, reformatar ou extrair informações de um contexto.  
2. **Requisito de Qualidade (RQ):** Qual o nível de polimento exigido para a saída?  
   * \[RQ-B\] **Básico/Rascunho:** Uma primeira versão é suficiente. A velocidade é mais importante que a perfeição.  
   * \[RQ-A\] **Alto/Confiável:** A resposta precisa ser correta, bem estruturada e confiável.  
   * \[RQ-M\] **Máximo/Final:** A saída deve ser de qualidade profissional, pronta para uso, minimizando a necessidade de edição humana.  
3. **Complexidade do Problema (CP):** Quão profundo é o problema a ser resolvido?  
   * \[CP-S\] **Simples:** Tarefa direta, com poucas variáveis.  
   * \[CP-C\] **Composta:** Tarefa com múltiplos passos ou que requer a consideração de vários fatores.  
   * \[CP-A\] **Abstrata/Sistêmica:** O problema envolve princípios subjacentes, sistemas complexos ou premissas que podem ser falsas.  
4. **Restrição de Recursos (RR):** Qual é a tolerância a custos e latência?  
   * \[RR-A\] **Alta:** Custo e tempo não são problema; a qualidade máxima é a única prioridade.  
   * \[RR-M\] **Média:** Um equilíbrio entre custo/tempo e qualidade é necessário.  
   * \[RR-B\] **Baixa:** A resposta precisa ser rápida e barata.

#### **Passo 2: Matriz de Seleção de Técnica**

Com os vetores analisados, esta matriz deve ser usada para selecionar a técnica primária.

| Natureza da Tarefa (NT) | Requisito de Qualidade (RQ) | Complexidade do Problema (CP) | Restrição de Recursos (RR) | Técnica Recomendada | ID da Técnica |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Qualquer | \[RQ-B\] (Básico) | \[CP-S\] (Simples) | Qualquer | **Prompt Simples** | T00\_SIMPLES |
| \[NT-G\], \[NT-E\] | \[RQ-A\] (Alto) | \[CP-C\] (Composta) | \[RR-M/A\] | **Chain-of-Thought (CoT)** | T01\_COT |
| \[NT-R\], \[NT-P\] | \[RQ-A\] (Alto) | \[CP-A\] (Abstrata) | \[RR-M/A\] | **Step-Back Prompting** | T02\_STEPBACK |
| \[NT-G\], \[NT-P\] | \[RQ-M\] (Máximo) | \[CP-C\], \[CP-A\] | \[RR-A\] (Alta) | **Self-Critique Loop** | T03\_SELFCRITIQUE |
| \[NT-R\], \[NT-P\] | \[RQ-M\] (Máximo) | \[CP-A\] (Abstrata) | \[RR-A\] (Alta) | **Combinado (Step-Back \+ CoT/Critique)** | T04\_COMBINADO |

#### **Passo 3: Lógica de Combinação**

* Se a Matriz de Seleção apontar para T04\_COMBINADO, a regra de implementação é:  
  1. **Primeiro, aplique T02\_STEPBACK** para extrair os princípios fundamentais e estabelecer um framework de raciocínio.  
  2. **Em seguida, use a saída do Step-Back como contexto para aplicar T01\_COT ou T03\_SELFCRITIQUE** para executar a tarefa específica dentro do framework estabelecido.

### ---

**Seção 2: Catálogo de Técnicas e Templates**

Esta seção serve como a biblioteca de implementação para a construção dos prompts.  
\<details\>  
\<summary\>\<strong\>T01\_COT: Chain-of-Thought\</strong\>\</summary\>

* **Definição Operacional:** Força a IA a detalhar seu processo de raciocínio passo a passo antes de dar a resposta final.  
* **Triggers de Ativação:** NT=\[G/E\], RQ=\[A\], CP=\[C\]. Útil para aumentar a transparência e a confiabilidade em tarefas com múltiplos passos.  
* **Análise de Custo:** Custo computacional \~1.5x-2x em relação a um prompt simples.  
* **Template de Prompt:**  
  Dada a seguinte tarefa: {{TAREFA}}  
  Pense passo a passo para chegar à solução. Detalhe sua linha de raciocínio.  
  Finalmente, apresente a resposta final.

\</details\>  
\<details\>  
\<summary\>\<strong\>T02\_STEPBACK: Step-Back Prompting\</strong\>\</summary\>

* **Definição Operacional:** Instruir a IA a abstrair conceitos e princípios gerais de uma pergunta específica antes de respondê-la.  
* **Triggers de Ativação:** NT=\[R/P\], RQ=\[A\], CP=\[A\]. Essencial para problemas complexos ou com premissas potencialmente enganosas.  
* **Análise de Custo:** Custo computacional \~1.5x-2.5x. Pode reduzir o custo total ao evitar tentativas e erros.  
* **Template de Prompt:**  
  Antes de responder à pergunta específica, dê um passo para trás e explique os princípios fundamentais que governam este problema.  
  Pergunta Específica: {{PERGUNTA}}  
  Princípios Fundamentais: \[IA preenche aqui\]  
  Agora, com base nos princípios acima, responda à pergunta específica.

\</details\>  
\<details\>  
\<summary\>\<strong\>T03\_SELFCRITIQUE: Self-Critique Loop\</strong\>\</summary\>

* **Definição Operacional:** Um processo iterativo onde a IA gera um rascunho, o critica com base em critérios, e o refina.  
* **Triggers de Ativação:** NT=\[G/P\], RQ=\[M\], RR=\[A\]. Usado quando a qualidade da saída final é a prioridade máxima.  
* **Análise de Custo:** Custo computacional \~2.5x-4x. É a técnica mais "cara".  
* **Template de Prompt:**  
  \*\*Tarefa:\*\* {{TAREFA}}

  \*\*Processo de 3 Passos:\*\*  
  1\. \*\*Rascunho:\*\* Gere uma primeira versão da resposta.  
  2\. \*\*Autocrítica:\*\* Analise o rascunho com base nos seguintes critérios: {{CRITÉRIO\_1}}, {{CRITÉRIO\_2}}, {{CRITÉRIO\_3}}. Identifique os pontos fracos.  
  3\. \*\*Versão Final:\*\* Reescreva a resposta, incorporando as melhorias identificadas na autocrítica para produzir uma saída de qualidade máxima.

\</details\>  
\<details\>  
\<summary\>\<strong\>T04\_COMBINADO: Step-Back \+ Self-Critique\</strong\>\</summary\>

* **Definição Operacional:** Orquestra a abstração de princípios (Step-Back) com a execução e o refinamento iterativo (Self-Critique) para máxima robustez.  
* **Triggers de Ativação:** NT=\[R/P\], RQ=\[M\], CP=\[A\], RR=\[A\]. A solução definitiva para problemas estratégicos complexos.  
* **Análise de Custo:** Custo computacional \~3x-5x. Reservado para as tarefas de maior valor.  
* **Template de Prompt:**  
  \*\*Persona:\*\* {{PERSONA}}  
  \*\*Contexto:\*\* {{CONTEXTO}}

  \*\*Fase 1: Step-Back (Abstração de Princípios)\*\*  
  Antes de qualquer outra coisa, identifique e descreva os princípios fundamentais ou o framework conceitual necessário para resolver a seguinte tarefa: {{TAREFA\_ABSTRATA}}

  \*\*Fase 2: Execução e Refinamento (Self-Critique Loop)\*\*  
  Agora, usando os princípios da Fase 1 como seu guia:  
  1\. \*\*Rascunho:\*\* Elabore um plano/resposta detalhado para a tarefa específica: {{TAREFA\_ESPECÍFICA}}.  
  2\. \*\*Autocrítica:\*\* Avalie criticamente seu rascunho. Ele está totalmente alinhado com os princípios da Fase 1? Quais são os 3 maiores riscos ou pontos fracos do seu plano? {{CRITÉRIOS\_ADICIONAIS}}  
  3\. \*\*Plano Final:\*\* Apresente a versão final e refinada, ajustada para mitigar os riscos e fortalecer os pontos fracos.

\</details\>

### ---

**Seção 3: Protocolo de Otimização Contínua**

A eficácia deste framework depende de sua aplicação e refinamento.

1. **Proposta de Otimização:** Ao sugerir uma otimização, a recomendação deve ser estruturada: "Com base na análise da tarefa (NT, RQ, CP), o framework recomenda a técnica \[ID da Técnica\]. Isso visa melhorar \[Métrica Alvo, ex: precisão, completude\] com um custo computacional estimado de \[Análise de Custo\]."  
2. **Protocolo de Teste (A/B):** A validação da recomendação deve ser sugerida. "Para confirmar a eficácia, sugiro comparar a saída do prompt original com a do prompt otimizado, avaliando \[Critério de Sucesso 1\] e \[Critério de Sucesso 2\]."  
3. **Ciclo de Feedback:** Os resultados das otimizações devem ser registrados para, potencialmente, refinar a Matriz de Seleção de Técnica no futuro. O framework é um documento vivo.