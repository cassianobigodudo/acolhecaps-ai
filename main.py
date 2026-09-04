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
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from app.models.acolhimento import EntradaAcolhimento, FichaTriagemCAPS, HITLAprovacao, HITLCorrecao
from app.services.alert_service import obter_alert_service
from app.services.observability import setup_observability_logger
from app.services.graph_service import executar_acolhimento
from app.services.hitl_manager import obter_hitl_manager

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
        - requer_aprovacao_humana: bool indicando se precisa de HITL
    
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
            "requer_aprovacao_humana": resultado["ficha_triagem"].get("status_aprovacao") == "pendente",
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


@app.post("/acolhimento/hitl")
async def responder_hitl(hitl_request: HITLAprovacao | HITLCorrecao):
    """
    Responde a uma ficha em estado HITL (Human-in-the-Loop).
    
    Profissional pode:
    1. APROVAR a classificação da IA (usar HITLAprovacao)
    2. CORRIGIR a classificação (usar HITLCorrecao)
    
    Request Body:
        - trace_id: str (ID retornado em POST /acolhimento)
        - status_aprovacao: "aprovado" ou "corrigido"
        - Para aprovação: observacoes, profissional_nome, profissional_profissao (opcional)
        - Para correção: nivel_prioridade_corrigido, novo_encaminhamento (opcional), etc
    
    Returns:
        - status: sucesso ou erro
        - ficha_triagem: Ficha atualizada com decisão profissional
        - trace_id: ID da triagem
    
    Raises:
        - 404: Ficha pendente não encontrada
        - 400: Validação falhou
        - 500: Erro ao processar
    """
    try:
        trace_id = hitl_request.trace_id
        status_aprovacao = hitl_request.status_aprovacao
        
        logger.info(
            f"[HITL] Recebido POST /acolhimento/hitl | "
            f"trace_id={trace_id} | "
            f"acao={status_aprovacao}"
        )
        
        # Obtém manager
        hitl_manager = obter_hitl_manager()
        
        # Verifica se ficha pendente existe
        ficha = hitl_manager.obter_ficha_pendente(trace_id)
        if not ficha:
            logger.warning(
                f"[HITL] Ficha pendente não encontrada | trace_id={trace_id}"
            )
            raise HTTPException(
                status_code=404,
                detail=f"Ficha pendente não encontrada para trace_id: {trace_id}"
            )
        
        # Processa aprovação ou correção
        if isinstance(hitl_request, HITLAprovacao):
            logger.info(
                f"[HITL] Processando APROVAÇÃO | trace_id={trace_id} | "
                f"profissional={hitl_request.profissional_nome}"
            )
            
            ficha_atualizada = hitl_manager.aprovar_ficha(
                trace_id=trace_id,
                profissional_nome=hitl_request.profissional_nome,
                profissional_profissao=hitl_request.profissional_profissao,
                observacoes=hitl_request.observacoes,
            )
            
        else:  # HITLCorrecao
            logger.info(
                f"[HITL] Processando CORREÇÃO | trace_id={trace_id} | "
                f"prioridade={ficha.get('nivel_prioridade')} → "
                f"{hitl_request.nivel_prioridade_corrigido} | "
                f"profissional={hitl_request.profissional_nome}"
            )
            
            ficha_atualizada = hitl_manager.corrigir_ficha(
                trace_id=trace_id,
                nivel_prioridade_corrigido=hitl_request.nivel_prioridade_corrigido,
                profissional_nome=hitl_request.profissional_nome,
                profissional_profissao=hitl_request.profissional_profissao,
                observacoes=hitl_request.observacoes,
                novo_encaminhamento=hitl_request.novo_encaminhamento,
            )
        
        logger.info(
            f"[HITL] Processamento concluído com sucesso | "
            f"trace_id={trace_id} | "
            f"status={ficha_atualizada.get('status_aprovacao')} | "
            f"prioridade_final={ficha_atualizada.get('nivel_prioridade')}"
        )
        
        # Dispara alerta para Discord via n8n webhook
        if alert_service:
            try:
                # Gera mensagem formatada
                mensagem_discord, cor_discord = hitl_manager.gerar_mensagem_discord(
                    trace_id=trace_id,
                    ficha=ficha_atualizada,
                )
                
                logger.info(
                    f"[HITL] Mensagem Discord gerada | trace_id={trace_id}"
                )
                logger.info(
                    f"[HITL] AlertService disponível, disparando alerta | trace_id={trace_id}"
                )
                
                # Cria payload para n8n
                payload = {
                    "tipo": "hitl_decision",
                    "nivel_prioridade": ficha_atualizada.get("nivel_prioridade"),
                    "status_aprovacao": ficha_atualizada.get("status_aprovacao"),
                    "mensagem": mensagem_discord,
                    "cor": cor_discord,
                    "trace_id": trace_id,
                    "timestamp": datetime.now().isoformat(),
                }
                
                # Executa em thread para não bloquear
                import threading
                thread_alerta = threading.Thread(
                    target=_disparar_alerta_hitl_async,
                    args=(alert_service, mensagem_discord, trace_id, ficha_atualizada),
                    daemon=False,  # NÃO é daemon para garantir que complete
                )
                thread_alerta.start()
                thread_alerta.join(timeout=60)  # Aguarda até 60s (1 minuto) para completar
                
                logger.info(
                    f"[HITL] Thread de alerta finalizada | trace_id={trace_id}"
                )
                
            except Exception as e:
                logger.warning(
                    f"[HITL] Erro ao disparar alerta (não bloqueia resposta) | "
                    f"erro={str(e)} | trace_id={trace_id}"
                )
        else:
            logger.info(
                f"[HITL] AlertService não configurado, alertas desabilitados | "
                f"trace_id={trace_id}"
            )
        
        return {
            "status": "sucesso",
            "trace_id": trace_id,
            "ficha_triagem": ficha_atualizada,
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"[HITL] Erro de validação | erro={str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[HITL] Erro ao processar HITL | erro={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar HITL: {str(e)}",
        )


