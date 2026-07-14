"""Testes mínimos: (a) modo mock funciona sem chave; (b) chamada trivial ao Groq responde."""
import os

from seed import popular_banco_se_vazio
from analise import analisar_processo, analisar_processo_llm, usar_llm
from database import get_connection, init_db


def _obter_processo_id_existente() -> int:
    init_db()
    popular_banco_se_vazio()
    with get_connection() as conn:
        linha = conn.execute("SELECT id FROM processos LIMIT 1").fetchone()
    return linha["id"]


def test_modo_mock_sem_chave():
    os.environ.pop("PROCESSIA_MODO", None)
    os.environ.pop("GROQ_API_KEY", None)

    assert usar_llm() is False

    processo_id = _obter_processo_id_existente()
    resultado = analisar_processo(processo_id)
    assert resultado.get("recomendacao")
    print("OK (a): modo mock funciona sem depender de GROQ_API_KEY.")


def test_chamada_trivial_groq():
    from dotenv import load_dotenv
    load_dotenv(encoding="utf-8-sig")

    if not os.getenv("GROQ_API_KEY"):
        print("PULADO (b): GROQ_API_KEY não definida no .env.")
        return

    processo_id = _obter_processo_id_existente()
    resposta = analisar_processo_llm(processo_id)
    assert isinstance(resposta, str) and resposta.strip()
    print(f"OK (b): Groq respondeu: {resposta!r}")


if __name__ == "__main__":
    test_modo_mock_sem_chave()
    test_chamada_trivial_groq()
