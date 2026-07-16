# Registro de prompts — ProcessIA

## Prompt 1 — Esqueleto do projeto
Prompt: estrutura Streamlit multipage + SQLite (app.py, 5 pages, database.py, checklists.py, analise.py, minutas.py, requirements.txt, .gitignore).
Resultado: gerou tudo de primeira, HTTP 200, banco criado com 3 tabelas, zero intervenção manual no código. Observação: agente entrou em loop de verificações repetidas ao encerrar o servidor de teste; corrigido com regra no CLAUDE.md.
## Prompt 2 — Checklists por tipo de processo
Prompt: especificação completa dos 3 checklists (itens críticos/complementares definidos por mim a partir da prática profissional) + tabela checklist_estado.
Resultado: transcrição fiel, zero itens inventados, IDs únicos. Ativou PRAGMA foreign_keys no SQLite por conta própria (boa prática que não pedi). Testou FK com processo inexistente sozinho.

## Prompt 3 — Lógica de análise de risco e agentes ReAct
Prompt: regras determinísticas de risco em 3 dimensões + recomendação + etapas ReAct de 3 agentes simulados.
Resultado: lógica correta nos 5 cenários de teste. ERRO ENCONTRADO: a minuta sugerida pelo Agente de Minuta dependia só do tipo de processo e ignorava a recomendação (sugeria "Autorização de Pagamento" para processo devolvido). Corrigido no prompt 4. O agente também tomou decisão de interpretação própria (restringiu risco jurídico a Prorrogação), revisada e aceita.

## Prompt 4 — Telas de cadastro, checklist e análise + correção da minuta
Prompt: correção da minuta por recomendação + 3 telas com detalhes de UX (agrupamento, barra de progresso, efeito sequencial ReAct, cards coloridos).
Resultado: telas funcionais de primeira. Cacheou análise em session_state para sobreviver a reruns (não pedido, correto). EPISÓDIO: mesmo instruído a não criar testes automatizados de UI, começou a inspecionar a API do AppTest; precisei negar o comando e reforçar a regra no CLAUDE.md.

## Prompt 5 — Minuta e avaliação LLM-as-a-judge simulada
Prompt: gerador de minuta institucional (Despacho/Ofício, parágrafos numerados, fundamentação legal) + painel de avaliação com 5 critérios em escala 1-4.
Resultado: estrutura correta, mas o texto exigiu revisão de domínio: concordância errada ("classificação documental Alto"), Ofício com registro opinativo de Despacho, fundamentação sem artigo. Corrigido especificando artigos por tipo (141/14.133 + 62-63/4.320; 106-107; 117). Lição: agente não substitui conhecimento do domínio no texto final.

## Prompt 6 — Dashboard, seed e navegação
Prompt: métricas, gráficos, tabela colorida; seed idempotente com 9 processos fictícios chamado automaticamente se banco vazio (necessário porque o Streamlit Cloud não persiste o .db); correção dos nomes do menu via st.navigation.
Resultado: funcionou de primeira, incluindo adição espontânea de pandas ao requirements.txt. Verificou a versão do pandas antes de escolher API do Styler.
# FASE 2 — Integração LLM

## Prompt 7 — Cliente Groq e modo dual
Resultado: gerou de primeira. Descoberta do agente: o .env criado pelo PowerShell tinha BOM UTF-8 que quebrava a leitura da chave silenciosamente; resolvido com encoding utf-8-sig no leitor, sem tocar no arquivo. Também construiu comando que lê o .env sem expor valores.

## Prompt 8 — Agente Documental com tool calling
Resultado: Llama 3.3 70B chamou consultar_processo e verificar_checklist por decisão própria; pendências retornadas idênticas ao banco.

## Prompt 9 — Agentes de Risco e Minuta
Resultado: pipeline completo coincidiu com o mock nos dois extremos (Alto/devolução e Baixo/apto). BUG REAL: o agente de minuta chamou buscar_fundamentacao_legal com tipo 'Pagamento' num processo de Prorrogação, mesmo tendo o tipo correto no contexto — limitação de instruction following do modelo aberto. Corrigido com restrição explícita no prompt; o modelo passou a se autocorrigir no loop.

## Prompt 10 — Refinamento da minuta (2 rodadas)
Primeira rodada de minutas tinha: ofício afirmando encaminhamento já ocorrido, vigência vencida omitida, "no" sem º. Corrigido editando só o .txt do prompt — nenhuma linha de código alterada. Uma das iterações foi feita manualmente durante indisponibilidade do agente, provando a vantagem de prompts em arquivos.

## Prompt 11 — Avaliador LLM e integração às telas
Resultado: fallback provado duas vezes — com chave inválida (sintético) e com rate limit real do Groq (100k tokens/dia esgotados pelos testes). O erro real na tela com fallback funcionando é a melhor evidência de que a integração é genuína.
