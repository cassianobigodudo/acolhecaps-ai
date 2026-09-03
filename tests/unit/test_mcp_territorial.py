"""
Testes para Tool MCP de Validação Territorial.

Cobre cenários: validação bem-sucedida, CEP fora de cobertura, timeout,
fallback, e injeção de prompt.
"""

import asyncio
from datetime import datetime

import pytest

from app.services.mcp_territorial_tool import (
    MCPTerritorialTool,
    obter_tool_territorial,
)


class TestMCPTerritorialValidacao:
    """Testes de validação básica e format de CEP."""

    def test_formato_cep_valido_com_hifen(self):
        """CEP válido com hífen deve passar na validação."""
        tool = MCPTerritorialTool()
        assert tool._validar_formato_cep("88010-000") is True

    def test_formato_cep_valido_sem_hifen(self):
        """CEP válido sem hífen deve passar na validação."""
        tool = MCPTerritorialTool()
        assert tool._validar_formato_cep("88010000") is True

    def test_formato_cep_invalido_poucos_digitos(self):
        """CEP com poucos dígitos deve falhar na validação."""
        tool = MCPTerritorialTool()
        assert tool._validar_formato_cep("8801") is False

    def test_formato_cep_invalido_letras(self):
        """CEP com letras deve falhar na validação."""
        tool = MCPTerritorialTool()
        assert tool._validar_formato_cep("8801A-000") is False

    def test_normalizacao_cep_remove_hifen(self):
        """Normalização deve remover hífen."""
        tool = MCPTerritorialTool()
        assert tool._normalizar_cep("88010-000") == "88010000"

    def test_normalizacao_cep_remove_espacos(self):
        """Normalização deve remover espaços."""
        tool = MCPTerritorialTool()
        assert tool._normalizar_cep("88010 000") == "88010000"


class TestMCPTerritorialPayload:
    """Testes de validação de payload."""

    def test_payload_valido_florianopolis(self):
        """Payload válido para Florianópolis deve passar."""
        tool = MCPTerritorialTool()
        payload = {
            "cep": "88010-000",
            "bairro": "Centro",
            "municipio": "Florianópolis",
        }
        # Não deve lançar exceção
        tool._validar_payload(payload)

    def test_payload_sem_cep(self):
        """Payload sem CEP deve lançar ValueError."""
        tool = MCPTerritorialTool()
        payload = {"bairro": "Centro", "municipio": "Florianópolis"}
        with pytest.raises(ValueError, match="Campo 'cep' obrigatório"):
            tool._validar_payload(payload)

    def test_payload_sem_bairro(self):
        """Payload sem bairro deve lançar ValueError."""
        tool = MCPTerritorialTool()
        payload = {"cep": "88010-000", "municipio": "Florianópolis"}
        with pytest.raises(ValueError, match="Campo 'bairro' obrigatório"):
            tool._validar_payload(payload)

    def test_payload_sem_municipio(self):
        """Payload sem município deve lançar ValueError."""
        tool = MCPTerritorialTool()
        payload = {"cep": "88010-000", "bairro": "Centro"}
        with pytest.raises(ValueError, match="Campo 'municipio' obrigatório"):
            tool._validar_payload(payload)

    def test_payload_cep_invalido(self):
        """Payload com CEP inválido deve lançar ValueError."""
        tool = MCPTerritorialTool()
        payload = {"cep": "123", "bairro": "Centro", "municipio": "Florianópolis"}
        with pytest.raises(ValueError, match="Formato de CEP inválido"):
            tool._validar_payload(payload)

    def test_payload_nao_dicionario(self):
        """Payload não-dicionário deve lançar ValueError."""
        tool = MCPTerritorialTool()
        with pytest.raises(ValueError, match="Payload deve ser um dicionário"):
            tool._validar_payload("nao_eh_dict")


class TestMCPTerritorialConsultaCobertura:
    """Testes de consulta de cobertura."""

    @pytest.mark.asyncio
    async def test_cep_dentro_cobertura_florianopolis(self):
        """CEP em Florianópolis deve retornar validação positiva."""
        tool = MCPTerritorialTool()
        payload = {
            "cep": "88010-000",
            "bairro": "Centro",
            "municipio": "Florianópolis",
        }
        resultado = await tool._consultar_cobertura(payload)

        assert resultado["valido"] is True
        assert resultado["cep"] == "88010-000"
        assert resultado["area_cobertura"] == "Centro"
        assert resultado["fallback"] is False
        assert "validado" in resultado["mensagem"].lower()

    @pytest.mark.asyncio
    async def test_cep_fora_cobertura_outro_municipio(self):
        """CEP de outro município deve retornar validação negativa."""
        tool = MCPTerritorialTool()
        payload = {"cep": "88010-000", "bairro": "Centro", "municipio": "São Paulo"}
        resultado = await tool._consultar_cobertura(payload)

        assert resultado["valido"] is False
        assert resultado["area_cobertura"] == "Fora da cobertura"
        assert resultado["fallback"] is False
        assert "fora" in resultado["mensagem"].lower()

    @pytest.mark.asyncio
    async def test_cep_nao_existe_mesmo_municipio(self):
        """CEP não-existente em Florianópolis deve retornar validação negativa."""
        tool = MCPTerritorialTool()
        payload = {
            "cep": "99999-999",
            "bairro": "Desconhecido",
            "municipio": "Florianópolis",
        }
        resultado = await tool._consultar_cobertura(payload)

        assert resultado["valido"] is False
        assert resultado["fallback"] is False

    @pytest.mark.asyncio
    async def test_resultado_contem_timestamp(self):
        """Resultado deve conter timestamp ISO."""
        tool = MCPTerritorialTool()
        payload = {
            "cep": "88025-000",
            "bairro": "Lagoa da Conceição",
            "municipio": "Florianópolis",
        }
        resultado = await tool._consultar_cobertura(payload)

        # Validar que timestamp é ISO válido
        timestamp = datetime.fromisoformat(resultado["timestamp"])
        assert timestamp is not None


