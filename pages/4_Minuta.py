import streamlit as st

from database import init_db
from minutas import gerar_minuta

st.set_page_config(page_title="Minuta", page_icon="📄", layout="wide")

init_db()

st.title("📄 Minuta")
st.info("Tela de geração de minuta a ser implementada.")

minuta = gerar_minuta(processo_id=0)
st.text_area("Conteúdo da minuta", value=minuta, height=300)
