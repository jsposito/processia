import streamlit as st

from database import init_db
from checklists import get_checklist, TIPOS_PROCESSO

st.set_page_config(page_title="Checklist", page_icon="✅", layout="wide")

init_db()

st.title("✅ Checklist")
st.info("Tela de checklist a ser implementada (ainda sem seleção de processo nem persistência).")

tipo_processo = st.selectbox("Tipo de processo", TIPOS_PROCESSO)

itens = get_checklist(tipo_processo)
if not itens:
    st.write("Nenhum item de checklist disponível.")
else:
    for item in itens:
        marcador = "🔴 crítico" if item["critico"] else "⚪ complementar"
        st.write(f"**{item['descricao']}** ({marcador})")