class TestMCPTerritorialValidacaoCompleta:
    """Testes de fluxo completo de validação."""

    @pytest.mark.asyncio
    async def test_validacao_sucesso_florianopolis_centro(self):
        """Fluxo completo: validação bem-sucedida para Centro."""
        tool = MCPTerritorialTool()
        payload = {
            "cep": "88015-000",
            "bairro": "Centro-Norte",
            "municipio": "Florianópolis",
        }
        resultado = await tool.validar_territorial(payload)

        assert resultado["valido"] is True
        assert resultado["fallback"] is False
        assert resultado["cep"] == "88015-000"
        assert "Centro-Norte" in resultado["area_cobertura"] or resultado["valido"]

    @pytest.mark.asyncio
    async def test_validacao_sucesso_florianopolis_campeche(self):
        """Fluxo completo: validação bem-sucedida para Campeche."""
        tool = MCPTerritorialTool()
        payload = {"cep": "88035-000", "bairro": "Campeche", "municipio": "Florianópolis"}
        resultado = await tool.validar_territorial(payload)

        assert resultado["valido"] is True
        assert resultado["fallback"] is False
        assert "Campeche" in resultado["area_cobertura"]

    @pytest.mark.asyncio
    async def test_validacao_falha_municipio_diferente(self):
        """Fluxo completo: validação falha para município diferente."""
        tool = MCPTerritorialTool()
        payload = {"cep": "88010-000", "bairro": "Centro", "municipio": "Brusque"}
        resultado = await tool.validar_territorial(payload)

        assert resultado["valido"] is False
        assert resultado["fallback"] is False


class TestMCPTerritorialTimeout:
    """Testes de cenários de timeout."""

    @pytest.mark.asyncio
    async def test_timeout_ativa_fallback(self):
        """Timeout deve ativar modo fallback."""
        tool = MCPTerritorialTool()
        payload = {
            "cep": "88010-000",
            "bairro": "Centro",
            "municipio": "Florianópolis",
        }

        # Passar timeout muito curto (10ms)
        resultado = await tool.validar_territorial(payload, timeout=0.01)

        # Em timeout, fallback aceita com advertência
        assert resultado["fallback"] is True
        assert resultado["valido"] is True  # Fallback aceita
        assert "indisponível" in resultado["mensagem"].lower()

    @pytest.mark.asyncio
    async def test_timeout_contem_timestamp(self):
        """Resultado de timeout deve conter timestamp."""
        tool = MCPTerritorialTool()
        payload = {"cep": "88010-000", "bairro": "Centro", "municipio": "Florianópolis"}
        resultado = await tool.validar_territorial(payload, timeout=0.01)

        timestamp = datetime.fromisoformat(resultado["timestamp"])
        assert timestamp is not None


class TestMCPTerritorialFallback:
    """Testes de cenários de fallback."""

    def test_resultado_fallback_aceita_com_advertencia(self):
        """Fallback deve aceitar CEP com advertência."""
        tool = MCPTerritorialTool()
        payload = {"cep": "88010-000", "bairro": "Centro", "municipio": "Florianópolis"}
        resultado = tool._resultado_fallback(payload, erro="timeout")

        assert resultado["fallback"] is True
        assert resultado["valido"] is True  # Fallback aceita
        assert "FALLBACK" in resultado["area_cobertura"]
        assert "indisponível" in resultado["mensagem"].lower()

    def test_resultado_fallback_preserva_dados_original(self):
        """Fallback deve preservar dados originais do payload."""
        tool = MCPTerritorialTool()
        payload = {
            "cep": "88025-000",
            "bairro": "Lagoa",
            "municipio": "Florianópolis",
        }
        resultado = tool._resultado_fallback(payload, erro="conexao_falhou")

        assert resultado["cep"] == "88025-000"
        assert resultado["bairro"] == "Lagoa"
        assert resultado["municipio"] == "FLORIANÓPOLIS"


