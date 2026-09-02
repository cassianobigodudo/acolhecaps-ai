"""
Orquestra├º├úo do Grafo LangGraph para AcolheCAPS AI.

Este m├│dulo implementa o fluxo ag├¬ntico com:
- StateGraph tipado e seguro
- N├│s com responsabilidades isoladas
- Execu├º├úo sequencial e paralela
- Roteamento condicional baseado em prioridade de risco
- Prote├º├úo contra loops infinitos
- Integra├º├úo com Groq LLM para an├ílise de risco
"""

import json
import logging
import uuid
from typing import TypedDict, List, Optional, Any, Literal
from datetime import datetime

from langgraph.graph import StateGraph, END

from app.models import EntradaAcolhimento, FichaTriagemCAPS, EstadoAcolhimento
from app.services.llm_service import get_groq_llm
from app.services.mcp_territorial_tool import obter_tool_territorial
import asyncio


# ============================================================================
# Logging Configuration
# ============================================================================
logger = logging.getLogger(__name__)


def setup_logging(trace_id: str) -> None:
    """Configure JSON logging with trace_id injection."""
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        json.dumps({
            "timestamp": "%(asctime)s",
            "level": "%(levelname)s",
            "message": "%(message)s",
            "trace_id": trace_id
        })
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ============================================================================
# State Graph Definition
# ============================================================================
class AcolhimentoState(TypedDict):
    """
    State tipado para o grafo LangGraph.
    
    Attributes:
        entrada: Dados de entrada validados
        historico_chat: Hist├│rico de intera├º├Áes e decis├Áes
        contexto_rag: Contexto recuperado de diretrizes cl├¡nicas
        resultado_territorial: Resultado da valida├º├úo territorial
        ficha_triagem: Ficha de triagem estruturada
        requer_aprovacao_humana: Flag de human-in-the-loop
        status_processamento: Status atual do processamento
        tentativas_approval: Contador de tentativas de aprova├º├úo (para evitar loops)
    """
    entrada: dict  # EntradaAcolhimento serializado
    historico_chat: List[dict]
    contexto_rag: Optional[str]
    resultado_territorial: Optional[dict]
    ficha_triagem: Optional[dict]  # FichaTriagemCAPS serializado
    requer_aprovacao_humana: bool
    status_processamento: str
    tentativas_approval: int


# ============================================================================
# Node Functions
# ============================================================================

def node_extracao(state: AcolhimentoState) -> AcolhimentoState:
    """
    NODE 1: Extra├º├úo e S├¡ntese do Relato
    """
    trace_id = _current_trace_id
    logger.info(f"[NODE_EXTRACAO] Iniciando s├¡ntese do relato | trace_id={trace_id}")
    
    try:
        entrada = state["entrada"]
        relato = entrada.get("relato", "")
        
        # Simula├º├úo de extra├º├úo e s├¡ntese (em produ├º├úo, usaria LLM)
        pontos_chave = [
            "Sintoma identificado no relato",
            "Dura├º├úo/frequ├¬ncia dos sintomas",
            "Contexto socioecon├┤mico"
        ]
        
        # Atualiza hist├│rico
        novo_historico = state["historico_chat"].copy()
        novo_historico.append({
            "node": "extracao",
            "timestamp": datetime.utcnow().isoformat(),
            "action": "relato_processado",
            "pontos_chave": pontos_chave,
            "trace_id": trace_id
        })
        
        state["historico_chat"] = novo_historico
        state["status_processamento"] = "extracao_concluida"
        
        logger.info(
            f"[NODE_EXTRACAO] S├¡ntese conclu├¡da | "
            f"pontos_chave={len(pontos_chave)} | trace_id={trace_id}"
        )
        
    except Exception as e:
        logger.error(
            f"[NODE_EXTRACAO] Erro durante s├¡ntese | "
            f"erro={str(e)} | trace_id={trace_id}"
        )
        raise
    
    return state


