
# ProcessIA — Assistente de Instrução Processual com IA (protótipo)

**Endpoint:** https://processia-myw6wrxdektdqj6yfpfuyv.streamlit.app/
**Avaliação final — IA Generativa (UniSENAI, Prof. Douglas)**

> O endpoint público roda em **modo simulado** (mock), por decisão de custo e segurança: não há chave de API exposta em produção, e o serviço não depende de cota de terceiros para ficar no ar. A integração com LLM real (Groq/Llama 3.3 70B) roda localmente e será demonstrada ao vivo na avaliação.

## O problema e a solução

Órgãos públicos instruem diariamente processos administrativos que exigem conferência documental, análise de conformidade, classificação de riscos e elaboração de despachos e ofícios — trabalho repetitivo, sensível a erro humano e dependente de conhecimento administrativo e jurídico, com público claro que pagaria por isso (unidades de gestão contratual de qualquer órgão público). O ProcessIA é um protótipo web que assiste esse fluxo: cadastro do processo, checklist documental dinâmico por tipo (Prorrogação Contratual, Pagamento, Fiscalização Contratual), análise de risco em 3 dimensões no padrão ReAct (Thought/Action/Observation), geração de minuta institucional (Despacho/Ofício) e avaliação da minuta no estilo LLM-as-a-judge (5 critérios, escala 1 a 4). A fase 1 implementou tudo isso de forma determinística (mock); esta fase substitui o núcleo de análise por agentes LLM reais, mantendo o mock como modo padrão e como rede de segurança.

## Arquitetura de LLM

```
input do usuário (id do processo)
        │
        ▼
seletor mock/llm — usar_llm() em analise.py
   (PROCESSIA_MODO=llm E chave presente?)
        │
        ├── não → pipeline mock (regras determinísticas, fase 1)
        │
        └── sim → pipeline sequencial via LLM:

            Agente Documental
                 │  (descobre pendências via tools)
                 ▼
            Agente de Risco
                 │  (recebe as pendências do agente anterior)
                 ▼
            Agente de Minuta
                 │  (recebe pendências + riscos + recomendação)
                 ▼
            Avaliador (LLM-as-a-judge)
                 │  (recebe a minuta + pendências + riscos)
                 ▼
            resultado (mesmo formato JSON do mock)
```

Cada agente tem um system prompt próprio em `prompts/*.txt`, ferramentas tipadas em `tools/definicoes.py` (quando aplicável) e retorno validado como structured output Pydantic. Qualquer falha na chamada LLM (chave ausente, timeout, rate limit, JSON inválido após retries) cai automaticamente para o resultado do mock, com aviso explícito na tela.

## Decisões e justificativas

### Modelo: Llama 3.3 70B via Groq

Escolhido por estar disponível em free tier, pela velocidade de inferência do Groq (relevante para um pipeline de 4 chamadas sequenciais) e por ser suficiente para tool calling e structured output — não é uma tarefa que exige raciocínio de ponta, e sim seguir instruções e formato com precisão.

Na prática, apareceram dois limites concretos:
- **Deslize de instrução em tool calling**: o Agente de Minuta chamou `buscar_fundamentacao_legal` com o tipo de processo errado (`"Pagamento"` para um processo de Prorrogação Contratual), mesmo tendo acabado de consultar o tipo correto via `consultar_processo` na mesma iteração. Só foi corrigido reforçando explicitamente no prompt para usar "exatamente o valor do campo tipo retornado... para ESTE processo" — o modelo passou a se autocorrigir dentro do próprio loop de tool calling.
- **Rate limit de 100.000 tokens/dia (TPD)** no tier gratuito: estourado repetidas vezes durante os testes desta sessão (o pipeline de 4 agentes com tool calling consome bem mais tokens por execução do que uma chamada simples). Isso chegou a impedir a captura de uma última demonstração bem-sucedida via navegador no fim dos testes — contornado apenas parcialmente esperando a cota recuperar.

Com um modelo pago (ex.: Claude Sonnet) a expectativa é de menos deslizes desse tipo em instruções compostas, redação institucional mais natural sem tantas rodadas de ajuste de prompt, e nenhum limite diário de tokens travando teste — ao custo de pagar por token em vez de usar free tier.

### Framework: SDK OpenAI direto, sem LangChain

