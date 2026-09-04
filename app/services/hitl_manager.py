"""
Gerenciador de Human-in-the-Loop (HITL).

Responsável por:
1. Armazenar fichas em estado "pendente" aguardando aprovação
2. Receber decisões do profissional (aprovação ou correção)
3. Atualizar o estado da ficha no grafo via checkpointer

Padrão Singleton para manter estado compartilhado.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class HITLManager:
    """Gerencia fichas em estado HITL (Human-in-the-Loop)."""

    def __init__(self):
        """Inicializa manager com dicionário de fichas pendentes."""
        # Dict: trace_id -> ficha_triagem com status pendente
        self._fichas_pendentes: Dict[str, Dict] = {}

    def registrar_ficha_pendente(self, trace_id: str, ficha_triagem: Dict) -> None:
        """
        Registra uma ficha que está aguardando aprovação.

        Args:
            trace_id: ID único da triagem
            ficha_triagem: Dados da ficha em estado pendente
        """
        if ficha_triagem.get("status_aprovacao") == "pendente":
            self._fichas_pendentes[trace_id] = ficha_triagem.copy()
            logger.info(
                f"[HITL_MANAGER] Ficha registrada como pendente | "
                f"trace_id={trace_id} | prioridade={ficha_triagem.get('nivel_prioridade')}"
            )
        else:
            logger.warning(
                f"[HITL_MANAGER] Tentativa de registrar ficha sem status pendente | "
                f"trace_id={trace_id} | status={ficha_triagem.get('status_aprovacao')}"
            )

    def obter_ficha_pendente(self, trace_id: str) -> Optional[Dict]:
        """
        Obtém uma ficha pendente.

        Args:
            trace_id: ID único da triagem

        Returns:
            Dict com ficha ou None se não encontrada
        """
        ficha = self._fichas_pendentes.get(trace_id)
        if ficha:
            logger.info(f"[HITL_MANAGER] Ficha recuperada | trace_id={trace_id}")
        else:
            logger.warning(f"[HITL_MANAGER] Ficha não encontrada | trace_id={trace_id}")
        return ficha

    def listar_fichas_pendentes(self) -> Dict[str, Dict]:
        """
        Lista todas as fichas pendentes.

        Returns:
            Dict com todas as fichas pendentes
        """
        logger.info(f"[HITL_MANAGER] Listando fichas pendentes | total={len(self._fichas_pendentes)}")
        return self._fichas_pendentes.copy()

    def aprovar_ficha(
        self,
        trace_id: str,
        profissional_nome: Optional[str] = None,
        profissional_profissao: Optional[str] = None,
        observacoes: Optional[str] = None,
    ) -> Dict:
        """
        Aprova uma ficha pendente.

        Args:
            trace_id: ID único da triagem
            profissional_nome: Nome do profissional que aprovou
            profissional_profissao: Profissão do profissional
            observacoes: Observações adicionais

        Returns:
            Ficha atualizada com status "aprovado"

        Raises:
            ValueError: Se ficha não for encontrada
        """
        ficha = self._fichas_pendentes.get(trace_id)
        if not ficha:
            raise ValueError(f"Ficha pendente não encontrada: {trace_id}")

        # Atualiza ficha
        ficha["status_aprovacao"] = "aprovado"
        ficha["data_aprovacao"] = datetime.utcnow().isoformat()
        
        if observacoes:
            ficha["observacoes"] = observacoes
        
        if profissional_nome or profissional_profissao:
            ficha["profissional_aprovador"] = {
                "nome": profissional_nome,
                "profissao": profissional_profissao,
            }

        logger.info(
            f"[HITL_MANAGER] Ficha APROVADA | "
            f"trace_id={trace_id} | "
            f"prioridade={ficha.get('nivel_prioridade')} | "
            f"profissional={profissional_nome}"
        )

        return ficha

    def corrigir_ficha(
        self,
        trace_id: str,
        nivel_prioridade_corrigido: str,
        profissional_nome: Optional[str] = None,
        profissional_profissao: Optional[str] = None,
        observacoes: Optional[str] = None,
        novo_encaminhamento: Optional[str] = None,
    ) -> Dict:
        """
        Corrige uma ficha pendente (muda prioridade e/ou encaminhamento).

        Args:
            trace_id: ID único da triagem
            nivel_prioridade_corrigido: Nova prioridade
            profissional_nome: Nome do profissional que corrigiu
            profissional_profissao: Profissão do profissional
            observacoes: Observações sobre a correção
            novo_encaminhamento: Novo encaminhamento (opcional)

        Returns:
            Ficha atualizada com status "corrigido"

        Raises:
            ValueError: Se ficha não for encontrada
        """
        ficha = self._fichas_pendentes.get(trace_id)
        if not ficha:
            raise ValueError(f"Ficha pendente não encontrada: {trace_id}")

        # Valida prioridade
        if nivel_prioridade_corrigido not in ["Alta", "Média", "Baixa"]:
            raise ValueError(f"Prioridade inválida: {nivel_prioridade_corrigido}")

        # Armazena prioridade original para referência
        prioridade_original = ficha.get("nivel_prioridade")

        # Atualiza ficha
        ficha["status_aprovacao"] = "corrigido"
        ficha["nivel_prioridade_original"] = prioridade_original
        ficha["nivel_prioridade"] = nivel_prioridade_corrigido
        ficha["data_aprovacao"] = datetime.utcnow().isoformat()

        if novo_encaminhamento:
            ficha["encaminhamento_recomendado"] = novo_encaminhamento

        if observacoes:
            ficha["observacoes"] = observacoes

        if profissional_nome or profissional_profissao:
            ficha["profissional_corretor"] = {
                "nome": profissional_nome,
                "profissao": profissional_profissao,
            }

        logger.info(
            f"[HITL_MANAGER] Ficha CORRIGIDA | "
            f"trace_id={trace_id} | "
            f"prioridade={prioridade_original} → {nivel_prioridade_corrigido} | "
            f"profissional={profissional_nome}"
        )

        return ficha

    def remover_ficha_pendente(self, trace_id: str) -> None:
        """
        Remove uma ficha pendente após decisão profissional.

        Args:
            trace_id: ID único da triagem
        """
        if trace_id in self._fichas_pendentes:
            del self._fichas_pendentes[trace_id]
            logger.info(f"[HITL_MANAGER] Ficha removida de pendentes | trace_id={trace_id}")

    def gerar_mensagem_discord(
        self, 
        trace_id: str, 
        ficha: Dict,
        entrada: Optional[Dict] = None,
    ) -> tuple:
        """
        Gera mensagem formatada para Discord sobre decisão HITL.
        Retorna (mensagem_texto, cor_embed).

        Args:
            trace_id: ID único da triagem
            ficha: Ficha com decisão profissional
            entrada: Dados de entrada (opcional, para mais contexto)

        Returns:
            Tupla (mensagem_texto, cor_hex) para usar em Discord embed
        """
        status = ficha.get("status_aprovacao", "desconhecido").upper()
        prioridade = ficha.get("nivel_prioridade", "?")
        encaminhamento = ficha.get("encaminhamento_recomendado", "Não especificado")
        observacoes = ficha.get("observacoes", "Sem observações")

        # Define cor baseada em prioridade (Discord hex colors)
        cores = {
            "Média": 16776960,      # Amarelo (FFFF00)
            "Alta": 16711680,       # Vermelho (FF0000)
        }
        cor = cores.get(prioridade, 9807270)  # Cinza padrão

        profissional_nome = "Não informado"
        profissional_profissao = "Não informado"

        if status == "APROVADO":
            prof_info = ficha.get("profissional_aprovador", {})
            profissional_nome = prof_info.get("nome", "Não informado")
            profissional_profissao = prof_info.get("profissao", "Não informado")
        else:  # CORRIGIDO
            prof_info = ficha.get("profissional_corretor", {})
            profissional_nome = prof_info.get("nome", "Não informado")
            profissional_profissao = prof_info.get("profissao", "Não informado")

        # Define emoji de prioridade
        emoji_prioridade = "⚠️" if prioridade == "Média" else "🚨"

        # Monta mensagem em formato Markdown para Discord
        mensagem = f"""{emoji_prioridade} **HITL - Prioridade {prioridade}**

**Status:** {status}
**Encaminhamento:** {encaminhamento}

**Profissional:** {profissional_nome} ({profissional_profissao})
**Observações:** {observacoes}

**Trace ID:** `{trace_id}`
**Data:** {ficha.get('data_aprovacao', 'Desconhecida')}"""

        logger.info(
            f"[HITL_MANAGER] Mensagem Discord gerada | "
            f"trace_id={trace_id} | status={status} | prioridade={prioridade}"
        )

        return mensagem, cor


# Singleton global
_hitl_manager_instance: Optional[HITLManager] = None


def obter_hitl_manager() -> HITLManager:
    """
    Obtém instância global do HITLManager.

    Returns:
        Instância singleton do HITLManager
    """
    global _hitl_manager_instance
    if _hitl_manager_instance is None:
        _hitl_manager_instance = HITLManager()
        logger.info("[HITL_MANAGER] Instância criada (singleton)")
    return _hitl_manager_instance
