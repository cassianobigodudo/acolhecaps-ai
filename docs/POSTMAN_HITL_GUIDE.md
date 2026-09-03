# Guia Postman: Como Testar HITL (Human-in-the-Loop)

Este guia mostra **exatamente** como testar o fluxo completo de triagem com HITL no Postman.

---

## 🎯 Visão Geral do Fluxo

```
1️⃣ POST /acolhimento (Enviar relato)
                ↓
2️⃣ Receber resposta com:
   - ficha_triagem (resultado IA)
   - requer_aprovacao_humana (true/false)
   - trace_id (para rastreabilidade)
                ↓
   Se requer_aprovacao_humana = true:
   3️⃣ POST /acolhimento/hitl (Aprovar ou Corrigir)
                ↓
   4️⃣ Receber resposta final com status_aprovacao
```

---

## 📝 PASSO 1: Fazer Triagem (POST /acolhimento)

### Request

**Método:** `POST`  
**URL:** `http://localhost:8000/acolhimento`

**Headers:**
```
Content-Type: application/json
```

### Caso 1: Prioridade BAIXA (sem HITL)

**Body:**
```json
{
  "id_paciente": "PAC-LOW-001",
  "relato": "Paciente Maria, 30 anos, relata ansiedade ocasional. Continua trabalhando normalmente, dorme bem, tem apoio da família. Sem sintomas graves.",
  "cep": "88015-100"
}
```

**Resposta (sem HITL):**
```json
{
  "status": "sucesso",
  "trace_id": "trace-2024-001-abc123",
  "ficha_triagem": {
    "nivel_prioridade": "Baixa",
    "fatores_risco": [],
    "encaminhamento_recomendado": "Psicólogo + Acompanhamento em grupo",
    "status_aprovacao": "pendente",
    "data_criacao": "2024-01-15T10:30:45",
    "oficinas_sugeridas": ["Oficina de Mindfulness", "Grupo de Suporte"],
    "requer_aprovacao_humana": false,
    "trace_id": "trace-2024-001-abc123"
  }
}
```

✅ **Sem HITL**: `requer_aprovacao_humana = false` → Fluxo termina aqui!

---

### Caso 2: Prioridade MÉDIA (com HITL)

**Body:**
```json
{
  "id_paciente": "PAC-MED-001",
  "relato": "Paciente João, 45 anos, apresenta perda de interesse em atividades há 2 meses. Dorme pouco, sem apetite, cansaço constante. Falta muito do trabalho (absenteísmo). Esposa preocupada. Nega ideação suicida. Já fez acompanhamento psicológico no passado, mas parou.",
  "cep": "88015-100"
}
```

**Resposta (COM HITL):**
```json
{
  "status": "sucesso",
  "trace_id": "trace-2024-002-def456",
  "ficha_triagem": {
    "nivel_prioridade": "Média",
    "fatores_risco": [
      "Depressão moderada",
      "Absenteísmo laboral",
      "Comprometimento funcional"
    ],
    "encaminhamento_recomendado": "Psicólogo + Grupo de Apoio para Depressão",
    "status_aprovacao": "pendente",
    "data_criacao": "2024-01-15T10:35:20",
    "oficinas_sugeridas": ["Grupo de Apoio", "Terapia Ocupacional"],
    "requer_aprovacao_humana": true,
    "trace_id": "trace-2024-002-def456"
  }
}
```

⚠️ **COM HITL**: `requer_aprovacao_humana = true` → **Você precisa aprovar ou corrigir!**

---

### Caso 3: Prioridade ALTA/CRÍTICA (com HITL obrigatório)

**Body:**
```json
{
  "id_paciente": "PAC-HIGH-001",
  "relato": "Paciente Carlos, 38 anos, chega ao acolhimento em crise aguda. Relata ideação suicida ativa COM PLANO DEFINIDO (medicação em casa). Perdeu emprego há 1 mês, separou-se da esposa, sem família disponível. Não tem apoio. Histórico de tentativa de suicídio aos 28 anos. Internação prévia aos 30 anos. Está desesperado, chorando, pedindo ajuda. URGÊNCIA MÁXIMA.",
  "cep": "88015-100"
}
```

