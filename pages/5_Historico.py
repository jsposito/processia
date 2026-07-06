import json

import streamlit as st

from database import init_db, listar_processos, listar_analises, listar_minutas

init_db()

st.title("🗂️ Histórico")

aba_processos, aba_analises, aba_minutas = st.tabs(["Processos", "Análises", "Minutas"])

with aba_processos:
    processos = listar_processos()
    if not processos:
        st.write("Nenhum processo cadastrado ainda.")
    else:
        st.dataframe(
            [
                {
                    "ID": p["id"],
                    "Número SEI": p["numero"],
                    "Tipo": p["tipo"],
                    "Status": p["status"],
                    "Unidade demandante": p["unidade_demandante"],
                    "Valor estimado (R$)": p["valor_estimado"],
                    "Data fim vigência": p["data_fim_vigencia"],
                    "Urgência": p["urgencia"],
                    "Criado em": p["criado_em"],
                }
                for p in processos
            ],
            use_container_width=True,
            hide_index=True,
        )

with aba_analises:
    analises = listar_analises()
    if not analises:
        st.write("Nenhuma análise realizada ainda.")
    else:
        resumo = []
        for a in analises:
            conteudo = json.loads(a["conteudo"])
            resumo.append(
                {
                    "ID": a["id"],
                    "Processo": f"{a['processo_numero']} — {a['processo_tipo']}",
                    "Risco documental": conteudo["risco_documental"],
                    "Risco financeiro": conteudo["risco_financeiro"],
                    "Risco jurídico": conteudo["risco_juridico"],
                    "Recomendação": conteudo["recomendacao"],
                    "Data": a["criado_em"],
                }
            )
        st.dataframe(resumo, use_container_width=True, hide_index=True)

        st.subheader("Detalhamento")
        for a in analises:
            conteudo = json.loads(a["conteudo"])
            with st.expander(f"Análise #{a['id']} — {a['processo_numero']} ({a['criado_em']})"):
                criticos = conteudo["documentos_faltantes"]["criticos"]
                complementares = conteudo["documentos_faltantes"]["complementares"]
                if criticos:
                    st.markdown("**Documentos críticos faltantes:** " + "; ".join(criticos))
                if complementares:
                    st.markdown("**Documentos complementares faltantes:** " + "; ".join(complementares))
                if not criticos and not complementares:
                    st.markdown("**Documentos faltantes:** nenhum.")
                st.markdown(f"**Recomendação:** {conteudo['recomendacao']}")
                st.markdown("**Etapas ReAct:**")
                for etapa in conteudo["etapas_react"]:
                    st.markdown(f"- **{etapa['agente']}** — {etapa['observation']}")

with aba_minutas:
    minutas = listar_minutas()
    if not minutas:
        st.write("Nenhuma minuta gerada ainda.")
    else:
        st.dataframe(
            [
                {
                    "ID": m["id"],
                    "Processo": f"{m['processo_numero']} — {m['processo_tipo']}",
                    "Tipo de minuta": m["tipo"],
                    "Data": m["criado_em"],
                }
                for m in minutas
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Textos gerados")
        for m in minutas:
            with st.expander(f"Minuta #{m['id']} — {m['tipo']} — {m['processo_numero']} ({m['criado_em']})"):
                st.text_area(
                    "Conteúdo",
                    value=m["texto"],
                    height=300,
                    key=f"minuta_texto_{m['id']}",
                    disabled=True,
                )
