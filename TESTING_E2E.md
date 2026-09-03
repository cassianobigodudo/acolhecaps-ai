# Teste E2E: Servidor + AlertService + n8n + Discord

Guia para testar o fluxo completo de ponta a ponta.

## 📋 Pré-requisitos

✅ Python 3.10+  
✅ Dependências instaladas (`pip install -r requirements.txt`)  
✅ Variáveis de ambiente configuradas (`.env`)  
✅ n8n webhook configurado e rodando (`docs/N8N_WEBHOOK_SETUP.md`)  
✅ Discord bot configurado e webhook pronto  

## 🚀 Passo 1: Iniciar o Servidor FastAPI

```bash
python main.py
```

Você verá:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
[MAIN] Iniciando AcolheCAPS AI Server
[MAIN] AlertService inicializado com webhook: https://cassibigodudo.app.n8n.cloud/webhook/acolhecaps-alerts
[MAIN] Servidor pronto para aceitar requisições
```

✅ Servidor rodando e AlertService conectado ao n8n

## 🧪 Passo 2: Rodar Testes E2E em Outra Aba

Abra um novo terminal:

```bash
python scripts/test_e2e_alert.py
```

O script vai:

1. **Verificar saúde do servidor** (GET /health)
2. **Testar 3 casos de acolhimento:**
   - Caso 1: Baixa Prioridade → SEM alerta
   - Caso 2: Média Prioridade → COM alerta
   - Caso 3: Alta Prioridade → COM alerta + HITL
3. **Gerar resumo com resultados**

Saída esperada:

```
╔════════════════════════════════════════════════════════════════════╗
║  AcolheCAPS AI - Teste E2E: AlertService + n8n + Discord          ║
╚════════════════════════════════════════════════════════════════════╝

📡 Verificando saúde do servidor...
✅ Servidor pronto!
   Status: ok
   Alert Service: conectado

========================================================================
🧪 Caso 1: Baixa Prioridade (SEM alerta)
========================================================================

📋 Entrada:
   ID Paciente: PAC-TEST-001
   CEP: 88015-100
   Relato: Paciente relata sentimentos leves de ansiedade, sem história de crises.

📤 Fazendo POST /acolhimento...
   Status Code: 200
   Tempo de Processamento: 2.34s

📊 Resultado:
   Trace ID: trace-20240115102034-a7b8c9d0
   Nível de Prioridade: Baixa
   Fatores de Risco: Ansiedade leve
   Oficinas Sugeridas: Oficina de Mindfulness
   Status: concluido

✅ Comportamento esperado:
   ✓ Sem alerta (prioridade=Baixa não requer)

...

📋 RESUMO DOS TESTES
========================================================================

Testes Executados: 3
Sucessos: 3/3
Alertas Disparados: 2

📊 Detalhes:
   1. ✗ Sem alerta | Prioridade: Baixa | Tempo: 2.34s
   2. ✓ Alerta | Prioridade: Média | Tempo: 2.45s
   3. ✓ Alerta | Prioridade: Alta | Tempo: 2.56s

✅ Verificação:
   • Todos os testes foram executados
   • Verifique no n8n se os webhooks foram recebidos
   • Verifique no Discord se os alertas chegaram para Média/Alta/Crítica
```

## 🔍 Passo 3: Verificar Webhook no n8n

1. Acesse seu dashboard n8n
2. Abra o workflow de alertas
3. Procure pela aba **"Logs"** ou **"Debug"**
4. Você deve ver:
   - Webhook recebido (POST) para Caso 2 e Caso 3
   - 2 POSTs no total (Média e Alta)
   - Payload com dados do paciente, risco, etc.

**N8N Logs esperados:**

```
[Webhook] POST /acolhecaps-alerts
  Timestamp: 2024-01-15T10:20:34.123Z
  Body: {
    "tipo_evento": "alerta_urgencia_paciente",
    "trace_id": "trace-20240115102034-a7b8c9d0",
    "paciente": {
      "id": "PAC-TEST-002",
      "cep": "88015-100"
    },
    "risco": {
      "nivel": "Média",
      "severidade": 60,
      "fatores": ["Ansiedade moderada", ...]
    }
  }

[Discord] Enviando embed para canal
  Title: ⚠️ ALERTA DE URGÊNCIA - PACIENTE COM RISCO ELEVADO
  Color: ffa500 (Laranja)
  Severity: 60/100
```

## 💬 Passo 4: Verificar Mensagens no Discord

1. Abra seu servidor Discord
2. Vá para o canal configurado (ex: #alertas-urgentes)
3. Você deve ver:

**Mensagem 1 (Caso 2 - Média):**
```
⚠️ ALERTA DE URGÊNCIA - PACIENTE COM RISCO ELEVADO

