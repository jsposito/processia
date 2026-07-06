import streamlit as st

from database import init_db, criar_processo
from checklists import TIPOS_PROCESSO

st.set_page_config(page_title="Novo Processo", page_icon="🆕", layout="wide")

init_db()

st.title("🆕 Novo Processo")
st.write("Cadastro de processo administrativo para posterior análise documental.")

with st.form("form_novo_processo", clear_on_submit=True):
    numero = st.text_input("Número SEI", placeholder="00000.000000/0000-00")
    tipo = st.selectbox("Tipo de processo", TIPOS_PROCESSO)
    unidade_demandante = st.text_input("Unidade demandante")
    objeto = st.text_area("Objeto")

    col1, col2, col3 = st.columns(3)
    valor_estimado = col1.number_input("Valor estimado (R$)", min_value=0.0, step=1000.0, format="%.2f")
    data_fim_vigencia = col2.date_input("Data fim de vigência", value=None)
    urgencia = col3.selectbox("Urgência", ["Normal", "Urgente"])

    observacoes = st.text_area("Observações")

    submitted = st.form_submit_button("Salvar processo")

    if submitted:
        if not numero.strip():
            st.error("Informe o número SEI do processo.")
        elif not unidade_demandante.strip():
            st.error("Informe a unidade demandante.")
        else:
            processo_id = criar_processo(
                numero=numero.strip(),
                tipo=tipo,
                unidade_demandante=unidade_demandante.strip(),
                objeto=objeto.strip(),
                valor_estimado=valor_estimado or None,
                data_fim_vigencia=data_fim_vigencia.isoformat() if data_fim_vigencia else None,
                urgencia=urgencia,
                observacoes=observacoes.strip(),
            )
            st.success(f"Processo nº {numero} cadastrado com sucesso (id {processo_id}).")
