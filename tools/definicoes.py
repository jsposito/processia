"""Ferramentas (tool calling) disponíveis aos agentes de análise via LLM.

Cada ferramenta combina o schema no formato de function calling do SDK
OpenAI (para o modelo decidir quando/como chamá-la) com a função Python
correspondente (para execução local). As implementações reaproveitam as
funções já existentes de database.py e checklists.py, retornando apenas os
campos relevantes para o agente.
"""
from database import buscar_processo, carregar_estado_checklist
from checklists import get_checklist


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

TOOLS_AGENTE_DOCUMENTAL = [TOOL_CONSULTAR_PROCESSO, TOOL_VERIFICAR_CHECKLIST]
