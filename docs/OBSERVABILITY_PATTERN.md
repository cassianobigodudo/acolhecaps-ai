# Padrão de Observabilidade - Card 6

**Data:** 2026-09-02  
**Card:** Card 6 - Observabilidade e Logs Estruturados Correlacionados  
**Status:** ✅ CONCLUÍDO

---

## 1. Visão Geral

O sistema AcolheCAPS implementa observabilidade completa através de:

1. **Logs Estruturados em JSON** - Todos os eventos emitidos como JSON estruturado
2. **trace_id Correlacionado** - Cada requisição recebe um ID único que permite rastrear todas as operações
3. **Métricas de Latência** - Captura de duração em cada operação
4. **Arquivo JSONL Centralizado** - Todos os logs correlacionados em arquivo único para análise

---

## 2. Arquitetura de Observabilidade

```
┌─────────────────────────────────────────────────┐
│  Requisição de Acolhimento (trace-123)          │
└────────────┬────────────────────────────────────┘
             │
             ├─── [EVENTO] node_extracao (iniciado)
             │    └─ trace_id: trace-123
             │    └─ timestamp: 2026-09-02T10:30:00.123Z
             │    └─ duration_ms: 45.2
             │
             ├─── [EVENTO] node_rag_diretrizes (consulta_realizada)
             │    └─ trace_id: trace-123
             │    └─ documentos: 3
             │    └─ duration_ms: 156.3
             │
             ├─── [EVENTO] node_mcp_territorio (validacao_territorial)
             │    └─ trace_id: trace-123
             │    └─ valido: true
             │    └─ duration_ms: 89.2
             │
             ├─── [EVENTO] node_avaliacao_risco (risco_avaliado)
             │    └─ trace_id: trace-123
             │    └─ prioridade: "Média"
             │    └─ duration_ms: 312.5
             │
             ├─── [EVENTO] node_human_in_the_loop (aprovacao_obtida)
             │    └─ trace_id: trace-123
             │    └─ status: "aprovado"
             │    └─ duration_ms: 50.0
             │
             └─── [EVENTO] node_finalizacao (fluxo_finalizado)
                  └─ trace_id: trace-123
                  └─ status: "concluido"
                  └─ total_duration: 653.2 ms
```

---

## 3. Exemplo de Log Estruturado

### 3.1 Evento Individual (JSON)

```json
{
  "timestamp": "2026-09-02T10:30:00.123Z",
  "level": "INFO",
  "logger": "RequestContext[trace-2026-0902-103000-abc123]",
  "message": "[EVENT] node_extracao: iniciado",
  "trace_id": "trace-2026-0902-103000-abc123",
  "metadata": {
    "node": "node_extracao",
    "action": "iniciado",
    "timestamp": "2026-09-02T10:30:00.123Z",
    "elapsed_ms": 2.5
  }
}
```

### 3.2 Arquivo JSONL Completo (exemplo)

```
{"timestamp":"2026-09-02T10:30:00.100Z","level":"INFO","logger":"RequestContext[trace-123]","message":"[EVENT] node_extracao: iniciado","trace_id":"trace-123","metadata":{"node":"node_extracao","action":"iniciado","elapsed_ms":2.5}}

{"timestamp":"2026-09-02T10:30:00.150Z","level":"INFO","logger":"RequestContext[trace-123]","message":"[METRIC] relato_tamanho","trace_id":"trace-123","metadata":{"metric":"relato_tamanho","value":245,"unit":"chars"}}

{"timestamp":"2026-09-02T10:30:00.200Z","level":"INFO","logger":"RequestContext[trace-123]","message":"[EVENT] node_extracao: concluido","trace_id":"trace-123","metadata":{"node":"node_extracao","action":"concluido","elapsed_ms":100}}

{"timestamp":"2026-09-02T10:30:00.300Z","level":"INFO","logger":"RequestContext[trace-123]","message":"[EVENT] node_rag_diretrizes: iniciado","trace_id":"trace-123","metadata":{"node":"node_rag_diretrizes","action":"iniciado","elapsed_ms":300}}

{"timestamp":"2026-09-02T10:30:00.450Z","level":"INFO","logger":"RequestContext[trace-123]","message":"[METRIC] rag_latencia","trace_id":"trace-123","metadata":{"metric":"rag_latencia","value":156.3,"unit":"ms"}}

{"timestamp":"2026-09-02T10:30:00.500Z","level":"INFO","logger":"RequestContext[trace-123]","message":"[EVENT] node_rag_diretrizes: concluido","trace_id":"trace-123","metadata":{"node":"node_rag_diretrizes","action":"concluido","elapsed_ms":156,"metadata":{"docs":3}}}

{"timestamp":"2026-09-02T10:30:00.950Z","level":"INFO","logger":"ObservabilityAggregator","message":"Request completed","trace_id":"trace-123","metadata":{"type":"request_complete","timestamp":"2026-09-02T10:30:00.950Z","trace_id":"trace-123","duration_ms":850.0,"events_count":12,"summary":{"start_node":"node_extracao","end_node":"node_finalizacao","total_events":12}}}
```

