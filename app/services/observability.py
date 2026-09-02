"""
Observabilidade e Instrumentação - Logs Estruturados com trace_id Correlacionado.

Este módulo fornece infraestrutura centralizada para:
- Logging estruturado em JSON com trace_id global
- Captura de métricas de latência em cada operação
- Correlação de eventos ao longo do fluxo completo
- Arquivo de log centralizado para análise
"""

import json
import logging
import time
import functools
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

# ============================================================================
# Global State para trace_id
# ============================================================================

_trace_id_stack: list = []  # Stack de trace_ids para suportar chamadas aninhadas


def get_current_trace_id() -> str:
    """Obtém o trace_id atual do contexto (top of stack)."""
    return _trace_id_stack[-1] if _trace_id_stack else "no-trace"


def set_trace_id(trace_id: str) -> None:
    """Define um novo trace_id no contexto."""
    _trace_id_stack.append(trace_id)


def pop_trace_id() -> Optional[str]:
    """Remove e retorna o trace_id do contexto."""
    return _trace_id_stack.pop() if _trace_id_stack else None


@contextmanager
def trace_context(trace_id: str):
    """Context manager para gerenciar trace_id."""
    set_trace_id(trace_id)
    try:
        yield trace_id
    finally:
        pop_trace_id()


# ============================================================================
# JSON Logger Estruturado
# ============================================================================

class StructuredJSONFormatter(logging.Formatter):
    """Formatter customizado que emite logs em JSON estruturado."""

    def format(self, record: logging.LogRecord) -> str:
        """Formata o registro de log como JSON estruturado."""
        log_obj = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": get_current_trace_id(),
        }

        # Adiciona duração se disponível (para decoradores de latência)
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms

        # Adiciona metadata customizada
        if hasattr(record, "metadata"):
            log_obj.update(record.metadata)

        # Adiciona exceção se houver
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, ensure_ascii=False)


def setup_observability_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Configura um logger estruturado com JSON formatter.

    Args:
        name: Nome do logger
        log_file: Caminho para arquivo de log (opcional)
        level: Nível de logging

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove handlers antigos
    logger.handlers.clear()

    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredJSONFormatter())
    logger.addHandler(console_handler)

    # Handler para arquivo (se especificado)
    if log_file:
        log_path = Path(log_file).parent
        log_path.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setFormatter(StructuredJSONFormatter())
        logger.addHandler(file_handler)

    return logger


# ============================================================================
# Decorador de Latência
# ============================================================================

def measure_latency(logger: logging.Logger, operation_name: str):
    """
    Decorador que mede e registra latência de uma função.

    Args:
        logger: Logger para registrar métrica
        operation_name: Nome da operação para identificação

    Returns:
        Função decorada com medição de latência
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start_time) * 1000
                record = logging.LogRecord(
                    name=logger.name,
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f"[LATENCY] {operation_name}",
                    args=(),
                    exc_info=None,
                )
                record.duration_ms = duration_ms
                record.metadata = {
                    "operation": operation_name,
                    "duration_ms": duration_ms,
                }
                logger.handle(record)

        return wrapper

    return decorator


# ============================================================================
# Contexto de Requisição
# ============================================================================

class RequestContext:
    """Contexto de requisição com métricas e eventos correlacionados."""

    def __init__(self, trace_id: str):
        """
        Inicializa contexto de requisição.

        Args:
            trace_id: ID único para correlação
        """
        self.trace_id = trace_id
        self.start_time = time.time()
        self.events: list = []
        self.logger = setup_observability_logger(
            f"RequestContext[{trace_id}]"
        )

    def log_event(
        self,
        node: str,
        action: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra um evento correlacionado no contexto.

        Args:
            node: Nome do nó do grafo
            action: Ação realizada
            metadata: Dados adicionais (opcional)
        """
        event = {
            "node": node,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_ms": (time.time() - self.start_time) * 1000,
        }

        if metadata:
            event.update(metadata)

        self.events.append(event)

        # Log estruturado
        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"[EVENT] {node}: {action}",
            args=(),
            exc_info=None,
        )
        record.metadata = event
        self.logger.handle(record)

    def log_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "",
    ) -> None:
        """
        Registra uma métrica no contexto.

        Args:
            metric_name: Nome da métrica
            value: Valor numérico
            unit: Unidade de medida
        """
        metric = {
            "metric": metric_name,
            "value": value,
            "unit": unit,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"[METRIC] {metric_name}",
            args=(),
            exc_info=None,
        )
        record.metadata = metric
        self.logger.handle(record)

    def get_duration_ms(self) -> float:
        """Retorna duração total em milissegundos."""
        return (time.time() - self.start_time) * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Converte contexto para dicionário estruturado."""
        return {
            "trace_id": self.trace_id,
            "duration_ms": self.get_duration_ms(),
            "events_count": len(self.events),
            "events": self.events,
        }


# ============================================================================
# Log Aggregator para Análise
# ============================================================================

class ObservabilityLogAggregator:
    """Agregador de logs para análise de execução end-to-end."""

    def __init__(self, log_file: str = "logs/observability.jsonl"):
        """
        Inicializa agregador.

        Args:
            log_file: Caminho para arquivo de logs agregados
        """
        self.log_file = log_file
        self.logger = setup_observability_logger(
            "ObservabilityAggregator",
            log_file=log_file,
        )

    def record_request(self, context: RequestContext) -> None:
        """Registra contexto de requisição completo no arquivo de log."""
        log_entry = {
            "type": "request_complete",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": context.trace_id,
            "duration_ms": context.get_duration_ms(),
            "events_count": len(context.events),
            "summary": {
                "start_node": context.events[0]["node"]
                if context.events
                else None,
                "end_node": context.events[-1]["node"]
                if context.events
                else None,
                "total_events": len(context.events),
            },
        }

        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Request completed",
            args=(),
            exc_info=None,
        )
        record.metadata = log_entry
        self.logger.handle(record)

    def get_latency_stats(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Extrai estatísticas de latência para um trace_id.

        Args:
            trace_id: ID da requisição

        Returns:
            Dicionário com estatísticas ou None se não encontrado
        """
        # Lê o arquivo de log e busca pela requisição
        stats = {
            "trace_id": trace_id,
            "total_duration_ms": 0,
            "events": [],
            "found": False,
        }

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("trace_id") == trace_id:
                            stats["found"] = True
                            if "duration_ms" in entry:
                                stats["total_duration_ms"] = entry[
                                    "duration_ms"
                                ]
                            if "metadata" in entry and "node" in entry[
                                "metadata"
                            ]:
                                stats["events"].append(
                                    entry.get("metadata")
                                )
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass

        return stats if stats["found"] else None


# ============================================================================
# Inicialização Global
# ============================================================================

# Logger global para observabilidade
observability_logger = setup_observability_logger(
    "AcolheCAPS.Observability",
    log_file="logs/application.jsonl",
)

# Agregador global
log_aggregator = ObservabilityLogAggregator(log_file="logs/observability.jsonl")