def node_rag_diretrizes(state: AcolhimentoState) -> dict:
    """NODE 2A: Busca em RAG (Diretrizes Cl├¡nicas)"""
    trace_id = _current_trace_id
    logger.info(f"[NODE_RAG_DIRETRIZES] Iniciando busca em diretrizes | trace_id={trace_id}")
    
    try:
        contexto_rag = "Diretrizes para Ansiedade: Avalia├º├úo de sintomatologia..."
        
        logger.info(
            f"[NODE_RAG_DIRETRIZES] Contexto recuperado | "
            f"comprimento={len(contexto_rag)} | trace_id={trace_id}"
        )
        
        return {"contexto_rag": contexto_rag}
        
    except Exception as e:
        logger.error(f"[NODE_RAG_DIRETRIZES] Erro | erro={str(e)} | trace_id={trace_id}")
        return {"contexto_rag": None}


def node_mcp_territorio(state: AcolhimentoState) -> dict:
    """
    NODE 2B: Validacao Territorial via MCP Tool
    
    Integra a Tool MCP para validar se o CEP/Bairro pertence a area
    de cobertura do CAPS. Suporta timeout e fallback automatico.
    """
    trace_id = _current_trace_id
    logger.info(f"[NODE_MCP_TERRITORIO] Iniciando validacao territorial | trace_id={trace_id}")
    
    try:
        entrada = state["entrada"]
        cep = entrada.get("cep", "").strip()
        bairro = entrada.get("bairro", "").strip()
        municipio = entrada.get("municipio", "").strip()
        
        # Obtem a Tool MCP
        tool = obter_tool_territorial(trace_id=trace_id)
        
        # Valida territorialmente (async)
        payload = {
            "cep": cep,
            "bairro": bairro or "Desconhecido",
            "municipio": municipio or "Nao informado"
        }
        
        # Executa validacao com timeout de 5 segundos
        resultado = asyncio.run(
            tool.validar_territorial(payload, timeout=5)
        )
        
        logger.info(
            f"[NODE_MCP_TERRITORIO] Validacao concluida | "
            f"cep={cep} | valido={resultado['valido']} | "
            f"fallback={resultado['fallback']} | trace_id={trace_id}"
        )
        
        return {"resultado_territorial": resultado}
        
    except Exception as e:
        logger.error(
            f"[NODE_MCP_TERRITORIO] Erro na validacao territorial | "
            f"erro={str(e)} | trace_id={trace_id}"
        )
        # Retorna resultado de erro (sem fallback, falha clara)
        return {
            "resultado_territorial": {
                "valido": False,
                "cep": entrada.get("cep", ""),
                "municipio": entrada.get("municipio", ""),
                "mensagem": f"Erro ao validar: {str(e)}",
                "fallback": False
            }
        }