A orquestração aqui é uma sequência fixa de 4 chamadas (Documental → Risco → Minuta → Avaliador), sem ramificação condicional nem grafo de estados — não há decisão dinâmica de "qual agente chamar a seguir" que justifique um framework de orquestração. Implementar o loop de tool calling diretamente com o SDK da OpenAI (`llm_client.py`) manteve menos dependências no projeto e deixou explícito, em código simples, exatamente o que acontece em cada iteração (chamada, execução de tool, devolução do resultado, repetição até resposta final ou limite de iterações).

### Parâmetros: temperatura

- **0.2** nos três agentes do pipeline de análise (Documental, Risco, Minuta): baixa o suficiente para reduzir variação entre execuções do mesmo processo, mas sem zerar completamente a temperatura — a redação da minuta se beneficia de alguma liberdade estilística, contanto que o conteúdo (riscos, recomendação, pendências) permaneça consistente.
- **0** no Avaliador: aqui a consistência é o próprio objetivo — as notas atribuídas a uma mesma minuta devem ser reprodutíveis entre chamadas, já que é um critério de qualidade sendo medido, não um texto sendo redigido.

### Tools

Quatro ferramentas em `tools/definicoes.py`, cada uma cobrindo um tipo de dado que o modelo não deve inventar ou não sabe calcular:

- **`consultar_processo`**: dados cadastrais do processo (número, tipo, unidade, objeto, valor, vigência, urgência) — vêm do banco, não da memória do modelo.
- **`verificar_checklist`**: estado real do checklist documental (marcado/pendente, crítico ou não) — é o fato central que o Agente Documental precisa apurar, não presumir.
- **`calcular_prazo_vigencia`**: dias restantes até o fim da vigência (negativo se vencida) — aritmética de datas é um ponto conhecido de erro em LLMs; a conta é feita em Python e devolvida pronta.
- **`buscar_fundamentacao_legal`**: artigos de lei aplicáveis por tipo de processo — citação legal não pode ser "aproximada" ou parafraseada pelo modelo; vem de um mapa fixo no código.

### Prompting

Os quatro prompts em `prompts/*.txt` seguem a mesma estrutura: tags XML (`<funcao>`, `<restricoes>`, `<formato_saida>`, `<exemplo>`), persona fixa (ex.: "Você é o Agente de Risco do ProcessIA..."), restrições explícitas anti-alucinação ("baseie-se EXCLUSIVAMENTE nos dados retornados pelas ferramentas", "nunca presuma..."), um exemplo few-shot completo em JSON, e o formato de saída descrito campo a campo. No prompt do Agente de Risco, as regras de classificação (documental/financeiro/jurídico) e de recomendação foram transcritas literalmente das mesmas funções Python do mock (`analise.py`) — não resumidas, não reformuladas — como guardrail para que o LLM chegue à mesma conclusão que a lógica determinística chegaria, dado o mesmo processo.

## O que funcionou

- **Tool calling autônomo**: o Llama 3.3 70B decidiu sozinho quando e quais ferramentas chamar (às vezes mais de uma vez, revisando a própria decisão), sem que os prompts descrevessem um passo a passo de chamadas.
- **Equivalência LLM vs. mock**: nos dois processos de teste do seed (um com pendências críticas, outro completo), os riscos documental/financeiro/jurídico e a recomendação final do LLM bateram exatamente com o resultado do mock determinístico.
- **Iteração de prompt sem tocar código**: todas as correções de comportamento (tipo de processo errado na tool, registro do Ofício, menção à vigência vencida, grafia da lei) foram feitas editando apenas os arquivos `.txt` em `prompts/`, sem alterar uma linha de Python.
- **Fallback provado com erro real**: o mecanismo de fallback foi testado tanto com uma chave inválida forçada (erro 401) quanto — sem ter sido planejado — com um rate limit real do Groq batendo em pleno teste (erro 429); nos dois casos a tela mostrou o erro real da API e caiu para o resultado mock corretamente.

## O que não funcionou

