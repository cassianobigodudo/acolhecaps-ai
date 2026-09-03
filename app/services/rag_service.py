"""
Serviço de RAG (Retrieval Augmented Generation) com FAISS.

Este módulo implementa recuperação de contexto a partir de diretrizes clínicas
do Ministério da Saúde para embasar as decisões de triagem do agente.

Características:
- Indexação vetorial com FAISS
- Diretrizes clínicas pré-indexadas
- Suporte a PDFs customizados
- Busca semântica por similaridade
- Cache de embeddings
- Logging estruturado com trace_id
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class DiretrizesClinicas:
    """Base de diretrizes clínicas do Ministério da Saúde para CAPS."""

    # Diretrizes para diferentes níveis de prioridade
    DIRETRIZES = {
        "baixa": [
            "Transtornos de ansiedade leve: técnicas de respiração, mindfulness, "
            "suporte em grupos de autoajuda",
            "Stress relacionado a trabalho: orientação profissional, "
            "relaxamento muscular, oficinas de resiliência",
            "Sintomas de tristeza leve: acompanhamento psicossocial, "
            "oficinas terapêuticas, suporte familiar",
            "Insônia moderada: higiene do sono, meditação guiada, "
            "atividades recreativas estruturadas",
        ],
        "media": [
            "Transtornos de ansiedade moderada: psicoterapia cognitivo-comportamental, "
            "possível farmacoterapia",
            "Depressão leve a moderada: acompanhamento psicológico regular, "
            "intervenções psicossociais",
            "Sintomas obsessivo-compulsivos: exposição e prevenção de resposta (EPR), "
            "suporte multiprofissional",
            "Abuso de substâncias inicial: avaliação de dependência, "
            "psicoeducação, redução de danos",
            "Crises de pânico: técnicas de controle de respiração, "
            "exposição gradual, TCC especializada",
        ],
        "alta": [
            "Risco de autolesão ou suicídio: avaliação imediata, "
            "acompanhamento psiquiátrico diário, plano de segurança",
            "Psicose aguda: encaminhamento para serviço especializado, "
            "possível internação, medicação antipsicótica",
            "Crise de ansiedade severa: intervenção em crise, medicação ansiosa, "
            "acompanhamento contínuo",
            "Risco de violência: avaliação forense, medidas de proteção, "
            "envolvimento de segurança pública",
            "Surto maníaco ou depressivo severo: internação, medicalização urgente, "
            "acompanhamento psiquiátrico",
            "Ideação suicida com plano: encaminhamento imediato, monitoramento 24h, "
            "envolvimento de profissional urgentista",
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
            json.dumps(
                {
                    "trace_id": self.trace_id,
                    "evento": "rag_service_inicializado",
                    "timestamp": self._timestamp_iso(),
                }
            )
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
            json.dumps(
                {
                    "trace_id": self.trace_id,
                    "evento": "indexacao_iniciada",
                    "timestamp": self._timestamp_iso(),
                }
            )
        )

        try:
            # Coletar todas as diretrizes
            todos_docs = []
            for prioridade in ["baixa", "media", "alta"]:
                diretrizes = DiretrizesClinicas.obter_por_prioridade(prioridade)
                for diretriz in diretrizes:
                    todos_docs.append({"conteudo": diretriz, "prioridade": prioridade})

            # Gerar embeddings simples (hash-based para demo)
            embeddings = np.array(
                [self._gerar_embedding_simples(doc["conteudo"]) for doc in todos_docs],
                dtype=np.float32,
            )

            # Criar índice FAISS
            try:
                import faiss

                self.index = faiss.IndexFlatL2(self.dimensao_embedding)
                self.index.add(embeddings)
            except ImportError:
                # Fallback: usar índice em memória
                logger.warning(
                    json.dumps(
                        {
                            "trace_id": self.trace_id,
                            "evento": "faiss_nao_disponivel_usando_fallback",
                            "timestamp": self._timestamp_iso(),
                        }
                    )
                )
                self.index = None

            self.documents = todos_docs
            self.embeddings_cache = {i: embeddings[i] for i in range(len(embeddings))}

            logger.info(
                json.dumps(
                    {
                        "trace_id": self.trace_id,
                        "evento": "indexacao_concluida",
                        "total_documentos": len(todos_docs),
                        "timestamp": self._timestamp_iso(),
                    }
                )
            )

            return {"sucesso": True, "total_documentos": len(todos_docs), "status": "indexado"}

        except Exception as e:
            logger.error(
                json.dumps(
                    {
                        "trace_id": self.trace_id,
                        "evento": "erro_indexacao",
                        "erro": str(e),
                        "timestamp": self._timestamp_iso(),
                    }
                )
            )
            raise

    def recuperar_contexto(
        self, query: str, prioridade: Optional[str] = None, top_k: int = 3
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
            json.dumps(
                {
                    "trace_id": self.trace_id,
                    "evento": "recuperacao_iniciada",
                    "query": query[:50],
                    "prioridade_filtro": prioridade,
                    "timestamp": self._timestamp_iso(),
                }
            )
        )

        try:
            if not self.documents:
                logger.warning(
                    json.dumps(
                        {
                            "trace_id": self.trace_id,
                            "evento": "base_vazia",
                            "timestamp": self._timestamp_iso(),
                        }
                    )
                )
                return {
                    "sucesso": False,
                    "documentos": [],
                    "total": 0,
                    "mensagem": "Base de diretrizes não indexada",
                    "fallback": True,
                }

            # Gerar embedding da query
            query_embedding = self._gerar_embedding_simples(query)

            # Busca com FAISS se disponível
            if self.index is not None:
                distances, indices = self.index.search(
                    np.array([query_embedding], dtype=np.float32), min(top_k, len(self.documents))
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

                documentos.append(
                    {
                        "conteudo": doc["conteudo"],
                        "prioridade": doc["prioridade"],
                        "score": float(1 / (1 + distance)),  # Converter distância em score
                    }
                )

            logger.info(
                json.dumps(
                    {
                        "trace_id": self.trace_id,
                        "evento": "recuperacao_concluida",
                        "documentos_recuperados": len(documentos),
                        "timestamp": self._timestamp_iso(),
                    }
                )
            )

            return {
                "sucesso": True,
                "documentos": documentos,
                "total": len(documentos),
                "fallback": self.index is None,
            }

        except Exception as e:
            logger.error(
                json.dumps(
                    {
                        "trace_id": self.trace_id,
                        "evento": "erro_recuperacao",
                        "erro": str(e),
                        "timestamp": self._timestamp_iso(),
                    }
                )
            )
            return {"sucesso": False, "documentos": [], "erro": str(e), "fallback": True}

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

    def carregar_pdf_protocolo(self, caminho_pdf: str) -> Dict:
        """
        Carrega um PDF de protocolo e indexa seu conteúdo.
        
        Args:
            caminho_pdf: Caminho para o arquivo PDF
            
        Returns:
            Dicionário com status do carregamento
        """
        try:
            import pdfplumber
        except ImportError:
            logger.warning(
                json.dumps(
                    {
                        "trace_id": self.trace_id,
                        "evento": "pdfplumber_nao_instalado",
                        "timestamp": self._timestamp_iso(),
                    }
                )
            )
            return {"sucesso": False, "erro": "pdfplumber não instalado"}

        logger.info(
            json.dumps(
                {
                    "trace_id": self.trace_id,
                    "evento": "carregamento_pdf_iniciado",
                    "arquivo": caminho_pdf,
                    "timestamp": self._timestamp_iso(),
                }
            )
        )

        try:
            documentos_pdf = []
            
            with pdfplumber.open(caminho_pdf) as pdf:
                total_paginas = len(pdf.pages)
                
                for num_pagina, page in enumerate(pdf.pages, 1):
                    texto = page.extract_text()
                    
                    if texto and texto.strip():
                        # Dividir em chunks pequenos para melhor retrieval
                        chunks = self._dividir_em_chunks(texto, tamanho=500)
                        
                        for chunk in chunks:
                            documentos_pdf.append({
                                "conteudo": chunk,
                                "prioridade": "protocolo",
                                "fonte": Path(caminho_pdf).name,
                                "pagina": num_pagina,
                            })
            
            # Adicionar aos documentos existentes
            self.documents.extend(documentos_pdf)
            
            # Reindexar tudo
            self.indexar_diretrizes()
            
            logger.info(
                json.dumps(
                    {
                        "trace_id": self.trace_id,
                        "evento": "pdf_carregado_com_sucesso",
                        "arquivo": caminho_pdf,
                        "total_chunks": len(documentos_pdf),
                        "timestamp": self._timestamp_iso(),
                    }
                )
            )
            
            return {
                "sucesso": True,
                "arquivo": Path(caminho_pdf).name,
                "total_paginas": total_paginas,
                "total_chunks": len(documentos_pdf),
                "status": "indexado"
            }
            
        except Exception as e:
            logger.error(
                json.dumps(
                    {
                        "trace_id": self.trace_id,
                        "evento": "erro_carregamento_pdf",
                        "arquivo": caminho_pdf,
                        "erro": str(e),
                        "timestamp": self._timestamp_iso(),
                    }
                )
            )
            return {"sucesso": False, "erro": str(e), "arquivo": caminho_pdf}

    @staticmethod
    def _dividir_em_chunks(texto: str, tamanho: int = 500, sobreposicao: int = 100) -> List[str]:
        """
        Divide texto em chunks com sobreposição.
        
        Args:
            texto: Texto a dividir
            tamanho: Tamanho máximo de cada chunk
            sobreposicao: Número de caracteres de sobreposição entre chunks
            
        Returns:
            Lista de chunks
        """
        chunks = []
        inicio = 0
        
        while inicio < len(texto):
            fim = min(inicio + tamanho, len(texto))
            chunk = texto[inicio:fim].strip()
            
            if chunk:
                chunks.append(chunk)
            
            # Mover para próximo chunk com sobreposição
            inicio += (tamanho - sobreposicao)
        
        return chunks if chunks else [texto]


# Exportar instância singleton
_rag_singleton: Optional[RAGService] = None


def obter_rag_service(trace_id: Optional[str] = None) -> RAGService:
    """
    Obtém ou cria a instância do RAG Service (singleton).
    
    Carrega automaticamente:
    1. Diretrizes clínicas hardcoded
    2. PDF de protocolo se existir em docs/

    Args:
        trace_id: ID único para correlação de logs

    Returns:
        Instância de RAGService
    """
    global _rag_singleton
    if _rag_singleton is None:
        _rag_singleton = RAGService(trace_id=trace_id)
        _rag_singleton.indexar_diretrizes()
        
        # Tentar carregar PDF de protocolo se existir
        pdf_protocolo = Path(__file__).parent.parent.parent / "docs" / "PROTOCOLO -CLASSIFICACAO-DE-RISCO-EM-SAUDE-MENTAL.pdf"
        if pdf_protocolo.exists():
            logger.info(f"Carregando PDF de protocolo: {pdf_protocolo}")
            resultado = _rag_singleton.carregar_pdf_protocolo(str(pdf_protocolo))
            logger.info(f"Resultado do carregamento: {resultado}")
    
    return _rag_singleton
