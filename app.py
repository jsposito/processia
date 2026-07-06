import streamlit as st

from database import init_db, get_connection

st.set_page_config(page_title="Processia - Dashboard", page_icon="📋", layout="wide")

init_db()

st.title("📋 Processia")
st.subheader("Dashboard")

with get_connection() as conn:
    total_processos = conn.execute("SELECT COUNT(*) FROM processos").fetchone()[0]
    total_analises = conn.execute("SELECT COUNT(*) FROM analises").fetchone()[0]
    total_minutas = conn.execute("SELECT COUNT(*) FROM minutas").fetchone()[0]

col1, col2, col3 = st.columns(3)
col1.metric("Processos", total_processos)
col2.metric("Análises", total_analises)
col3.metric("Minutas", total_minutas)

st.info("Use o menu lateral para navegar entre as páginas do sistema.")
