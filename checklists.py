"""Definições estáticas dos checklists por tipo de processo."""

PRORROGACAO_CONTRATUAL = "Prorrogação Contratual"
PAGAMENTO = "Pagamento"
FISCALIZACAO_CONTRATUAL = "Fiscalização Contratual"

TIPOS_PROCESSO = [PRORROGACAO_CONTRATUAL, PAGAMENTO, FISCALIZACAO_CONTRATUAL]

CHECKLISTS = {
    PRORROGACAO_CONTRATUAL: [
        {"id": "prorrogacao_01", "descricao": "Manifestação de interesse da contratada", "critico": True},
        {"id": "prorrogacao_02", "descricao": "Justificativa da área demandante quanto à vantajosidade", "critico": True},
        {"id": "prorrogacao_03", "descricao": "Relatório do fiscal/gestor sobre a execução", "critico": True},
        {"id": "prorrogacao_04", "descricao": "Comprovação de manutenção das condições de habilitação", "critico": True},
        {"id": "prorrogacao_05", "descricao": "Certidões de regularidade fiscal e trabalhista", "critico": True},
        {"id": "prorrogacao_06", "descricao": "Pesquisa de preços/demonstração de vantajosidade econômica", "critico": True},
        {"id": "prorrogacao_07", "descricao": "Disponibilidade orçamentária", "critico": True},
        {"id": "prorrogacao_08", "descricao": "Verificação de vigência", "critico": True},
        {"id": "prorrogacao_09", "descricao": "Minuta do termo aditivo", "critico": False},
        {"id": "prorrogacao_10", "descricao": "Manifestação da assessoria jurídica", "critico": False},
    ],
    PAGAMENTO: [
        {"id": "pagamento_01", "descricao": "Nota fiscal/fatura", "critico": True},
        {"id": "pagamento_02", "descricao": "Atesto do fiscal do contrato", "critico": True},
        {"id": "pagamento_03", "descricao": "Termo de recebimento definitivo", "critico": True},
        {"id": "pagamento_04", "descricao": "Certidões de regularidade (federal, FGTS, trabalhista, distrital)", "critico": True},
        {"id": "pagamento_05", "descricao": "Nota de empenho", "critico": True},
        {"id": "pagamento_06", "descricao": "Relatório de medição/comprovação de execução", "critico": True},
        {"id": "pagamento_07", "descricao": "Termo de recebimento provisório", "critico": False},
        {"id": "pagamento_08", "descricao": "Verificação de glosas aplicáveis", "critico": False},
        {"id": "pagamento_09", "descricao": "Ordem de serviço/autorização de execução", "critico": False},
        {"id": "pagamento_10", "descricao": "Conferência de retenções tributárias (IN RFB 1.234/2012)", "critico": False},
    ],
    FISCALIZACAO_CONTRATUAL: [
        {"id": "fiscalizacao_01", "descricao": "Designação formal do fiscal/gestor (portaria)", "critico": True},
        {"id": "fiscalizacao_02", "descricao": "Relatório circunstanciado do período", "critico": True},
        {"id": "fiscalizacao_03", "descricao": "Verificação de cumprimento das obrigações contratuais", "critico": True},
        {"id": "fiscalizacao_04", "descricao": "Controle de vigência e cronograma", "critico": True},
        {"id": "fiscalizacao_05", "descricao": "Registro de ocorrências", "critico": False},
        {"id": "fiscalizacao_06", "descricao": "Notificações à contratada", "critico": False},
        {"id": "fiscalizacao_07", "descricao": "Manifestação do preposto", "critico": False},
        {"id": "fiscalizacao_08", "descricao": "Verificação de garantia contratual vigente", "critico": False},
    ],
}


def get_checklist(tipo_processo: str) -> list:
    """Retorna os itens do checklist definido para o tipo de processo informado."""
    return CHECKLISTS.get(tipo_processo, [])
