"""
Serviço de Alertas para AcolheCAPS AI - Card 10: Low-Code/ChatOps Integration.

Este módulo implementa a lógica de detecção de fichas com risco elevado
e dispara webhooks para plataformas low-code (n8n/Make) que formatam
e roteiam notificações para Discord/Slack/Email.

Dispara alertas para níveis de prioridade: Média, Alta e Crítica.

Integração:
- Detecção: node_finalizacao observa nivel_prioridade em ["Média", "Alta", "Crítica"]
- Webhook: POST para n8n com payload estruturado (paciente, risco, dados da ficha)
- Output: n8n formata e envia para canais de comunicação (Discord, Slack, Email)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum

import httpx

# ============================================================================
# Logging Configuration
# ============================================================================
logger = logging.getLogger(__name__)


class NivelAlertar(str, Enum):
    """Níveis de prioridade que disparam alertas para n8n."""

    MEDIA = "Média"
    ALTA = "Alta"
    CRITICA = "Crítica"


class AlertService:
    """
    Serviço responsável por disparar alertas de urgência para plataformas low-code.

    Atributos:
        webhook_url: URL do webhook n8n/Make que recebe os alertas
        timeout: Timeout em segundos para requisições HTTP (default: 10s)
        retry_count: Número de tentativas em caso de falha (default: 3)
    """

    def __init__(
        self,
        webhook_url: str,
        timeout: int = 10,
        retry_count: int = 3,
    ):
        """
        Inicializa o serviço de alertas.

        Args:
            webhook_url: URL do webhook n8n/Make (ex: https://n8n.example.com/webhook/alerts)
            timeout: Timeout em segundos (default: 10)
            retry_count: Número de tentativas (default: 3)
        """
        self.webhook_url = webhook_url
        self.timeout = timeout
        self.retry_count = retry_count
        self.client = httpx.AsyncClient(timeout=timeout)

    async def verificar_e_disparar_alerta(
        self,
        nivel_prioridade: str,
        ficha_triagem: Dict[str, Any],
        entrada_acolhimento: Dict[str, Any],
        trace_id: str,
    ) -> bool:
        """
        Verifica se o nível de prioridade requer alerta e o dispara via webhook.

        Args:
            nivel_prioridade: Nível de prioridade da ficha ("Média", "Alta", "Crítica", "Baixa")
            ficha_triagem: Dados estruturados da ficha de triagem
            entrada_acolhimento: Dados de entrada do acolhimento (paciente, CEP, relato)
            trace_id: ID de rastreabilidade para observabilidade

        Returns:
            True se o alerta foi disparado com sucesso, False caso contrário
        """
        # Verifica se o nível de prioridade requer alerta (Média, Alta, Crítica)
        niveis_que_disparam = [NivelAlertar.MEDIA.value, NivelAlertar.ALTA.value, NivelAlertar.CRITICA.value]
        
        if nivel_prioridade not in niveis_que_disparam:
            logger.info(
                f"[ALERT_SERVICE] Nível {nivel_prioridade} não requer alerta | trace_id={trace_id}"
            )
            return False

        try:
            logger.info(
                f"[ALERT_SERVICE] Disparando alerta para nível {nivel_prioridade} | "
                f"trace_id={trace_id}"
            )

            # Constrói o payload estruturado para o webhook
            payload = self._construir_payload(
                nivel_prioridade=nivel_prioridade,
                ficha_triagem=ficha_triagem,
                entrada_acolhimento=entrada_acolhimento,
                trace_id=trace_id,
            )

            # Dispara o webhook com retry
            sucesso = await self._disparar_webhook(payload, trace_id)

            if sucesso:
                logger.info(
                    f"[ALERT_SERVICE] Alerta disparado com sucesso | "
                    f"prioridade={nivel_prioridade} | trace_id={trace_id}"
                )
                return True
            else:
                logger.warning(
                    f"[ALERT_SERVICE] Falha ao disparar alerta após {self.retry_count} "
                    f"tentativas | prioridade={nivel_prioridade} | trace_id={trace_id}"
                )
                return False

        except Exception as e:
            logger.error(
                f"[ALERT_SERVICE] Erro ao disparar alerta | "
                f"erro={str(e)} | prioridade={nivel_prioridade} | trace_id={trace_id}"
            )
            return False

    def _construir_payload(
        self,
        nivel_prioridade: str,
        ficha_triagem: Dict[str, Any],
        entrada_acolhimento: Dict[str, Any],
        trace_id: str,
    ) -> Dict[str, Any]:
        """
        Constrói o payload estruturado para envio ao webhook.

        Args:
            nivel_prioridade: Nível de prioridade
            ficha_triagem: Dados da ficha de triagem
            entrada_acolhimento: Dados de entrada
            trace_id: ID de rastreabilidade

        Returns:
            Dictionary com a estrutura completa do alerta
        """
        payload = {
            "tipo_evento": "alerta_urgencia_paciente",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "paciente": {
                "id": entrada_acolhimento.get("id_paciente", "DESCONHECIDO"),
                "cep": entrada_acolhimento.get("cep", "DESCONHECIDO"),
            },
            "risco": {
                "nivel": nivel_prioridade,
                "severidade": self._calcular_severidade(nivel_prioridade),
                "fatores": ficha_triagem.get("fatores_risco", []),
            },
            "ficha_triagem": ficha_triagem,
            "acao_requerida": "Revisar imediatamente e contatar paciente para atendimento urgente",
        }

        return payload

    def _calcular_severidade(self, nivel_prioridade: str) -> int:
        """
        Calcula um score de severidade numérico para ordenação em interfaces.

        Args:
            nivel_prioridade: Nível de prioridade ("Crítica", "Alta", "Média", "Baixa")

        Returns:
            Score de severidade (0-100)
        """
        mapa_severidade = {
            "Crítica": 100,
            "Alta": 80,
            "Média": 60,
            "Baixa": 10,
        }
        return mapa_severidade.get(nivel_prioridade, 0)

    async def _disparar_webhook(self, payload: Dict[str, Any], trace_id: str) -> bool:
        """
        Dispara o webhook para n8n/Make com retry automático.

        Args:
            payload: Dados a enviar
            trace_id: ID de rastreabilidade

        Returns:
            True se sucesso, False caso contrário
        """
        for tentativa in range(self.retry_count):
            try:
                logger.info(
                    f"[ALERT_SERVICE] Tentativa {tentativa + 1}/{self.retry_count} "
                    f"de webhook | trace_id={trace_id}"
                )

                response = await self.client.post(
                    self.webhook_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Trace-ID": trace_id,
                    },
                )

                if response.status_code in [200, 201, 202]:
                    logger.info(
                        f"[ALERT_SERVICE] Webhook retornou {response.status_code} | "
                        f"trace_id={trace_id}"
                    )
                    return True
                else:
                    logger.warning(
                        f"[ALERT_SERVICE] Webhook retornou {response.status_code} | "
                        f"response={response.text[:200]} | trace_id={trace_id}"
                    )

            except httpx.TimeoutException:
                logger.warning(
                    f"[ALERT_SERVICE] Timeout na tentativa {tentativa + 1} | "
                    f"trace_id={trace_id}"
                )

            except httpx.ConnectError:
                logger.warning(
                    f"[ALERT_SERVICE] Erro de conexão na tentativa {tentativa + 1} | "
                    f"trace_id={trace_id}"
                )

            except Exception as e:
                logger.error(
                    f"[ALERT_SERVICE] Erro na tentativa {tentativa + 1} | "
                    f"erro={str(e)} | trace_id={trace_id}"
                )

        return False

    async def fechar(self) -> None:
        """Fecha a conexão do cliente HTTP."""
        await self.client.aclose()


# ============================================================================
# Factory Function (para usar em graph_service)
# ============================================================================


def obter_alert_service(webhook_url: Optional[str] = None) -> Optional[AlertService]:
    """
    Factory function que retorna um AlertService configurado.

    Em produção, o webhook_url viria de variável de ambiente ou config.
    Para testes, retorna None se webhook_url não estiver configurado.

    Args:
        webhook_url: URL do webhook (se None, retorna None)

    Returns:
        AlertService ou None se webhook não estiver configurado
    """
    if not webhook_url:
        logger.warning(
            "[ALERT_SERVICE] Webhook URL não configurado. Alertas não serão disparados."
        )
        return None

    return AlertService(webhook_url=webhook_url)
