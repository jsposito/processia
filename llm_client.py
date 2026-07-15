"""Cliente para chamadas ao LLM via Groq (API compatível com OpenAI)."""
import json
import os
import time

from dotenv import load_dotenv
from openai import APITimeoutError, OpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

load_dotenv(encoding="utf-8-sig")  # utf-8-sig tolera BOM (o .env local foi salvo com BOM pelo PowerShell)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MODELO = "llama-3.3-70b-versatile"
TEMPERATURA = 0.2
MAX_RETRIES_JSON = 2
MAX_RETRIES_RATE_LIMIT = 3
MAX_ITERACOES_AGENTE = 5


class ChaveApiAusenteError(Exception):
    """Levantada quando GROQ_API_KEY não está definida no ambiente."""


def _obter_cliente() -> OpenAI:
    chave = os.getenv("GROQ_API_KEY")
    if not chave:
        raise ChaveApiAusenteError(
            "GROQ_API_KEY não encontrada no ambiente. Defina-a no arquivo .env."
        )
    return OpenAI(api_key=chave, base_url=GROQ_BASE_URL)


def _criar_chat_completion(cliente: OpenAI, mensagens: list, **kwargs):
    """Executa cliente.chat.completions.create com backoff exponencial em caso de rate limit."""
    for tentativa in range(MAX_RETRIES_RATE_LIMIT + 1):
        try:
            return cliente.chat.completions.create(
                model=MODELO,
                messages=mensagens,
                timeout=30,
                **kwargs,
            )
        except RateLimitError:
            if tentativa == MAX_RETRIES_RATE_LIMIT:
                raise
            time.sleep(2 ** tentativa)
        except APITimeoutError as erro:
            raise TimeoutError("Tempo limite excedido ao chamar o LLM (Groq).") from erro


def _chamar_com_backoff(cliente: OpenAI, mensagens: list, temperatura: float) -> str:
    """Chama o LLM em modo JSON simples (sem tools) e retorna o texto da resposta."""
    resposta = _criar_chat_completion(
        cliente, mensagens, temperature=temperatura, response_format={"type": "json_object"}
    )
    return resposta.choices[0].message.content


def chamar_llm(
    system_prompt: str,
    user_prompt: str,
    response_model: type[BaseModel],
    temperatura: float = TEMPERATURA,
) -> BaseModel:
    """Chama o LLM em modo JSON e valida a resposta contra response_model.

    Faz até MAX_RETRIES_JSON novas tentativas caso a resposta não seja um JSON
    válido para o modelo informado, reenviando o erro ao LLM para correção.
    """
    cliente = _obter_cliente()

    mensagens = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    ultimo_erro: Exception | None = None
    for _ in range(MAX_RETRIES_JSON + 1):
        conteudo = _chamar_com_backoff(cliente, mensagens, temperatura)
        try:
            dados = json.loads(conteudo)
            return response_model.model_validate(dados)
        except (json.JSONDecodeError, ValidationError) as erro:
            ultimo_erro = erro
            mensagens.append({"role": "assistant", "content": conteudo})
            mensagens.append({
                "role": "user",
                "content": (
                    "A resposta anterior não é um JSON válido para o formato esperado. "
                    f"Erro: {erro}. Responda novamente apenas com o JSON correto."
                ),
            })

    raise ValueError(
        f"Resposta do LLM não pôde ser validada após {MAX_RETRIES_JSON} nova(s) tentativa(s): {ultimo_erro}"
    )


def _serializar_tool_calls(tool_calls) -> list:
    return [
        {
            "id": tool_call.id,
            "type": "function",
            "function": {
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments,
            },
        }
        for tool_call in tool_calls
    ]


def _executar_tool_call(tool_call, funcoes: dict) -> str:
    nome = tool_call.function.name
    argumentos = json.loads(tool_call.function.arguments or "{}")

    funcao = funcoes.get(nome)
    if funcao is None:
        resultado = {"erro": f"Ferramenta '{nome}' não existe."}
    else:
        resultado = funcao(**argumentos)

    print(f"[tool_call] {nome}({argumentos}) -> {resultado}")
    return json.dumps(resultado, ensure_ascii=False)


def chamar_agente(system_prompt: str, user_prompt: str, tools: list, response_model: type[BaseModel]) -> BaseModel:
    """Executa um agente com tool calling real.

    O modelo decide se e quando chamar as ferramentas em `tools` (cada item com
    "schema" no formato OpenAI e "funcao" Python correspondente); as chamadas
    são executadas localmente e seus resultados devolvidos ao modelo, repetindo
    até uma resposta final (sem tool_calls) ser produzida e validada contra
    response_model, ou até MAX_ITERACOES_AGENTE ser atingido.
    """
    cliente = _obter_cliente()

    schemas = [tool["schema"] for tool in tools]
    funcoes = {tool["schema"]["function"]["name"]: tool["funcao"] for tool in tools}

    mensagens = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    ultimo_erro: Exception | None = None
    for _ in range(MAX_ITERACOES_AGENTE):
        resposta = _criar_chat_completion(
            cliente, mensagens, temperature=TEMPERATURA, tools=schemas, tool_choice="auto"
        )
        mensagem = resposta.choices[0].message

        if mensagem.tool_calls:
            mensagens.append({
                "role": "assistant",
                "content": mensagem.content,
                "tool_calls": _serializar_tool_calls(mensagem.tool_calls),
            })
            for tool_call in mensagem.tool_calls:
                resultado_json = _executar_tool_call(tool_call, funcoes)
                mensagens.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": resultado_json,
                })
            continue

        conteudo = mensagem.content or ""
        try:
            dados = json.loads(conteudo)
            return response_model.model_validate(dados)
        except (json.JSONDecodeError, ValidationError) as erro:
            ultimo_erro = erro
            mensagens.append({"role": "assistant", "content": conteudo})
            mensagens.append({
                "role": "user",
                "content": (
                    "A resposta anterior não é um JSON válido para o formato esperado. "
                    f"Erro: {erro}. Responda novamente apenas com o JSON correto, sem tool calls."
                ),
            })

    raise ValueError(
        f"Limite de {MAX_ITERACOES_AGENTE} iterações de tool calling atingido sem resposta final válida "
        f"(último erro: {ultimo_erro})."
    )
