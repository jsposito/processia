import streamlit as st

from database import init_db, get_connection

st.set_page_config(page_title="Histórico", page_icon="🗂️", layout="wide")

init_db()

st.title("🗂️ Histórico")
st.info("Tela de histórico de processos a ser implementada.")

with get_connection() as conn:
    rows = conn.execute(
        "SELECT id, numero, tipo, status, criado_em FROM processos ORDER BY criado_em DESC"
    ).fetchall()

if rows:
    st.dataframe([dict(row) for row in rows], use_container_width=True)
else:
    st.write("Nenhum processo cadastrado ainda.")
