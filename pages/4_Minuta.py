import streamlit as st

from database import init_db, listar_processos
from analise import usar_llm
from minutas import gerar_minuta, gerar_minuta_llm, avaliar_minuta, avaliar_minuta_llm, TIPOS_MINUTA

init_db()

st.title("📄 Minuta")

if usar_llm():
    st.info("Modo ativo: Minuta via LLM (Groq/Llama 3.3 70B)")
else:
    st.caption("Modo ativo: Minuta simulada")

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
    if usar_llm():
        st.caption(
            "No modo LLM, o tipo de minuta (Despacho ou Ofício) é definido pelo Agente de "
            "Minuta conforme a recomendação apurada; esta seleção só é usada no modo simulado."
        )

    chave = (processo_id, tipo_minuta)

    if st.button("Gerar minuta"):
        if usar_llm():
            try:
                resultado = gerar_minuta_llm(processo_id)
            except Exception as erro:
                st.warning(
                    f"Falha ao gerar a minuta via LLM ({erro}). Exibindo o resultado da minuta simulada."
                )
                resultado = gerar_minuta(processo_id, tipo_minuta)
        else:
            resultado = gerar_minuta(processo_id, tipo_minuta)

        st.session_state["minutas_geradas"][chave] = resultado

    resultado = st.session_state["minutas_geradas"].get(chave)

    if resultado:
        if resultado["aviso"]:
            st.warning(resultado["aviso"])
        else:
            st.subheader("Texto da minuta")
            st.text_area("Conteúdo (copiável)", value=resultado["texto"], height=420)

            st.divider()
            st.subheader("Avaliação da minuta")

            if usar_llm():
                try:
                    avaliacao = avaliar_minuta_llm(processo_id, resultado["texto"])
                    st.caption("Avaliação via LLM-as-a-judge real (Groq/Llama 3.3 70B).")
                except Exception as erro:
                    st.warning(
                        f"Falha ao avaliar a minuta via LLM ({erro}). Exibindo a avaliação simulada."
                    )
                    avaliacao = avaliar_minuta(processo_id, resultado["texto"])
            else:
                avaliacao = avaliar_minuta(processo_id, resultado["texto"])
                st.caption("Avaliação estilo LLM-as-a-judge, com notas derivadas deterministicamente dos dados do processo e da análise.")

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
