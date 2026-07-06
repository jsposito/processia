"""Geração determinística de minutas institucionais e avaliação simulada (LLM-as-a-judge)."""
import json

from database import buscar_processo, buscar_ultima_analise, salvar_minuta
from checklists import PAGAMENTO, PRORROGACAO_CONTRATUAL, FISCALIZACAO_CONTRATUAL
from analise import RECOMENDACAO_DEVOLUCAO, RECOMENDACAO_RESSALVAS, RECOMENDACAO_APTO

DESPACHO = "Despacho"
OFICIO = "Ofício"

TIPOS_MINUTA = [DESPACHO, OFICIO]

_FUNDAMENTACAO_POR_TIPO_PROCESSO = {
    PAGAMENTO: "Fundamentação: art. 141 da Lei nº 14.133/2021 e arts. 62 e 63 da Lei nº 4.320/1964.",
    PRORROGACAO_CONTRATUAL: "Fundamentação: arts. 106 e 107 da Lei nº 14.133/2021.",
    FISCALIZACAO_CONTRATUAL: "Fundamentação: art. 117 da Lei nº 14.133/2021.",
}

_SELOS_POR_NOTA = {
    1: "Inadequado",
    2: "Parcialmente adequado",
    3: "Adequado com ajustes",
    4: "Adequado",
}


def _cabecalho(processo: dict, tipo_minuta: str) -> str:
    unidade = processo.get("unidade_demandante") or "não informada"
    linhas = [tipo_minuta.upper(), "", f"Processo SEI nº {processo['numero']}", f"Unidade: {unidade}"]
    if tipo_minuta == OFICIO:
        linhas.append("")
        linhas.append("Ao(À) Responsável pela Unidade Demandante,")
    return "\n".join(linhas)


def _paragrafo_objeto(processo: dict) -> str:
    objeto = processo.get("objeto") or "não informado nos autos"
    return f"1. Trata o presente processo de {processo['tipo'].lower()}, tendo por objeto: {objeto}."


def _paragrafo_analise(conteudo_analise: dict) -> str:
    criticos = conteudo_analise["documentos_faltantes"]["criticos"]
    complementares = conteudo_analise["documentos_faltantes"]["complementares"]

    partes_pendencia = []
    if criticos:
        partes_pendencia.append("documentos críticos pendentes (" + "; ".join(criticos) + ")")
    if complementares:
        partes_pendencia.append("documentos complementares pendentes (" + "; ".join(complementares) + ")")

    if partes_pendencia:
        texto_pendencias = "Da análise realizada, foram identificadas as seguintes pendências: " + "; ".join(
            partes_pendencia
        ) + "."
    else:
        texto_pendencias = "Da análise realizada, não foram identificadas pendências documentais."

    return (
        f"2. {texto_pendencias} Quanto aos riscos, apurou-se risco documental "
        f"{conteudo_analise['risco_documental']}, risco financeiro {conteudo_analise['risco_financeiro']} "
        f"e risco jurídico {conteudo_analise['risco_juridico']}."
    )


def _paragrafo_conclusao(recomendacao: str, tipo_minuta: str) -> str:
    if tipo_minuta == OFICIO:
        if recomendacao == RECOMENDACAO_DEVOLUCAO:
            texto = (
                "Comunico a Vossa Senhoria que o processo está sendo devolvido a essa unidade demandante "
                "para saneamento das pendências apontadas, previamente ao prosseguimento do feito."
            )
        elif recomendacao == RECOMENDACAO_RESSALVAS:
            texto = (
                "Comunico a Vossa Senhoria que o processo terá prosseguimento com ressalvas, devendo as "
                "pendências remanescentes ser saneadas em paralelo à tramitação."
            )
        else:
            texto = (
                "Comunico a Vossa Senhoria que o processo encontra-se apto ao prosseguimento, tendo sido "
                "encaminhado à autoridade competente para as providências cabíveis."
            )
        return f"3. {texto}"

    if recomendacao == RECOMENDACAO_DEVOLUCAO:
        texto = (
            "opina-se pela devolução dos autos à unidade demandante para saneamento das pendências "
            "apontadas, previamente ao prosseguimento do feito"
        )
    elif recomendacao == RECOMENDACAO_RESSALVAS:
        texto = (
            "opina-se pelo prosseguimento do processo com ressalvas, devendo as pendências remanescentes "
            "ser saneadas em paralelo à tramitação"
        )
    else:
        texto = "opina-se pelo encaminhamento do processo à autoridade competente para as providências cabíveis"
    return f"3. Ante o exposto, {texto}."


def _fecho(tipo_minuta: str) -> str:
    if tipo_minuta == OFICIO:
        return "Atenciosamente,\n\nDocumento assinado eletronicamente, nos termos da legislação vigente."
    return (
        "É o parecer, que se submete à superior consideração para as providências cabíveis.\n\n"
        "Documento assinado eletronicamente, nos termos da legislação vigente."
    )


