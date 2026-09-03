"""
Testes E2E para o AlertService (Card 10: Low-Code/ChatOps Integration).

Suite de testes que valida:
- Detecção de níveis de prioridade que disparam alertas (Média, Alta, Crítica)
- Construção correta do payload estruturado
- Disparo de webhooks com retry automático
- Tratamento de falhas de rede (timeout, connect error, HTTP error)
- Integração com node_finalizacao do grafo
- Observabilidade com trace_id correlacionado
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.alert_service import AlertService, NivelAlertar, obter_alert_service


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def webhook_url():
    """URL de webhook de teste."""
    return "https://n8n.example.com/webhook/alerts"


@pytest.fixture
def alert_service(webhook_url):
    """Instância do AlertService para testes."""
    service = AlertService(
        webhook_url=webhook_url,
        timeout=5,
        retry_count=3,
    )
    yield service
    # Cleanup assíncrono
    asyncio.run(service.fechar())


@pytest.fixture
def entrada_acolhimento():
    """Dados de entrada do acolhimento."""
    return {
        "id_paciente": "PAC-2024-001",
        "relato": "Paciente relata ideação suicida e crise aguda de ansiedade.",
        "cep": "88015-100",
    }


@pytest.fixture
def ficha_triagem_media_prioridade():
    """Ficha de triagem com prioridade média."""
    return {
        "nivel_prioridade": "Média",
        "fatores_risco": ["Ansiedade moderada", "Stress ocupacional"],
        "oficinas_sugeridas": ["Grupo de Suporte", "Oficina de Resiliência"],
        "status_aprovacao": "pendente",
        "data_criacao": "2024-01-15T10:30:00",
        "observacoes": "Caso moderado. Requer seguimento em 1 semana.",
    }


@pytest.fixture
def ficha_triagem_alta_prioridade():
    """Ficha de triagem com prioridade alta."""
    return {
        "nivel_prioridade": "Alta",
        "fatores_risco": ["Ideação suicida", "Crise aguda", "Isolamento social"],
        "oficinas_sugeridas": ["Acompanhamento psicológico intensivo"],
        "status_aprovacao": "pendente",
        "data_criacao": "2024-01-15T10:30:00",
        "observacoes": "Caso crítico. Requer avaliação urgente.",
    }


@pytest.fixture
def ficha_triagem_critica_prioridade():
    """Ficha de triagem com prioridade crítica."""
    return {
        "nivel_prioridade": "Crítica",
        "fatores_risco": ["Tentativa de suicídio em 24h", "Intoxicação"],
        "oficinas_sugeridas": ["Internação imediata"],
        "status_aprovacao": "pendente",
        "data_criacao": "2024-01-15T10:30:00",
        "observacoes": "Paciente em risco iminente de morte. Acionado protocolo de emergência.",
    }


@pytest.fixture
def ficha_triagem_baixa_prioridade():
    """Ficha de triagem com prioridade baixa (não dispara alerta)."""
    return {
        "nivel_prioridade": "Baixa",
        "fatores_risco": ["Ansiedade leve"],
        "oficinas_sugeridas": ["Oficina de Mindfulness"],
        "status_aprovacao": "aprovado",
        "data_criacao": "2024-01-15T10:30:00",
        "observacoes": "Paciente com sintomas leves. Recomenda-se seguimento ambulatorial.",
    }


@pytest.fixture
def trace_id():
    """ID de rastreabilidade."""
    return "trace-2024-001-xyz789"


# ============================================================================
# TESTES: Detecção de Prioridades (Média, Alta, Crítica disparam alerta)
# ============================================================================


@pytest.mark.asyncio
async def test_alerta_nao_dispara_para_prioridade_baixa(
    alert_service, entrada_acolhimento, ficha_triagem_baixa_prioridade, trace_id
):
    """Verifica que nível Baixa não dispara alerta."""
    resultado = await alert_service.verificar_e_disparar_alerta(
        nivel_prioridade="Baixa",
        ficha_triagem=ficha_triagem_baixa_prioridade,
        entrada_acolhimento=entrada_acolhimento,
        trace_id=trace_id,
    )

    assert resultado is False, "Alerta não deve ser disparado para prioridade Baixa"


@pytest.mark.asyncio
async def test_alerta_dispara_para_prioridade_media(
    alert_service,
    entrada_acolhimento,
    ficha_triagem_media_prioridade,
    trace_id,
    webhook_url,
):
    """Verifica que nível Média dispara alerta com webhook."""
    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        resultado = await alert_service.verificar_e_disparar_alerta(
            nivel_prioridade="Média",
            ficha_triagem=ficha_triagem_media_prioridade,
            entrada_acolhimento=entrada_acolhimento,
            trace_id=trace_id,
        )

        assert resultado is True, "Alerta deve ser disparado para prioridade Média"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == webhook_url


@pytest.mark.asyncio
async def test_alerta_dispara_para_prioridade_alta(
    alert_service,
    entrada_acolhimento,
    ficha_triagem_alta_prioridade,
    trace_id,
    webhook_url,
):
    """Verifica que nível Alta dispara alerta com webhook."""
    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        resultado = await alert_service.verificar_e_disparar_alerta(
            nivel_prioridade="Alta",
            ficha_triagem=ficha_triagem_alta_prioridade,
            entrada_acolhimento=entrada_acolhimento,
            trace_id=trace_id,
        )

        assert resultado is True, "Alerta deve ser disparado para prioridade Alta"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == webhook_url


@pytest.mark.asyncio
async def test_alerta_dispara_para_prioridade_critica(
    alert_service,
    entrada_acolhimento,
    ficha_triagem_critica_prioridade,
    trace_id,
    webhook_url,
):
    """Verifica que nível Crítica dispara alerta com webhook."""
    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=201)

        resultado = await alert_service.verificar_e_disparar_alerta(
            nivel_prioridade="Crítica",
            ficha_triagem=ficha_triagem_critica_prioridade,
            entrada_acolhimento=entrada_acolhimento,
            trace_id=trace_id,
        )

        assert resultado is True, "Alerta deve ser disparado para prioridade Crítica"
        mock_post.assert_called_once()


# ============================================================================
# TESTES: Construção de Payload
# ============================================================================


@pytest.mark.asyncio
async def test_payload_estrutura_completa(
    alert_service, entrada_acolhimento, ficha_triagem_alta_prioridade, trace_id
):
    """Verifica que o payload contém todos os campos obrigatórios."""
    payload = alert_service._construir_payload(
        nivel_prioridade="Alta",
        ficha_triagem=ficha_triagem_alta_prioridade,
        entrada_acolhimento=entrada_acolhimento,
        trace_id=trace_id,
    )

    # Campos obrigatórios
    assert "tipo_evento" in payload
    assert "timestamp" in payload
    assert "trace_id" in payload
    assert "paciente" in payload
    assert "risco" in payload
    assert "ficha_triagem" in payload
    assert "acao_requerida" in payload

    # Validações específicas
    assert payload["tipo_evento"] == "alerta_urgencia_paciente"
    assert payload["trace_id"] == trace_id
    assert payload["paciente"]["id"] == "PAC-2024-001"
    assert payload["paciente"]["cep"] == "88015-100"
    assert payload["risco"]["nivel"] == "Alta"


@pytest.mark.asyncio
async def test_payload_inclui_fatores_risco(
    alert_service, entrada_acolhimento, ficha_triagem_alta_prioridade, trace_id
):
    """Verifica que o payload inclui os fatores de risco identificados."""
    payload = alert_service._construir_payload(
        nivel_prioridade="Alta",
        ficha_triagem=ficha_triagem_alta_prioridade,
        entrada_acolhimento=entrada_acolhimento,
        trace_id=trace_id,
    )

    assert payload["risco"]["fatores"] == [
        "Ideação suicida",
        "Crise aguda",
        "Isolamento social",
    ]


@pytest.mark.asyncio
async def test_payload_timestamp_valido(
    alert_service, entrada_acolhimento, ficha_triagem_alta_prioridade, trace_id
):
    """Verifica que o timestamp do payload está em formato ISO."""
    payload = alert_service._construir_payload(
        nivel_prioridade="Alta",
        ficha_triagem=ficha_triagem_alta_prioridade,
        entrada_acolhimento=entrada_acolhimento,
        trace_id=trace_id,
    )

    # Tenta fazer parse do ISO timestamp
    try:
        datetime.fromisoformat(payload["timestamp"])
        assert True
    except ValueError:
        pytest.fail(f"Timestamp inválido: {payload['timestamp']}")


# ============================================================================
# TESTES: Cálculo de Severidade
# ============================================================================


@pytest.mark.asyncio
async def test_severidade_critica(alert_service):
    """Verifica que nível Crítica tem severidade 100."""
    severidade = alert_service._calcular_severidade("Crítica")
    assert severidade == 100


@pytest.mark.asyncio
async def test_severidade_alta(alert_service):
    """Verifica que nível Alta tem severidade 80."""
    severidade = alert_service._calcular_severidade("Alta")
    assert severidade == 80


@pytest.mark.asyncio
async def test_severidade_media(alert_service):
    """Verifica que nível Média tem severidade 60."""
    severidade = alert_service._calcular_severidade("Média")
    assert severidade == 60


@pytest.mark.asyncio
async def test_severidade_baixa(alert_service):
    """Verifica que nível Baixa tem severidade 10."""
    severidade = alert_service._calcular_severidade("Baixa")
    assert severidade == 10


# ============================================================================
# TESTES: Disparo de Webhook com Retry
# ============================================================================


@pytest.mark.asyncio
async def test_webhook_sucesso_primeira_tentativa(
    alert_service, webhook_url
):
    """Verifica que webhook com sucesso não faz retry."""
    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        payload = {"test": "payload"}
        resultado = await alert_service._disparar_webhook(payload, "trace-1")

        assert resultado is True
        assert mock_post.call_count == 1


@pytest.mark.asyncio
async def test_webhook_retry_timeout(alert_service, webhook_url):
    """Verifica que webhook com timeout faz retry 3 vezes."""
    import httpx

    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Timeout")

        payload = {"test": "payload"}
        resultado = await alert_service._disparar_webhook(payload, "trace-1")

        assert resultado is False
        assert mock_post.call_count == 3, f"Esperava 3 tentativas, obteve {mock_post.call_count}"


@pytest.mark.asyncio
async def test_webhook_retry_connect_error(alert_service, webhook_url):
    """Verifica que webhook com erro de conexão faz retry 3 vezes."""
    import httpx

    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        payload = {"test": "payload"}
        resultado = await alert_service._disparar_webhook(payload, "trace-1")

        assert resultado is False
        assert mock_post.call_count == 3


@pytest.mark.asyncio
async def test_webhook_retry_http_error_recupera(alert_service, webhook_url):
    """Verifica que webhook falha inicialmente mas recupera no retry."""
    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        # Falha nas 2 primeiras tentativas, sucesso na 3ª
        mock_post.side_effect = [
            MagicMock(status_code=500),
            MagicMock(status_code=503),
            MagicMock(status_code=200),
        ]

        payload = {"test": "payload"}
        resultado = await alert_service._disparar_webhook(payload, "trace-1")

        assert resultado is True
        assert mock_post.call_count == 3


@pytest.mark.asyncio
async def test_webhook_header_trace_id(alert_service, webhook_url):
    """Verifica que o header X-Trace-ID é enviado corretamente."""
    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        payload = {"test": "payload"}
        trace_id = "trace-test-123"
        await alert_service._disparar_webhook(payload, trace_id)

        call_args = mock_post.call_args
        headers = call_args[1]["headers"]
        assert headers["X-Trace-ID"] == trace_id


@pytest.mark.asyncio
async def test_webhook_content_type_json(alert_service, webhook_url):
    """Verifica que o header Content-Type é application/json."""
    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        payload = {"test": "payload"}
        await alert_service._disparar_webhook(payload, "trace-1")

        call_args = mock_post.call_args
        headers = call_args[1]["headers"]
        assert headers["Content-Type"] == "application/json"


# ============================================================================
# TESTES: Factory Function
# ============================================================================


def test_obter_alert_service_com_webhook():
    """Verifica que factory retorna AlertService quando webhook está configurado."""
    webhook_url = "https://example.com/webhook"
    service = obter_alert_service(webhook_url=webhook_url)

    assert service is not None
    assert isinstance(service, AlertService)
    assert service.webhook_url == webhook_url


def test_obter_alert_service_sem_webhook():
    """Verifica que factory retorna None quando webhook não está configurado."""
    service = obter_alert_service(webhook_url=None)
    assert service is None


# ============================================================================
# TESTES: Integração End-to-End
# ============================================================================


@pytest.mark.asyncio
async def test_fluxo_completo_alerta_media_prioridade(
    alert_service,
    entrada_acolhimento,
    ficha_triagem_media_prioridade,
    trace_id,
):
    """Testa o fluxo completo: detecção → construção → webhook para Média."""
    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        # Dispara o alerta
        resultado = await alert_service.verificar_e_disparar_alerta(
            nivel_prioridade="Média",
            ficha_triagem=ficha_triagem_media_prioridade,
            entrada_acolhimento=entrada_acolhimento,
            trace_id=trace_id,
        )

        assert resultado is True

        # Verifica que o webhook foi chamado com payload válido
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        # Validações do payload
        assert payload["tipo_evento"] == "alerta_urgencia_paciente"
        assert payload["risco"]["nivel"] == "Média"
        assert payload["risco"]["severidade"] == 60
        assert payload["paciente"]["id"] == "PAC-2024-001"
        assert payload["trace_id"] == trace_id


@pytest.mark.asyncio
async def test_fluxo_completo_alerta_alta_prioridade(
    alert_service,
    entrada_acolhimento,
    ficha_triagem_alta_prioridade,
    trace_id,
):
    """Testa o fluxo completo: detecção → construção → webhook para Alta."""
    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        # Dispara o alerta
        resultado = await alert_service.verificar_e_disparar_alerta(
            nivel_prioridade="Alta",
            ficha_triagem=ficha_triagem_alta_prioridade,
            entrada_acolhimento=entrada_acolhimento,
            trace_id=trace_id,
        )

        assert resultado is True

        # Verifica que o webhook foi chamado com payload válido
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        # Validações do payload
        assert payload["tipo_evento"] == "alerta_urgencia_paciente"
        assert payload["risco"]["nivel"] == "Alta"
        assert payload["risco"]["severidade"] == 80
        assert payload["paciente"]["id"] == "PAC-2024-001"
        assert payload["trace_id"] == trace_id


@pytest.mark.asyncio
async def test_fluxo_completo_alerta_critica_prioridade(
    alert_service,
    entrada_acolhimento,
    ficha_triagem_critica_prioridade,
    trace_id,
):
    """Testa o fluxo completo com prioridade Crítica."""
    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=201)

        resultado = await alert_service.verificar_e_disparar_alerta(
            nivel_prioridade="Crítica",
            ficha_triagem=ficha_triagem_critica_prioridade,
            entrada_acolhimento=entrada_acolhimento,
            trace_id=trace_id,
        )

        assert resultado is True

        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["risco"]["nivel"] == "Crítica"
        assert payload["risco"]["severidade"] == 100


@pytest.mark.asyncio
async def test_multiplos_alertas_em_sequencia(
    alert_service,
    entrada_acolhimento,
    ficha_triagem_media_prioridade,
    ficha_triagem_alta_prioridade,
    ficha_triagem_critica_prioridade,
):
    """Testa múltiplos alertas disparados em sequência (Média, Alta, Crítica)."""
    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        # Primeiro alerta (Média)
        resultado1 = await alert_service.verificar_e_disparar_alerta(
            nivel_prioridade="Média",
            ficha_triagem=ficha_triagem_media_prioridade,
            entrada_acolhimento=entrada_acolhimento,
            trace_id="trace-1",
        )

        # Segundo alerta (Alta)
        resultado2 = await alert_service.verificar_e_disparar_alerta(
            nivel_prioridade="Alta",
            ficha_triagem=ficha_triagem_alta_prioridade,
            entrada_acolhimento=entrada_acolhimento,
            trace_id="trace-2",
        )

        # Terceiro alerta (Crítica)
        resultado3 = await alert_service.verificar_e_disparar_alerta(
            nivel_prioridade="Crítica",
            ficha_triagem=ficha_triagem_critica_prioridade,
            entrada_acolhimento={
                "id_paciente": "PAC-2024-003",
                "relato": "Crise aguda",
                "cep": "88015-100",
            },
            trace_id="trace-3",
        )

        assert resultado1 is True
        assert resultado2 is True
        assert resultado3 is True
        assert mock_post.call_count == 3


@pytest.mark.asyncio
async def test_alerta_com_dados_parciais_entrada(
    alert_service, ficha_triagem_alta_prioridade, trace_id
):
    """Testa que alerta funciona mesmo com dados parciais na entrada."""
    entrada_parcial = {
        "id_paciente": "PAC-DESCONHECIDO",
        # CEP faltando é ok
    }

    with patch.object(alert_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        resultado = await alert_service.verificar_e_disparar_alerta(
            nivel_prioridade="Alta",
            ficha_triagem=ficha_triagem_alta_prioridade,
            entrada_acolhimento=entrada_parcial,
            trace_id=trace_id,
        )

        assert resultado is True
        payload = mock_post.call_args[1]["json"]
        assert payload["paciente"]["cep"] == "DESCONHECIDO"


# ============================================================================
# TESTES: Enum NivelAlertar
# ============================================================================


def test_nivel_alertar_enum_valores():
    """Verifica que o enum tem os valores corretos (Média, Alta, Crítica)."""
    assert NivelAlertar.MEDIA.value == "Média"
    assert NivelAlertar.ALTA.value == "Alta"
    assert NivelAlertar.CRITICA.value == "Crítica"


def test_nivel_alertar_enum_comparacao():
    """Verifica que o enum pode ser comparado com strings."""
    assert "Média" in [NivelAlertar.MEDIA.value, NivelAlertar.ALTA.value, NivelAlertar.CRITICA.value]
    assert "Alta" in [NivelAlertar.MEDIA.value, NivelAlertar.ALTA.value, NivelAlertar.CRITICA.value]
    assert "Crítica" in [NivelAlertar.MEDIA.value, NivelAlertar.ALTA.value, NivelAlertar.CRITICA.value]
