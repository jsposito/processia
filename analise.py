"""Análise determinística de processos (regras fixas, sem geração livre de conteúdo)."""
import json
import os
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from database import get_connection, carregar_estado_checklist, buscar_processo
from checklists import get_checklist, PRORROGACAO_CONTRATUAL, PAGAMENTO, FISCALIZACAO_CONTRATUAL
from llm_client import chamar_agente
from tools.definicoes import TOOLS_AGENTE_DOCUMENTAL, TOOLS_AGENTE_RISCO, TOOLS_AGENTE_MINUTA

_PASTA_PROMPTS = Path(__file__).parent / "prompts"
PROMPT_AGENTE_DOCUMENTAL = (_PASTA_PROMPTS / "agente_documental.txt").read_text(encoding="utf-8")
PROMPT_AGENTE_RISCO = (_PASTA_PROMPTS / "agente_risco.txt").read_text(encoding="utf-8")
PROMPT_AGENTE_MINUTA = (_PASTA_PROMPTS / "agente_minuta.txt").read_text(encoding="utf-8")

RISCO_BAIXO = "Baixo"
RISCO_MEDIO = "Médio"
RISCO_ALTO = "Alto"

RECOMENDACAO_DEVOLUCAO = "Devolver à unidade demandante para saneamento das pendências"
RECOMENDACAO_RESSALVAS = "Prosseguir com ressalvas, saneando pendências em paralelo"
RECOMENDACAO_APTO = "Processo apto para encaminhamento à autoridade competente"

_MINUTA_APTO_POR_TIPO = {
    PAGAMENTO: "Despacho de Autorização de Pagamento",
    PRORROGACAO_CONTRATUAL: "Despacho de Encaminhamento para Formalização de Termo Aditivo",
    FISCALIZACAO_CONTRATUAL: "Despacho de Ciência de Relatório de Fiscalização",
}


def _item_marcado(itens: list, estado: dict, trecho_descricao: str) -> bool:
    """Verifica se o item cuja descrição contém o trecho informado está marcado."""
    trecho = trecho_descricao.lower()
    for item in itens:
        if trecho in item["descricao"].lower():
            return estado.get(item["id"], False)
    return False


def _documentos_faltantes(itens: list, estado: dict) -> tuple:
    criticos = [item["descricao"] for item in itens if item["critico"] and not estado.get(item["id"], False)]
    complementares = [item["descricao"] for item in itens if not item["critico"] and not estado.get(item["id"], False)]
    return criticos, complementares


def _risco_documental(criticos_faltantes: list, complementares_faltantes: list) -> str:
    if criticos_faltantes:
        return RISCO_ALTO
    if complementares_faltantes:
        return RISCO_MEDIO
    return RISCO_BAIXO


def _risco_financeiro(tipo: str, itens: list, estado: dict, valor_estimado, tem_pendencia: bool) -> str:
    if tipo == FISCALIZACAO_CONTRATUAL:
        return RISCO_BAIXO
    if tipo == PAGAMENTO and not _item_marcado(itens, estado, "nota de empenho"):
        return RISCO_ALTO
    if tipo == PRORROGACAO_CONTRATUAL and not _item_marcado(itens, estado, "disponibilidade orçamentária"):
        return RISCO_ALTO
    if valor_estimado is not None and valor_estimado > 1_000_000 and tem_pendencia:
        return RISCO_MEDIO
    return RISCO_BAIXO


def _risco_juridico(tipo: str, itens: list, estado: dict, data_fim_vigencia) -> str:
    if tipo != PRORROGACAO_CONTRATUAL:
        return RISCO_BAIXO

    vigencia_vencida = False
    if data_fim_vigencia:
        try:
            vigencia_vencida = date.fromisoformat(str(data_fim_vigencia)) < date.today()
        except ValueError:
            vigencia_vencida = False

    certidoes_ausentes = not _item_marcado(itens, estado, "certidões de regularidade fiscal e trabalhista")

    if vigencia_vencida or certidoes_ausentes:
        return RISCO_ALTO
    if not _item_marcado(itens, estado, "manifestação da assessoria jurídica"):
        return RISCO_MEDIO
    return RISCO_BAIXO


def _recomendacao(riscos: list) -> str:
    if RISCO_ALTO in riscos:
        return RECOMENDACAO_DEVOLUCAO
    if RISCO_MEDIO in riscos:
        return RECOMENDACAO_RESSALVAS
    return RECOMENDACAO_APTO


def _etapa_agente_documental(processo: dict, criticos_faltantes: list, complementares_faltantes: list) -> dict:
    if not criticos_faltantes and not complementares_faltantes:
        observacao = "Todos os itens do checklist encontram-se marcados como cumpridos."
    else:
        partes = []
        if criticos_faltantes:
            partes.append(f"{len(criticos_faltantes)} item(ns) crítico(s) pendente(s): {', '.join(criticos_faltantes)}")
        if complementares_faltantes:
            partes.append(
                f"{len(complementares_faltantes)} item(ns) complementar(es) pendente(s): {', '.join(complementares_faltantes)}"
            )
        observacao = "; ".join(partes) + "."

    return {
        "agente": "Agente Documental",
        "thought": (
            f"Preciso verificar o checklist do processo nº {processo['numero']} "
            f"(tipo: {processo['tipo']}) e identificar eventuais pendências documentais."
        ),
        "action": "Consultar os itens do checklist e o respectivo estado de marcação do processo.",
        "observation": observacao,
    }


