"""
Serviço de RAG (Retrieval Augmented Generation) com FAISS.

Este módulo implementa recuperação de contexto a partir de diretrizes clínicas
do Ministério da Saúde para embasar as decisões de triagem do agente.

Características:
- Indexação vetorial com FAISS
- Diretrizes clínicas pré-indexadas
- Busca semântica por similaridade
- Cache de embeddings
- Logging estruturado com trace_id
"""

import json
import logging
import numpy as np
from typing import List, Optional, Dict
from pathlib import Path
import pickle

logger = logging.getLogger(__name__)


class DiretrizesClinicas:
    """Base de diretrizes clínicas do Ministério da Saúde para CAPS."""
    
    # Diretrizes para diferentes níveis de prioridade
    DIRETRIZES = {
        "baixa": [
            "Transtornos de ansiedade leve: técnicas de respiração, mindfulness, suporte em grupos de autoajuda",
            "Stress relacionado a trabalho: orientação profissional, relaxamento muscular, oficinas de resiliência",
            "Sintomas de tristeza leve: acompanhamento psicossocial, oficinas terapêuticas, suporte familiar",
            "Insônia moderada: higiene do sono, meditação guiada, atividades recreativas estruturadas",
        ],
        "media": [
            "Transtornos de ansiedade moderada: psicoterapia cognitivo-comportamental, possível farmacoterapia",
            "Depressão leve a moderada: acompanhamento psicológico regular, intervenções psicossociais",
            "Sintomas obsessivo-compulsivos: exposição e prevenção de resposta (EPR), suporte multiprofissional",
            "Abuso de substâncias inicial: avaliação de dependência, psicoeducação, redução de danos",
            "Crises de pânico: técnicas de controle de respiração, exposição gradual, TCC especializada",
        ],
        "alta": [
            "Risco de autolesão ou suicídio: avaliação imediata, acompanhamento psiquiátrico diário, plano de segurança",
            "Psicose aguda: encaminhamento para serviço especializado, possível internação, medicação antipsicótica",
            "Crise de ansiedade severa: intervenção em crise, medicação ansiosa, acompanhamento contínuo",
            "Risco de violência: avaliação forense, medidas de proteção, envolvimento de segurança pública",
            "Surto maníaco ou depressivo severo: internação, medicalização urgente, acompanhamento psiquiátrico",
            "Ideação suicida com plano: encaminhamento imediato, monitoramento 24h, envolvimento de profissional urgentista",
        ],
    }

    @classmethod
    def obter_por_prioridade(cls, prioridade: str) -> List[str]:
        """Obtém diretrizes por nível de prioridade."""
        return cls.DIRETRIZES.get(prioridade.lower(), [])


