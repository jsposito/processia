"""Ferramentas (tool calling) disponíveis aos agentes de análise via LLM.

Cada ferramenta combina o schema no formato de function calling do SDK
OpenAI (para o modelo decidir quando/como chamá-la) com a função Python
correspondente (para execução local). As implementações reaproveitam as
funções já existentes de database.py e checklists.py, retornando apenas os
campos relevantes para o agente.
"""
from datetime import date

from database import buscar_processo, carregar_estado_checklist
from checklists import get_checklist, PAGAMENTO, PRORROGACAO_CONTRATUAL, FISCALIZACAO_CONTRATUAL


def consultar_processo(processo_id: int) -> dict:
    """Retorna os dados cadastrais essenciais de um processo."""
    processo = buscar_processo(processo_id)
    if not processo:
        return {"erro": f"Processo de id {processo_id} não encontrado."}

    return {
        "numero": processo["numero"],
        "tipo": processo["tipo"],
        "unidade_demandante": processo["unidade_demandante"],
        "objeto": processo["objeto"],
        "valor_estimado": processo["valor_estimado"],
        "data_fim_vigencia": processo["data_fim_vigencia"],
        "urgencia": processo["urgencia"],
    }


def verificar_checklist(processo_id: int) -> dict:
    """Retorna os itens do checklist do tipo do processo, com estado marcado/pendente e criticidade."""
    processo = buscar_processo(processo_id)
    if not processo:
        return {"erro": f"Processo de id {processo_id} não encontrado."}

    itens = get_checklist(processo["tipo"])
    estado = carregar_estado_checklist(processo_id)

    return {
        "itens": [
            {
                "descricao": item["descricao"],
                "critico": item["critico"],
                "marcado": estado.get(item["id"], False),
            }
            for item in itens
        ]
    }


def calcular_prazo_vigencia(processo_id: int) -> dict:
    """Calcula quantos dias faltam para o fim da vigência do processo (negativo se já vencida)."""
    processo = buscar_processo(processo_id)
    if not processo:
        return {"erro": f"Processo de id {processo_id} não encontrado."}

    data_fim = processo.get("data_fim_vigencia")
    hoje = date.today()

    if not data_fim:
        return {
            "data_fim_vigencia": None,
            "data_atual": hoje.isoformat(),
            "dias_restantes": None,
            "vencida": False,
        }

    try:
        dias_restantes = (date.fromisoformat(str(data_fim)) - hoje).days
    except ValueError:
        return {"erro": f"Data de fim de vigência inválida: {data_fim!r}."}

    return {
        "data_fim_vigencia": data_fim,
        "data_atual": hoje.isoformat(),
        "dias_restantes": dias_restantes,
        "vencida": dias_restantes < 0,
    }


_FUNDAMENTACAO_POR_TIPO = {
    PAGAMENTO: "art. 141 da Lei nº 14.133/2021 e arts. 62 e 63 da Lei nº 4.320/1964",
    PRORROGACAO_CONTRATUAL: "arts. 106 e 107 da Lei nº 14.133/2021",
    FISCALIZACAO_CONTRATUAL: "art. 117 da Lei nº 14.133/2021",
}


def buscar_fundamentacao_legal(tipo_processo: str) -> dict:
    """Retorna os artigos de lei aplicáveis ao tipo de processo informado."""
    fundamentacao = _FUNDAMENTACAO_POR_TIPO.get(tipo_processo)
    if not fundamentacao:
        return {"erro": f"Tipo de processo '{tipo_processo}' não reconhecido."}
    return {"tipo_processo": tipo_processo, "fundamentacao": fundamentacao}


TOOL_CONSULTAR_PROCESSO = {
    "schema": {
        "type": "function",
        "function": {
            "name": "consultar_processo",
            "description": (
                "Consulta os dados cadastrais de um processo administrativo: número, tipo, "
                "unidade demandante, objeto, valor estimado, data de fim de vigência e urgência."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "processo_id": {
                        "type": "integer",
                        "description": "Id numérico do processo no banco de dados.",
                    },
                },
                "required": ["processo_id"],
            },
        },
    },
    "funcao": consultar_processo,
}

TOOL_VERIFICAR_CHECKLIST = {
    "schema": {
        "type": "function",
        "function": {
            "name": "verificar_checklist",
            "description": (
                "Consulta os itens do checklist documental exigido para o tipo do processo, "
                "indicando para cada item sua descrição, se é crítico e se está marcado (presente) "
                "ou pendente (ausente)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "processo_id": {
                        "type": "integer",
                        "description": "Id numérico do processo no banco de dados.",
                    },
                },
                "required": ["processo_id"],
            },
        },
    },
    "funcao": verificar_checklist,
}

TOOL_CALCULAR_PRAZO_VIGENCIA = {
    "schema": {
        "type": "function",
        "function": {
            "name": "calcular_prazo_vigencia",
            "description": (
                "Calcula o prazo de vigência de um processo: retorna a data de fim de vigência "
                "cadastrada, a data atual e quantos dias faltam para o vencimento (valor negativo "
                "se a vigência já estiver vencida)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "processo_id": {
                        "type": "integer",
                        "description": "Id numérico do processo no banco de dados.",
                    },
                },
                "required": ["processo_id"],
            },
        },
    },
    "funcao": calcular_prazo_vigencia,
}

TOOL_BUSCAR_FUNDAMENTACAO_LEGAL = {
    "schema": {
        "type": "function",
        "function": {
            "name": "buscar_fundamentacao_legal",
            "description": (
                "Consulta os artigos de lei aplicáveis a um tipo de processo administrativo "
                "('Pagamento', 'Prorrogação Contratual' ou 'Fiscalização Contratual'), para "
                "citação na fundamentação legal de minutas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_processo": {
                        "type": "string",
                        "description": (
                            "Tipo do processo: 'Pagamento', 'Prorrogação Contratual' ou "
                            "'Fiscalização Contratual'."
                        ),
                    },
                },
                "required": ["tipo_processo"],
            },
        },
    },
    "funcao": buscar_fundamentacao_legal,
}

TOOLS_AGENTE_DOCUMENTAL = [TOOL_CONSULTAR_PROCESSO, TOOL_VERIFICAR_CHECKLIST]
TOOLS_AGENTE_RISCO = [TOOL_CONSULTAR_PROCESSO, TOOL_CALCULAR_PRAZO_VIGENCIA]
TOOLS_AGENTE_MINUTA = [TOOL_CONSULTAR_PROCESSO, TOOL_BUSCAR_FUNDAMENTACAO_LEGAL]
