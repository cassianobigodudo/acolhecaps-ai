"""
Contratos de dados para AcolheCAPS AI - Assistente de Triagem e Apoio Multiprofissional
Define os schemas Pydantic para validação de entrada e saída do fluxo de acolhimento.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, validator


class EntradaAcolhimento(BaseModel):
    """
    Schema para entrada de dados do acolhimento do paciente.

    Attributes:
        id_paciente: Identificador único do paciente
        relato: Descrição do relato de acolhimento fornecido pelo paciente
        cep: Código de Endereçamento Postal para validação territorial
    """

    id_paciente: str = Field(
        ..., description="Identificador único do paciente no sistema", min_length=1, max_length=50
    )
    relato: str = Field(
        ...,
        description="Relato textual do acolhimento - motivo da consulta e sintomas",
        min_length=10,
        max_length=5000,
    )
    cep: str = Field(
        ...,
        description="CEP do endereço do paciente para validação de cobertura territorial",
        pattern=r"^\d{5}-?\d{3}$",
    )

    @validator("relato")
    def validar_relato_seguranca(cls, v):
        """Validação básica de segurança contra prompt injection no relato."""
        # Verifica sinais de prompt injection simples
        sinais_suspeitos = [
            "ignore as regras",
            "ignore as diretrizes",
            "libere medicação",
            "by-pass",
            "override",
            "forget the context",
        ]
        v_lower = v.lower()
        for sinal in sinais_suspeitos:
            if sinal in v_lower:
                raise ValueError(
                    "Relato contém instruções suspeitas. "
                    "Mantendo limites de autonomia do agente."
                )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id_paciente": "PAC-2024-001",
                "relato": "Paciente relata sentimentos de ansiedade persistente, "
                "dificuldade de concentração e insônia há 3 meses.",
                "cep": "88015-100",
            }
        }


class FichaTriagemCAPS(BaseModel):
    """
    Schema para saída estruturada da ficha de triagem do CAPS.
    Consolida a análise de risco, prioridade e recomendações de atendimento.

    Attributes:
        nivel_prioridade: Nível de prioridade do atendimento (Alta, Média, Baixa)
        fatores_risco: Lista de fatores de risco identificados no relato
        encaminhamento_recomendado: Profissional/especialidade recomendada baseado no diagnóstico
        oficinas_sugeridas: Lista de oficinas terapêuticas recomendadas
        status_aprovacao: Status da aprovação humana (pendente, aprovado, rejeitado)
    """

    nivel_prioridade: Literal["Alta", "Média", "Baixa"] = Field(
        ..., description="Nível de prioridade da triagem determinado pelo fluxo de análise"
    )
    fatores_risco: List[str] = Field(
        default_factory=list,
        description="Lista de fatores de risco identificados (ex: ideação suicida, crise aguda)",
        max_length=20,
    )
    encaminhamento_recomendado: Optional[str] = Field(
        default=None,
        description="Profissional/especialidade recomendada para atendimento baseado no diagnóstico "
        "(ex: Psicólogo, Psiquiatra, Assistente Social, Grupo de Apoio, etc)",
        max_length=200,
    )
    oficinas_sugeridas: List[str] = Field(
        default_factory=list,
        description="Oficinas terapêuticas recomendadas baseadas em diretrizes clínicas",
        max_length=10,
    )
    status_aprovacao: Literal["pendente", "aprovado", "corrigido"] = Field(
        default="pendente",
        description="Status da aprovação por profissional de saúde. "
        "'aprovado': IA acertou a classificação. "
        "'corrigido': Profissional ajustou nivel_prioridade e/ou encaminhamento_recomendado.",
    )
    data_criacao: datetime = Field(
        default_factory=datetime.utcnow, description="Data e hora de criação da ficha de triagem"
    )
    observacoes: Optional[str] = Field(
        default=None, description="Observações adicionais do profissional de saúde", max_length=1000
    )

    class Config:
        json_schema_extra = {
            "example": {
                "nivel_prioridade": "Alta",
                "fatores_risco": ["Ansiedade com ideação suicida histórica"],
                "encaminhamento_recomendado": "Psiquiatra + Psicólogo (atendimento urgente)",
                "oficinas_sugeridas": [],
                "status_aprovacao": "corrigido",
                "data_criacao": "2024-01-15T10:30:00",
                "observacoes": "IA subestimou risco. Paciente tem tentativa de suicídio prévia. Redirecionado para Psiquiatra urgente.",
            }
        }


class EstadoAcolhimento(BaseModel):
    """
    Schema para o estado interno do grafo LangGraph.
    Mantém histórico de execução, contexto RAG e metadados do paciente.

    Attributes:
        id_sessao: Identificador único da sessão de acolhimento
        entrada: Dados de entrada do acolhimento
        historico_chat: Histórico de mensagens e decisões do agente
        contexto_rag: Contexto recuperado das diretrizes clínicas
        resultado_territorial: Resultado da validação territorial via Tool MCP
        ficha_triagem: Ficha de triagem estruturada (saída)
        trace_id: ID de rastreabilidade para observabilidade
    """

    id_sessao: str = Field(..., description="Identificador único da sessão de acolhimento")
    entrada: EntradaAcolhimento = Field(..., description="Dados de entrada do acolhimento")
    historico_chat: List[dict] = Field(
        default_factory=list, description="Histórico de mensagens e decisões do agente"
    )
    contexto_rag: Optional[str] = Field(
        default=None, description="Contexto recuperado do banco vetorial de diretrizes"
    )
    resultado_territorial: Optional[dict] = Field(
        default=None, description="Resultado da validação territorial (CEP válido, cobertura, etc)"
    )
    ficha_triagem: Optional[FichaTriagemCAPS] = Field(
        default=None, description="Ficha de triagem estruturada (preenchida ao final do fluxo)"
    )
    trace_id: str = Field(
        ..., description="ID de rastreabilidade para observabilidade e logging estruturado"
    )
    requer_aprovacao_humana: bool = Field(
        default=False, description="Flag indicando se requer human-in-the-loop antes de prosseguir"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id_sessao": "SES-2024-001-ABC123",
                "entrada": {
                    "id_paciente": "PAC-2024-001",
                    "relato": "Ansiedade persistente...",
                    "cep": "88015-100",
                },
                "historico_chat": [],
                "contexto_rag": None,
                "resultado_territorial": None,
                "ficha_triagem": None,
                "trace_id": "trace-2024-001-xyz789",
                "requer_aprovacao_humana": False,
            }
        }