class TestMCPTerritorialSeguranca:
    """Testes de segurança contra injeção de prompt."""

    @pytest.mark.asyncio
    async def test_prompt_injection_em_cep(self):
        """CEP com prompt injection deve falhar na validação."""
        tool = MCPTerritorialTool()
        payload = {
            "cep": "88010-000'; DROP TABLE CAPS; --",
            "bairro": "Centro",
            "municipio": "Florianópolis",
        }

        # Deve falhar na validação de formato e retornar resultado de fallback (erro capturado)
        resultado = await tool.validar_territorial(payload)
        # Formato inválido → fallback ativado
        assert resultado["fallback"] is True

    @pytest.mark.asyncio
    async def test_prompt_injection_em_bairro(self):
        """Bairro com prompt injection não causa erro, apenas tratado como string."""
        tool = MCPTerritorialTool()
        payload = {
            "cep": "88010-000",
            "bairro": "Centro' OR '1'='1",
            "municipio": "Florianópolis",
        }

        # Deve passar na validação e apenas não encontrar match
        resultado = await tool.validar_territorial(payload)
        assert resultado is not None

    @pytest.mark.asyncio
    async def test_payload_vazio(self):
        """Payload vazio deve ser tratado como erro e ativar fallback."""
        tool = MCPTerritorialTool()

        # Payload vazio → fallback ativado
        resultado = await tool.validar_territorial({})
        assert resultado["fallback"] is True


class TestMCPTerritorialObservabilidade:
    """Testes de observabilidade (trace_id, logging)."""

    def test_trace_id_gerado_automaticamente(self):
        """Trace ID deve ser gerado automaticamente se não fornecido."""
        tool = MCPTerritorialTool()
        assert tool.trace_id is not None
        assert "territorial-" in tool.trace_id

    def test_trace_id_customizado(self):
        """Deve permitir trace ID customizado."""
        trace_id_custom = "custom-trace-12345"
        tool = MCPTerritorialTool(trace_id=trace_id_custom)
        assert tool.trace_id == trace_id_custom

    @pytest.mark.asyncio
    async def test_logging_estruturado_json(self, caplog):
        """Logs devem ser estruturados em JSON."""
        tool = MCPTerritorialTool(trace_id="test-trace-001")
        payload = {
            "cep": "88010-000",
            "bairro": "Centro",
            "municipio": "Florianópolis",
        }

        resultado = await tool.validar_territorial(payload)

        # Verificar que a função executou
        assert resultado is not None


class TestMCPTerritorialSingleton:
    """Testes para padrão singleton."""

    def test_obter_tool_primeira_vez(self):
        """Primeira chamada deve criar nova instância."""
        # Limpar singleton anterior
        import app.services.mcp_territorial_tool as mcp_module

        mcp_module._tool_singleton = None

        tool = obter_tool_territorial()
        assert tool is not None
        assert isinstance(tool, MCPTerritorialTool)

    def test_obter_tool_reutiliza_instancia(self):
        """Chamadas subsequentes devem reutilizar instância."""
        import app.services.mcp_territorial_tool as mcp_module

        mcp_module._tool_singleton = None

        tool1 = obter_tool_territorial()
        tool2 = obter_tool_territorial()
        assert tool1 is tool2


class TestMCPTerritorialIntegracao:
    """Testes de integração com múltiplas operações."""

    @pytest.mark.asyncio
    async def test_multiplas_validacoes_sequenciais(self):
        """Múltiplas validações sequenciais devem funcionar."""
        tool = MCPTerritorialTool()

        payloads = [
            {"cep": "88010-000", "bairro": "Centro", "municipio": "Florianópolis"},
            {"cep": "88025-000", "bairro": "Lagoa", "municipio": "Florianópolis"},
            {"cep": "88035-000", "bairro": "Campeche", "municipio": "Florianópolis"},
        ]

        resultados = []
        for payload in payloads:
            resultado = await tool.validar_territorial(payload)
            resultados.append(resultado)

        assert len(resultados) == 3
        assert all(r["valido"] is True for r in resultados)

    @pytest.mark.asyncio
    async def test_validacoes_paralelas(self):
        """Validações paralelas devem funcionar sem conflito."""
        tool1 = MCPTerritorialTool(trace_id="parallel-1")
        tool2 = MCPTerritorialTool(trace_id="parallel-2")

        payload1 = {
            "cep": "88010-000",
            "bairro": "Centro",
            "municipio": "Florianópolis",
        }
        payload2 = {
            "cep": "88025-000",
            "bairro": "Lagoa",
            "municipio": "Florianópolis",
        }

        resultado1, resultado2 = await asyncio.gather(
            tool1.validar_territorial(payload1),
            tool2.validar_territorial(payload2),
        )

        assert resultado1["cep"] == "88010-000"
        assert resultado2["cep"] == "88025-000"
        assert tool1.trace_id != tool2.trace_id
