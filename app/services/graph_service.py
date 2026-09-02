"""
Orquestração do Grafo LangGraph para AcolheCAPS AI.

Este módulo implementa o fluxo agêntico com:
- StateGraph tipado e seguro
- Nós com responsabilidades isoladas
- Execução sequencial e paralela
- Roteamento condicional baseado em prioridade de risco
- Proteção contra loops infinitos
- Integração com Groq LLM para análise de risco
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
        historico_chat: Histórico de interações e decisões
        contexto_rag: Contexto recuperado de diretrizes clínicas
        resultado_territorial: Resultado da validação territorial
        ficha_triagem: Ficha de triagem estruturada
        requer_aprovacao_humana: Flag de human-in-the-loop
        status_processamento: Status atual do processamento
        tentativas_approval: Contador de tentativas de aprovação (para evitar loops)
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
    NODE 1: Extração e Síntese do Relato
    """
    trace_id = _current_trace_id
    logger.info(f"[NODE_EXTRACAO] Iniciando síntese do relato | trace_id={trace_id}")
    
    try:
        entrada = state["entrada"]
        relato = entrada.get("relato", "")
        
        # Simulação de extração e síntese (em produção, usaria LLM)
        pontos_chave = [
            "Sintoma identificado no relato",
            "Duração/frequência dos sintomas",
            "Contexto socioeconômico"
        ]
        
        # Atualiza histórico
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
            f"[NODE_EXTRACAO] Síntese concluída | "
            f"pontos_chave={len(pontos_chave)} | trace_id={trace_id}"
        )
        
    except Exception as e:
        logger.error(
            f"[NODE_EXTRACAO] Erro durante síntese | "
            f"erro={str(e)} | trace_id={trace_id}"
        )
        raise
    
    return state


def node_rag_diretrizes(state: AcolhimentoState) -> dict:
    """NODE 2A: Busca em RAG (Diretrizes Clínicas)"""
    trace_id = _current_trace_id
    logger.info(f"[NODE_RAG_DIRETRIZES] Iniciando busca em diretrizes | trace_id={trace_id}")
    
    try:
        contexto_rag = "Diretrizes para Ansiedade: Avaliação de sintomatologia..."
        
        logger.info(
            f"[NODE_RAG_DIRETRIZES] Contexto recuperado | "
            f"comprimento={len(contexto_rag)} | trace_id={trace_id}"
        )
        
        return {"contexto_rag": contexto_rag}
        
    except Exception as e:
        logger.error(f"[NODE_RAG_DIRETRIZES] Erro | erro={str(e)} | trace_id={trace_id}")
        return {"contexto_rag": None}


