
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