**Resposta (COM HITL OBRIGATÓRIO):**
```json
{
  "status": "sucesso",
  "trace_id": "trace-2024-003-ghi789",
  "ficha_triagem": {
    "nivel_prioridade": "Crítica",
    "fatores_risco": [
      "Ideação suicida ativa com plano definido",
      "Ausência total de apoio familiar",
      "Histórico de tentativa anterior",
      "Desemprego recente",
      "Crise emocional aguda"
    ],
    "encaminhamento_recomendado": "Psiquiatra + Psicólogo (ATENDIMENTO EMERGENCIAL URGENTE)",
    "status_aprovacao": "pendente",
    "data_criacao": "2024-01-15T10:40:00",
    "oficinas_sugeridas": [],
    "requer_aprovacao_humana": true,
    "trace_id": "trace-2024-003-ghi789"
  }
}
```

🚨 **CRÍTICA**: `requer_aprovacao_humana = true` → **APROVAÇÃO URGENTE!**

---

## ✅ PASSO 2: Responder HITL - OPÇÃO 1 - APROVAR

Quando `requer_aprovacao_humana = true`, você pode **aprovar** a classificação da IA.

### Request

**Método:** `POST`  
**URL:** `http://localhost:8000/acolhimento/hitl`

**Headers:**
```
Content-Type: application/json
```

**Body - APROVAÇÃO:**
```json
{
  "trace_id": "trace-2024-002-def456",
  "status_aprovacao": "aprovado",
  "observacoes": "Classificação validada pelo profissional. Concordo com a análise da IA."
}
```

**Resposta:**
```json
{
  "status": "sucesso",
  "trace_id": "trace-2024-002-def456",
  "ficha_triagem": {
    "nivel_prioridade": "Média",
    "fatores_risco": [
      "Depressão moderada",
      "Absenteísmo laboral",
      "Comprometimento funcional"
    ],
    "encaminhamento_recomendado": "Psicólogo + Grupo de Apoio para Depressão",
    "status_aprovacao": "aprovado",
    "data_criacao": "2024-01-15T10:35:20",
    "data_aprovacao": "2024-01-15T10:36:00",
    "observacoes": "Classificação validada pelo profissional. Concordo com a análise da IA.",
    "requer_aprovacao_humana": false
  }
}
```

✅ **Status**: `aprovado`  
✅ **Fluxo**: Encerrado com sucesso

---

## 🔧 PASSO 2: Responder HITL - OPÇÃO 2 - CORRIGIR

Quando você **discorda** da IA, pode corrigir a classificação.

### Request - CORREÇÃO

**Método:** `POST`  
**URL:** `http://localhost:8000/acolhimento/hitl`

**Body - CORREÇÃO (Aumentar prioridade):**
```json
{
  "trace_id": "trace-2024-002-def456",
  "status_aprovacao": "corrigido",
  "nivel_prioridade_corrigido": "Alta",
  "observacoes": "IA subestimou o risco. Paciente com histórico de tentativa anterior + absenteísmo crescente. Necessário atendimento mais urgente com Psiquiatra.",
  "profissional_nome": "Dr. Silva",
  "profissional_profissao": "Psicólogo"
}
```

