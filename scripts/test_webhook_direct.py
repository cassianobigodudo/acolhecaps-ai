"""
Script para testar webhook n8n diretamente com requests.
"""

import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

webhook_url = os.getenv("N8N_WEBHOOK_URL")
print(f"[TEST] Webhook URL: {webhook_url}\n")

if not webhook_url:
    print("[TEST] ❌ N8N_WEBHOOK_URL não configurado!")
    exit(1)

# Cria payload de teste
payload = {
    "tipo": "hitl_decision_test",
    "mensagem": """
✅ DECISÃO HITL REGISTRADA - TESTE

Status: APROVADO
Prioridade: ⚠️ Média
Encaminhamento: Psicólogo + Grupo de Apoio

Profissional:
├─ Nome: Dr. Teste
└─ Profissão: Psicólogo

Observações: Classificação validada pelo profissional

Trace ID: `trace-test-webhook-001`
Data: 2024-01-15T10:36:00
    """.strip(),
    "trace_id": "trace-test-webhook-001",
    "timestamp": datetime.now().isoformat(),
}

print("[TEST] Enviando payload:")
print(json.dumps(payload, indent=2))
print("\n" + "="*60)

try:
    print(f"[TEST] POST para {webhook_url}")
    response = requests.post(
        webhook_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    
    print(f"[TEST] Status Code: {response.status_code}")
    print(f"[TEST] Response: {response.text[:500]}")
    
    if response.status_code in [200, 201, 202]:
        print("[TEST] ✅ Webhook enviado com sucesso!")
    else:
        print(f"[TEST] ⚠️ Webhook retornou status {response.status_code}")
        
except requests.exceptions.Timeout:
    print("[TEST] ❌ Timeout (10s)")
except requests.exceptions.ConnectionError as e:
    print(f"[TEST] ❌ Erro de conexão: {str(e)}")
except Exception as e:
    print(f"[TEST] ❌ Erro: {str(e)}")

print("="*60)