def node_avaliacao_risco(state: AcolhimentoState) -> AcolhimentoState:
    """
    NODE 3: Avalia├º├úo de Risco e Defini├º├úo de Prioridade
    """
    trace_id = _current_trace_id
    logger.info(f"[NODE_AVALIACAO_RISCO] Iniciando avalia├º├úo de risco com Groq | trace_id={trace_id}")
    
    try:
        entrada = state["entrada"]
        relato = entrada.get("relato", "").lower()
        contexto_rag = state.get("contexto_rag", "")
        
        # Obt├®m LLM Groq
        llm = get_groq_llm()
        
        # Chama Groq para avalia├º├úo
        prioridade, fatores_risco = llm.avaliar_nivel_prioridade(
            relato=entrada.get("relato", ""),
            contexto_rag=contexto_rag,
            trace_id=trace_id
        )
        
        # Valida prioridade retornada
        if prioridade not in ["Alta", "M├®dia", "Baixa"]:
            prioridade = "M├®dia"  # default seguro
            logger.warning(
                f"[NODE_AVALIACAO_RISCO] Prioridade inv├ílida retornada por Groq | "
                f"prioridade={prioridade} | usando M├®dia como fallback | trace_id={trace_id}"
            )
        
        # Recomenda oficinas baseado em prioridade
        oficinas_sugeridas = []
        if prioridade == "Baixa":
            oficinas_sugeridas = [
                "Oficina de Mindfulness",
                "Grupo de Suporte em Ansiedade",
                "Psicoeduca├º├úo em Sa├║de Mental"
            ]
        # Prioridades M├®dia e Alta: sem recomenda├º├úo autom├ítica de oficinas
        # Recomenda├º├Áes vir├úo ap├│s aprova├º├úo humana profissional
        
        # Cria ficha de triagem
        ficha = {
            "nivel_prioridade": prioridade,
            "fatores_risco": fatores_risco if fatores_risco else [],
            "oficinas_sugeridas": oficinas_sugeridas,
            "status_aprovacao": "pendente",
            "data_criacao": datetime.utcnow().isoformat(),
            "observacoes": None
        }
        
        state["ficha_triagem"] = ficha
        # Human-in-the-loop para prioridades M├®dia e Alta
        state["requer_aprovacao_humana"] = (prioridade in ["Alta", "M├®dia"])
        
        novo_historico = state["historico_chat"].copy()
        novo_historico.append({
            "node": "avaliacao_risco",
            "timestamp": datetime.utcnow().isoformat(),
            "action": "risco_avaliado_com_groq",
            "nivel_prioridade": prioridade,
            "fatores_risco": fatores_risco,
            "requer_aprovacao": state["requer_aprovacao_humana"],
            "trace_id": trace_id
        })
        state["historico_chat"] = novo_historico
        state["status_processamento"] = "avaliacao_concluida"
        
        logger.info(
            f"[NODE_AVALIACAO_RISCO] Avalia├º├úo conclu├¡da com Groq | "
            f"prioridade={prioridade} | "
            f"fatores_risco={len(fatores_risco)} | "
            f"requer_approval={state['requer_aprovacao_humana']} | trace_id={trace_id}"
        )
        
    except Exception as e:
        logger.error(
            f"[NODE_AVALIACAO_RISCO] Erro durante avalia├º├úo com Groq | "
            f"erro={str(e)} | trace_id={trace_id}"
        )
        # Fallback: classifica como M├®dia para ser seguro
        state["ficha_triagem"] = {
            "nivel_prioridade": "M├®dia",
            "fatores_risco": ["Erro na avalia├º├úo - necess├íria revis├úo profissional"],
            "oficinas_sugeridas": [],
            "status_aprovacao": "pendente",
            "data_criacao": datetime.utcnow().isoformat(),
            "observacoes": f"Erro na an├ílise: {str(e)}"
        }
        state["requer_aprovacao_humana"] = True
        raise
    
    return state


def node_human_in_the_loop(state: AcolhimentoState) -> AcolhimentoState:
    """
    NODE 4A: Human-in-the-Loop para Prioridade Alta
    """
    trace_id = _current_trace_id
    logger.info(f"[NODE_HUMAN_IN_THE_LOOP] Aguardando aprova├º├úo humana | trace_id={trace_id}")
    
    try:
        # Prote├º├úo contra loops infinitos
        tentativas = state.get("tentativas_approval", 0)
        max_tentativas = 3
        
        if tentativas >= max_tentativas:
            logger.warning(
                f"[NODE_HUMAN_IN_THE_LOOP] Limite de tentativas atingido | "
                f"tentativas={tentativas} | trace_id={trace_id}"
            )
            state["ficha_triagem"]["status_aprovacao"] = "rejeitado"
            state["status_processamento"] = "limite_tentativas_atingido"
            return state
        
        # Incrementa contador
        state["tentativas_approval"] = tentativas + 1
        
        # Em produ├º├úo, integraria com UI/API para aprova├º├úo
        # Por enquanto, simula aprova├º├úo autom├ítica para teste
        state["ficha_triagem"]["status_aprovacao"] = "aprovado"
        state["ficha_triagem"]["observacoes"] = "Aprovado automaticamente para demonstra├º├úo"
        
        novo_historico = state["historico_chat"].copy()
        novo_historico.append({
            "node": "human_in_the_loop",
            "timestamp": datetime.utcnow().isoformat(),
            "action": "aprovacao_obtida",
            "tentativa": state["tentativas_approval"],
            "status": state["ficha_triagem"]["status_aprovacao"],
            "trace_id": trace_id
        })
        state["historico_chat"] = novo_historico
        
        logger.info(
            f"[NODE_HUMAN_IN_THE_LOOP] Aprova├º├úo processada | "
            f"status={state['ficha_triagem']['status_aprovacao']} | "
            f"tentativa={state['tentativas_approval']} | trace_id={trace_id}"
        )
        
    except Exception as e:
        logger.error(
            f"[NODE_HUMAN_IN_THE_LOOP] Erro durante aprova├º├úo | "
            f"erro={str(e)} | trace_id={trace_id}"
        )
        raise
    
    return state


