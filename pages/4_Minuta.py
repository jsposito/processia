import streamlit as st

from database import init_db, listar_processos
from minutas import gerar_minuta, avaliar_minuta, TIPOS_MINUTA

st.set_page_config(page_title="Minuta", page_icon="📄", layout="wide")

init_db()

st.title("📄 Minuta")

CORES_SELO = {
    "Inadequado": ("#dc3545", "#ffffff"),
    "Parcialmente adequado": ("#fd7e14", "#ffffff"),
    "Adequado com ajustes": ("#ffc107", "#000000"),
    "Adequado": ("#28a745", "#ffffff"),
}

if "minutas_geradas" not in st.session_state:
    st.session_state["minutas_geradas"] = {}

processos = listar_processos()

if not processos:
    st.info("Nenhum processo cadastrado. Cadastre um processo na página 'Novo Processo'.")
else:
    opcoes = {f"{p['numero']} — {p['tipo']}": p["id"] for p in processos}
    escolha = st.selectbox("Processo", list(opcoes.keys()))
    processo_id = opcoes[escolha]

    tipo_minuta = st.selectbox("Tipo de minuta", TIPOS_MINUTA)

    chave = (processo_id, tipo_minuta)

    if st.button("Gerar minuta"):
        st.session_state["minutas_geradas"][chave] = gerar_minuta(processo_id, tipo_minuta)

    resultado = st.session_state["minutas_geradas"].get(chave)

    if resultado:
        if resultado["aviso"]:
            st.warning(resultado["aviso"])
        else:
            st.subheader("Texto da minuta")
            st.text_area("Conteúdo (copiável)", value=resultado["texto"], height=420)

            st.divider()
            st.subheader("Avaliação da minuta (simulada)")
            st.caption("Avaliação estilo LLM-as-a-judge, com notas derivadas deterministicamente dos dados do processo e da análise.")

            avaliacao = avaliar_minuta(processo_id, resultado["texto"])

            for criterio in avaliacao["criterios"]:
                st.markdown(f"**{criterio['nome']}** (nota {criterio['nota']}/4): {criterio['justificativa']}")

            st.markdown("")
            col_media, col_selo = st.columns(2)
            col_media.metric("Média geral", f"{avaliacao['media']:.2f}/4")

            cor_fundo, cor_texto = CORES_SELO.get(avaliacao["selo"], ("#6c757d", "#ffffff"))
            col_selo.markdown(
                f"""
                <div style="background-color:{cor_fundo};color:{cor_texto};
                            padding:1rem;border-radius:0.5rem;text-align:center;">
                    <div style="font-size:0.9rem;font-weight:600;">Selo</div>
                    <div style="font-size:1.3rem;font-weight:700;">{avaliacao['selo']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.caption("Clique em \"Gerar minuta\" para produzir o texto deste processo.")