def _disparar_alerta_hitl_async(
    alert_service,
    mensagem_discord: str,
    trace_id: str,
    ficha_triagem: dict,
) -> None:
    """
    Dispara alerta HITL para Discord em thread separada.
    Usa requests síncrono para evitar problemas com event loop em threads.
    """
    try:
        import requests
        
        logger.info(
            f"[ALERTA_HITL] ▶️ Iniciando disparo | trace_id={trace_id}"
        )
        
        logger.info(
            f"[ALERTA_HITL] Webhook URL: {alert_service.webhook_url}"
        )
        
        # Cria payload para n8n
        payload = {
            "tipo": "hitl_decision",
            "nivel_prioridade": ficha_triagem.get("nivel_prioridade"),
            "status_aprovacao": ficha_triagem.get("status_aprovacao"),
            "mensagem": mensagem_discord,
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.info(
            f"[ALERTA_HITL] 📦 Payload preparado | size={len(str(payload))} bytes | trace_id={trace_id}"
        )
        
        # Usa requests síncrono em vez de httpx assíncrono
        try:
            logger.info(
                f"[ALERTA_HITL] 🚀 Enviando POST para webhook..."
            )
            
            response = requests.post(
                alert_service.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            
            logger.info(
                f"[ALERTA_HITL] 📬 Resposta recebida | status={response.status_code}"
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(
                    f"[ALERTA_HITL] ✅ Sucesso! Webhook disparado | "
                    f"status={response.status_code} | "
                    f"response={response.text[:200]} | trace_id={trace_id}"
                )
            else:
                logger.warning(
                    f"[ALERTA_HITL] ⚠️ Status não esperado | "
                    f"status={response.status_code} | "
                    f"response={response.text[:500]} | trace_id={trace_id}"
                )
                
        except requests.exceptions.Timeout:
            logger.error(
                f"[ALERTA_HITL] ⏱️ Timeout ao enviar webhook (10s) | trace_id={trace_id}"
            )
        except requests.exceptions.ConnectionError as ce:
            logger.error(
                f"[ALERTA_HITL] 🔌 Erro de conexão | erro={str(ce)} | trace_id={trace_id}"
            )
        except Exception as re:
            logger.error(
                f"[ALERTA_HITL] 📡 Erro na requisição | erro={str(re)} | trace_id={trace_id}"
            )
        
    except Exception as e:
        logger.error(
            f"[ALERTA_HITL] ❌ Erro geral | erro={str(e)} | tipo={type(e).__name__} | trace_id={trace_id}"
        )


@app.get("/acolhimento/hitl/pendentes")
async def listar_fichas_pendentes():
    """
    Lista todas as fichas em estado HITL (aguardando aprovação profissional).
    
    Útil para dashboard de profissionais verem quais fichas precisam de revisão.
    
    Returns:
        - status: sucesso
        - fichas_pendentes: Dict[trace_id] -> ficha_triagem
        - total: Número de fichas pendentes
    """
    try:
        hitl_manager = obter_hitl_manager()
        fichas_pendentes = hitl_manager.listar_fichas_pendentes()
        
        logger.info(
            f"[HITL] Listando fichas pendentes | total={len(fichas_pendentes)}"
        )
        
        return {
            "status": "sucesso",
            "fichas_pendentes": fichas_pendentes,
            "total": len(fichas_pendentes),
        }
        
    except Exception as e:
        logger.error(f"[HITL] Erro ao listar pendentes | erro={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar fichas pendentes: {str(e)}",
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