def _etapa_agente_risco(processo: dict, risco_documental: str, risco_financeiro: str, risco_juridico: str) -> dict:
    return {
        "agente": "Agente de Risco",
        "thought": (
            f"Com base nas pendências identificadas, preciso classificar os riscos documental, "
            f"financeiro e jurídico do processo nº {processo['numero']}."
        ),
        "action": "Aplicar as regras de classificação de risco documental, financeiro e jurídico.",
        "observation": (
            f"Risco documental: {risco_documental}. "
            f"Risco financeiro: {risco_financeiro}. "
            f"Risco jurídico: {risco_juridico}."
        ),
    }


def _minuta_sugerida(processo: dict, recomendacao: str) -> str:
    """Define a minuta a partir da recomendação; só depende do tipo quando o processo está apto."""
    if recomendacao == RECOMENDACAO_DEVOLUCAO:
        return "Despacho de Devolução para Saneamento"
    if recomendacao == RECOMENDACAO_RESSALVAS:
        return "Despacho de Prosseguimento com Ressalvas"
    return _MINUTA_APTO_POR_TIPO.get(processo["tipo"], "Minuta genérica")


def _etapa_agente_minuta(processo: dict, recomendacao: str) -> dict:
    tipo_minuta = _minuta_sugerida(processo, recomendacao)
    return {
        "agente": "Agente de Minuta",
        "thought": (
            f"Considerando a classificação de risco do processo nº {processo['numero']}, "
            "preciso indicar o encaminhamento cabível e o tipo de minuta correspondente."
        ),
        "action": "Definir a recomendação final e o tipo de minuta sugerida para o processo.",
        "observation": f"Recomendação: {recomendacao}. Minuta sugerida: {tipo_minuta}.",
    }


def _salvar_analise(processo_id: int, resultado: dict) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO analises (processo_id, conteudo) VALUES (?, ?)",
            (processo_id, json.dumps(resultado, ensure_ascii=False)),
        )
        conn.commit()


def analisar_processo(processo_id: int) -> dict:
    """Carrega o processo, seu checklist e estado marcado, e retorna a análise de risco."""
    processo = buscar_processo(processo_id)
    if not processo:
        return {}

    tipo = processo["tipo"]
    itens = get_checklist(tipo)
    estado = carregar_estado_checklist(processo_id)

    criticos_faltantes, complementares_faltantes = _documentos_faltantes(itens, estado)
    tem_pendencia = bool(criticos_faltantes or complementares_faltantes)

    risco_documental = _risco_documental(criticos_faltantes, complementares_faltantes)
    risco_financeiro = _risco_financeiro(tipo, itens, estado, processo.get("valor_estimado"), tem_pendencia)
    risco_juridico = _risco_juridico(tipo, itens, estado, processo.get("data_fim_vigencia"))

    recomendacao = _recomendacao([risco_documental, risco_financeiro, risco_juridico])

    etapas_react = [
        _etapa_agente_documental(processo, criticos_faltantes, complementares_faltantes),
        _etapa_agente_risco(processo, risco_documental, risco_financeiro, risco_juridico),
        _etapa_agente_minuta(processo, recomendacao),
    ]

    resultado = {
        "documentos_faltantes": {
            "criticos": criticos_faltantes,
            "complementares": complementares_faltantes,
        },
        "risco_documental": risco_documental,
        "risco_financeiro": risco_financeiro,
        "risco_juridico": risco_juridico,
        "recomendacao": recomendacao,
        "etapas_react": etapas_react,
    }

    _salvar_analise(processo_id, resultado)
    return resultado


def usar_llm() -> bool:
    """Indica se a análise via LLM real deve ser usada (PROCESSIA_MODO=llm e chave presente)."""
    if os.getenv("PROCESSIA_MODO", "mock").lower() != "llm":
        return False
    return bool(os.getenv("GROQ_API_KEY"))


class RespostaAgenteDocumental(BaseModel):
    criticos_pendentes: list[str]
    complementares_pendentes: list[str]
    observacao: str


class RespostaAgenteRisco(BaseModel):
    risco_documental: Literal[RISCO_BAIXO, RISCO_MEDIO, RISCO_ALTO]
    risco_financeiro: Literal[RISCO_BAIXO, RISCO_MEDIO, RISCO_ALTO]
    risco_juridico: Literal[RISCO_BAIXO, RISCO_MEDIO, RISCO_ALTO]
    recomendacao: Literal[RECOMENDACAO_DEVOLUCAO, RECOMENDACAO_RESSALVAS, RECOMENDACAO_APTO]
    justificativa: str