def node_finalizacao(state: AcolhimentoState) -> AcolhimentoState:
    """
    NODE 4B: Finaliza├º├úo do Fluxo
    """
    trace_id = _current_trace_id
    logger.info(f"[NODE_FINALIZACAO] Finalizando fluxo de acolhimento | trace_id={trace_id}")
    
    try:
        novo_historico = state["historico_chat"].copy()
        novo_historico.append({
            "node": "finalizacao",
            "timestamp": datetime.utcnow().isoformat(),
            "action": "fluxo_finalizado",
            "ficha_triagem": state["ficha_triagem"],
            "trace_id": trace_id
        })
        state["historico_chat"] = novo_historico
        state["status_processamento"] = "concluido"
        
        logger.info(
            f"[NODE_FINALIZACAO] Fluxo finalizado com sucesso | "
            f"prioridade={state['ficha_triagem'].get('nivel_prioridade')} | "
            f"trace_id={trace_id}"
        )
        
    except Exception as e:
        logger.error(
            f"[NODE_FINALIZACAO] Erro durante finaliza├º├úo | "
            f"erro={str(e)} | trace_id={trace_id}"
        )
        raise
    
    return state


# ============================================================================
# Conditional Routing Functions
# ============================================================================

def rota_condicional_prioridade(state: AcolhimentoState) -> str:
    """Rota condicional baseada em n├¡vel de prioridade."""
    ficha = state.get("ficha_triagem", {})
    prioridade = ficha.get("nivel_prioridade", "Baixa")
    
    trace_id = _current_trace_id
    
    if prioridade in ["Alta", "M├®dia"]:
        logger.info(
            f"[ROTA] Desviando para human-in-the-loop | "
            f"prioridade={prioridade} (requer aprova├º├úo profissional) | trace_id={trace_id}"
        )
        return "node_human_in_the_loop"
    else:
        logger.info(
            f"[ROTA] Desviando para finaliza├º├úo | "
            f"prioridade={prioridade} (autonomia relativa) | trace_id={trace_id}"
        )
        return "node_finalizacao"


def rota_pos_aprovacao(state: AcolhimentoState) -> str:
    """Rota p├│s human-in-the-loop."""
    ficha = state.get("ficha_triagem", {})
    status_approval = ficha.get("status_aprovacao", "pendente")
    
    trace_id = _current_trace_id
    
    if status_approval == "aprovado":
        logger.info(
            f"[ROTA] Aprova├º├úo concedida, prosseguindo para finaliza├º├úo | "
            f"trace_id={trace_id}"
        )
        return "node_finalizacao"
    else:
        logger.warning(
            f"[ROTA] Aprova├º├úo rejeitada, encerrando fluxo | "
            f"status={status_approval} | trace_id={trace_id}"
        )
        return END


# ============================================================================
# Graph Builder
# ============================================================================

