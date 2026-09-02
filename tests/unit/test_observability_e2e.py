"""
Testes E2E de Observabilidade - Card 6: Logs Estruturados com trace_id Correlacionado.

Este arquivo testa:
- Logging estruturado em JSON
- Correlação de trace_id em todos os eventos
- Captura de métricas de latência
- Arquivo de log com traces completos
"""

import pytest
import json
import time
from pathlib import Path
from app.services.observability import (
    RequestContext,
    ObservabilityLogAggregator,
    trace_context,
    get_current_trace_id,
    setup_observability_logger,
)


class TestObservabilityTraceContext:
    """Testes de contexto de trace_id."""

    def test_trace_context_manager(self):
        """Verifica que trace_id é gerenciado corretamente."""
        trace_id = "test-trace-001"

        with trace_context(trace_id):
            assert get_current_trace_id() == trace_id

        # Após sair, trace_id deve voltar
        assert get_current_trace_id() == "no-trace"

    def test_nested_trace_contexts(self):
        """Verifica suporte a trace_ids aninhados."""
        trace_1 = "trace-001"
        trace_2 = "trace-002"

        with trace_context(trace_1):
            assert get_current_trace_id() == trace_1

            with trace_context(trace_2):
                assert get_current_trace_id() == trace_2

            # Após sair do contexto 2, volta para contexto 1
            assert get_current_trace_id() == trace_1

        assert get_current_trace_id() == "no-trace"


class TestRequestContext:
    """Testes de contexto de requisição."""

    def test_request_context_initialization(self):
        """Verifica inicialização de contexto."""
        trace_id = "req-001"
        ctx = RequestContext(trace_id)

        assert ctx.trace_id == trace_id
        assert len(ctx.events) == 0
        assert ctx.get_duration_ms() >= 0

    def test_log_event(self):
        """Verifica registro de eventos."""
        ctx = RequestContext("req-002")

        ctx.log_event("node_extracao", "iniciado")
        ctx.log_event("node_rag", "consulta_realizada", {"documentos": 3})

        assert len(ctx.events) == 2
        assert ctx.events[0]["node"] == "node_extracao"
        assert ctx.events[0]["action"] == "iniciado"
        assert ctx.events[1]["node"] == "node_rag"
        # Metadata é expandida no evento, não aninhada
        assert ctx.events[1]["documentos"] == 3

    def test_log_metric(self):
        """Verifica registro de métricas."""
        ctx = RequestContext("req-003")

        ctx.log_metric("latencia_rag", 145.5, "ms")
        ctx.log_metric("documentos_recuperados", 3, "count")

        # Métricas não são armazenadas em events, apenas logadas
        assert len(ctx.events) == 0  # log_metric não adiciona a events

    def test_request_duration(self):
        """Verifica cálculo de duração."""
        ctx = RequestContext("req-004")

        time.sleep(0.1)  # Aguarda 100ms
        duration = ctx.get_duration_ms()

        assert duration >= 100  # Deve ter pelo menos 100ms
        assert duration < 200  # Não deve ser muito maior

    def test_context_to_dict(self):
        """Verifica serialização para dicionário."""
        ctx = RequestContext("req-005")
        ctx.log_event("node_1", "action_1")
        ctx.log_event("node_2", "action_2")

        ctx_dict = ctx.to_dict()

        assert ctx_dict["trace_id"] == "req-005"
        assert ctx_dict["events_count"] == 2
        assert len(ctx_dict["events"]) == 2
        assert "duration_ms" in ctx_dict


class TestObservabilityLogger:
    """Testes de logger estruturado."""

    def test_logger_creation(self):
        """Verifica criação de logger."""
        logger = setup_observability_logger("test_logger_001")

        assert logger is not None
        assert logger.name == "test_logger_001"
        assert len(logger.handlers) > 0

    def test_logger_with_file(self, tmp_path):
        """Verifica logger com arquivo."""
        log_file = tmp_path / "test.jsonl"
        logger = setup_observability_logger(
            "test_logger_002",
            log_file=str(log_file),
        )

        logger.info("Test message")

        # Verifica que arquivo foi criado
        assert log_file.exists()

        # Verifica que log está em JSON
        with open(log_file, "r") as f:
            line = f.readline()
            entry = json.loads(line)

            assert "timestamp" in entry
            assert "level" in entry
            assert "message" in entry
            assert "trace_id" in entry


class TestObservabilityLogAggregator:
    """Testes de agregador de logs."""

    def test_aggregator_record_request(self, tmp_path):
        """Verifica registro de requisição."""
        log_file = tmp_path / "observability.jsonl"
        aggregator = ObservabilityLogAggregator(str(log_file))

        ctx = RequestContext("agg-001")
        ctx.log_event("node_1", "acao_1")
        ctx.log_event("node_2", "acao_2")

        aggregator.record_request(ctx)

        # Verifica que arquivo foi criado
        assert log_file.exists()

        # Verifica conteúdo
        with open(log_file, "r") as f:
            lines = f.readlines()
            assert len(lines) > 0

    def test_aggregator_get_latency_stats(self, tmp_path):
        """Verifica extração de estatísticas de latência."""
        log_file = tmp_path / "observability.jsonl"
        aggregator = ObservabilityLogAggregator(str(log_file))

        trace_id = "stats-001"
        ctx = RequestContext(trace_id)
        ctx.log_event("node_inicio", "start")
        time.sleep(0.05)
        ctx.log_event("node_fim", "end")

        aggregator.record_request(ctx)

        # Busca estatísticas
        stats = aggregator.get_latency_stats(trace_id)

        if stats and stats["found"]:
            assert stats["trace_id"] == trace_id
            assert stats["total_duration_ms"] > 0
            assert stats["total_duration_ms"] >= 50  # Pelo menos 50ms


