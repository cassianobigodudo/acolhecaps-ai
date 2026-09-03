"""
Serviço de Detecção de Anomalias e Análise de Tendência - Card 9.

Monitora padrões irregulares em latência, taxa de erros e identifica
tendências que indicam risco de falha iminente.
"""

import json
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.observability import RequestContext, trace_context


class AnomalyDetector:
    """Detector de anomalias em métricas de execução."""

    def __init__(self, trace_id: Optional[str] = None):
        """
        Inicializa o detector de anomalias.

        Args:
            trace_id: ID de rastreamento para correlação
        """
        self.trace_id = trace_id or f"trace-{datetime.now().isoformat()}"
        self.metrics: List[Dict[str, Any]] = []
        self.anomalies: List[Dict[str, Any]] = []

    def add_metric(
        self,
        node_name: str,
        latency_ms: float,
        status: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Adiciona uma métrica de execução.

        Args:
            node_name: Nome do nó executado
            latency_ms: Latência em millisegundos
            status: Status (success, error, timeout)
            timestamp: Timestamp do evento (default: agora)
        """
        if timestamp is None:
            timestamp = datetime.now()

        metric = {
            "node": node_name,
            "latency_ms": latency_ms,
            "status": status,
            "timestamp": timestamp.isoformat(),
            "trace_id": self.trace_id,
        }
        self.metrics.append(metric)

    def detect_latency_anomalies(
        self, node_name: Optional[str] = None, zscore_threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Detecta anomalias em latência usando Z-score.

        Args:
            node_name: Filtrar por nó específico (None = todos)
            zscore_threshold: Threshold de Z-score para anomalia

        Returns:
            Lista de anomalias detectadas
        """
        anomalies = []

        # Filtrar métricas
        metrics_to_analyze = self.metrics
        if node_name:
            metrics_to_analyze = [m for m in self.metrics if m["node"] == node_name]

        if len(metrics_to_analyze) < 3:
            return anomalies

        latencies = [m["latency_ms"] for m in metrics_to_analyze]
        mean = statistics.mean(latencies)
        stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0

        if stdev == 0:
            return anomalies

        for metric in metrics_to_analyze:
            zscore = abs((metric["latency_ms"] - mean) / stdev)
            if zscore > zscore_threshold:
                anomaly = {
                    "type": "latency_spike",
                    "node": metric["node"],
                    "value": metric["latency_ms"],
                    "mean": mean,
                    "zscore": zscore,
                    "timestamp": metric["timestamp"],
                    "trace_id": self.trace_id,
                }
                anomalies.append(anomaly)
                self.anomalies.append(anomaly)

        return anomalies

    def detect_error_rate_anomalies(
        self, window_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Detecta anomalias em taxa de erro usando janela deslizante.

        Args:
            window_size: Tamanho da janela para cálculo

        Returns:
            Lista de anomalias de taxa de erro
        """
        anomalies = []

        if len(self.metrics) < window_size:
            return anomalies

        # Calcular taxa de erro em janelas
        for i in range(window_size, len(self.metrics)):
            window = self.metrics[i - window_size : i]
            error_count = sum(1 for m in window if m["status"] != "success")
            error_rate = error_count / window_size

            # Se taxa de erro > 30%, anomalia
            if error_rate > 0.3:
                anomaly = {
                    "type": "high_error_rate",
                    "window": window_size,
                    "error_rate": error_rate,
                    "error_count": error_count,
                    "timestamp": datetime.now().isoformat(),
                    "trace_id": self.trace_id,
                }
                anomalies.append(anomaly)
                self.anomalies.append(anomaly)

        return anomalies

    def detect_pattern_drift(self) -> Optional[Dict[str, Any]]:
        """
        Detecta mudança de padrão (drift) em latência ao longo do tempo.

        Returns:
            Anomalia de drift ou None
        """
        if len(self.metrics) < 6:
            return None

        # Dividir em primeira e segunda metade
        mid = len(self.metrics) // 2
        first_half = [m["latency_ms"] for m in self.metrics[:mid]]
        second_half = [m["latency_ms"] for m in self.metrics[mid:]]

        mean1 = statistics.mean(first_half)
        mean2 = statistics.mean(second_half)

        # Se mudança > 50%, é drift
        drift_pct = abs(mean2 - mean1) / mean1 * 100 if mean1 > 0 else 0

        if drift_pct > 50:
            anomaly = {
                "type": "pattern_drift",
                "first_half_mean": mean1,
                "second_half_mean": mean2,
                "drift_percent": drift_pct,
                "timestamp": datetime.now().isoformat(),
                "trace_id": self.trace_id,
            }
            self.anomalies.append(anomaly)
            return anomaly

        return None

    def estimate_failure_probability(self) -> float:
        """
        Estima probabilidade de falha iminente baseado em anomalias.

        Usa simples heurística:
        - Cada anomalia adiciona 10% de risco
        - Taxa de erro > 30% adiciona 20%
        - Pattern drift adiciona 15%

        Returns:
            Probabilidade de falha (0.0 a 1.0)
        """
        probability = 0.0

        # Contar anomalias por tipo
        latency_anomalies = sum(
            1 for a in self.anomalies if a["type"] == "latency_spike"
        )
        error_rate_anomalies = sum(
            1 for a in self.anomalies if a["type"] == "high_error_rate"
        )
        drift_anomalies = sum(
            1 for a in self.anomalies if a["type"] == "pattern_drift"
        )

        # Calcular risco
        probability += min(latency_anomalies * 0.1, 0.3)  # Max 30%
        probability += min(error_rate_anomalies * 0.2, 0.3)  # Max 30%
        probability += min(drift_anomalies * 0.15, 0.2)  # Max 20%

        return min(probability, 1.0)

    def trend_analysis(self) -> Dict[str, Any]:
        """
        Análise de tendência: detecta se situação está piorando, melhorando ou estável.

        Returns:
            Dicionário com trend, velocidade e prognóstico
        """
        if len(self.metrics) < 4:
            return {"trend": "insufficient_data", "metrics_count": len(self.metrics)}

        # Últimas 4 métricas
        recent = self.metrics[-4:]
        recent_latencies = [m["latency_ms"] for m in recent]

        # Calcular slope (tendência)
        diffs = [recent_latencies[i + 1] - recent_latencies[i] for i in range(3)]
        avg_diff = statistics.mean(diffs)

        if avg_diff > 10:
            trend = "degrading"
            prognosis = "Latência aumentando - risco de falha em breve"
        elif avg_diff < -10:
            trend = "improving"
            prognosis = "Latência diminuindo - sistema se recuperando"
        else:
            trend = "stable"
            prognosis = "Latência estável - sem mudanças significativas"

        return {
            "trend": trend,
            "avg_latency_change_ms": avg_diff,
            "prognosis": prognosis,
            "recent_latencies": recent_latencies,
        }

    def generate_report(self) -> Dict[str, Any]:
        """
        Gera relatório completo de anomalias e análise.

        Returns:
            Relatório estruturado
        """
        # Análises
        latency_anomalies = self.detect_latency_anomalies()
        error_anomalies = self.detect_error_rate_anomalies()
        drift = self.detect_pattern_drift()
        failure_prob = self.estimate_failure_probability()
        trend = self.trend_analysis()

        # Métricas gerais
        if self.metrics:
            avg_latency = statistics.mean([m["latency_ms"] for m in self.metrics])
            error_count = sum(1 for m in self.metrics if m["status"] != "success")
            error_rate = error_count / len(self.metrics)
        else:
            avg_latency = 0
            error_rate = 0

        report = {
            "trace_id": self.trace_id,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_metrics": len(self.metrics),
                "total_anomalies": len(self.anomalies),
                "average_latency_ms": avg_latency,
                "error_rate": error_rate,
                "estimated_failure_probability": failure_prob,
            },
            "anomalies_detected": {
                "latency_spikes": latency_anomalies,
                "error_rate_issues": error_anomalies,
                "pattern_drift": drift,
            },
            "trend_analysis": trend,
            "recommendation": self._get_recommendation(
                failure_prob, error_rate, trend
            ),
        }

        return report

    def _get_recommendation(
        self, failure_prob: float, error_rate: float, trend: Dict[str, Any]
    ) -> str:
        """Gera recomendação baseada em análises."""
        if failure_prob > 0.7:
            return (
                "CRÍTICO: Probabilidade de falha muito alta. "
                "Investigar imediatamente e preparar rollback."
            )
        elif failure_prob > 0.5:
            return (
                "ALERTA: Probabilidade de falha moderada. "
                "Monitorar de perto e preparar intervenção."
            )
        elif error_rate > 0.3:
            return "AVISO: Taxa de erro elevada. Revisar logs e corrigir erros comuns."
        elif trend.get("trend") == "degrading":
            return "ATENÇÃO: Performance degradando. Verificar causas antes de piorar."
        else:
            return "OK: Sistema operando normalmente."

    def save_report(self, filepath: Optional[Path] = None) -> Path:
        """
        Salva relatório em arquivo JSON.

        Args:
            filepath: Caminho do arquivo (default: logs/anomaly-report.json)

        Returns:
            Path do arquivo salvo
        """
        if filepath is None:
            filepath = Path(__file__).parent.parent.parent / "logs" / "anomaly-report.json"

        filepath.parent.mkdir(parents=True, exist_ok=True)

        report = self.generate_report()
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        return filepath


class AnomalyAggregator:
    """Agregador de anomalias para análise across múltiplos detectors."""

    def __init__(self):
        """Inicializa o agregador."""
        self.detectors: Dict[str, AnomalyDetector] = {}

    def register_detector(self, trace_id: str, detector: AnomalyDetector) -> None:
        """Registra um detector para agregação."""
        self.detectors[trace_id] = detector

    def aggregate_anomalies(self) -> Dict[str, Any]:
        """
        Agrega anomalias de todos os detectors.

        Returns:
            Agregação de anomalias e estatísticas
        """
        total_anomalies = sum(
            len(d.anomalies) for d in self.detectors.values()
        )
        total_metrics = sum(len(d.metrics) for d in self.detectors.values())

        failure_probs = [d.estimate_failure_probability() for d in self.detectors.values()]
        avg_failure_prob = (
            statistics.mean(failure_probs) if failure_probs else 0
        )

        anomaly_types = {}
        for detector in self.detectors.values():
            for anomaly in detector.anomalies:
                atype = anomaly.get("type", "unknown")
                anomaly_types[atype] = anomaly_types.get(atype, 0) + 1

        return {
            "total_detectors": len(self.detectors),
            "total_metrics": total_metrics,
            "total_anomalies": total_anomalies,
            "average_failure_probability": avg_failure_prob,
            "anomaly_distribution": anomaly_types,
        }


def obter_anomaly_detector(trace_id: Optional[str] = None) -> AnomalyDetector:
    """Factory para obter instância do detector de anomalias."""
    return AnomalyDetector(trace_id=trace_id)
