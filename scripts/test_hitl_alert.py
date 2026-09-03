"""
Script para testar se o webhook HITL está funcionando corretamente.

Simula uma aprovação/correção de HITL e verifica se o alerta é disparado.
"""

import asyncio
import json
from app.services.alert_service import obter_alert_service
from app.services.hitl_manager import obter_hitl_manager
import os
from dotenv import load_dotenv

load_dotenv()

async def test_hitl_alert():
    """Testa o disparo de alerta HITL."""
    
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    print(f"[TEST] Webhook URL: {webhook_url}")
    
    if not webhook_url:
        print("[TEST] ❌ N8N_WEBHOOK_URL não configurado!")
        return
    
    # Inicializa serviços
    alert_service = obter_alert_service(webhook_url=webhook_url)
    hitl_manager = obter_hitl_manager()
    
    # Cria ficha de teste
    trace_id = "trace-test-001"
    ficha_teste = {
        "status_aprovacao": "aprovado",
        "nivel_prioridade": "Média",
        "nivel_prioridade_original": "Média",
        "encaminhamento_recomendado": "Psicólogo + Grupo de Apoio",
        "fatores_risco": ["Ansiedade leve"],
        "data_criacao": "2024-01-15T10:30:00",
        "data_aprovacao": "2024-01-15T10:36:00",
        "observacoes": "Teste de alerta HITL",
        "profissional_aprovador": {
            "nome": "Dr. Teste",
            "profissao": "Psicólogo"
        }
    }
    
    # Gera mensagem
    print("\n[TEST] Gerando mensagem Discord...")
    mensagem = hitl_manager.gerar_mensagem_discord(
        trace_id=trace_id,
        ficha=ficha_teste,
    )
    print(f"[TEST] Mensagem gerada:\n{mensagem}")
    
    # Testa envio direto
    print("\n[TEST] Testando envio direto do webhook...")
    payload = {
        "tipo": "hitl_decision",
        "mensagem": mensagem,
        "trace_id": trace_id,
        "timestamp": "2024-01-15T10:36:00",
    }
    
    print(f"[TEST] Payload:\n{json.dumps(payload, indent=2)}")
    
    resultado = await alert_service.enviar_webhook_direto(payload)
    
    if resultado:
        print("[TEST] ✅ Webhook disparado com sucesso!")
    else:
        print("[TEST] ❌ Falha ao disparar webhook!")
    
    await alert_service.fechar()

if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DE ALERTA HITL")
    print("=" * 60)
    asyncio.run(test_hitl_alert())
    print("=" * 60)
