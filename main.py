"""
Servidor FastAPI para AcolheCAPS AI - Aplicação Principal

Endpoints:
- POST /acolhimento - Inicia o fluxo de triagem de um paciente
- GET /health - Verificação de saúde do servidor
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from app.models.acolhimento import EntradaAcolhimento, FichaTriagemCAPS
from app.services.alert_service import obter_alert_service
from app.services.observability import setup_observability_logger
from app.services.graph_service import executar_acolhimento

# Carregar variáveis de ambiente do .env
load_dotenv()

# ============================================================================
# Logging Configuration
# ============================================================================
logger = logging.getLogger(__name__)
setup_observability_logger("acolhecaps-ai")

# ============================================================================
# Global Alert Service
# ============================================================================
alert_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Inicializa serviços no startup e limpa no shutdown.
    """
    global alert_service

    # Startup
    logger.info("[MAIN] Iniciando AcolheCAPS AI Server")
    
    # Inicializar AlertService
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    if webhook_url:
        alert_service = obter_alert_service(webhook_url=webhook_url)
        logger.info(f"[MAIN] AlertService inicializado com webhook: {webhook_url}")
    else:
        logger.warning("[MAIN] N8N_WEBHOOK_URL não configurado. Alertas desabilitados.")
    
    logger.info("[MAIN] Servidor pronto para aceitar requisições")
    
    yield
    
    # Shutdown
    logger.info("[MAIN] Encerrando AcolheCAPS AI Server")
    if alert_service:
        await alert_service.fechar()
        logger.info("[MAIN] AlertService encerrado")


# ============================================================================
# FastAPI App
# ============================================================================
app = FastAPI(
    title="AcolheCAPS AI",
    description="Assistente de Triagem e Apoio Multiprofissional para CAPS",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# Endpoints
# ============================================================================


@app.get("/health")
async def health():
    """
    Verificação de saúde do servidor.
    
    Returns:
        - status: ok
        - alert_service: conectado ou desabilitado
    """
    return {
        "status": "ok",
        "alert_service": "conectado" if alert_service else "desabilitado",
        "service": "AcolheCAPS AI",
    }


@app.post("/acolhimento")
async def criar_acolhimento(entrada: EntradaAcolhimento):
    """
    Inicia o fluxo de triagem de um paciente.
    
    Request Body:
        - id_paciente: str (ex: "PAC-2024-001")
        - relato: str (descrição do relato de acolhimento, min 10 chars)
        - cep: str (formato: 12345-678 ou 12345678)
    
    Returns:
        - status: sucesso ou erro
        - ficha_triagem: FichaTriagemCAPS com resultado
        - trace_id: ID para rastreabilidade
    
    Raises:
        - 400: Validação de entrada falhou
        - 500: Erro ao processar o acolhimento
    """
    try:
        logger.info(
            f"[ACOLHIMENTO] Recebido POST /acolhimento | "
            f"paciente={entrada.id_paciente} | cep={entrada.cep}"
        )

        # Executar o grafo LangGraph
        resultado = executar_acolhimento(
            entrada_dict=entrada.dict(),
            alert_service=alert_service,
        )

        logger.info(
            f"[ACOLHIMENTO] Fluxo concluído com sucesso | "
            f"prioridade={resultado['ficha_triagem'].get('nivel_prioridade')} | "
            f"trace_id={resultado['trace_id']}"
        )

        return {
            "status": "sucesso",
            "ficha_triagem": resultado["ficha_triagem"],
            "trace_id": resultado["trace_id"],
        }

    except ValidationError as e:
        logger.error(
            f"[ACOLHIMENTO] Erro de validação | "
            f"erro={str(e)}"
        )
        raise HTTPException(status_code=400, detail=f"Validação falhou: {str(e)}")

    except Exception as e:
        logger.error(
            f"[ACOLHIMENTO] Erro ao processar acolhimento | "
            f"erro={str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar acolhimento: {str(e)}",
        )


# ============================================================================
# Main
# ============================================================================
if __name__ == "__main__":
    import uvicorn

    logger.info("[MAIN] Iniciando servidor uvicorn")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