- **Bug de tool com tipo de processo errado**: descrito acima (seção Modelo). Corrigido via instrução explícita no prompt do Agente de Minuta.
- **Minutas exigiram 2 rodadas de refinamento de registro institucional**: a primeira gerava um Ofício afirmando que o processo "já foi encaminhado" quando na verdade a minuta é o próprio instrumento do encaminhamento (ainda não expedido); também não mencionava vigência contratual vencida como pendência no parágrafo de análise — descobri nesse processo que a ferramenta de cálculo de prazo de vigência nem estava disponível para o Agente de Minuta (erro de configuração de tools, não de prompt). Segunda rodada corrigiu a redação do Ofício, adicionou a tool faltante e padronizou a grafia "Lei nº 14.133/2021".
- **Rate limit diário estourado nos testes**: a cota de 100.000 tokens/dia do tier gratuito do Groq foi consumida ao longo desta sessão de testes (múltiplos pipelines completos de 4 agentes, cada um com vários tool calls), a ponto de bloquear uma última demonstração bem-sucedida via navegador — mitigado documentando que o mesmo caminho já havia funcionado por script antes de a cota esgotar, e que o próprio erro 429 aparecendo na tela prova que a integração é real.
- **BOM do PowerShell no `.env`**: o arquivo `.env` local foi salvo com um BOM UTF-8 (comportamento padrão do PowerShell), o que fazia o `python-dotenv` ler a chave como `﻿GROQ_API_KEY` em vez de `GROQ_API_KEY`, quebrando a leitura silenciosamente. Corrigido carregando o `.env` com `encoding="utf-8-sig"` em `llm_client.py`, sem alterar o arquivo `.env` do usuário.

## Guardrails

- **Fallback automático para o mock** em qualquer exceção da chamada LLM (chave ausente, timeout, rate limit, JSON inválido após esgotar retries), com aviso visível na tela.
- **Modo mock como padrão** do endpoint público: `usar_llm()` só retorna `True` se `PROCESSIA_MODO=llm` estiver explicitamente definido e a chave existir; sem isso, o sistema nunca tenta chamar a API.
- **Limite de 5 iterações** no loop de tool calling (`MAX_ITERACOES_AGENTE` em `llm_client.py`), evitando loops indefinidos de chamadas de ferramenta.
- **Structured output com retries**: toda resposta final é validada contra um schema Pydantic; se o JSON vier inválido, o erro é devolvido ao modelo e ele tenta de novo, até 2 vezes, antes de desistir e propagar a falha (que aciona o fallback acima).

## Como rodar localmente

```
pip install -r requirements.txt
python -m streamlit run app.py
```

Por padrão roda em modo mock. Para usar a integração LLM real, copie `.env.example` para `.env`, preencha `GROQ_API_KEY` e defina `PROCESSIA_MODO=llm`.

## Fase 1 (resumo)

A fase 1 entregou o protótipo determinístico: Streamlit + SQLite por rapidez de deploy, domínio separado da UI (`checklists.py`, `analise.py`, `minutas.py` como módulos Python puros, desenhados desde então para permitir trocar a análise por LLM sem tocar nas telas), seed automático idempotente (o Streamlit Cloud não persiste o `.db` entre deploys) e checklists/regras de risco especificados a partir de prática real em gestão de contratos públicos (Lei 14.133/2021), não gerados pelo agente.

Do trabalho com o agente de codificação nessa fase, destacaram-se acertos espontâneos (PRAGMA foreign_keys, camada de acesso a dados, cache em session_state) e a constatação de que prompts localizados por arquivo superam instruções vagas. Do lado dos problemas: um erro de lógica na minuta (recomendação ignorada, dependia só do tipo de processo), texto institucional que exigiu revisão humana de domínio (concordância, registro trocado entre Despacho/Ofício, fundamentação legal genérica), loops de verificação redundantes (mitigado com regra de 1 verificação por entrega no CLAUDE.md) e um caso de desobediência pontual a uma instrução conversacional, resolvido só depois de virar regra persistente no arquivo de contexto.

Limitações conhecidas mantidas por decisão de escopo: sem tela de edição de processo, sem autenticação, sem upload de documentos. O próximo passo definido ao final da fase 1 — substituir os mocks por LLM real com structured outputs, tool calling e prompts por agente — é exatamente o que esta fase implementou.

## Mapa do repositório
- `prompts/` — system prompts dos 3 agentes e do avaliador (um arquivo por agente)
- `tools/definicoes.py` — as 4 ferramentas (schema + implementação)
- `llm_client.py` — cliente Groq, loop de tool calling (máx. 5 iterações), structured output com Pydantic e retries
- `analise.py` — pipeline sequencial Documental → Risco → Minuta e seletor mock/llm
- `minutas.py` — geração e avaliação de minuta (LLM-as-a-judge) nos dois modos
- `pages/3_Analise.py` e `pages/4_Minuta.py` — integração às telas com fallback automático
- `PROMPTS.md` — histórico das iterações de prompt, incluindo os erros

## Registro de prompts

O arquivo `PROMPTS.md` documenta os prompts usados ao longo do projeto e o resultado de cada um.
