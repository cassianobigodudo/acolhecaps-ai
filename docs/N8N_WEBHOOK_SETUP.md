# Configuração de Webhook n8n para Alertas de Pacientes com Risco Elevado

Este guia detalha como configurar um workflow no n8n para receber os alertas POST do AcolheCAPS AI e rotear para Discord.

## 📋 Pré-requisitos

- Conta no n8n (https://n8n.io ou instalação local)
- Token/Webhook URL do n8n
- Servidor Discord ou Webhook Discord configurado
- AlertService do AcolheCAPS configurado com o webhook_url do n8n

## 🔧 Passo 1: Criar um Webhook no n8n

1. Acesse sua instância n8n (cloud ou local)
2. Clique em **"New Workflow"** ou **"New"**
3. Procure por **"Webhook"** e adicione como trigger
4. Configure:
   - **HTTP Method**: POST
   - **Path**: `/acolhecaps-alerts` (ou o path que preferir)
   - **Ativar**: marque "Ativar automaticamente"
5. Clique em **"Copy URL"** para obter a URL do webhook
   - Exemplo: `https://n8n-instance.com/webhook/acolhecaps-alerts`
6. Esta é a URL que você usará no AlertService do Python (variável de ambiente `N8N_WEBHOOK_URL`)

## 📦 Passo 2: Entender o Payload Recebido

O AlertService envia um JSON estruturado assim:

```json
{
  "tipo_evento": "alerta_urgencia_paciente",
  "timestamp": "2024-01-15T10:30:45.123456+00:00",
  "trace_id": "trace-2024-001-xyz789",
  "paciente": {
    "id": "PAC-2024-001",
    "cep": "88015-100"
  },
  "risco": {
    "nivel": "Média",
    "severidade": 60,
    "fatores": ["Ansiedade moderada", "Stress ocupacional"]
  },
  "ficha_triagem": {
    "nivel_prioridade": "Média",
    "fatores_risco": ["Ansiedade moderada", "Stress ocupacional"],
    "oficinas_sugeridas": ["Grupo de Suporte", "Oficina de Resiliência"],
    "status_aprovacao": "pendente",
    "data_criacao": "2024-01-15T10:30:00"
  },
  "acao_requerida": "Revisar imediatamente e contatar paciente para atendimento urgente"
}
```

## 🎯 Passo 3: Construir o Workflow no n8n

Após adicionar o Webhook, construa o fluxo assim:

### 3.1 Webhook (Trigger)
- Já configurado no Passo 1

### 3.2 Adicionar nó "Set" (para transformar dados)
Clique no **"+"** e procure por **"Set"**

Configure assim:
```
Modo: Specify all values (one by one)

Nome do campo: message
Valor: `Alert de urgência: Paciente {{$json["paciente"]["id"]}} - Prioridade {{$json["risco"]["nivel"]}}`

Nome do campo: severity_color
Valor (usar IF):
`{{$json["risco"]["severidade"] > 80 ? "ff0000" : ($json["risco"]["severidade"] > 60 ? "ffa500" : "ffff00")}}`
Tradução:
- > 80: Vermelho (#ff0000)
- > 60: Laranja (#ffa500)
- ≤ 60: Amarelo (#ffff00)

Nome do campo: fatores_list
Valor: `{{$json["risco"]["fatores"].join(", ")}}`
```

### 3.3 Adicionar nó "Discord" (para enviar mensagem)
Clique no **"+"** e procure por **"Discord"**

Configure:
1. **Autenticação**:
   - Clique em "Create new credential"
   - Cole seu Discord **Bot Token** (veja Passo 4)
   - Nome: "Discord Bot Token"

2. **Configuração**:
   - **Operation**: Send Message
   - **Channel ID**: ID do canal Discord onde quer receber alertas
     - (Clique com botão direito no canal → "Copy channel ID")
   - **Message**: Deixe em branco por enquanto, vamos usar embeds

### 3.4 Adicionar "Embed" (para mensagem formatada no Discord)
Na seção **"Additional Fields"** do nó Discord:

```
Embeds (Array):
[
  {
    "title": "⚠️ ALERTA DE URGÊNCIA - PACIENTE COM RISCO ELEVADO",
    "description": "{{$json["acao_requerida"]}}",
    "color": "{{$json["severity_color"]}}",
    "fields": [
      {
        "name": "ID do Paciente",
        "value": "{{$json["paciente"]["id"]}}",
        "inline": true
      },
      {
        "name": "Nível de Risco",
        "value": "{{$json["risco"]["nivel"]}}",
        "inline": true
      },
      {
        "name": "Severidade",
        "value": "{{$json["risco"]["severidade"]}}/100",
        "inline": true
      },
      {
        "name": "CEP",
        "value": "{{$json["paciente"]["cep"]}}",
        "inline": true
      },
      {
        "name": "Fatores de Risco",
        "value": "{{$json["fatores_list"]}}",
        "inline": false
      },
      {
        "name": "Timestamp",
        "value": "{{$json["timestamp"]}}",
        "inline": false
      },
      {
        "name": "Trace ID",
        "value": "`{{$json["trace_id"]}}`",
        "inline": false
      }
    ],
    "footer": {
      "text": "AcolheCAPS AI - Sistema de Alertas de Urgência"
    }
  }
]
```

### 3.5 Adicionar nó "Log" (para debug)
Clique em **"+"** e procure por **"Log"**

Configure:
- **Modo**: JSON
- **Message**: Deixe vazio (vai logar todo o JSON recebido)

Isso ajuda a debugar se algo não está funcionando.

## 🔐 Passo 4: Configurar Discord Bot Token

### 4.1 Criar um Bot no Discord Developer Portal

1. Acesse https://discord.com/developers/applications
2. Clique em **"New Application"** e dê um nome (ex: "AcolheCAPS Alerts")
3. Vá na aba **"Bot"** e clique em **"Add Bot"**
4. Copie o **Token** (este é seu Bot Token)
   - **IMPORTANTE**: Nunca compartilhe este token! É como uma senha.
5. Na aba **"Permissions"**, marque:
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Read Message History

### 4.2 Adicionar o Bot ao seu Servidor Discord

1. Vá na aba **"OAuth2"** → **"URL Generator"**
2. Scopes: marca **"bot"**
3. Permissions: marca **"Send Messages"** e **"Embed Links"**
4. Copie a URL gerada e abra em uma nova aba
5. Selecione seu servidor Discord e autorize

### 4.3 Obter o Channel ID

1. No Discord, clique com botão direito no canal onde quer receber alertas
2. Selecione **"Copy Channel ID"**
3. Cole este ID na configuração do nó Discord no n8n

## 🧪 Passo 5: Testar o Workflow

### 5.1 Testar via n8n

1. Na interface do n8n, clique em **"Test workflow"**
2. O webhook URL aparecerá com um botão "Send test request"
3. Clique para enviar um POST de teste

### 5.2 Testar via Python (Local)

```python
import httpx
import asyncio

async def testar_webhook():
    webhook_url = "https://n8n-instance.com/webhook/acolhecaps-alerts"
    
    payload = {
        "tipo_evento": "alerta_urgencia_paciente",
        "timestamp": "2024-01-15T10:30:45.123456+00:00",
        "trace_id": "trace-test-manual",
        "paciente": {
            "id": "PAC-TEST-001",
            "cep": "88015-100"
        },
        "risco": {
            "nivel": "Alta",
            "severidade": 80,
            "fatores": ["Ideação suicida", "Crise aguda"]
        },
        "ficha_triagem": {
            "nivel_prioridade": "Alta",
            "fatores_risco": ["Ideação suicida", "Crise aguda"],
            "oficinas_sugeridas": [],
            "status_aprovacao": "pendente",
            "data_criacao": "2024-01-15T10:30:00"
        },
        "acao_requerida": "Revisar imediatamente"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(webhook_url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

asyncio.run(testar_webhook())
```

## 🚀 Passo 6: Integrar no AcolheCAPS

1. Defina a variável de ambiente no seu `.env`:
```env
N8N_WEBHOOK_URL=https://n8n-instance.com/webhook/acolhecaps-alerts
```

2. Configure o AlertService na inicialização da aplicação:
```python
from app.services.alert_service import obter_alert_service
import os

webhook_url = os.getenv("N8N_WEBHOOK_URL")
alert_service = obter_alert_service(webhook_url=webhook_url)
```

3. No `node_finalizacao` do grafo, chame:
```python
if alert_service:
    await alert_service.verificar_e_disparar_alerta(
        nivel_prioridade=ficha["nivel_prioridade"],
        ficha_triagem=ficha,
        entrada_acolhimento=entrada,
        trace_id=trace_id
    )
```

## 📊 Estrutura Completa do Workflow n8n

```
┌─────────────┐
│   Webhook   │ (POST /acolhecaps-alerts)
└──────┬──────┘
       │
       ▼
┌──────────────────────────────┐
│  Set (Formatar dados)        │
│  - message                   │
│  - severity_color            │
│  - fatores_list              │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Discord (Send Message)      │
│  - Bot Token                 │
│  - Channel ID                │
│  - Embed formatado           │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Log (Debug)                 │
│  - JSON completo             │
└──────────────────────────────┘
```

## 🔍 Troubleshooting

### Webhook não recebe POST
- Confirme que a URL no AlertService está correta
- Verifique se o webhook está "Ativar automaticamente" no n8n
- Verifique os logs do n8n

### Discord bot não envia mensagem
- Confirme que o Bot Token está correto
- Verifique que o bot está no servidor Discord
- Confirme que o Channel ID está correto
- Verifique permissões do bot no canal

### Severidade não mostra cor
- Confirme que o color_code é um número válido (ex: "ff0000")
- Discord aceita valores hex sem "#"

### Fatores de risco não aparecem
- Confirme que `fatores_list` está usando `.join(", ")`
- Se vazio, aparecerá como string vazia

## 📝 Alternativas

### Slack
No lugar do Discord, use o nó **"Slack"** com configuração similar.

### Email
Use nó **"Send Email"** para alertas por email também.

### Multiple Channels
Adicione múltiplos nós Discord para enviar para canais diferentes baseado na severidade:
```
if severidade > 80 → #alertas-criticos
if severidade > 60 → #alertas-urgentes
if severidade > 30 → #alertas-normais
```

## 🎬 Próximos Passos

1. ✅ Configurar webhook n8n
2. ✅ Configurar Discord bot
3. ✅ Criar workflow completo
4. ✅ Testar com POST manual
5. ✅ Integrar no AcolheCAPS (node_finalizacao)
6. ✅ Testar fluxo E2E: Acolhimento → Python → n8n → Discord
7. ✅ Monitorar em produção

---

**Pronto!** Com isso, você terá alertas automáticos no Discord toda vez que um paciente com risco Média, Alta ou Crítica for processado.
