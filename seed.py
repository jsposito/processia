"""Popula o banco com processos fictícios de demonstração (idempotente: só roda se o banco estiver vazio)."""
import database as db
from analise import analisar_processo
from minutas import gerar_minuta
from checklists import get_checklist, PRORROGACAO_CONTRATUAL, PAGAMENTO, FISCALIZACAO_CONTRATUAL

PROCESSOS_SEED = [
    dict(
        tipo=PRORROGACAO_CONTRATUAL,
        unidade_demandante="Prefeitura Universitária",
        objeto="Prorrogação do contrato de prestação de serviços de vigilância patrimonial dos campi",
        valor_estimado=1_200_000.00,
        data_fim_vigencia="2025-12-31",
        urgencia="Urgente",
        observacoes="Contrato próximo do vencimento; unidade solicitou análise prioritária.",
        estado="pendencias_criticas",
        gerar_analise=True,
        tipo_minuta="Despacho",
    ),
    dict(
        tipo=PRORROGACAO_CONTRATUAL,
        unidade_demandante="Superintendência de Infraestrutura",
        objeto="Prorrogação do contrato de manutenção predial preventiva e corretiva",
        valor_estimado=450_000.00,
        data_fim_vigencia="2027-06-30",
        urgencia="Normal",
        observacoes="Execução contratual sem intercorrências registradas.",
        estado="completo",
        gerar_analise=True,
        tipo_minuta="Ofício",
    ),
    dict(
        tipo=PRORROGACAO_CONTRATUAL,
        unidade_demandante="Restaurante Universitário",
        objeto="Prorrogação do contrato de fornecimento de gêneros alimentícios",
        valor_estimado=980_000.00,
        data_fim_vigencia="2027-03-31",
        urgencia="Normal",
        observacoes="Aguardando manifestação da assessoria jurídica.",
        estado="intermediario",
        gerar_analise=False,
        tipo_minuta=None,
    ),
    dict(
        tipo=PAGAMENTO,
        unidade_demandante="Biblioteca Central",
        objeto="Pagamento referente à aquisição de acervo bibliográfico",
        valor_estimado=65_000.00,
        data_fim_vigencia=None,
        urgencia="Normal",
        observacoes="Nota fiscal recebida, aguardando conferência da unidade.",
        estado="pendencias_criticas",
        gerar_analise=True,
        tipo_minuta="Despacho",
    ),
    dict(
        tipo=PAGAMENTO,
        unidade_demandante="Centro de Tecnologia da Informação",
        objeto="Pagamento de serviços de manutenção de infraestrutura de rede de dados",
        valor_estimado=320_000.00,
        data_fim_vigencia=None,
        urgencia="Normal",
        observacoes="Medição mensal aprovada pelo fiscal do contrato.",
        estado="completo",
        gerar_analise=True,
        tipo_minuta=None,
    ),
    dict(
        tipo=PAGAMENTO,
        unidade_demandante="Hospital Universitário",
        objeto="Pagamento de fornecimento de insumos hospitalares",
        valor_estimado=1_500_000.00,
        data_fim_vigencia=None,
        urgencia="Urgente",
        observacoes="Falta conferência de retenções tributárias.",
        estado="intermediario",
        gerar_analise=True,
        tipo_minuta="Ofício",
    ),
    dict(
        tipo=FISCALIZACAO_CONTRATUAL,
        unidade_demandante="Coordenadoria de Contratos",
        objeto="Fiscalização do contrato de limpeza e conservação predial",
        valor_estimado=None,
        data_fim_vigencia=None,
        urgencia="Normal",
        observacoes="Relatório do período ainda não elaborado pelo fiscal designado.",
        estado="pendencias_criticas",
        gerar_analise=True,
        tipo_minuta=None,
    ),
    dict(
        tipo=FISCALIZACAO_CONTRATUAL,
        unidade_demandante="Departamento de Compras",
        objeto="Fiscalização do contrato de fornecimento de material de expediente",
        valor_estimado=None,
        data_fim_vigencia=None,
        urgencia="Normal",
        observacoes="Fiscalização em dia, sem ocorrências registradas.",
        estado="completo",
        gerar_analise=True,
        tipo_minuta=None,
    ),
    dict(
        tipo=FISCALIZACAO_CONTRATUAL,
        unidade_demandante="Pró-Reitoria de Extensão",
        objeto="Fiscalização do contrato de prestação de serviços de eventos institucionais",
        valor_estimado=None,
        data_fim_vigencia=None,
        urgencia="Normal",
        observacoes="Notificação à contratada pendente de formalização.",
        estado="intermediario",
        gerar_analise=False,
        tipo_minuta=None,
    ),
]


def _numero_sei(sequencial: int) -> str:
    return f"04030-000001{sequencial:02d}/2026-{sequencial:02d}"


def _marcar_completo(processo_id: int, tipo: str) -> None:
    for item in get_checklist(tipo):
        db.salvar_estado_checklist(processo_id, item["id"], True)


def _marcar_pendencias_criticas(processo_id: int, tipo: str) -> None:
    complementares = [item for item in get_checklist(tipo) if not item["critico"]]
    if complementares:
        db.salvar_estado_checklist(processo_id, complementares[0]["id"], True)


def _marcar_intermediario(processo_id: int, tipo: str) -> None:
    itens = get_checklist(tipo)
    for item in itens:
        if item["critico"]:
            db.salvar_estado_checklist(processo_id, item["id"], True)
    complementares = [item for item in itens if not item["critico"]]
    for item in complementares[:-1]:
        db.salvar_estado_checklist(processo_id, item["id"], True)


_MARCADORES_ESTADO = {
    "completo": _marcar_completo,
    "pendencias_criticas": _marcar_pendencias_criticas,
    "intermediario": _marcar_intermediario,
}


def popular_banco_se_vazio() -> None:
    """Insere os 9 processos fictícios de demonstração caso o banco ainda não tenha nenhum processo."""
    if db.listar_processos():
        return

    for sequencial, dados in enumerate(PROCESSOS_SEED, start=1):
        processo_id = db.criar_processo(
            numero=_numero_sei(sequencial),
            tipo=dados["tipo"],
            unidade_demandante=dados["unidade_demandante"],
            objeto=dados["objeto"],
            valor_estimado=dados["valor_estimado"],
            data_fim_vigencia=dados["data_fim_vigencia"],
            urgencia=dados["urgencia"],
            observacoes=dados["observacoes"],
        )

        _MARCADORES_ESTADO[dados["estado"]](processo_id, dados["tipo"])

        if dados["gerar_analise"]:
            analisar_processo(processo_id)

        if dados["tipo_minuta"]:
            gerar_minuta(processo_id, dados["tipo_minuta"])
