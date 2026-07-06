import streamlit as st

import database as db
from seed import popular_banco_se_vazio

st.set_page_config(page_title="Processia", page_icon="📋", layout="wide")

db.init_db()
popular_banco_se_vazio()

pagina_dashboard = st.Page("views/dashboard.py", title="Dashboard", icon="📋", default=True)
pagina_novo_processo = st.Page("pages/1_Novo_Processo.py", title="Novo Processo", icon="🆕")
pagina_checklist = st.Page("pages/2_Checklist.py", title="Checklist", icon="✅")
pagina_analise = st.Page("pages/3_Analise.py", title="Análise", icon="🔍")
pagina_minuta = st.Page("pages/4_Minuta.py", title="Minuta", icon="📄")
pagina_historico = st.Page("pages/5_Historico.py", title="Histórico", icon="🗂️")

navegacao = st.navigation(
    [
        pagina_dashboard,
        pagina_novo_processo,
        pagina_checklist,
        pagina_analise,
        pagina_minuta,
        pagina_historico,
    ]
)

navegacao.run()