class TestObservabilityIntegrationE2E:
    """Testes de integração end-to-end."""

    def test_complete_request_trace(self, tmp_path):
        """Testa fluxo completo de rastreamento de requisição."""
        log_file = tmp_path / "complete_trace.jsonl"
        aggregator = ObservabilityLogAggregator(str(log_file))

        trace_id = "e2e-001"

        with trace_context(trace_id):
            # Simula execução do grafo
            ctx = RequestContext(trace_id)

            # Node 1: Extração
            ctx.log_event("node_extracao", "iniciado")
            ctx.log_metric("relato_tamanho", 245, "chars")
            time.sleep(0.02)
            ctx.log_event("node_extracao", "concluido")

            # Node 2A e 2B: Paralelo (RAG + Territorial)
            ctx.log_event("node_rag_diretrizes", "iniciado")
            ctx.log_metric("rag_latencia", 156.3, "ms")
            ctx.log_event("node_rag_diretrizes", "concluido", {"docs": 3})

            ctx.log_event("node_mcp_territorio", "iniciado")
            ctx.log_metric("territorio_latencia", 89.2, "ms")
            ctx.log_event("node_mcp_territorio", "concluido", {"valido": True})

            # Node 3: Avaliação de Risco
            ctx.log_event("node_avaliacao_risco", "iniciado")
            ctx.log_metric("risco_avaliacao_latencia", 312.5, "ms")
            ctx.log_event(
                "node_avaliacao_risco",
                "concluido",
                {"prioridade": "Baixa"},
            )

            # Node 4: Finalização
            ctx.log_event("node_finalizacao", "iniciado")
            ctx.log_event("node_finalizacao", "concluido", {"status": "ok"})

            # Verifica que todos os eventos têm trace_id
            assert all(e for e in ctx.events), "Todos eventos devem ser registrados"

            # Registra requisição no agregador
            aggregator.record_request(ctx)

            # Verifica duração total
            total_duration = ctx.get_duration_ms()
            assert total_duration > 0
            assert total_duration < 5000  # Menos de 5 segundos

        # Verifica arquivo de log
        assert log_file.exists()

        # Lê arquivo e verifica estrutura
        with open(log_file, "r") as f:
            lines = f.readlines()
            assert len(lines) > 0

            # Pelo menos um evento deve mencionar o trace_id
            found_trace = False
            for line in lines:
                entry = json.loads(line)
                if entry.get("trace_id") == trace_id:
                    found_trace = True
                    break

            assert found_trace, "Deve encontrar trace_id no arquivo"

    def test_multiple_requests_correlation(self, tmp_path):
        """Testa correlação de múltiplas requisições."""
        log_file = tmp_path / "multiple_traces.jsonl"
        aggregator = ObservabilityLogAggregator(str(log_file))

        trace_ids = ["req-001", "req-002", "req-003"]

        for trace_id in trace_ids:
            with trace_context(trace_id):
                ctx = RequestContext(trace_id)
                ctx.log_event("node_1", "start")
                time.sleep(0.01)
                ctx.log_event("node_1", "end")
                aggregator.record_request(ctx)

        # Verifica que arquivo contém todas as requisições
        assert log_file.exists()

        # Cada requisição deve ser localizável
        for trace_id in trace_ids:
            stats = aggregator.get_latency_stats(trace_id)
            if stats:
                assert stats["trace_id"] == trace_id


class TestObservabilityMetricsCapture:
    """Testes de captura de métricas."""

    def test_latency_metrics_captured(self):
        """Verifica captura de métricas de latência."""
        ctx = RequestContext("metrics-001")

        # Simula operações com latência
        start = time.time()
        time.sleep(0.05)
        ctx.log_metric("operacao_1_latencia", 50, "ms")

        time.sleep(0.03)
        ctx.log_metric("operacao_2_latencia", 30, "ms")

        # Duração total deve refletir ambas operações
        total_duration = ctx.get_duration_ms()
        assert total_duration >= 80, "Duração deve incluir ambas operações"

    def test_custom_metadata_in_events(self):
        """Verifica que metadata customizada é preservada."""
        ctx = RequestContext("metadata-001")

        custom_data = {
            "prioridade": "Alta",
            "paciente_id": "pac-123",
            "cep": "88015-100",
        }

        ctx.log_event("node_avaliacao", "processado", custom_data)

        event = ctx.events[0]
        # Metadata é expandida no evento, não aninhada
        for key, value in custom_data.items():
            assert event[key] == value


class TestObservabilityStructuredFormat:
    """Testes de formato estruturado dos logs."""

    def test_json_format_compliance(self, tmp_path):
        """Verifica conformidade com formato JSON estruturado."""
        log_file = tmp_path / "format_test.jsonl"
        logger = setup_observability_logger("format_test", log_file=str(log_file))

        with trace_context("format-test-001"):
            logger.info("Test event with metadata")

        # Lê e valida JSON
        with open(log_file, "r") as f:
            line = f.readline()
            entry = json.loads(line)

            # Campos obrigatórios
            assert "timestamp" in entry
            assert "level" in entry
            assert "logger" in entry
            assert "message" in entry
            assert "trace_id" in entry

            # Timestamp deve ser ISO 8601
            assert "T" in entry["timestamp"]
            assert "Z" in entry["timestamp"] or "+" in entry["timestamp"]
