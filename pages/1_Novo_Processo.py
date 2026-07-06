import streamlit as st

from database import init_db

st.set_page_config(page_title="Novo Processo", page_icon="🆕", layout="wide")

init_db()

st.title("🆕 Novo Processo")
st.info("Formulário de cadastro de processo a ser implementado.")

with st.form("form_novo_processo"):
    numero = st.text_input("Número do processo")
    tipo = st.text_input("Tipo")
    submitted = st.form_submit_button("Salvar")

    if submitted:
        st.warning("Lógica de salvamento ainda não implementada.")
