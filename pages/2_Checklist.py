import streamlit as st

from database import init_db
from checklists import get_checklist

st.set_page_config(page_title="Checklist", page_icon="✅", layout="wide")

init_db()

st.title("✅ Checklist")
st.info("Tela de checklist a ser implementada.")

itens = get_checklist(processo_id=0)
if not itens:
    st.write("Nenhum item de checklist disponível.")