def node_mcp_territorio(state: AcolhimentoState) -> dict:
    """NODE 2B: Validação Territorial via MCP Tool"""
    trace_id = _current_trace_id
    logger.info(f"[NODE_MCP_TERRITORIO] Iniciando validação territorial | trace_id={trace_id}")
    
    try:
        entrada = state["entrada"]
        cep = entrada.get("cep", "").strip()
        bairro = entrada.get("bairro", "").strip()
        municipio = entrada.get("municipio", "").strip()
        
        # Obtém a Tool MCP
        tool = obter_tool_territorial(trace_id=trace_id)
        
        # Valida territorialmente (async)
        payload = {
            "cep": cep,
            "bairro": bairro or "Desconhecido",
            "municipio": municipio or "Nao informado"
        }
        
        # Executa validação com timeout de 5 segundos
        resultado = asyncio.run(
            tool.validar_territorial(payload, timeout=5)
        )
        
        logger.info(
            f"[NODE_MCP_TERRITORIO] Validação concluída | "
            f"cep={cep} | valido={resultado['valido']} | "
            f"fallback={resultado['fallback']} | trace_id={trace_id}"
        )
        
        return {"resultado_territorial": resultado}
        
    except Exception as e:
        logger.error(
            f"[NODE_MCP_TERRITORIO] Erro na validação territorial | "
            f"erro={str(e)} | trace_id={trace_id}"
        )
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
    NODE 3: Avaliação de Risco e Definição de Prioridade
    """
    trace_id = _current_trace_id
    logger.info(f"[NODE_AVALIACAO_RISCO] Iniciando avaliação de risco com Groq | trace_id={trace_id}")
    
    try:
        entrada = state["entrada"]
        relato = entrada.get("relato", "").lower()
        contexto_rag = state.get("contexto_rag", "")
        
        # Obtém LLM Groq
        llm = get_groq_llm()
        
        # Chama Groq para avaliação
        prioridade, fatores_risco = llm.avaliar_nivel_prioridade(
            relato=entrada.get("relato", ""),
            contexto_rag=contexto_rag,
            trace_id=trace_id
        )
        
        # Valida prioridade retornada
        if prioridade not in ["Alta", "Média", "Baixa"]:
            prioridade = "Média"  # default seguro
            logger.warning(
                f"[NODE_AVALIACAO_RISCO] Prioridade inválida retornada por Groq | "
                f"prioridade={prioridade} | usando Média como fallback | trace_id={trace_id}"
            )
        
        # Recomenda oficinas baseado em prioridade
        oficinas_sugeridas = []
        if prioridade == "Baixa":
            oficinas_sugeridas = [
                "Oficina de Mindfulness",
                "Grupo de Suporte em Ansiedade",
                "Psicoeducação em Saúde Mental"
            ]
        # Prioridades Média e Alta: sem recomendação automática de oficinas
        # Recomendações virão após aprovação humana profissional
        
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
        # Human-in-the-loop para prioridades Média e Alta
        state["requer_aprovacao_humana"] = (prioridade in ["Alta", "Média"])
        
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
            f"[NODE_AVALIACAO_RISCO] Avaliação concluída com Groq | "
            f"prioridade={prioridade} | "
            f"fatores_risco={len(fatores_risco)} | "
            f"requer_approval={state['requer_aprovacao_humana']} | trace_id={trace_id}"
        )
        
    except Exception as e:
        logger.error(
            f"[NODE_AVALIACAO_RISCO] Erro durante avaliação com Groq | "
            f"erro={str(e)} | trace_id={trace_id}"
        )
        # Fallback: classifica como Média para ser seguro
        state["ficha_triagem"] = {
            "nivel_prioridade": "Média",
            "fatores_risco": ["Erro na avaliação - necessária revisão profissional"],
            "oficinas_sugeridas": [],
            "status_aprovacao": "pendente",
            "data_criacao": datetime.utcnow().isoformat(),
            "observacoes": f"Erro na análise: {str(e)}"
        }
        state["requer_aprovacao_humana"] = True
        raise
    
    return state


def node_human_in_the_loop(state: AcolhimentoState) -> AcolhimentoState:
    """
    NODE 4A: Human-in-the-Loop para Prioridade Alta
    """
    trace_id = _current_trace_id
    logger.info(f"[NODE_HUMAN_IN_THE_LOOP] Aguardando aprovação humana | trace_id={trace_id}")
    
    try:
        # Proteção contra loops infinitos
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
        
        # Em produção, integraria com UI/API para aprovação
        # Por enquanto, simula aprovação automática para teste
        state["ficha_triagem"]["status_aprovacao"] = "aprovado"
        state["ficha_triagem"]["observacoes"] = "Aprovado automaticamente para demonstração"
        
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
            f"[NODE_HUMAN_IN_THE_LOOP] Aprovação processada | "
            f"status={state['ficha_triagem']['status_aprovacao']} | "
            f"tentativa={state['tentativas_approval']} | trace_id={trace_id}"
        )
        
    except Exception as e:
        logger.error(
            f"[NODE_HUMAN_IN_THE_LOOP] Erro durante aprovação | "
            f"erro={str(e)} | trace_id={trace_id}"
        )
        raise
    
    return state


def node_finalizacao(state: AcolhimentoState) -> AcolhimentoState:
    """
    NODE 4B: Finalização do Fluxo
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
            f"[NODE_FINALIZACAO] Erro durante finalização | "
            f"erro={str(e)} | trace_id={trace_id}"
        )
        raise
    
    return state


# ============================================================================
# Conditional Routing Functions
# ============================================================================

