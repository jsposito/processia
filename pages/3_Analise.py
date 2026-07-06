import streamlit as st

from database import init_db
from analise import analisar_processo

st.set_page_config(page_title="Análise", page_icon="🔍", layout="wide")

init_db()

st.title("🔍 Análise")
st.info("Tela de análise de processo a ser implementada.")

resultado = analisar_processo(processo_id=0)
if not resultado:
    st.write("Nenhuma análise disponível.")
