# Fluxo do Sistema - AcolheCAPS AI

## Diagrama de Arquitetura

```
┌─────────────────────┐
│  ENTRADA PACIENTE   │
│ (relato + CEP)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  node_extracao      │
│ (normaliza relato)  │
└──────────┬──────────┘
           │
      ┌────┴────┐
      │          │
      ▼          ▼
┌──────────┐ ┌──────────┐
│ node_RAG │ │node_MCP  │  (PARALELO)
│(diretrizes)│(CEP OK?) │
└────┬─────┘ └────┬─────┘
     │            │
     └────┬───────┘
          ▼
┌─────────────────────┐
│ node_avaliacao_risco│
│ (classifica risco)  │
└──────────┬──────────┘
           │
      ┌────┴────────┐
      │             │
      ▼             ▼
    BAIXA      MÉDIA/ALTA
      │             │
      ▼             ▼
 FINALIZACAO  node_HITL
      │       (aguarda aprovação)
      │             │
      └─────┬───────┘
            ▼
     ┌─────────────┐
     │ FINALIZACAO │
     │ (webhook)   │
     └──────┬──────┘
            ▼
     ┌─────────────┐
     │ n8n Discord │
     │ (alerta)    │
     └─────────────┘
```

## Fluxo Passo a Passo

1. **Entrada**: Paciente envia relato + CEP
2. **Extração**: Normaliza o relato (limpeza, validação)
3. **Paralelo**:
   - **RAG**: Busca diretrizes clínicas relevantes
   - **MCP**: Valida se CEP está na cobertura territorial
4. **Avaliação de Risco**: Consolida contexto e classifica em Baixa, Média ou Alta
5. **Condicional**:
   - **Se Baixa**: Vai direto para Finalizacao
   - **Se Média/Alta**: Ativa node_HITL (Human-in-the-Loop)
6. **HITL**: Profissional de saúde revisa e aprova
7. **Finalizacao**: Gera ficha de triagem
8. **Webhook**: Dispara alerta para n8n (se Média/Alta)
9. **Discord**: n8n envia alerta para equipe de plantão

## Componentes Principais

| Componente | Função | Status |
|-----------|--------|--------|
| node_extracao | Normalizar e validar relato | ✅ |
| node_rag_diretrizes | RAG com protocolo clínico | ✅ |
| node_mcp_territorio | Validar CEP e cobertura | ✅ |
| node_avaliacao_risco | Classificar prioridade | ✅ |
| node_human_in_the_loop | Aprovação humana | ✅ |
| node_finalizacao | Gerar ficha e webhook | ✅ |

## Integrações Externas

- **Groq LLM**: Modelo de linguagem para análise
- **FAISS**: Indexação vetorial para RAG
- **n8n**: Orquestração low-code
- **Discord**: Canal de notificações
- **GitHub Actions**: CI/CD pipeline

## Cenários de Uso

### Cenário 1: Risco Baixo (Fluxo Direto)
```
Entrada → Extracao → (RAG + MCP) → Avaliacao → BAIXA → Finalizacao → [FIM]
```

### Cenário 2: Risco Médio/Alto (Com HITL)
```
Entrada → Extracao → (RAG + MCP) → Avaliacao → MÉDIA/ALTA → HITL → Finalizacao → Webhook → Discord
```

## Características Principais

✅ **Paralelismo**: RAG e MCP executam simultaneamente  
✅ **Human-in-the-Loop**: Aprovação obrigatória para risco alto  
✅ **Rastreabilidade**: Cada requisição tem trace_id correlacionado  
✅ **Segurança**: 4 camadas de validação (bloqueio de injeção)  
✅ **Observabilidade**: Logs JSON estruturados em cada node  
✅ **Automação**: Webhooks para n8n dispararem alertas  

