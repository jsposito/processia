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


class ChaveApiAusenteError(Exception):
    """Levantada quando GROQ_API_KEY não está definida no ambiente."""


def _obter_cliente() -> OpenAI:
    chave = os.getenv("GROQ_API_KEY")
    if not chave:
        raise ChaveApiAusenteError(
            "GROQ_API_KEY não encontrada no ambiente. Defina-a no arquivo .env."
        )
    return OpenAI(api_key=chave, base_url=GROQ_BASE_URL)


def _chamar_com_backoff(cliente: OpenAI, mensagens: list) -> str:
    """Executa a chamada ao chat completions com backoff exponencial em caso de rate limit."""
    for tentativa in range(MAX_RETRIES_RATE_LIMIT + 1):
        try:
            resposta = cliente.chat.completions.create(
                model=MODELO,
                messages=mensagens,
                temperature=TEMPERATURA,
                response_format={"type": "json_object"},
                timeout=30,
            )
            return resposta.choices[0].message.content
        except RateLimitError:
            if tentativa == MAX_RETRIES_RATE_LIMIT:
                raise
            time.sleep(2 ** tentativa)
        except APITimeoutError as erro:
            raise TimeoutError("Tempo limite excedido ao chamar o LLM (Groq).") from erro


def chamar_llm(system_prompt: str, user_prompt: str, response_model: type[BaseModel]) -> BaseModel:
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
        conteudo = _chamar_com_backoff(cliente, mensagens)
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