**Resposta:**
```json
{
  "status": "sucesso",
  "trace_id": "trace-2024-002-def456",
  "ficha_triagem": {
    "nivel_prioridade": "Alta",
    "fatores_risco": [
      "Depressão moderada com agravamento",
      "Absenteísmo laboral crescente",
      "Comprometimento funcional significativo",
      "Necessidade de urgência maior"
    ],
    "encaminhamento_recomendado": "Psiquiatra + Psicólogo (atendimento urgente)",
    "status_aprovacao": "corrigido",
    "data_criacao": "2024-01-15T10:35:20",
    "data_aprovacao": "2024-01-15T10:36:30",
    "observacoes": "IA subestimou o risco. Paciente com histórico de tentativa anterior + absenteísmo crescente. Necessário atendimento mais urgente com Psiquiatra.",
    "nivel_prioridade_original": "Média",
    "profissional_corretor": {
      "nome": "Dr. Silva",
      "profissao": "Psicólogo"
    },
    "requer_aprovacao_humana": false
  }
}
```

🔧 **Status**: `corrigido`  
🔧 **Prioridade**: Aumentada de Média → Alta  
🔧 **Fluxo**: Encerrado com ajuste

---

### Body - CORREÇÃO (Diminuir prioridade)

```json
{
  "trace_id": "trace-2024-003-ghi789",
  "status_aprovacao": "corrigido",
  "nivel_prioridade_corrigido": "Média",
  "observacoes": "Após conversa com o paciente e familia, conseguimos estruturar rede de apoio. Risco imediato reduzido. Acompanhamento pode ser em CAPS com intensidade intermediária.",
  "profissional_nome": "Dra. Rosa",
  "profissional_profissao": "Assistente Social"
}
```

⬇️ **Prioridade**: Reduzida de Crítica → Média (após estruturação de rede de apoio)

---

## 📋 Exemplos Postman - Passo a Passo

### Exemplo Completo: Caso MÉDIO com Aprovação

**Request 1 - Triagem:**
```
POST http://localhost:8000/acolhimento
Content-Type: application/json

{
  "id_paciente": "PAC-TEST-001",
  "relato": "Depressão há 2 meses, absenteísmo no trabalho, sem apoio familiar",
  "cep": "88015-100"
}
```

**Response 1:**
```json
{
  "status": "sucesso",
  "trace_id": "trace-test-001",
  "ficha_triagem": {
    "nivel_prioridade": "Média",
    "requer_aprovacao_humana": true,
    "status_aprovacao": "pendente"
  }
}
```

**Request 2 - HITL Aprovação:**
```
POST http://localhost:8000/acolhimento/hitl
Content-Type: application/json

{
  "trace_id": "trace-test-001",
  "status_aprovacao": "aprovado",
  "observacoes": "Classificação correta"
}
```

**Response 2:**
```json
{
  "status": "sucesso",
  "trace_id": "trace-test-001",
  "ficha_triagem": {
    "nivel_prioridade": "Média",
    "status_aprovacao": "aprovado",
    "requer_aprovacao_humana": false
  }
}
```

---

## 🚀 Coleção Postman (JSON)

Aqui está uma **coleção Postman pronta** que você pode importar:

```json
{
  "info": {
    "name": "AcolheCAPS HITL Tests",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "1. Triagem Baixa Prioridade",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\"id_paciente\": \"PAC-LOW-001\", \"relato\": \"Ansiedade leve, sem sintomas graves\", \"cep\": \"88015-100\"}"
        },
        "url": {
          "raw": "http://localhost:8000/acolhimento",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["acolhimento"]
        }
      }
    },
    {
      "name": "2. Triagem Média Prioridade (HITL)",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\"id_paciente\": \"PAC-MED-001\", \"relato\": \"Depressão há 2 meses, absenteísmo laboral\", \"cep\": \"88015-100\"}"
        },
        "url": {
          "raw": "http://localhost:8000/acolhimento",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["acolhimento"]
        }
      }
    },
    {
      "name": "3. HITL - Aprovar",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\"trace_id\": \"substitua-com-trace-id-real\", \"status_aprovacao\": \"aprovado\", \"observacoes\": \"Classificação validada\"}"
        },
        "url": {
          "raw": "http://localhost:8000/acolhimento/hitl",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["acolhimento", "hitl"]
        }
      }
    },
    {
      "name": "4. HITL - Corrigir",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\"trace_id\": \"substitua-com-trace-id-real\", \"status_aprovacao\": \"corrigido\", \"nivel_prioridade_corrigido\": \"Alta\", \"observacoes\": \"IA subestimou\", \"profissional_nome\": \"Dr. Silva\", \"profissional_profissao\": \"Psicólogo\"}"
        },
        "url": {
          "raw": "http://localhost:8000/acolhimento/hitl",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["acolhimento", "hitl"]
        }
      }
    }
  ]
}
```

