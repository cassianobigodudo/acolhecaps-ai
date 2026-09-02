"""
Tool MCP para Validação Territorial - Verificação de cobertura CAPS.

Este módulo implementa uma ferramenta integrada via protocolo MCP para validar
se o CEP/Bairro do paciente pertence à área de cobertura regional do CAPS.

Características:
- Validação de formato de CEP (padrão brasileiro)
- Tratamento de timeouts e exceções de integração
- Cenários de fallback em caso de falha
- Logging estruturado com trace_id
"""

import json
import logging
import re
from typing import TypedDict, Optional
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger(__name__)


class ValidacaoTerritorialPayload(TypedDict):
    """Schema de validação para payload territorial."""
    cep: str
    bairro: str
    municipio: str


class ResultadoValidacaoTerritorial(TypedDict):
    """Resultado da validação territorial."""
    valido: bool
    cep: str
    bairro: str
    municipio: str
    area_cobertura: str
    mensagem: str
    timestamp: str
    fallback: bool


class MCPTerritorialTool:
    """
    Tool MCP para validação territorial de pacientes no CAPS.
    
    Simula consulta em base de dados geográfica do SUS para validar
    se o endereço pertence à área de cobertura do CAPS de Florianópolis/SC.
    """

    # Área de cobertura simulada: CEPs de Florianópolis
    CEPS_COBERTURA_FLORIANOPOLIS = {
        "88010": "Centro",
        "88015": "Centro",
        "88020": "Centro-Norte",
        "88025": "Lagoa da Conceição",
        "88030": "Lagoa da Conceição",
        "88035": "Campeche",
        "88040": "Campeche",
        "88045": "Armação",
        "88050": "Armação",
        "88055": "Pântano do Sul",
        "88060": "Ribeirão da Ilha",
        "88065": "Ratones",
        "88070": "Canasvieiras",
        "88075": "Jurerê",
        "88080": "Piratininga",
        "88085": "Ingleses",
        "88090": "Bom Abrigo",
        "88095": "São João do Rio Vermelho",
        "88100": "Praia Brava",
    }

    TIMEOUT_SEGUNDOS = 5
    MAX_RETRIES = 2

    def __init__(self, trace_id: Optional[str] = None):
        """
        Inicializa a Tool MCP.
        
        Args:
            trace_id: ID único para correlação de logs (opcional)
        """
        self.trace_id = trace_id or self._gerar_trace_id()
        self.tentativas = 0

    @staticmethod
    def _gerar_trace_id() -> str:
        """Gera um trace_id único."""
        from uuid import uuid4
        return f"territorial-{uuid4().hex[:8]}"

    @staticmethod
    def _validar_formato_cep(cep: str) -> bool:
        """
        Valida o formato do CEP (padrão brasileiro: XXXXX-XXX ou XXXXXXXX).
        
        Args:
            cep: CEP a validar
            
        Returns:
            True se formato é válido, False caso contrário
        """
        padrao = r"^\d{5}-?\d{3}$"
        return bool(re.match(padrao, cep.strip()))

    def _normalizar_cep(self, cep: str) -> str:
        """
        Normaliza CEP removendo hífen e espaços.
        
        Args:
            cep: CEP a normalizar
            
        Returns:
            CEP normalizado (8 dígitos)
        """
        return cep.replace("-", "").replace(" ", "").strip()

    async def validar_territorial(
        self,
        payload: ValidacaoTerritorialPayload,
        timeout: Optional[int] = None,
    ) -> ResultadoValidacaoTerritorial:
        """
        Valida se o CEP/Bairro pertence à área de cobertura CAPS.
        
        Args:
            payload: Dicionário com cep, bairro e municipio
            timeout: Timeout em segundos (default: TIMEOUT_SEGUNDOS)
            
        Returns:
            Resultado da validação com status, mensagem e fallback
            
        Raises:
            asyncio.TimeoutError: Se exceder timeout
            ValueError: Se payload inválido
        """
        timeout = timeout or self.TIMEOUT_SEGUNDOS
        self.tentativas = 0

        logger.info(
            json.dumps({
                "trace_id": self.trace_id,
                "evento": "validacao_territorial_iniciada",
                "cep": payload.get("cep", ""),
                "municipio": payload.get("municipio", ""),
            })
        )

        try:
            # Validar payload
            self._validar_payload(payload)

            # Executar com timeout
            resultado = await asyncio.wait_for(
                self._consultar_cobertura(payload),
                timeout=timeout,
            )

            logger.info(
                json.dumps({
                    "trace_id": self.trace_id,
                    "evento": "validacao_territorial_sucesso",
                    "valido": resultado["valido"],
                })
            )

            return resultado

        except asyncio.TimeoutError:
            logger.warning(
                json.dumps({
                    "trace_id": self.trace_id,
                    "evento": "validacao_territorial_timeout",
                    "timeout_segundos": timeout,
                })
            )
            return self._resultado_fallback(payload, erro="timeout")

        except ValueError as e:
            logger.error(
                json.dumps({
                    "trace_id": self.trace_id,
                    "evento": "validacao_territorial_erro_validacao",
                    "erro": str(e),
                })
            )
            return self._resultado_fallback(payload, erro=str(e))

        except Exception as e:
            logger.error(
                json.dumps({
                    "trace_id": self.trace_id,
                    "evento": "validacao_territorial_erro_desconhecido",
                    "erro": str(e),
                    "tipo_erro": type(e).__name__,
                })
            )
            return self._resultado_fallback(payload, erro="erro_desconhecido")

    def _validar_payload(self, payload: ValidacaoTerritorialPayload) -> None:
        """
        Valida o payload de entrada.
        
        Args:
            payload: Dicionário com cep, bairro e municipio
            
        Raises:
            ValueError: Se payload inválido
        """
        if not isinstance(payload, dict):
            raise ValueError("Payload deve ser um dicionário")

        campos_obrigatorios = ["cep", "bairro", "municipio"]
        for campo in campos_obrigatorios:
            if campo not in payload or not payload[campo]:
                raise ValueError(f"Campo '{campo}' obrigatório e não pode estar vazio")

        cep = str(payload["cep"]).strip()
        if not self._validar_formato_cep(cep):
            raise ValueError(f"Formato de CEP inválido: {cep}")

    async def _consultar_cobertura(
        self, payload: ValidacaoTerritorialPayload
    ) -> ResultadoValidacaoTerritorial:
        """
        Consulta a base de cobertura (simulado com pequeno delay).
        
        Args:
            payload: Dicionário com cep, bairro e municipio
            
        Returns:
            Resultado da validação
        """
        # Simula latência de consulta
        await asyncio.sleep(0.1)

        cep_normalizado = self._normalizar_cep(payload["cep"])
        prefixo_cep = cep_normalizado[:5]
        municipio = payload.get("municipio", "").strip().upper()

        # Validar se CEP está na cobertura
        valido = (
            prefixo_cep in self.CEPS_COBERTURA_FLORIANOPOLIS
            and municipio == "FLORIANÓPOLIS"
        )

        area_cobertura = (
            self.CEPS_COBERTURA_FLORIANOPOLIS.get(prefixo_cep, "Desconhecida")
            if valido
            else "Fora da cobertura"
        )

        mensagem = (
            f"CEP {payload['cep']} validado na região {area_cobertura}"
            if valido
            else f"CEP {payload['cep']} está fora da área de cobertura do CAPS"
        )

        return {
            "valido": valido,
            "cep": payload["cep"],
            "bairro": payload.get("bairro", "").strip(),
            "municipio": municipio,
            "area_cobertura": area_cobertura,
            "mensagem": mensagem,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fallback": False,
        }

    def _resultado_fallback(
        self, payload: ValidacaoTerritorialPayload, erro: str
    ) -> ResultadoValidacaoTerritorial:
        """
        Retorna resultado de fallback em caso de erro.
        
        Em modo fallback, aceita qualquer CEP com aviso.
        
        Args:
            payload: Payload original
            erro: Descrição do erro
            
        Returns:
            Resultado com flag de fallback ativado
        """
        logger.info(
            json.dumps({
                "trace_id": self.trace_id,
                "evento": "validacao_territorial_fallback_ativado",
                "erro_original": erro,
            })
        )

        return {
            "valido": True,  # Em fallback, aceita (com advertência)
            "cep": payload.get("cep", ""),
            "bairro": payload.get("bairro", "").strip(),
            "municipio": payload.get("municipio", "").strip().upper(),
            "area_cobertura": "FALLBACK - Validação indisponível",
            "mensagem": f"Validação territorial indisponível ({erro}). "
                       "Aceitando CEP com ressalva para revisão manual.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fallback": True,
        }


# Exportar instância singleton para uso no grafo
_tool_singleton: Optional[MCPTerritorialTool] = None


def obter_tool_territorial(trace_id: Optional[str] = None) -> MCPTerritorialTool:
    """
    Obtém ou cria a instância da Tool MCP (singleton).
    
    Args:
        trace_id: ID único para correlação de logs
        
    Returns:
        Instância de MCPTerritorialTool
    """
    global _tool_singleton
    if _tool_singleton is None:
        _tool_singleton = MCPTerritorialTool(trace_id=trace_id)
    return _tool_singleton