class RAGService:
    """
    Serviço de RAG com FAISS para recuperação de contexto.
    
    Implementa indexação e busca semântica de diretrizes clínicas.
    """
    
    def __init__(self, trace_id: Optional[str] = None):
        """
        Inicializa o serviço RAG.
        
        Args:
            trace_id: ID único para correlação de logs
        """
        self.trace_id = trace_id or self._gerar_trace_id()
        self.index = None
        self.documents = []
        self.embeddings_cache = {}
        self.dimensao_embedding = 384  # Tamanho do embedding (simples)
        
        logger.info(
            json.dumps({
                "trace_id": self.trace_id,
                "evento": "rag_service_inicializado",
                "timestamp": self._timestamp_iso()
            })
        )
    
    @staticmethod
    def _gerar_trace_id() -> str:
        """Gera um trace_id único."""
        from uuid import uuid4
        return f"rag-{uuid4().hex[:8]}"
    
    @staticmethod
    def _timestamp_iso() -> str:
        """Retorna timestamp ISO."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def indexar_diretrizes(self) -> Dict:
        """
        Indexa as diretrizes clínicas em FAISS.
        
        Returns:
            Dicionário com status da indexação
        """
        logger.info(
            json.dumps({
                "trace_id": self.trace_id,
                "evento": "indexacao_iniciada",
                "timestamp": self._timestamp_iso()
            })
        )
        
        try:
            # Coletar todas as diretrizes
            todos_docs = []
            for prioridade in ["baixa", "media", "alta"]:
                diretrizes = DiretrizesClinicas.obter_por_prioridade(prioridade)
                for diretriz in diretrizes:
                    todos_docs.append({
                        "conteudo": diretriz,
                        "prioridade": prioridade
                    })
            
            # Gerar embeddings simples (hash-based para demo)
            embeddings = np.array([
                self._gerar_embedding_simples(doc["conteudo"]) 
                for doc in todos_docs
            ], dtype=np.float32)
            
            # Criar índice FAISS
            try:
                import faiss
                self.index = faiss.IndexFlatL2(self.dimensao_embedding)
                self.index.add(embeddings)
            except ImportError:
                # Fallback: usar índice em memória
                logger.warning(
                    json.dumps({
                        "trace_id": self.trace_id,
                        "evento": "faiss_nao_disponivel_usando_fallback",
                        "timestamp": self._timestamp_iso()
                    })
                )
                self.index = None
            
            self.documents = todos_docs
            self.embeddings_cache = {
                i: embeddings[i] for i in range(len(embeddings))
            }
            
            logger.info(
                json.dumps({
                    "trace_id": self.trace_id,
                    "evento": "indexacao_concluida",
                    "total_documentos": len(todos_docs),
                    "timestamp": self._timestamp_iso()
                })
            )
            
            return {
                "sucesso": True,
                "total_documentos": len(todos_docs),
                "status": "indexado"
            }
            
        except Exception as e:
            logger.error(
                json.dumps({
                    "trace_id": self.trace_id,
                    "evento": "erro_indexacao",
                    "erro": str(e),
                    "timestamp": self._timestamp_iso()
                })
            )
            raise
    
    def recuperar_contexto(
        self, 
        query: str, 
        prioridade: Optional[str] = None,
        top_k: int = 3
    ) -> Dict:
        """
        Recupera contexto relevante para uma query.
        
        Args:
            query: Texto da query
            prioridade: Filtro opcional por prioridade
            top_k: Número de documentos a retornar
            
        Returns:
            Dicionário com documentos recuperados e scores
        """
        logger.info(
            json.dumps({
                "trace_id": self.trace_id,
                "evento": "recuperacao_iniciada",
                "query": query[:50],
                "prioridade_filtro": prioridade,
                "timestamp": self._timestamp_iso()
            })
        )
        
        try:
            if not self.documents:
                logger.warning(
                    json.dumps({
                        "trace_id": self.trace_id,
                        "evento": "base_vazia",
                        "timestamp": self._timestamp_iso()
                    })
                )
                return {
                    "sucesso": False,
                    "documentos": [],
                    "total": 0,
                    "mensagem": "Base de diretrizes não indexada",
                    "fallback": True
                }
            
            # Gerar embedding da query
            query_embedding = self._gerar_embedding_simples(query)
            
            # Busca com FAISS se disponível
            if self.index is not None:
                distances, indices = self.index.search(
                    np.array([query_embedding], dtype=np.float32), 
                    min(top_k, len(self.documents))
                )
                distances = distances[0]
                indices = indices[0]
            else:
                # Fallback: busca por similaridade manual
                indices, distances = self._busca_manual(query_embedding, top_k)
            
            # Recuperar documentos
            documentos = []
            for idx, distance in zip(indices, distances):
                doc = self.documents[int(idx)]
                
                # Filtrar por prioridade se especificada
                if prioridade and doc["prioridade"] != prioridade.lower():
                    continue
                
                documentos.append({
                    "conteudo": doc["conteudo"],
                    "prioridade": doc["prioridade"],
                    "score": float(1 / (1 + distance))  # Converter distância em score
                })
            
            logger.info(
                json.dumps({
                    "trace_id": self.trace_id,
                    "evento": "recuperacao_concluida",
                    "documentos_recuperados": len(documentos),
                    "timestamp": self._timestamp_iso()
                })
            )
            
            return {
                "sucesso": True,
                "documentos": documentos,
                "total": len(documentos),
                "fallback": self.index is None
            }
            
        except Exception as e:
            logger.error(
                json.dumps({
                    "trace_id": self.trace_id,
                    "evento": "erro_recuperacao",
                    "erro": str(e),
                    "timestamp": self._timestamp_iso()
                })
            )
            return {
                "sucesso": False,
                "documentos": [],
                "erro": str(e),
                "fallback": True
            }
    
    def _gerar_embedding_simples(self, texto: str) -> np.ndarray:
        """
        Gera embedding simples baseado em hash (para demo).
        Em produção, usar embeddings reais (SentenceTransformer, etc).
        
        Args:
            texto: Texto para embedar
            
        Returns:
            Array numpy com embedding
        """
        # Hash do texto como seed
        seed = hash(texto) % (2**32)
        rng = np.random.RandomState(seed)
        embedding = rng.randn(self.dimensao_embedding).astype(np.float32)
        
        # Normalizar
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        return embedding
    
    def _busca_manual(self, query_embedding: np.ndarray, top_k: int):
        """Busca manual por similaridade de cosseno (fallback)."""
        if not self.embeddings_cache:
            return np.array([]), np.array([])
        
        scores = []
        for idx, embedding in self.embeddings_cache.items():
            # Similaridade de cosseno
            score = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding) + 1e-8
            )
            scores.append((idx, 1 - score))  # Converter em distância
        
        # Ordenar por distância
        scores.sort(key=lambda x: x[1])
        
        indices = np.array([s[0] for s in scores[:top_k]])
        distances = np.array([s[1] for s in scores[:top_k]])
        
        return indices, distances


# Exportar instância singleton
_rag_singleton: Optional[RAGService] = None


def obter_rag_service(trace_id: Optional[str] = None) -> RAGService:
    """
    Obtém ou cria a instância do RAG Service (singleton).
    
    Args:
        trace_id: ID único para correlação de logs
        
    Returns:
        Instância de RAGService
    """
    global _rag_singleton
    if _rag_singleton is None:
        _rag_singleton = RAGService(trace_id=trace_id)
        _rag_singleton.indexar_diretrizes()
    return _rag_singleton