Para importar no Postman:
1. Crie uma coleção nova
2. Vá em "Import" → Escolha "Raw Text"
3. Cole o JSON acima
4. Clique "Import"

---

## 🔄 Fluxo Completo (Visualizado)

```
PASSO 1: Triagem (id_paciente + relato + cep)
  ├─ Se Baixa → FIM (sem HITL)
  ├─ Se Média → HITL ATIVADO
  └─ Se Alta/Crítica → HITL OBRIGATÓRIO

PASSO 2: Se HITL ativado, você escolhe:
  ├─ APROVAR (profissional concorda com IA)
  │  └─ status_aprovacao = "aprovado"
  │  └─ FIM do fluxo
  │
  └─ CORRIGIR (profissional discorda da IA)
     ├─ Pode aumentar/diminuir prioridade
     ├─ Adiciona observações
     ├─ status_aprovacao = "corrigido"
     └─ FIM do fluxo com ajuste
```

---

## 💡 Dicas para Testar no Postman

### 1. Guardar trace_id em Variável

Na resposta da triagem, você recebe `trace_id`. Para não ficar copiando e colando:

1. Na aba "Tests" da sua requisição de triagem:
```javascript
var jsonData = pm.response.json();
pm.environment.set("trace_id", jsonData.trace_id);
```

2. Na requisição HITL, use `{{trace_id}}`:
```json
{
  "trace_id": "{{trace_id}}",
  "status_aprovacao": "aprovado"
}
```

### 2. Testar Todos os Cenários

| Cenário | Prioridade | HITL | Ação | Esperado |
|---------|-----------|------|------|----------|
| Ansiedade leve | Baixa | ❌ | Nada | Ficha criada |
| Depressão moderada | Média | ✅ | Aprovar | status=aprovado |
| Ideação suicida | Alta | ✅ | Corrigir | status=corrigido |
| Tentativa ativa | Crítica | ✅ | Aprovar | status=aprovado |

### 3. Verificar Logs

Enquanto testa, veja os logs do servidor:
```
[NODE_AVALIACAO_RISCO] Prioridade=Média, requer_approval=true
[NODE_HUMAN_IN_THE_LOOP] Aguardando validação...
[NODE_HUMAN_IN_THE_LOOP] ✅ Profissional APROVA
```

### 4. Exemplo com cURL (alternativa)

```bash
# Triagem
curl -X POST http://localhost:8000/acolhimento \
  -H "Content-Type: application/json" \
  -d '{
    "id_paciente": "PAC-001",
    "relato": "Depressão leve",
    "cep": "88015-100"
  }' | jq .

# Responder HITL
curl -X POST http://localhost:8000/acolhimento/hitl \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "trace-xxx",
    "status_aprovacao": "aprovado",
    "observacoes": "OK"
  }' | jq .
```

---

## 🎯 Resumo

| Ação | Endpoint | Quando | Resultado |
|------|----------|--------|-----------|
| **Triagem** | `POST /acolhimento` | Sempre | ficha_triagem + trace_id |
| **HITL Aprovar** | `POST /acolhimento/hitl` | Se Média+ | status=aprovado |
| **HITL Corrigir** | `POST /acolhimento/hitl` | Se Média+ | status=corrigido + nova prioridade |

---

**Pronto!** Agora você sabe exatamente como testar HITL no Postman. Qualquer dúvida, verifique os logs do servidor! 🚀
