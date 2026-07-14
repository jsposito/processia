"""Teste do Agente Documental via LLM com tool calling real, usando o banco de seed."""
import os

from dotenv import load_dotenv

load_dotenv(encoding="utf-8-sig")

from database import init_db, get_connection, carregar_estado_checklist
from checklists import get_checklist
from seed import popular_banco_se_vazio
from analise import analisar_processo_llm


def _achar_processo_com_pendencias_criticas():
    """Retorna (processo_id, descricoes_criticas_pendentes) do primeiro processo do seed com pendência crítica."""
    with get_connection() as conn:
        rows = conn.execute("SELECT id, tipo FROM processos ORDER BY id").fetchall()

    for row in rows:
        itens = get_checklist(row["tipo"])
        estado = carregar_estado_checklist(row["id"])
        criticos_faltantes = [item["descricao"] for item in itens if item["critico"] and not estado.get(item["id"], False)]
        if criticos_faltantes:
            return row["id"], criticos_faltantes

    raise RuntimeError("Nenhum processo do seed possui pendência crítica.")


def test_agente_documental_identifica_pendencias_criticas():
    if not os.getenv("GROQ_API_KEY"):
        print("PULADO: GROQ_API_KEY não definida no .env.")
        return

    init_db()
    popular_banco_se_vazio()

    processo_id, criticos_esperados = _achar_processo_com_pendencias_criticas()
    print(f"Processo de teste: id={processo_id}, críticos pendentes esperados={criticos_esperados}")

    resultado = analisar_processo_llm(processo_id)

    print(f"Resultado do Agente Documental: {resultado}")

    assert set(resultado["criticos_pendentes"]) == set(criticos_esperados), (
        f"Divergência nas pendências críticas.\nEsperado: {criticos_esperados}\nRecebido: {resultado['criticos_pendentes']}"
    )
    assert resultado["observacao"].strip()
    print("OK: Agente Documental via LLM (com tool calling) identificou corretamente as pendências críticas.")


if __name__ == "__main__":
    test_agente_documental_identifica_pendencias_criticas()
