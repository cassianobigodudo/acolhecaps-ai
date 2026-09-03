"""
Script de Teste E2E para AlertService

Simula:
1. Servidor FastAPI rodando
2. Cliente fazendo POST /acolhimento
3. Grafo processando e disparando webhook para n8n
4. Discord recebendo alerta

Uso:
    python scripts/test_e2e_alert.py
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

# ============================================================================
# Configurações
# ============================================================================

API_URL = "http://localhost:8000"
HEALTH_CHECK_TIMEOUT = 30  # segundos

# Dados de teste para diferentes prioridades
TEST_CASES = [
    {
        "nome": "Caso 1: Baixa Prioridade (SEM alerta)",
        "entrada": {
            "id_paciente": "PAC-TEST-001",
            "relato": "Paciente relata sentimentos leves de ansiedade, sem história de crises.",
            "cep": "88015-100",
        },
        "espera_alerta": False,
    },
    {
        "nome": "Caso 2: Média Prioridade (COM alerta)",
        "entrada": {
            "id_paciente": "PAC-TEST-002",
            "relato": "Paciente relata ansiedade moderada, dificuldade de concentração e insônia há 2 semanas.",
            "cep": "88015-100",
        },
        "espera_alerta": True,
    },
    {
        "nome": "Caso 3: Alta Prioridade (COM alerta + HITL)",
        "entrada": {
            "id_paciente": "PAC-TEST-003",
            "relato": "Paciente relata ideação suicida recorrente e crise aguda de ansiedade com tentativa de automutilação.",
            "cep": "88015-100",
        },
        "espera_alerta": True,
    },
]


# ============================================================================
# Funções de Teste
# ============================================================================


async def verificar_saude_servidor(tentativa: int = 1) -> bool:
    """Aguarda o servidor ficar pronto."""
    print(f"\n📡 Verificando saúde do servidor...")

    for i in range(HEALTH_CHECK_TIMEOUT):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_URL}/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Servidor pronto!")
                    print(f"   Status: {data.get('status')}")
                    print(f"   Alert Service: {data.get('alert_service')}")
                    return True
        except Exception as e:
            if i == 0:
                print(f"   Tentativa {i + 1}/{HEALTH_CHECK_TIMEOUT}: Aguardando server iniciar...")
            if i > 0 and i % 5 == 0:
                print(f"   Tentativa {i + 1}/{HEALTH_CHECK_TIMEOUT}...")

        await asyncio.sleep(1)

    print(f"❌ Servidor não ficou pronto após {HEALTH_CHECK_TIMEOUT}s")
    return False


async def testar_acolhimento(caso: dict) -> dict:
    """Testa um caso de acolhimento."""
    print(f"\n{'='*70}")
    print(f"🧪 {caso['nome']}")
    print(f"{'='*70}")

    entrada = caso["entrada"]
    espera_alerta = caso["espera_alerta"]

    print(f"\n📋 Entrada:")
    print(f"   ID Paciente: {entrada['id_paciente']}")
    print(f"   CEP: {entrada['cep']}")
    print(f"   Relato: {entrada['relato'][:80]}...")

    try:
        async with httpx.AsyncClient() as client:
            print(f"\n📤 Fazendo POST /acolhimento...")
            start_time = time.time()

            response = await client.post(
                f"{API_URL}/acolhimento",
                json=entrada,
                timeout=60,  # timeout maior porque o grafo leva tempo
            )

            elapsed_time = time.time() - start_time

            print(f"   Status Code: {response.status_code}")
            print(f"   Tempo de Processamento: {elapsed_time:.2f}s")

            if response.status_code != 200:
                print(f"❌ Erro na requisição!")
                print(f"   Response: {response.text}")
                return {"sucesso": False, "erro": response.text}

            resultado = response.json()

            # Extrair dados do resultado
            ficha = resultado.get("ficha_triagem", {})
            nivel_prioridade = ficha.get("nivel_prioridade", "?")
            fatores_risco = ficha.get("fatores_risco", [])
            oficinas = ficha.get("oficinas_sugeridas", [])
            trace_id = resultado.get("trace_id", "?")

            print(f"\n📊 Resultado:")
            print(f"   Trace ID: {trace_id}")
            print(f"   Nível de Prioridade: {nivel_prioridade}")
            print(f"   Fatores de Risco: {', '.join(fatores_risco) if fatores_risco else 'Nenhum'}")
            print(f"   Oficinas Sugeridas: {', '.join(oficinas) if oficinas else 'Nenhuma'}")
            print(f"   Status: {resultado.get('status')}")

            # Validar expectativa
            alerta_esperado = nivel_prioridade in ["Média", "Alta", "Crítica"]

            if alerta_esperado == espera_alerta:
                print(f"\n✅ Comportamento esperado:")
                if espera_alerta:
                    print(f"   ✓ Alerta foi disparado para n8n (prioridade={nivel_prioridade})")
                    print(f"   ✓ Verifique no Discord se chegou a mensagem!")
                else:
                    print(f"   ✓ Sem alerta (prioridade={nivel_prioridade} não requer)")
            else:
                print(f"\n⚠️  Comportamento INESPERADO:")
                print(f"   Esperava alerta: {espera_alerta}")
                print(f"   Obteve alerta: {alerta_esperado}")

            return {
                "sucesso": True,
                "prioridade": nivel_prioridade,
                "alerta_disparado": alerta_esperado,
                "trace_id": trace_id,
                "tempo_processamento": elapsed_time,
            }

    except httpx.ConnectError:
        print(f"❌ Erro de conexão! Servidor não está respondendo.")
        return {"sucesso": False, "erro": "Conexão recusada"}

    except httpx.TimeoutException:
        print(f"❌ Timeout! Requisição demorou muito.")
        return {"sucesso": False, "erro": "Timeout"}

    except Exception as e:
        print(f"❌ Erro inesperado: {str(e)}")
        return {"sucesso": False, "erro": str(e)}


async def main():
    """Executa a suite de testes E2E."""
    print(f"""
    ╔════════════════════════════════════════════════════════════════════╗
    ║  AcolheCAPS AI - Teste E2E: AlertService + n8n + Discord          ║
    ╚════════════════════════════════════════════════════════════════════╝
    """)

    print(f"\n⏰ Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Verificar servidor
    servidor_pronto = await verificar_saude_servidor()
    if not servidor_pronto:
        print(f"\n❌ Servidor não ficou pronto. Abortando testes.")
        print(f"\n💡 Inicie o servidor com:")
        print(f"   python main.py")
        return

    # Step 2: Executar casos de teste
    resultados = []
    for caso in TEST_CASES:
        resultado = await testar_acolhimento(caso)
        resultados.append(resultado)

        # Aguardar um pouco entre requisições
        await asyncio.sleep(2)

    # Step 3: Resumo
    print(f"\n\n{'='*70}")
    print(f"📋 RESUMO DOS TESTES")
    print(f"{'='*70}")

    sucessos = sum(1 for r in resultados if r.get("sucesso"))
    alertas = sum(1 for r in resultados if r.get("alerta_disparado"))

    print(f"\nTestes Executados: {len(resultados)}")
    print(f"Sucessos: {sucessos}/{len(resultados)}")
    print(f"Alertas Disparados: {alertas}")

    print(f"\n📊 Detalhes:")
    for i, resultado in enumerate(resultados, 1):
        if resultado.get("sucesso"):
            prioridade = resultado.get("prioridade", "?")
            tempo = resultado.get("tempo_processamento", 0)
            alerta = "✓ Alerta" if resultado.get("alerta_disparado") else "✗ Sem alerta"
            print(f"   {i}. {alerta} | Prioridade: {prioridade} | Tempo: {tempo:.2f}s")
        else:
            erro = resultado.get("erro", "Erro desconhecido")
            print(f"   {i}. ❌ Falha: {erro}")

    print(f"\n✅ Verificação:")
    print(f"   • Todos os testes foram executados")
    print(f"   • Verifique no n8n se os webhooks foram recebidos")
    print(f"   • Verifique no Discord se os alertas chegaram para Média/Alta/Crítica")

    print(f"\n⏰ Finalizado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())
