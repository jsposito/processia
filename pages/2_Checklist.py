import streamlit as st

from database import init_db, listar_processos, carregar_estado_checklist, salvar_estado_checklist
from checklists import get_checklist

st.set_page_config(page_title="Checklist", page_icon="✅", layout="wide")

init_db()

st.title("✅ Checklist")

processos = listar_processos()

if not processos:
    st.info("Nenhum processo cadastrado. Cadastre um processo na página 'Novo Processo'.")
else:
    opcoes = {f"{p['numero']} — {p['tipo']}": p["id"] for p in processos}
    escolha = st.selectbox("Processo", list(opcoes.keys()))
    processo_id = opcoes[escolha]
    processo = next(p for p in processos if p["id"] == processo_id)

    itens = get_checklist(processo["tipo"])
    estado_persistido = carregar_estado_checklist(processo_id)
    estado_atual = dict(estado_persistido)

    progresso_placeholder = st.empty()
    st.divider()

    criticos = [item for item in itens if item["critico"]]
    complementares = [item for item in itens if not item["critico"]]

    st.subheader("Documentos críticos")
    for item in criticos:
        marcado_antes = estado_persistido.get(item["id"], False)
        marcado = st.checkbox(item["descricao"], value=marcado_antes, key=f"chk_{processo_id}_{item['id']}")
        estado_atual[item["id"]] = marcado
        if marcado != marcado_antes:
            salvar_estado_checklist(processo_id, item["id"], marcado)

    st.subheader("Documentos complementares")
    for item in complementares:
        marcado_antes = estado_persistido.get(item["id"], False)
        marcado = st.checkbox(item["descricao"], value=marcado_antes, key=f"chk_{processo_id}_{item['id']}")
        estado_atual[item["id"]] = marcado
        if marcado != marcado_antes:
            salvar_estado_checklist(processo_id, item["id"], marcado)

    total_itens = len(itens)
    total_marcados = sum(1 for item in itens if estado_atual.get(item["id"], False))
    progresso = (total_marcados / total_itens) if total_itens else 0
    progresso_placeholder.progress(
        progresso, text=f"Preenchimento: {total_marcados} de {total_itens} itens marcados ({progresso:.0%})"
    )