def rota_condicional_prioridade(state: AcolhimentoState) -> str:
    """Rota condicional baseada em nível de prioridade."""
    ficha = state.get("ficha_triagem", {})
    prioridade = ficha.get("nivel_prioridade", "Baixa")
    
    trace_id = _current_trace_id
    
    if prioridade in ["Alta", "Média"]:
        logger.info(
            f"[ROTA] Desviando para human-in-the-loop | "
            f"prioridade={prioridade} (requer aprovação profissional) | trace_id={trace_id}"
        )
        return "node_human_in_the_loop"
    else:
        logger.info(
            f"[ROTA] Desviando para finalização | "
            f"prioridade={prioridade} (autonomia relativa) | trace_id={trace_id}"
        )
        return "node_finalizacao"


def rota_pos_aprovacao(state: AcolhimentoState) -> str:
    """Rota pós human-in-the-loop."""
    ficha = state.get("ficha_triagem", {})
    status_approval = ficha.get("status_aprovacao", "pendente")
    
    trace_id = _current_trace_id
    
    if status_approval == "aprovado":
        logger.info(
            f"[ROTA] Aprovação concedida, prosseguindo para finalização | "
            f"trace_id={trace_id}"
        )
        return "node_finalizacao"
    else:
        logger.warning(
            f"[ROTA] Aprovação rejeitada, encerrando fluxo | "
            f"status={status_approval} | trace_id={trace_id}"
        )
        return END


# ============================================================================
# Graph Builder
# ============================================================================

def criar_grafo_acolhimento():
    """
    Constrói e compila o grafo LangGraph com todas as nós e rotas.
    
    Estrutura:
    1. node_extracao (sequencial)
    2. node_rag_diretrizes + node_mcp_territorio (paralelo)
    3. node_avaliacao_risco (sequencial)
    4. rota_condicional_prioridade -> node_human_in_the_loop OU node_finalizacao
    5. Se human-in-the-loop: rota_pos_aprovacao -> node_finalizacao OU END
    
    Returns:
        Grafo compilado e pronto para execução
    """
    
    # Cria StateGraph
    workflow = StateGraph(AcolhimentoState)
    
    # Adiciona nós
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
    
    # Converge os nós paralelos para avaliação
    workflow.add_edge("node_rag_diretrizes", "node_avaliacao_risco")
    workflow.add_edge("node_mcp_territorio", "node_avaliacao_risco")
    
    # Rota condicional pós-avaliação
    workflow.add_conditional_edges(
        "node_avaliacao_risco",
        rota_condicional_prioridade,
        {
            "node_human_in_the_loop": "node_human_in_the_loop",
            "node_finalizacao": "node_finalizacao"
        }
    )
    
    # Rota pós-aprovação
    workflow.add_conditional_edges(
        "node_human_in_the_loop",
        rota_pos_aprovacao,
        {
            "node_finalizacao": "node_finalizacao",
            END: END
        }
    )
    
    # Finalização (sempre END)
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
        entrada: Dict com id_paciente, relato, cep (será validado como EntradaAcolhimento)
        trace_id: ID de rastreabilidade (gerado se não fornecido)
    
    Returns:
        Dict com resultado final (ficha de triagem e histórico)
    """
    global _current_trace_id
    
    # Gera trace_id se não fornecido
    if trace_id is None:
        trace_id = f"trace-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    _current_trace_id = trace_id
    
    # Setup logging
    setup_logging(trace_id)
    
    logger.info(f"[EXEC] Iniciando execução do grafo | trace_id={trace_id}")
    
    try:
        # Valida entrada
        entrada_validada = EntradaAcolhimento(**entrada)
        logger.info(f"[EXEC] Entrada validada com sucesso | trace_id={trace_id}")
        
    except Exception as e:
        logger.error(f"[EXEC] Erro na validação de entrada | erro={str(e)} | trace_id={trace_id}")
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
    
    logger.info(f"[EXEC] Grafo criado, iniciando execução | trace_id={trace_id}")
    
    # Executa grafo
    resultado = grafo.invoke(estado_inicial)
    
    logger.info(f"[EXEC] Execução concluída | trace_id={trace_id}")
    
    return {
        "trace_id": trace_id,
        "ficha_triagem": resultado["ficha_triagem"],
        "resultado_territorial": resultado["resultado_territorial"],
        "historico": resultado["historico_chat"],
        "status": resultado["status_processamento"]
    }


# Variável global para armazenar trace_id entre nós
_current_trace_id: str = ""