def criar_grafo_acolhimento():
    """
    Constr├│i e compila o grafo LangGraph com todas as n├│s e rotas.
    
    Estrutura:
    1. node_extracao (sequencial)
    2. node_rag_diretrizes + node_mcp_territorio (paralelo)
    3. node_avaliacao_risco (sequencial)
    4. rota_condicional_prioridade -> node_human_in_the_loop OU node_finalizacao
    5. Se human-in-the-loop: rota_pos_aprovacao -> node_finalizacao OU END
    
    Returns:
        Grafo compilado e pronto para execu├º├úo
    """
    
    # Cria StateGraph
    workflow = StateGraph(AcolhimentoState)
    
    # Adiciona n├│s
    workflow.add_node("node_extracao", node_extracao)
    workflow.add_node("node_rag_diretrizes", node_rag_diretrizes)
    workflow.add_node("node_mcp_territorio", node_mcp_territorio)
    workflow.add_node("node_avaliacao_risco", node_avaliacao_risco)
    workflow.add_node("node_human_in_the_loop", node_human_in_the_loop)
    workflow.add_node("node_finalizacao", node_finalizacao)
    
    # Adiciona edges sequenciais
    workflow.set_entry_point("node_extracao")
    workflow.add_edge("node_extracao", "node_rag_diretrizes")
    workflow.add_edge("node_extracao", "node_mcp_territorio")
    
    # Converge os n├│s paralelos para avalia├º├úo
    workflow.add_edge("node_rag_diretrizes", "node_avaliacao_risco")
    workflow.add_edge("node_mcp_territorio", "node_avaliacao_risco")
    
    # Rota condicional p├│s-avalia├º├úo
    workflow.add_conditional_edges(
        "node_avaliacao_risco",
        rota_condicional_prioridade,
        {
            "node_human_in_the_loop": "node_human_in_the_loop",
            "node_finalizacao": "node_finalizacao"
        }
    )
    
    # Rota p├│s-aprova├º├úo
    workflow.add_conditional_edges(
        "node_human_in_the_loop",
        rota_pos_aprovacao,
        {
            "node_finalizacao": "node_finalizacao",
            END: END
        }
    )
    
    # Finaliza├º├úo (sempre END)
    workflow.add_edge("node_finalizacao", END)
    
    # Compila o grafo
    compiled_graph = workflow.compile()
    
    return compiled_graph


# ============================================================================
# Graph Execution
# ============================================================================

def executar_acolhimento(entrada: dict, trace_id: Optional[str] = None) -> dict:
    """
    Executa o grafo de acolhimento com entrada tipada.
    
    Args:
        entrada: Dict com id_paciente, relato, cep (ser├í validado como EntradaAcolhimento)
        trace_id: ID de rastreabilidade (gerado se n├úo fornecido)
    
    Returns:
        Dict com resultado final (ficha de triagem e hist├│rico)
    """
    global _current_trace_id
    
    # Gera trace_id se n├úo fornecido
    if trace_id is None:
        trace_id = f"trace-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    _current_trace_id = trace_id
    
    # Setup logging
    setup_logging(trace_id)
    
    logger.info(f"[EXEC] Iniciando execu├º├úo do grafo | trace_id={trace_id}")
    
    try:
        # Valida entrada
        entrada_validada = EntradaAcolhimento(**entrada)
        logger.info(f"[EXEC] Entrada validada com sucesso | trace_id={trace_id}")
        
    except Exception as e:
        logger.error(f"[EXEC] Erro na valida├º├úo de entrada | erro={str(e)} | trace_id={trace_id}")
        raise
    
    # Cria estado inicial
    estado_inicial = AcolhimentoState(
        entrada=entrada_validada.model_dump(),
        historico_chat=[],
        contexto_rag=None,
        resultado_territorial=None,
        ficha_triagem=None,
        requer_aprovacao_humana=False,
        status_processamento="iniciado",
        tentativas_approval=0
    )
    
    # Cria e executa grafo
    grafo = criar_grafo_acolhimento()
    
    logger.info(f"[EXEC] Grafo criado, iniciando execu├º├úo | trace_id={trace_id}")
    
    # Executa grafo
    resultado = grafo.invoke(estado_inicial)
    
    logger.info(f"[EXEC] Execu├º├úo conclu├¡da | trace_id={trace_id}")
    
    return {
        "trace_id": trace_id,
        "ficha_triagem": resultado["ficha_triagem"],
        "resultado_territorial": resultado["resultado_territorial"],
        "historico": resultado["historico_chat"],
        "status": resultado["status_processamento"]
    }


# Vari├ível global para armazenar trace_id entre n├│s
_current_trace_id: str = ""