---

## 4. Como Usar

### 4.1 Criar um Contexto de Requisição

```python
from app.services.observability import RequestContext, trace_context

# Gerar trace_id único
trace_id = f"trace-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"

# Criar contexto
ctx = RequestContext(trace_id)

# Usar context manager para propagar trace_id
with trace_context(trace_id):
    # Aqui, get_current_trace_id() retorna trace_id
    ctx.log_event("node_1", "acao_iniciada")
    ctx.log_metric("latencia_operacao", 123.5, "ms")
    ctx.log_event("node_1", "acao_concluida")

# Registrar no agregador
aggregator.record_request(ctx)
```

### 4.2 Integração no Grafo (LangGraph)

```python
from app.services.observability import RequestContext, trace_context

def node_extracao(state: AcolhimentoState, ctx: RequestContext) -> AcolhimentoState:
    """Node com observabilidade."""
    
    with trace_context(ctx.trace_id):
        ctx.log_event("node_extracao", "iniciado")
        
        try:
            # Processamento
            resultado = processar_relato(state["entrada"]["relato"])
            
            ctx.log_event("node_extracao", "concluido", {"resultado": resultado})
            
        except Exception as e:
            ctx.log_event("node_extracao", "erro", {"erro": str(e)})
            raise
    
    return state
```

### 4.3 Analisar Logs

```python
from app.services.observability import ObservabilityLogAggregator

aggregator = ObservabilityLogAggregator("logs/observability.jsonl")

# Buscar estatísticas de uma requisição
stats = aggregator.get_latency_stats("trace-123")

if stats["found"]:
    print(f"Trace: {stats['trace_id']}")
    print(f"Duração Total: {stats['total_duration_ms']} ms")
    print(f"Número de Eventos: {len(stats['events'])}")
    
    # Analisar cada evento
    for event in stats['events']:
        print(f"  - {event['node']}: {event['action']} ({event.get('elapsed_ms', 0):.1f}ms)")
```

---

## 5. Estrutura de Dados

### 5.1 RequestContext

```python
class RequestContext:
    trace_id: str                          # ID único da requisição
    start_time: float                      # Timestamp de início
    events: List[Dict]                     # Lista de eventos correlacionados
    logger: logging.Logger                 # Logger estruturado
    
    def log_event(node: str, action: str, metadata: Optional[Dict])
    def log_metric(metric_name: str, value: float, unit: str)
    def get_duration_ms() -> float
    def to_dict() -> Dict
```

### 5.2 Estrutura de Evento

```python
{
    "node": "node_extracao",                # Nome do nó
    "action": "iniciado",                   # Ação realizada
    "timestamp": "2026-09-02T10:30:00Z",   # Timestamp ISO 8601
    "elapsed_ms": 45.2,                     # Tempo decorrido desde início
    "metadata": {                           # Dados customizados
        "prioridade": "Alta",
        "documentos": 3,
        "valido": true
    }
}
```

### 5.3 Log Entry (JSONL)

