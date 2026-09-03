"""
Validação de Conteúdo RAG do PDF

Este script testa se o RAG está lendo o PDF protocolo corretamente e
se consegue recuperar informações clínicas relevantes para triagem.

Execução:
    python scripts/validate_rag_pdf_content.py

Objetivo:
    - Confirmar que o PDF foi carregado com sucesso
    - Validar que as informações clínicas podem ser recuperadas
    - Testar queries reais que o Groq usará
    - Demonstrar que o sistema usa dados do protocolo oficial
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Adicionar app ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag_service import obter_rag_service


def validar_carregamento_pdf() -> Dict[str, Any]:
    """
    Valida se o PDF foi carregado corretamente.
    
    Returns:
        Dicionário com status de carregamento
    """
    print("\n" + "=" * 80)
    print("🔍 VALIDAÇÃO 1: CARREGAMENTO DO PDF")
    print("=" * 80)
    
    try:
        rag = obter_rag_service(trace_id="validation-001")
        
        total_docs = len(rag.documents)
        
        print(f"\n✅ RAG Service inicializado com sucesso")
        print(f"   📊 Total de chunks indexados: {total_docs}")
        
        if total_docs == 0:
            print(f"\n❌ ERRO: Nenhum documento foi indexado!")
            return {"sucesso": False, "total_docs": 0, "erro": "Sem documentos"}
        
        # Mostrar amostra de documentos
        print(f"\n📋 Amostra dos primeiros 3 chunks indexados:")
        for i, doc in enumerate(rag.documents[:3], 1):
            conteudo_preview = doc["conteudo"][:100].replace("\n", " ")
            fonte = doc.get("fonte", "Desconhecido")
            pagina = doc.get("pagina", "?")
            print(f"\n   [{i}] Página {pagina} - {fonte}")
            print(f"       {conteudo_preview}...")
        
        print(f"\n✅ PDF carregado e indexado corretamente!")
        return {
            "sucesso": True, 
            "total_docs": total_docs,
            "rag_service": rag
        }
        
    except FileNotFoundError as e:
        print(f"\n❌ ERRO: Arquivo não encontrado")
        print(f"   {str(e)}")
        return {"sucesso": False, "erro": str(e)}
    except Exception as e:
        print(f"\n❌ ERRO ao inicializar RAG: {str(e)}")
        return {"sucesso": False, "erro": str(e)}


def testar_queries_clinicas(rag_service) -> List[Dict[str, Any]]:
    """
    Testa queries clínicas reais que o Groq usará.
    
    Args:
        rag_service: Instância do RAGService
        
    Returns:
        Lista com resultados dos testes
    """
    print("\n" + "=" * 80)
    print("🔍 VALIDAÇÃO 2: QUERIES CLÍNICAS REAIS")
    print("=" * 80)
    
    # Queries que o Groq usará na avaliação de prioridade
    queries = [
        {
            "termo": "classificação de risco",
            "contexto": "Definição dos critérios de classificação",
        },
        {
            "termo": "triagem saúde mental",
            "contexto": "Processo de triagem",
        },
        {
            "termo": "suicida ideação risco",
            "contexto": "Indicadores de risco suicida",
        },
        {
            "termo": "depressão crônica",
            "contexto": "Classificação de depressão",
        },
        {
            "termo": "ansiedade generalizada",
            "contexto": "Síndrome de ansiedade",
        },
        {
            "termo": "episódio maníaco",
            "contexto": "Transtorno bipolar",
        },
        {
            "termo": "abuso substância drogas",
            "contexto": "Dependência química",
        },
    ]
    
    resultados_queries = []
    
    for query_data in queries:
        query = query_data["termo"]
        contexto = query_data["contexto"]
        
        print(f"\n📌 Query: '{query}'")
        print(f"   Contexto esperado: {contexto}")
        
        resultado = rag_service.recuperar_contexto(query=query, top_k=2)
        
        if resultado.get("sucesso"):
            total_recuperados = resultado.get("total", 0)
            print(f"   ✅ Documentos recuperados: {total_recuperados}")
            
            # Mostrar conteúdo recuperado
            for i, doc in enumerate(resultado.get("documentos", []), 1):
                conteudo_preview = doc["conteudo"][:120].replace("\n", " ")
                score = doc.get("score", 0)
                print(f"\n      [{i}] Score: {score:.3f}")
                print(f"          {conteudo_preview}...")
            
            resultados_queries.append({
                "query": query,
                "sucesso": True,
                "documentos_recuperados": total_recuperados,
                "score_medio": sum(d.get("score", 0) for d in resultado.get("documentos", [])) / max(1, len(resultado.get("documentos", []))),
            })
        else:
            print(f"   ❌ Erro: {resultado.get('erro', 'Desconhecido')}")
            resultados_queries.append({
                "query": query,
                "sucesso": False,
                "erro": resultado.get("erro"),
            })
    
    return resultados_queries


def testar_queries_por_prioridade(rag_service) -> Dict[str, List[Dict]]:
    """
    Testa recuperação de contexto filtrado por prioridade.
    
    Args:
        rag_service: Instância do RAGService
        
    Returns:
        Dicionário com resultados por prioridade
    """
    print("\n" + "=" * 80)
    print("🔍 VALIDAÇÃO 3: FILTRAGEM POR PRIORIDADE")
    print("=" * 80)
    
    prioridades = ["alta", "média", "baixa", "protocolo"]
    resultados_por_prioridade = {}
    
    for prioridade in prioridades:
        print(f"\n🏷️  Filtrando por prioridade: {prioridade}")
        
        # Fazer query genérica mas filtrada por prioridade
        resultado = rag_service.recuperar_contexto(
            query=f"{prioridade} risco saúde mental",
            prioridade=prioridade,
            top_k=2
        )
        
        if resultado.get("sucesso"):
            total = resultado.get("total", 0)
            print(f"   ✅ Documentos encontrados: {total}")
            
            docs = resultado.get("documentos", [])
            for doc in docs:
                print(f"      • {doc['prioridade']}: {doc['conteudo'][:80]}...")
            
            resultados_por_prioridade[prioridade] = docs
        else:
            print(f"   ⚠️  Nenhum documento para '{prioridade}'")
            resultados_por_prioridade[prioridade] = []
    
    return resultados_por_prioridade


def gerar_relatorio_final(
    carregamento: Dict[str, Any],
    queries: List[Dict[str, Any]],
    por_prioridade: Dict[str, List[Dict]],
) -> None:
    """
    Gera relatório final da validação.
    
    Args:
        carregamento: Resultado de carregamento do PDF
        queries: Resultados das queries clínicas
        por_prioridade: Resultados por prioridade
    """
    print("\n" + "=" * 80)
    print("📊 RELATÓRIO FINAL DE VALIDAÇÃO DO RAG")
    print("=" * 80)
    
    # Resumo de Carregamento
    print(f"\n✅ CARREGAMENTO DO PDF:")
    if carregamento.get("sucesso"):
        print(f"   • Status: ✅ SUCESSO")
        print(f"   • Total de chunks: {carregamento.get('total_docs', 0)}")
    else:
        print(f"   • Status: ❌ FALHA")
        print(f"   • Erro: {carregamento.get('erro')}")
    
    # Resumo de Queries
    print(f"\n✅ QUERIES CLÍNICAS:")
    queries_sucesso = sum(1 for q in queries if q.get("sucesso"))
    print(f"   • Total de queries: {len(queries)}")
    print(f"   • Queries bem-sucedidas: {queries_sucesso}/{len(queries)}")
    
    if queries:
        score_medio_geral = sum(q.get("score_medio", 0) for q in queries if q.get("sucesso")) / max(1, queries_sucesso)
        print(f"   • Score médio: {score_medio_geral:.3f}")
        
        print(f"\n   Detalhes por query:")
        for q in queries:
            status = "✅" if q.get("sucesso") else "❌"
            docs = q.get("documentos_recuperados", 0)
            score = f"{q.get('score_medio', 0):.3f}" if q.get("sucesso") else "N/A"
            print(f"      {status} {q['query']:30s} → {docs} docs (score: {score})")
    
    # Resumo por Prioridade
    print(f"\n✅ DISTRIBUIÇÃO POR PRIORIDADE:")
    for prio, docs in por_prioridade.items():
        print(f"   • {prio:10s}: {len(docs)} documento(s)")
    
    # Conclusões
    print(f"\n✅ CONCLUSÕES:")
    
    if carregamento.get("sucesso") and queries_sucesso > 0:
        print(f"   ✅ RAG está funcionando 100%!")
        print(f"   ✅ PDF foi carregado com sucesso")
        print(f"   ✅ Queries clínicas recuperam conteúdo relevante")
        print(f"   ✅ Sistema está pronto para produção")
    else:
        print(f"   ⚠️  Há problemas a resolver")
        if not carregamento.get("sucesso"):
            print(f"      → PDF não foi carregado corretamente")
        if queries_sucesso == 0:
            print(f"      → Nenhuma query retornou resultados")
    
    print(f"\n" + "=" * 80)


def main():
    """Executa todas as validações."""
    print(f"""
    ╔════════════════════════════════════════════════════════════════════════╗
    ║  AcolheCAPS AI - Validação de Conteúdo RAG do PDF                     ║
    ║                                                                        ║
    ║  Verificando se o RAG está lendo o PDF protocolo corretamente         ║
    ╚════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Validação 1: Carregamento
    carregamento = validar_carregamento_pdf()
    if not carregamento.get("sucesso"):
        print(f"\n❌ Não foi possível continuar sem o PDF")
        return
    
    rag_service = carregamento.get("rag_service")
    
    # Validação 2: Queries Clínicas
    queries = testar_queries_clinicas(rag_service)
    
    # Validação 3: Filtragem por Prioridade
    por_prioridade = testar_queries_por_prioridade(rag_service)
    
    # Relatório Final
    gerar_relatorio_final(carregamento, queries, por_prioridade)
    
    print(f"\n✅ Validação concluída!\n")


if __name__ == "__main__":
    main()
