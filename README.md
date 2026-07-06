# ProcessIA — Assistente de Instrução Processual com IA (protótipo)

**Endpoint:** https://SUA-URL.streamlit.app
**Avaliação intermediária — IA Generativa (UniSENAI, Prof. Douglas)**

## O problema

Órgãos públicos instruem diariamente processos administrativos que exigem conferência documental, análise de conformidade, classificação de riscos e elaboração de despachos e ofícios. O trabalho é repetitivo, sensível a erro humano e depende de conhecimento administrativo e jurídico. Existe público claro que pagaria por isso: unidades de gestão contratual de qualquer órgão público.

## A solução

Protótipo web que simula o fluxo completo de instrução assistida por IA, sem integração com LLM nesta etapa (conforme regra da avaliação). Toda a "inteligência" é determinística e simulada, mas a arquitetura já delimita onde o LLM entraria.

Fluxo: cadastro do processo, checklist documental dinâmico por tipo (Prorrogação Contratual, Pagamento, Fiscalização Contratual), análise de risco em 3 dimensões executada por 3 agentes simulados no padrão ReAct (Thought/Action/Observation), geração de minuta institucional (Despacho/Ofício) e avaliação da minuta no estilo LLM-as-a-judge (5 critérios, escala 1 a 4, conforme material do curso sobre confiabilidade de avaliadores).

## Escolhas de design

- **Streamlit + SQLite**: escolha pragmática alinhada à recomendação em aula (rapidez para colocar no ar). O deploy no Streamlit Cloud reduz risco de endpoint fora do ar.
- **Domínio separado da UI**: `checklists.py`, `analise.py` e `minutas.py` são módulos Python puros. Na fase 2 (trabalho final), a função `analisar_processo()` pode ser substituída por chamada de API de LLM com structured output retornando o mesmo JSON, sem tocar nas telas.
- **Seed automático**: o banco nasce populado com 9 processos fictícios se estiver vazio, porque o Streamlit Cloud não persiste o arquivo .db entre deploys. A função é idempotente.
- **Conteúdo de domínio real**: checklists e regras de risco foram especificados por mim a partir da prática em gestão de contratos públicos (Lei 14.133/2021), não gerados pelo agente. O agente transcreveu a especificação.

## Como rodar localmente
