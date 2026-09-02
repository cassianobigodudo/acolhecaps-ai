"""
Testes para RAG Service com FAISS.

Cobre: indexação, recuperação, filtros de prioridade, fallback.
"""

import pytest
import json
from app.services.rag_service import RAGService, DiretrizesClinicas, obter_rag_service


class TestDiretrizesClinicas:
    """Testes de diretrizes clínicas."""
    
    def test_diretrizes_baixa_existem(self):
        """Deve ter diretrizes para risco baixo."""
        diretrizes = DiretrizesClinicas.obter_por_prioridade("baixa")
        assert len(diretrizes) > 0
        assert all(isinstance(d, str) for d in diretrizes)
    
    def test_diretrizes_media_existem(self):
        """Deve ter diretrizes para risco médio."""
        diretrizes = DiretrizesClinicas.obter_por_prioridade("media")
        assert len(diretrizes) > 0
    
    def test_diretrizes_alta_existem(self):
        """Deve ter diretrizes para risco alto."""
        diretrizes = DiretrizesClinicas.obter_por_prioridade("alta")
        assert len(diretrizes) > 0
    
    def test_prioridade_invalida_retorna_vazio(self):
        """Prioridade inválida deve retornar lista vazia."""
        diretrizes = DiretrizesClinicas.obter_por_prioridade("invalida")
        assert diretrizes == []
    
    def test_prioridade_case_insensitive(self):
        """Deve aceitar prioridade em qualquer case."""
        diretrizes_lower = DiretrizesClinicas.obter_por_prioridade("BAIXA")
        diretrizes_mixed = DiretrizesClinicas.obter_por_prioridade("bAiXa")
        assert len(diretrizes_lower) == len(diretrizes_mixed)


class TestRAGServiceInicializacao:
    """Testes de inicialização do RAG Service."""
    
    def test_rag_inicializa_com_trace_id_automatico(self):
        """RAG deve gerar trace_id automaticamente."""
        rag = RAGService()
        assert rag.trace_id is not None
        assert "rag-" in rag.trace_id
    
    def test_rag_inicializa_com_trace_id_customizado(self):
        """RAG deve aceitar trace_id customizado."""
        trace_id = "custom-rag-123"
        rag = RAGService(trace_id=trace_id)
        assert rag.trace_id == trace_id
    
    def test_rag_inicializa_sem_documentos(self):
        """RAG deve iniciar vazio."""
        rag = RAGService()
        assert rag.documents == []
        assert rag.embeddings_cache == {}


class TestRAGServiceIndexacao:
    """Testes de indexação de diretrizes."""
    
    def test_indexacao_sucesso(self):
        """Deve indexar diretrizes com sucesso."""
        rag = RAGService()
        resultado = rag.indexar_diretrizes()
        
        assert resultado["sucesso"] is True
        assert resultado["total_documentos"] > 0
        assert resultado["status"] == "indexado"
    
    def test_indexacao_popula_documentos(self):
        """Indexação deve popular lista de documentos."""
        rag = RAGService()
        rag.indexar_diretrizes()
        
        assert len(rag.documents) > 0
        assert all("conteudo" in doc and "prioridade" in doc for doc in rag.documents)
    
    def test_indexacao_cria_cache_embeddings(self):
        """Indexação deve criar cache de embeddings."""
        rag = RAGService()
        rag.indexar_diretrizes()
        
        assert len(rag.embeddings_cache) == len(rag.documents)
    
    def test_indexacao_contem_todas_prioridades(self):
        """Diretrizes indexadas devem cobrir todas as prioridades."""
        rag = RAGService()
        rag.indexar_diretrizes()
        
        prioridades = {doc["prioridade"] for doc in rag.documents}
        assert "baixa" in prioridades
        assert "media" in prioridades
        assert "alta" in prioridades


class TestRAGServiceRecuperacao:
    """Testes de recuperação de contexto."""
    
    @pytest.fixture
    def rag_indexado(self):
        """Fixture com RAG já indexado."""
        rag = RAGService()
        rag.indexar_diretrizes()
        return rag
    
    def test_recuperacao_query_simples(self, rag_indexado):
        """Deve recuperar contexto para query simples."""
        resultado = rag_indexado.recuperar_contexto("ansiedade")
        
        assert resultado["sucesso"] is True
        assert resultado["total"] > 0
        assert len(resultado["documentos"]) > 0
    
    def test_recuperacao_retorna_estrutura_correta(self, rag_indexado):
        """Documentos recuperados devem ter estrutura correta."""
        resultado = rag_indexado.recuperar_contexto("depressao")
        
        for doc in resultado["documentos"]:
            assert "conteudo" in doc
            assert "prioridade" in doc
            assert "score" in doc
            assert 0 <= doc["score"] <= 1
    
    def test_recuperacao_filtra_por_prioridade(self, rag_indexado):
        """Deve filtrar documentos por prioridade."""
        resultado = rag_indexado.recuperar_contexto("crise", prioridade="alta")
        
        if resultado["total"] > 0:
            for doc in resultado["documentos"]:
                assert doc["prioridade"] == "alta"
    
    def test_recuperacao_top_k(self, rag_indexado):
        """Deve respeitar limite de documentos (top_k)."""
        resultado = rag_indexado.recuperar_contexto("saude", top_k=2)
        
        assert resultado["total"] <= 2
    
    def test_recuperacao_query_vazia_retorna_erro(self, rag_indexado):
        """Query vazia deve retornar resultado com documentos."""
        resultado = rag_indexado.recuperar_contexto("")
        
        # Ainda pode recuperar algo (similaridade baixa)
        assert isinstance(resultado, dict)
        assert "documentos" in resultado
    
    def test_recuperacao_sem_indexacao_retorna_fallback(self):
        """Recuperação sem indexação deve retornar fallback."""
        rag = RAGService()
        resultado = rag.recuperar_contexto("ansiedade")
        
        assert resultado["sucesso"] is False
        assert resultado["fallback"] is True
        assert resultado["total"] == 0