```python
{
    "timestamp": "2026-09-02T10:30:00.123Z",     # Timestamp do log
    "level": "INFO",                             # Nível (INFO, ERROR, etc)
    "logger": "RequestContext[trace-123]",       # Logger que emitiu
    "message": "[EVENT] node_extracao: iniciado", # Mensagem legível
    "trace_id": "trace-123",                     # trace_id para correlação
    "duration_ms": 45.2,                         # Duração (se métrica)
    "metadata": { ... }                          # Dados adicionais
}
```

---

## 6. Padrão de Latência

Cada operação captura:

```
[OPERAÇÃO INICIADA]
    timestamp = T0
    ↓
[OPERAÇÃO EM PROGRESSO]
    ↓
[OPERAÇÃO FINALIZADA]
    timestamp = T1
    elapsed_ms = (T1 - T0) * 1000
    → Registra em log com duration_ms
```

---

## 7. Correlação de trace_id

### 7.1 Propagação Manual

```python
# Criar contexto
with trace_context(trace_id):
    # Todos os logs emitidos aqui terão trace_id propagado
    logger.info("Evento 1")  # trace_id = trace_id
    logger.info("Evento 2")  # trace_id = trace_id
```

### 7.2 Propagação em Chamadas Assíncronas

```python
# RequestContext propaga automaticamente
ctx = RequestContext(trace_id)

# Ao chamar operações assíncronas
resultado = await node_rag_diretrizes(state)  # ctx.trace_id propaga
resultado = await node_mcp_territorio(state)  # ctx.trace_id propaga
```

---

## 8. Análise de Logs

### 8.1 Comando para Listar Requisições

```bash
# Ver todas as requisições no arquivo
cat logs/observability.jsonl | grep '"type":"request_complete"' | jq .
```

### 8.2 Comando para Filtrar por trace_id

```bash
# Listar todos os eventos de uma requisição
cat logs/observability.jsonl | grep '"trace_id":"trace-123"' | jq .
```

### 8.3 Análise de Latência

```bash
# Extrair latências por nó
cat logs/observability.jsonl | grep '"metric"' | jq '.metadata | {metric: .metric, value: .value, unit: .unit}'
```

---

## 9. Boas Práticas

### ✅ Fazer

- ✅ Usar `trace_context()` para propagar trace_id
- ✅ Registrar eventos em cada transição de nó
- ✅ Capturar métricas de latência críticas
- ✅ Incluir metadata relevante em eventos
- ✅ Usar timestamps ISO 8601

### ❌ Não Fazer

- ❌ Não incluir PII em logs
- ❌ Não omitir trace_id em eventos
- ❌ Não misturar formatos (JSON + plaintext)
- ❌ Não deixar traces desconexas (sempre correlacionar)

---

## 10. Arquivos Gerados

```
logs/
├── application.jsonl      # Logs gerais da aplicação
└── observability.jsonl    # Logs de observabilidade (requisições completas)
```

---

## 11. Testes Implementados

| Teste | Propósito |
|-------|-----------|
| `test_trace_context_manager` | Verifica gerenciamento de trace_id |
| `test_request_context_initialization` | Inicialização de contexto |
| `test_log_event` | Registro de eventos |
| `test_log_metric` | Registro de métricas |
| `test_request_duration` | Cálculo de duração |
| `test_complete_request_trace` | Fluxo end-to-end completo |
| `test_multiple_requests_correlation` | Múltiplas requisições correlacionadas |
| `test_latency_metrics_captured` | Captura de latências |
| `test_json_format_compliance` | Conformidade com JSON estruturado |

---

## 12. Próximas Melhorias

### Curto Prazo
- Integrar observabilidade no grafo_service.py
- Testar com requisições reais
- Validar performance com alta carga

### Médio Prazo
- Dashboard de observabilidade (Grafana)
- Alertas baseados em latência
- Análise de anomalias

### Longo Prazo
- Tracing distribuído (OpenTelemetry)
- Correlação com métricas de sistema
- Machine learning para detecção de problemas

---

**Status:** ✅ Card 6 Concluído  
**Próximo:** Card 7 (Code Review e Testes com IA) ou Card 11 (Documentação Final + Vídeo)

