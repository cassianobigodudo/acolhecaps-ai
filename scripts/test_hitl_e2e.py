"""
Teste E2E completo do HITL com alerta Discord.
Simula: Triagem → Aprovação → Alerta
"""

import requests
import json
from datetime import datetime
import time

BASE_URL = "http://localhost:8000"

print("=" * 80)
print("TESTE E2E: HITL COM ALERTA DISCORD")
print("=" * 80)

# ========== PASSO 1: Triagem ==========
print("\n[1️⃣ TRIAGEM] Enviando relatório...\n")

triagem_payload = {
    "id_paciente": "PAC-TEST-E2E-001",
    "relato": "Paciente apresenta perda de interesse em atividades há 2 meses. Dorme pouco, sem apetite, cansaço constante. Falta muito do trabalho. Esposa preocupada.",
    "cep": "88015-100"
}

try:
    response = requests.post(
        f"{BASE_URL}/acolhimento",
        json=triagem_payload,
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    triagem_result = response.json()
    print(json.dumps(triagem_result, indent=2, ensure_ascii=False))
    
    # Extrai trace_id
    trace_id = triagem_result.get("trace_id")
    ficha = triagem_result.get("ficha_triagem", {})
    requer_approval = triagem_result.get("requer_aprovacao_humana")
    
    print(f"\n✅ Triagem concluída!")
    print(f"   - Trace ID: {trace_id}")
    print(f"   - Prioridade: {ficha.get('nivel_prioridade')}")
    print(f"   - Requer HITL: {requer_approval}")
    
except Exception as e:
    print(f"❌ Erro na triagem: {str(e)}")
    exit(1)

# ========== PASSO 2: Aguardar e depois Aprovar ==========
if requer_approval:
    print("\n[2️⃣ HITL] Aguardando 3 segundos antes de aprovar...\n")
    time.sleep(3)
    
    print("[2️⃣ HITL] Enviando aprovação...\n")
    
    approval_payload = {
        "trace_id": trace_id,
        "status_aprovacao": "aprovado",
        "observacoes": "Classificação validada - teste E2E",
        "profissional_nome": "Dr. Teste E2E",
        "profissional_profissao": "Psicólogo"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/acolhimento/hitl",
            json=approval_payload,
            timeout=70  # 70 segundos para aguardar webhook
        )
        
        print(f"Status: {response.status_code}")
        approval_result = response.json()
        print(json.dumps(approval_result, indent=2, ensure_ascii=False))
        
        print(f"\n✅ Aprovação concluída!")
        print(f"   - Status: {approval_result.get('ficha_triagem', {}).get('status_aprovacao')}")
        
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout! (70s) - Webhook pode estar processando...")
    except Exception as e:
        print(f"❌ Erro na aprovação: {str(e)}")
        exit(1)
else:
    print("\n❌ Triagem não requer HITL (prioridade baixa)")

print("\n" + "=" * 80)
print("✅ TESTE CONCLUÍDO!")
print("Verifique o Discord para ver se o alerta foi enviado.")
print("=" * 80)
