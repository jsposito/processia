"""Teste do pipeline Documental -> Risco -> Minuta via LLM (tool calling real).

Compara os riscos retornados pelo LLM com os riscos do mock determinístico
(analisar_processo) para dois processos do seed: um com pendências críticas
e um completo. Também imprime as tool calls executadas e a minuta gerada.
"""
import os

from dotenv import load_dotenv

load_dotenv(encoding="utf-8-sig")

from database import init_db, get_connection
from seed import popular_banco_se_vazio
from analise import analisar_processo, analisar_processo_llm


def _achar_processo_por_unidade(unidade: str) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM processos WHERE unidade_demandante = ? ORDER BY id LIMIT 1",
            (unidade,),
        ).fetchone()
    if not row:
        raise RuntimeError(f"Nenhum processo encontrado para a unidade '{unidade}'.")
    return row["id"]


def _comparar_com_mock(processo_id: int, rotulo: str) -> None:
    print(f"\n=== Processo {processo_id} ({rotulo}) ===")

    mock = analisar_processo(processo_id)
    print(f"Mock  -> documental={mock['risco_documental']}, financeiro={mock['risco_financeiro']}, "
          f"juridico={mock['risco_juridico']}, recomendacao={mock['recomendacao']!r}")

    llm = analisar_processo_llm(processo_id)
    print(f"LLM   -> documental={llm['risco_documental']}, financeiro={llm['risco_financeiro']}, "
          f"juridico={llm['risco_juridico']}, recomendacao={llm['recomendacao']!r}")

    assert llm["risco_documental"] == mock["risco_documental"], "risco_documental divergente"
    assert llm["risco_financeiro"] == mock["risco_financeiro"], "risco_financeiro divergente"
    assert llm["risco_juridico"] == mock["risco_juridico"], "risco_juridico divergente"
    assert llm["recomendacao"] == mock["recomendacao"], "recomendacao divergente"

    minuta_observation = llm["etapas_react"][-1]["observation"]
    print(f"\nMinuta gerada pelo Agente de Minuta:\n{minuta_observation}\n")

    print(f"OK: riscos e recomendação do LLM coincidem com o mock para o processo {processo_id} ({rotulo}).")


def test_pipeline_llm_coincide_com_mock():
    if not os.getenv("GROQ_API_KEY"):
        print("PULADO: GROQ_API_KEY não definida no .env.")
        return

    init_db()
    popular_banco_se_vazio()

    processo_pendencias_criticas = _achar_processo_por_unidade("Prefeitura Universitária")
    processo_completo = _achar_processo_por_unidade("Superintendência de Infraestrutura")

    _comparar_com_mock(processo_pendencias_criticas, "pendências críticas")
    _comparar_com_mock(processo_completo, "completo")


if __name__ == "__main__":
    test_pipeline_llm_coincide_com_mock()