Revisar imediatamente e contatar paciente para atendimento urgente

ID do Paciente: PAC-TEST-002
Nível de Risco: Média
Severidade: 60/100
CEP: 88015-100
Fatores de Risco: Ansiedade moderada, Stress ocupacional
Timestamp: 2024-01-15T10:20:34.123456+00:00
Trace ID: trace-20240115102034-a7b8c9d0

AcolheCAPS AI - Sistema de Alertas de Urgência
```

**Mensagem 2 (Caso 3 - Alta):**
```
🚨 ALERTA DE URGÊNCIA - PACIENTE COM RISCO ELEVADO  [Cor Laranja/Vermelho]
...
Nível de Risco: Alta
Severidade: 80/100
...
```

## ⚙️ Fluxo Completo (O que Acontece)

```
1. Cliente HTTP
   └─ POST /acolhimento { id_paciente, relato, cep }

2. Servidor FastAPI (main.py)
   └─ Recebe e valida entrada

3. LangGraph (graph_service.py)
   ├─ node_extracao
   ├─ node_rag_diretrizes + node_mcp_territorio (paralelo)
   ├─ node_avaliacao_risco → determina prioridade
   ├─ rota_condicional_prioridade
   │  └─ Se Média/Alta → node_human_in_the_loop (HITL)
   │  └─ Se Baixa → node_finalizacao
   └─ node_finalizacao
      ├─ Finaliza ficha de triagem
      ├─ Se nível em [Média, Alta, Crítica]:
      │  └─ Dispara AlertService em thread separada
      │     └─ POST para n8n webhook (assíncrono)
      └─ Retorna resultado

4. n8n Webhook
   ├─ Recebe POST do Python
   ├─ Set: formata dados (cor, fatores)
   └─ Discord: envia embed formatado

5. Discord
   └─ Equipe vê alerta em tempo real
```

## 🐛 Troubleshooting

### ❌ "Conexão recusada" ao rodar teste

**Problema:** Servidor não está rodando

**Solução:**
```bash
# Terminal 1
python main.py

# Terminal 2 (em paralelo)
python scripts/test_e2e_alert.py
```

### ❌ "AlertService: desabilitado"

**Problema:** `N8N_WEBHOOK_URL` não configurada no `.env`

**Solução:**
```bash
# Adicione ao .env
N8N_WEBHOOK_URL=https://seu-n8n.com/webhook/acolhecaps-alerts
```

### ❌ Webhook não chega no n8n

**Problema:** URL incorreta ou n8n não pronto

**Verificações:**
1. Confirme URL no `.env` (clique "Copy URL" no n8n)
2. Teste ping para URL: `curl https://seu-n8n.com/webhook/acolhecaps-alerts`
3. Verifique se webhook está "Ativar automaticamente" no n8n

### ❌ Alerta não aparece no Discord

**Problema:** Bot sem permissões ou channel ID incorreto

**Verificações:**
1. Confirme que bot está no servidor Discord
2. Verifique permissões do bot no canal (Send Messages, Embed Links)
3. Confirme Channel ID no workflow n8n
4. Verifique logs no n8n para erros no Discord node

### ❌ Timeout (requisição demorou muito)

**Problema:** Grafo levando muito tempo

**Info:** Primeiro acolhimento pode levar 3-5s (cold start do LLM). Subsequentes são mais rápidos.

## 📊 Monitorar em Tempo Real

**Terminal 1 - Logs do Servidor:**
```bash
# Veja logs estruturados com trace_id
python main.py
```

**Terminal 2 - Logs do n8n:**
```
Abra https://seu-n8n.com e monitore a aba Logs do workflow
```

**Terminal 3 - Testes:**
```bash
python scripts/test_e2e_alert.py
```

## ✅ Checklist Final

- [ ] Servidor rodando (`main.py`)
- [ ] N8N webhook pronto e URL no `.env`
- [ ] Discord bot adicionado ao servidor
- [ ] Script teste executado com sucesso
- [ ] 3 casos processados (1 sem alerta, 2 com alerta)
- [ ] Webhooks vistos no n8n logs
- [ ] 2 mensagens no Discord (Média e Alta)
- [ ] Trace IDs correlacionados entre sistemas

## 🎉 Pronto!

Card 10 está 100% funcional! Você tem:

✅ AlertService disparando webhooks  
✅ n8n recebendo e formatando  
✅ Discord exibindo alertas  
✅ Trace IDs para rastreabilidade  
✅ HITL funcionando (Média/Alta requerem aprovação)  

Próximo: Card 11 - README.md completo + vídeo demonstrativo

---

**Dúvidas?** Verifique `/docs/N8N_WEBHOOK_SETUP.md` para config detalhada do n8n.
