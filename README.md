
# ProcessIA — Assistente de Instrução Processual com IA (protótipo)

**Endpoint:** https://processia-myw6wrxdektdqj6yfpfuyv.streamlit.app/
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
```
pip install -r requirements.txt
python -m streamlit run app.py
```

## O que funcionou com o agente de codificação (Claude Code)

- **Esqueleto de primeira**: a estrutura multipage + SQLite subiu funcionando no primeiro prompt, sem intervenção manual.
- **Boas práticas espontâneas**: ativou `PRAGMA foreign_keys` no SQLite (armadilha clássica que muitos desenvolvedores esquecem), criou camada de funções de acesso a dados em vez de espalhar SQL nas páginas, cacheou resultados em `session_state` para sobreviver a reruns do Streamlit, e verificou a versão do pandas antes de escolher entre `Styler.map` e `applymap`.
- **Testes próprios de qualidade**: gerou cenários de teste que eu não tinha pedido, incluindo migração de schema sem perda de dados e idempotência do seed.
- **Prompts localizados funcionam melhor**: seguindo a técnica vista em aula, prompts que indicavam arquivo e comportamento esperado ("em minutas.py, o parágrafo 2 deve...") produziram resultado muito superior a instruções vagas.

## O que não funcionou e exigiu intervenção

- **Erro de lógica na minuta**: o agente sugeriu "Despacho de Autorização de Pagamento" para um processo cuja recomendação era devolução por pendências. A minuta dependia só do tipo de processo e ignorava a recomendação da análise. Corrigido por prompt específico.
- **Texto institucional exigiu revisão humana de domínio**: a primeira versão das minutas tinha erro de concordância ("classificação documental Alto"), Ofício com registro de Despacho (opinativo em vez de comunicativo) e fundamentação legal genérica sem citação de artigo. Corrigi especificando artigos por tipo (art. 141 da Lei 14.133/2021 e arts. 62/63 da Lei 4.320/1964 para pagamento, arts. 106/107 para prorrogação, art. 117 para fiscalização).
- **Loops de verificação**: o agente repetia checagens de servidor e limpeza várias vezes por etapa, consumindo cota. Mitigado com regra no CLAUDE.md limitando a 1 verificação por entrega.
- **Desobediência pontual**: mesmo após instrução para não criar testes automatizados de UI, o agente começou a inspecionar a API do AppTest do Streamlit. Foi necessário negar o comando e reforçar a regra no CLAUDE.md. Mostra que instruções conversacionais têm menos aderência que regras persistentes no arquivo de contexto.
- **Nomes de página no menu**: o Streamlit multipage nomeia páginas pelo arquivo, o que gerava menu sem acentos ("Analise", "Historico") e página principal chamada "app". Resolvido migrando para st.navigation.

## Limitações conhecidas

- Não há tela de edição de processo: erro de cadastro exige correção direta no banco (descoberto na prática, ao cadastrar processo com tipo errado durante os testes).
- Análise e avaliação são determinísticas: regras se-então, não IA. É o comportamento esperado nesta fase.
- Sem autenticação e sem upload de documentos, por decisão de escopo.

## Próximos passos (fase 2 — trabalho final)

Substituir os mocks por LLM real via API (candidatos: OpenRouter/Groq apresentados em aula), com structured outputs para manter o contrato JSON atual, tool calling para consulta ao banco, prompts por agente (documental, risco, minuta, avaliador) e guardrails com validação humana antes de qualquer encaminhamento.

## Registro de prompts

O arquivo PROMPTS.md documenta os prompts usados e o resultado de cada um.