def gerar_minuta(processo_id: int, tipo_minuta: str) -> dict:
    """Monta o texto institucional da minuta a partir do processo e da última análise salva.

    Retorna {"texto": str, "aviso": None} em caso de sucesso, ou {"texto": None, "aviso": str}
    quando o processo não existe ou ainda não possui análise salva.
    """
    processo = buscar_processo(processo_id)
    if not processo:
        return {"texto": None, "aviso": "Processo não encontrado."}

    ultima_analise = buscar_ultima_analise(processo_id)
    if not ultima_analise:
        return {
            "texto": None,
            "aviso": "É necessário executar a análise deste processo antes de gerar a minuta.",
        }

    conteudo_analise = json.loads(ultima_analise["conteudo"])

    blocos = [
        _cabecalho(processo, tipo_minuta),
        _paragrafo_objeto(processo),
        _paragrafo_analise(conteudo_analise),
        _paragrafo_conclusao(conteudo_analise["recomendacao"], tipo_minuta),
    ]

    fundamentacao = _FUNDAMENTACAO_POR_TIPO_PROCESSO.get(processo["tipo"])
    if fundamentacao:
        blocos.append(fundamentacao)

    blocos.append(_fecho(tipo_minuta))

    texto = "\n\n".join(blocos)

    salvar_minuta(processo_id, tipo_minuta, texto)

    return {"texto": texto, "aviso": None}


def _criterio_clareza(processo: dict) -> dict:
    if processo.get("objeto"):
        nota = 4
        justificativa = "o objeto do processo foi descrito no cadastro, permitindo relato direto e sem ambiguidade."
    else:
        nota = 3
        justificativa = "a ausência de objeto cadastrado tornou o relato do parágrafo inicial genérico."
    return {"nome": "Clareza", "nota": nota, "justificativa": justificativa}


def _criterio_completude(processo: dict) -> dict:
    campos_relevantes = {
        "número SEI": processo.get("numero"),
        "unidade demandante": processo.get("unidade_demandante"),
        "objeto": processo.get("objeto"),
    }
    if processo["tipo"] in (PAGAMENTO, PRORROGACAO_CONTRATUAL):
        campos_relevantes["valor estimado"] = processo.get("valor_estimado")
    if processo["tipo"] == PRORROGACAO_CONTRATUAL:
        campos_relevantes["data fim de vigência"] = processo.get("data_fim_vigencia")

    faltantes = [nome for nome, valor in campos_relevantes.items() if not valor]
    nota = max(1, 4 - len(faltantes))
    if faltantes:
        justificativa = "campos do processo não preenchidos: " + ", ".join(faltantes) + "."
    else:
        justificativa = "todos os campos relevantes do cadastro do processo estão preenchidos."
    return {"nome": "Completude", "nota": nota, "justificativa": justificativa}


def _criterio_aderencia(conteudo_analise: dict, texto: str) -> dict:
    criticos = conteudo_analise["documentos_faltantes"]["criticos"]
    if criticos:
        aderente = all(pendencia in texto for pendencia in criticos)
        if aderente:
            nota = 4
            justificativa = "o texto menciona expressamente as pendências críticas apuradas na análise."
        else:
            nota = 2
            justificativa = "nem todas as pendências críticas apuradas constam explicitamente no texto gerado."
    else:
        nota = 4
        justificativa = "não havendo pendências críticas, o texto reflete adequadamente a situação regular do processo."
    return {"nome": "Aderência ao processo", "nota": nota, "justificativa": justificativa}


def _criterio_risco_inconsistencia(conteudo_analise: dict) -> dict:
    criticos = conteudo_analise["documentos_faltantes"]["criticos"]
    complementares = conteudo_analise["documentos_faltantes"]["complementares"]
    tem_pendencia_documental = bool(criticos or complementares)
    recomendacao = conteudo_analise["recomendacao"]

    if recomendacao == RECOMENDACAO_DEVOLUCAO and not tem_pendencia_documental:
        nota = 2
        justificativa = (
            "a devolução decorre de risco financeiro ou jurídico sem pendência documental explicitada "
            "no checklist, podendo gerar leitura ambígua no texto."
        )
    elif recomendacao == RECOMENDACAO_RESSALVAS and not tem_pendencia_documental:
        nota = 3
        justificativa = (
            "o prosseguimento com ressalvas não decorre de pendência documental, cabendo reforçar no "
            "texto o risco que o motiva."
        )
    else:
        nota = 4
        justificativa = "o conteúdo do texto é compatível com a recomendação apresentada, sem indícios de inconsistência."
    return {"nome": "Risco de inconsistência", "nota": nota, "justificativa": justificativa}


def _criterio_formalidade() -> dict:
    return {
        "nome": "Formalidade",
        "nota": 4,
        "justificativa": "o texto observa o registro formal da redação oficial, com parágrafos numerados e fecho institucional.",
    }


def avaliar_minuta(processo_id: int, texto: str) -> dict:
    """Avaliação simulada da minuta (estilo LLM-as-a-judge), derivada deterministicamente dos dados."""
    processo = buscar_processo(processo_id)
    ultima_analise = buscar_ultima_analise(processo_id)
    conteudo_analise = json.loads(ultima_analise["conteudo"])

    criterios = [
        _criterio_clareza(processo),
        _criterio_completude(processo),
        _criterio_aderencia(conteudo_analise, texto),
        _criterio_risco_inconsistencia(conteudo_analise),
        _criterio_formalidade(),
    ]

    media = sum(c["nota"] for c in criterios) / len(criterios)
    selo = _SELOS_POR_NOTA[min(4, max(1, round(media)))]

    return {"criterios": criterios, "media": media, "selo": selo}
