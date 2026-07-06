import json

import pandas as pd
import streamlit as st

import database as db
from seed import popular_banco_se_vazio
from checklists import TIPOS_PROCESSO
from analise import RECOMENDACAO_DEVOLUCAO, RECOMENDACAO_RESSALVAS, RECOMENDACAO_APTO

st.set_page_config(page_title="Processia - Dashboard", page_icon="📋", layout="wide")

db.init_db()
popular_banco_se_vazio()

st.title("📋 Processia")
st.subheader("Dashboard")

SEM_ANALISE = "Sem análise"
_ORDEM_RISCO = {"Alto": 3, "Médio": 2, "Baixo": 1}
_CORES_RISCO = {
    "Alto": "background-color: #dc3545; color: white",
    "Médio": "background-color: #ffc107; color: black",
    "Baixo": "background-color: #28a745; color: white",
}


def _risco_geral(conteudo_analise: dict) -> str:
    riscos = [conteudo_analise["risco_documental"], conteudo_analise["risco_financeiro"], conteudo_analise["risco_juridico"]]
    return max(riscos, key=lambda r: _ORDEM_RISCO[r])


def _cor_risco(valor: str) -> str:
    return _CORES_RISCO.get(valor, "")


processos = db.listar_processos()
analises = db.listar_analises()
minutas = db.listar_minutas()

ultima_analise_por_processo = {}
for a in analises:
    if a["processo_id"] not in ultima_analise_por_processo:
        ultima_analise_por_processo[a["processo_id"]] = json.loads(a["conteudo"])

processos_risco_alto = sum(
    1
    for conteudo in ultima_analise_por_processo.values()
    if "Alto" in (conteudo["risco_documental"], conteudo["risco_financeiro"], conteudo["risco_juridico"])
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de processos", len(processos))
col2.metric("Processos com risco Alto", processos_risco_alto)
col3.metric("Minutas geradas", len(minutas))
col4.metric("Análises realizadas", len(analises))

st.divider()

grafico_col1, grafico_col2 = st.columns(2)

with grafico_col1:
    st.subheader("Processos por tipo")
    contagem_tipo = pd.Series([p["tipo"] for p in processos]).value_counts().reindex(TIPOS_PROCESSO, fill_value=0)
    st.bar_chart(contagem_tipo)

with grafico_col2:
    st.subheader("Processos por resultado de recomendação")
    recomendacoes = [
        ultima_analise_por_processo[p["id"]]["recomendacao"] if p["id"] in ultima_analise_por_processo else SEM_ANALISE
        for p in processos
    ]
    ordem_recomendacao = [RECOMENDACAO_DEVOLUCAO, RECOMENDACAO_RESSALVAS, RECOMENDACAO_APTO, SEM_ANALISE]
    contagem_recomendacao = pd.Series(recomendacoes).value_counts().reindex(ordem_recomendacao, fill_value=0)
    st.bar_chart(contagem_recomendacao)

st.divider()

st.subheader("Últimos 5 processos")
if not processos:
    st.write("Nenhum processo cadastrado ainda.")
else:
    linhas = []
    for p in processos[:5]:
        conteudo = ultima_analise_por_processo.get(p["id"])
        risco = _risco_geral(conteudo) if conteudo else SEM_ANALISE
        linhas.append(
            {
                "Número SEI": p["numero"],
                "Tipo": p["tipo"],
                "Urgência": p["urgencia"],
                "Risco (última análise)": risco,
            }
        )
    tabela = pd.DataFrame(linhas)
    tabela_estilizada = tabela.style.map(_cor_risco, subset=["Risco (última análise)"])
    st.dataframe(tabela_estilizada, use_container_width=True, hide_index=True)

st.info("Use o menu lateral para navegar entre as páginas do sistema.")