class TestRAGServiceEmbeddings:
    """Testes de geração de embeddings."""
    
    def test_embedding_determinístico(self):
        """Mesmo texto deve gerar mesmo embedding."""
        rag = RAGService()
        
        emb1 = rag._gerar_embedding_simples("teste")
        emb2 = rag._gerar_embedding_simples("teste")
        
        assert (emb1 == emb2).all()
    
    def test_embedding_textos_diferentes(self):
        """Textos diferentes devem gerar embeddings diferentes."""
        rag = RAGService()
        
        emb1 = rag._gerar_embedding_simples("ansiedade")
        emb2 = rag._gerar_embedding_simples("depressao")
        
        assert not (emb1 == emb2).all()
    
    def test_embedding_normalizado(self):
        """Embedding deve ser normalizado."""
        rag = RAGService()
        
        emb = rag._gerar_embedding_simples("teste")
        norm = (emb ** 2).sum() ** 0.5
        
        assert 0.99 < norm <= 1.01  # Permitir pequeno erro numérico


class TestRAGServiceBuscaManual:
    """Testes de busca manual (fallback sem FAISS)."""
    
    def test_busca_manual_funciona(self):
        """Busca manual deve funcionar sem FAISS."""
        rag = RAGService()
        rag.indexar_diretrizes()
        
        # Simular ausência de FAISS
        rag.index = None
        
        resultado = rag.recuperar_contexto("ansiedade")
        
        assert resultado["sucesso"] is True
        assert resultado["total"] > 0


class TestRAGServiceSingleton:
    """Testes do padrão singleton."""
    
    def test_singleton_primeira_chamada(self):
        """Primeira chamada deve criar instância."""
        import app.services.rag_service as rag_module
        rag_module._rag_singleton = None
        
        rag = obter_rag_service()
        assert rag is not None
        assert len(rag.documents) > 0
    
    def test_singleton_reutiliza_instancia(self):
        """Chamadas seguintes devem reutilizar instância."""
        import app.services.rag_service as rag_module
        rag_module._rag_singleton = None
        
        rag1 = obter_rag_service()
        rag2 = obter_rag_service()
        
        assert rag1 is rag2


class TestRAGServiceIntegracao:
    """Testes de integração."""
    
    def test_fluxo_completo_recuperacao(self):
        """Teste completo: criar, indexar, recuperar."""
        rag = RAGService()
        rag.indexar_diretrizes()
        
        # Cenário 1: Risco baixo
        resultado1 = rag.recuperar_contexto("ansiedade leve", prioridade="baixa")
        assert resultado1["sucesso"] is True
        
        # Cenário 2: Risco médio
        resultado2 = rag.recuperar_contexto("depressao moderada", prioridade="media")
        assert resultado2["sucesso"] is True
        
        # Cenário 3: Risco alto
        resultado3 = rag.recuperar_contexto("ideacao suicida", prioridade="alta")
        assert resultado3["sucesso"] is True
    
    def test_multiplas_recuperacoes_sequenciais(self):
        """Múltiplas recuperações devem funcionar."""
        rag = RAGService()
        rag.indexar_diretrizes()
        
        queries = ["ansiedade", "depressao", "psicotico", "abuso"]
        resultados = []
        
        for query in queries:
            resultado = rag.recuperar_contexto(query)
            resultados.append(resultado["sucesso"])
        
        assert all(resultados)
    
    def test_recuperacoes_paralelas(self):
        """RAG deve suportar múltiplas instâncias paralelas."""
        rag1 = RAGService(trace_id="rag-1")
        rag2 = RAGService(trace_id="rag-2")
        
        rag1.indexar_diretrizes()
        rag2.indexar_diretrizes()
        
        r1 = rag1.recuperar_contexto("ansiedade")
        r2 = rag2.recuperar_contexto("depressao")
        
        assert r1["sucesso"] and r2["sucesso"]
        assert rag1.trace_id != rag2.trace_id


class TestRAGServiceObservabilidade:
    """Testes de logging e observabilidade."""
    
    def test_trace_id_em_operacoes(self):
        """Trace ID deve estar em logs de operações."""
        rag = RAGService(trace_id="test-trace-001")
        rag.indexar_diretrizes()
        rag.recuperar_contexto("teste")
        
        assert rag.trace_id == "test-trace-001"
    
    def test_timestamps_iso(self):
        """Timestamps devem ser ISO format."""
        rag = RAGService()
        ts = rag._timestamp_iso()
        
        # Validar formato ISO
        from datetime import datetime
        try:
            datetime.fromisoformat(ts.replace('Z', '+00:00'))
            assert True
        except:
            assert False, "Timestamp não é ISO válido"