class RespostaAgenteMinuta(BaseModel):
    tipo_minuta: Literal["Despacho", "Ofício"]
    texto_minuta: str


def _etapa_agente_documental_llm(processo_id: int, resposta: RespostaAgenteDocumental) -> dict:
    return {
        "agente": "Agente Documental",
        "thought": (
            f"Preciso descobrir os dados cadastrais e o checklist do processo de id {processo_id} "
            "para identificar eventuais pendências documentais."
        ),
        "action": "Chamar as ferramentas consultar_processo e verificar_checklist.",
        "observation": resposta.observacao,
    }


def _etapa_agente_risco_llm(processo_id: int, resposta: RespostaAgenteRisco) -> dict:
    return {
        "agente": "Agente de Risco",
        "thought": (
            f"Com base nas pendências apuradas pelo Agente Documental, preciso classificar os riscos "
            f"documental, financeiro e jurídico do processo de id {processo_id}."
        ),
        "action": "Consultar os dados do processo e o prazo de vigência, e aplicar as regras de classificação de risco.",
        "observation": (
            f"Risco documental: {resposta.risco_documental}. "
            f"Risco financeiro: {resposta.risco_financeiro}. "
            f"Risco jurídico: {resposta.risco_juridico}. {resposta.justificativa}"
        ),
    }


def _etapa_agente_minuta_llm(processo_id: int, resposta: RespostaAgenteMinuta) -> dict:
    return {
        "agente": "Agente de Minuta",
        "thought": (
            f"Considerando a recomendação apurada pelo Agente de Risco, preciso redigir a minuta "
            f"institucional do processo de id {processo_id}."
        ),
        "action": "Consultar a fundamentação legal aplicável ao tipo do processo e redigir a minuta.",
        "observation": f"Minuta ({resposta.tipo_minuta}) redigida:\n\n{resposta.texto_minuta}",
    }


def _pipeline_llm(processo_id: int):
    """Executa o pipeline sequencial de agentes via LLM: Documental -> Risco -> Minuta.

    Cada agente recebe apenas o id do processo e o resultado dos agentes
    anteriores no user prompt, descobrindo os demais dados por conta própria
    via tool calling real. Salva a análise (mesmo formato do mock) e retorna
    (resultado, resposta_minuta), para reaproveitamento por analisar_processo_llm
    e por gerar_minuta_llm (em minutas.py).
    """
    resposta_documental = chamar_agente(
        system_prompt=PROMPT_AGENTE_DOCUMENTAL,
        user_prompt=f"Analise a situação documental do processo de id {processo_id}.",
        tools=TOOLS_AGENTE_DOCUMENTAL,
        response_model=RespostaAgenteDocumental,
    )

    resposta_risco = chamar_agente(
        system_prompt=PROMPT_AGENTE_RISCO,
        user_prompt=(
            f"Classifique os riscos do processo de id {processo_id}.\n"
            f"Pendências críticas apuradas pelo Agente Documental: {resposta_documental.criticos_pendentes}\n"
            f"Pendências complementares apuradas pelo Agente Documental: {resposta_documental.complementares_pendentes}"
        ),
        tools=TOOLS_AGENTE_RISCO,
        response_model=RespostaAgenteRisco,
    )

    resposta_minuta = chamar_agente(
        system_prompt=PROMPT_AGENTE_MINUTA,
        user_prompt=(
            f"Redija a minuta do processo de id {processo_id}.\n"
            f"Pendências críticas: {resposta_documental.criticos_pendentes}\n"
            f"Pendências complementares: {resposta_documental.complementares_pendentes}\n"
            f"Risco documental: {resposta_risco.risco_documental}\n"
            f"Risco financeiro: {resposta_risco.risco_financeiro}\n"
            f"Risco jurídico: {resposta_risco.risco_juridico}\n"
            f"Recomendação: {resposta_risco.recomendacao}"
        ),
        tools=TOOLS_AGENTE_MINUTA,
        response_model=RespostaAgenteMinuta,
    )

    etapas_react = [
        _etapa_agente_documental_llm(processo_id, resposta_documental),
        _etapa_agente_risco_llm(processo_id, resposta_risco),
        _etapa_agente_minuta_llm(processo_id, resposta_minuta),
    ]

    resultado = {
        "documentos_faltantes": {
            "criticos": resposta_documental.criticos_pendentes,
            "complementares": resposta_documental.complementares_pendentes,
        },
        "risco_documental": resposta_risco.risco_documental,
        "risco_financeiro": resposta_risco.risco_financeiro,
        "risco_juridico": resposta_risco.risco_juridico,
        "recomendacao": resposta_risco.recomendacao,
        "etapas_react": etapas_react,
    }

    _salvar_analise(processo_id, resultado)
    return resultado, resposta_minuta


def analisar_processo_llm(processo_id: int) -> dict:
    """Executa o pipeline de agentes via LLM e retorna o resultado no formato do mock
    (analisar_processo), para que as telas existentes funcionem sem alteração.
    """
    resultado, _ = _pipeline_llm(processo_id)
    return resultado
