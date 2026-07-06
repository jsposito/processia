import time

import streamlit as st

from database import init_db, listar_processos
from analise import (
    analisar_processo,
    RISCO_ALTO,
    RISCO_MEDIO,
    RISCO_BAIXO,
    RECOMENDACAO_DEVOLUCAO,
    RECOMENDACAO_RESSALVAS,
)

init_db()

st.title("🔍 Análise")

CORES_RISCO = {
    RISCO_ALTO: ("#dc3545", "#ffffff"),
    RISCO_MEDIO: ("#ffc107", "#000000"),
    RISCO_BAIXO: ("#28a745", "#ffffff"),
}


def _render_risco_card(coluna, titulo: str, nivel: str) -> None:
    cor_fundo, cor_texto = CORES_RISCO.get(nivel, ("#6c757d", "#ffffff"))
    coluna.markdown(
        f"""
        <div style="background-color:{cor_fundo};color:{cor_texto};
                    padding:1rem;border-radius:0.5rem;text-align:center;">
            <div style="font-size:0.9rem;font-weight:600;">{titulo}</div>
            <div style="font-size:1.6rem;font-weight:700;">{nivel}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if "analises_por_processo" not in st.session_state:
    st.session_state["analises_por_processo"] = {}

processos = listar_processos()

if not processos:
    st.info("Nenhum processo cadastrado. Cadastre um processo na página 'Novo Processo'.")
else:
    opcoes = {f"{p['numero']} — {p['tipo']}": p["id"] for p in processos}
    escolha = st.selectbox("Processo", list(opcoes.keys()))
    processo_id = opcoes[escolha]

    if st.button("Executar análise"):
        resultado = analisar_processo(processo_id)
        st.session_state["analises_por_processo"][processo_id] = resultado

        st.subheader("Processamento dos agentes")
        etapas = resultado["etapas_react"]
        for indice, etapa in enumerate(etapas):
            with st.status(etapa["agente"], expanded=True) as status:
                st.markdown(f"**Thought:** {etapa['thought']}")
                st.markdown(f"**Action:** {etapa['action']}")
                st.markdown(f"**Observation:** {etapa['observation']}")
                status.update(label=f"{etapa['agente']} — concluído", state="complete")
            if indice < len(etapas) - 1:
                time.sleep(1)

    resultado = st.session_state["analises_por_processo"].get(processo_id)

    if resultado:
        st.divider()
        st.subheader("Classificação de risco")
        col1, col2, col3 = st.columns(3)
        _render_risco_card(col1, "Risco documental", resultado["risco_documental"])
        _render_risco_card(col2, "Risco financeiro", resultado["risco_financeiro"])
        _render_risco_card(col3, "Risco jurídico", resultado["risco_juridico"])

        st.subheader("Documentos faltantes")
        faltantes = resultado["documentos_faltantes"]
        if not faltantes["criticos"] and not faltantes["complementares"]:
            st.write("Não há documentos pendentes.")
        else:
            if faltantes["criticos"]:
                st.markdown("**Críticos:**")
                for descricao in faltantes["criticos"]:
                    st.markdown(f"- {descricao}")
            if faltantes["complementares"]:
                st.markdown("**Complementares:**")
                for descricao in faltantes["complementares"]:
                    st.markdown(f"- {descricao}")

        st.subheader("Recomendação")
        recomendacao = resultado["recomendacao"]
        if recomendacao == RECOMENDACAO_DEVOLUCAO:
            st.error(recomendacao)
        elif recomendacao == RECOMENDACAO_RESSALVAS:
            st.warning(recomendacao)
        else:
            st.success(recomendacao)
    else:
        st.caption("Clique em \"Executar análise\" para gerar o resultado deste processo.")
