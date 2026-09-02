# AcolheCAPS AI - Roadmap de Desenvolvimento

**Status:** Rastreamento de cards de trabalho para controle de progresso e próximos passos.

---

## 📋 Cards de Trabalho (11 Total)

### ✅ Card 1: Arquitetura, Escopo e Schemas Pydantic
**Status:** CONCLUÍDO

**Descrição:** Definir o domínio de triagem do CAPS, classificar o sistema como híbrido e modelar os contratos de dados de entrada e saída.

**Objetivo:** Estruturar a modelagem das entradas do acolhimento e das saídas formatadas.

**Resultado Esperado:** 
- ✅ Classes Pydantic (EntradaAcolhimento e FichaTriagemCAPS)
- ✅ Diagrama de blocos da arquitetura em /docs

**Artefatos:**
- `app/models/acolhimento.py` - Schemas validados
- `steerings/spec.md` - Especificações técnicas

**Branch:** `feature/arquitetura-escopo`
**Commits:** `44de2fd`, `347d3a8`

---

### ✅ Card 2: Orquestração do Grafo Principal com LangGraph
**Status:** CONCLUÍDO

**Descrição:** Construir o fluxo agêntico utilizando StateGraph, nós com responsabilidades isoladas e controle explícito de rotas.

**Objetivo:** Garantir a execução sequencial do fluxo, ramificações condicionais de risco e execução em paralelo.

**Resultado Esperado:**
- ✅ Grafo funcional com State tipado
- ✅ Nós operacionais (extracao, rag, mcp, avaliacao, human-in-the-loop, finalizacao)
- ✅ Execução paralela (node_rag_diretrizes + node_mcp_territorio)
- ✅ Condição de parada contra loops infinitos
- ✅ 17/17 testes passando

**Artefatos:**
- `app/services/graph_service.py` - Orquestração LangGraph
- `tests/unit/test_llm_service.py` - Testes de integração

**Branch:** `feature/arquitetura-escopo`
**Commits:** `5b7473c`, `df2c251`, `4b16ef7`, `b98664f`

---

### ✅ Card 3: Integração da Tool MCP para Validação Territorial
**Status:** CONCLUÍDO

**Descrição:** Implementar uma tool integrada via protocolo MCP para verificar a cobertura do CEP/Bairro do paciente no CAPS da região.

**Objetivo:** Validar o endereço do atendimento com tratamento de exceções de integração.

**Resultado Esperado:**
- ✅ Tool MCP com validação de payload
- ✅ Timeout automático (5 segundos)
- ✅ Fallback em modo degradado
- ✅ 33/33 testes passando
- ✅ Logs estruturados com trace_id
- ✅ Proteção contra prompt injection

**Artefatos:**
- `app/services/mcp_territorial_tool.py` - Tool MCP (370 linhas)
- `tests/unit/test_mcp_territorial.py` - Suite de testes (400 linhas, 33 testes)
- `requirements.txt` - Dependências atualizadas

**Branch:** `feature/mcp-validacao-territorial`
**Commits:** `73ee2ba`, `46eae4c`

---

### ✅ Card 4: Estratégia de Memória e Recuperação RAG
**Status:** CONCLUÍDO

**Descrição:** Configurar a persistência da sessão com checkpointer e a busca vetorial (RAG) em diretrizes clínicas do Ministério da Saúde.

**Objetivo:** Fornecer contexto técnico confiável para o modelo embasar o nível de prioridade do atendimento.

**Resultado Esperado:**
- ✅ Base de conhecimento indexada (FAISS com fallback cosine similarity)
- ✅ 15 diretrizes clínicas cobrindo prioridades baixa, média e alta
- ✅ Recuperação contextual operando dentro do node_rag_diretrizes
- ✅ Checkpointer MemorySaver implementado para estado persistente
- ✅ 29/29 testes passando

**Tecnologias:**
- Busca vetorial com FAISS (fallback: cosine similarity manual)
- LangGraph MemorySaver (checkpointer com thread_id)
- Embeddings hash-based determinísticos (demo)

**Artefatos:**
- `app/services/rag_service.py` - RAGService com indexação e busca semântica
- `tests/unit/test_rag_service.py` - Suite de testes (29 testes)
- `app/services/graph_service.py` - node_rag_diretrizes integrado + MemorySaver

**Branch:** `feature/rag-checkpointer`
**Commits:** `d9b5cb9`, `e3c4b7e`

---

### ✅ Card 5: Controles de Segurança, Human-in-the-Loop e Prompt Injection
**Status:** CONCLUÍDO

**Descrição:** Implementar a interrupção manual para casos de alta prioridade/crise e validar defesas contra entradas maliciosas.

**Objetivo:** Impedir ações não autorizadas e garantir validação do profissional de saúde antes do encerramento da ficha.

**Resultado Esperado:**
- ✅ Human-in-the-loop para prioridades Alta e Média
- ✅ Proteção contra prompt injection no relato
- ✅ Bloqueio de CEPs malformados
- ✅ Relatório de segurança com cenários testados
- ✅ 18 testes E2E (100% passando)

**Tecnologias:**
- Validação Pydantic (regex patterns, keyword detection)
- Tool MCP com normalização de CEP
- LangGraph roteamento condicional (HITL)
- Defesa em 4 camadas

**Artefatos:**
- `app/services/graph_service.py` - node_human_in_the_loop implementado
- `tests/unit/test_security_e2e.py` - 18 testes E2E de segurança
- `docs/SECURITY_REPORT.md` - Relatório completo de segurança
- `tests/unit/test_mcp_territorial.py` - Testes de prompt injection (CEP)

**Branch:** `feature/rag-checkpointer`
**Commits:** `6b50d81`, `a603d32`

---

### ⏳ Card 6: Observabilidade e Logs Estruturados Correlacionados
**Status:** PARCIALMENTE CONCLUÍDO

**Descrição:** Instrumentar a aplicação para emitir logs estruturados em JSON contendo trace_id correlacionado a métricas de execução.

**Objetivo:** Permitir a rastreabilidade completa das decisões do agente, erros e latências sem expor dados sensíveis.

**Resultado Esperado:**
- ✅ Logs em JSON estruturado em todos os nós
- ✅ Trace_id correlacionado (gerado automaticamente)
- ✅ Timestamps ISO em cada operação
- ⏳ Arquivo de log com traces completos de uma requisição

**Artefatos:**
- `app/services/graph_service.py` - Logging integrado
- `app/services/mcp_territorial_tool.py` - Logs estruturados com metadata

**Próximos Passos:**
1. Criar log file com saída de requisição end-to-end
2. Adicionar métricas de latência
3. Documentar padrão de observabilidade

---

### ⏳ Card 7: Code Review e Geração de Testes Automatizados com IA
**Status:** INICIADO

**Descrição:** Utilizar IA para realizar revisão de código (diff/PR) e gerar suíte de testes de integração e E2E.

**Objetivo:** Garantir a cobertura de cenários críticos e tratamento de exceções no motor de triagem.

**Resultado Esperado:**
- Suíte de testes automatizados (integração + E2E)
- Análise de Code Review realizada por IA
- Cobertura de cenários: nominal, exceção, adversarial

**Próximos Passos:**
1. Gerar testes de integração (grafo + MCP + LLM)
2. Gerar testes E2E (cenários completos)
3. Executar code review com IA
4. Documentar análise

---

### ⏳ Card 8: Pipeline de CI e Análise Inteligente de Logs
**Status:** PENDENTE

**Descrição:** Criar automação no GitHub Actions para rodar linter, testes e validações, e aplicar IA para explicar a saída do build.

**Objetivo:** Garantir que novos commits não quebrem a aplicação e automatizar o diagnóstico de falhas no CI.

**Resultado Esperado:**
- Workflow GitHub Actions funcional (lint, test, build)
- Explicação automática de logs via IA
- Build passando com sucesso

**Tecnologias:**
- GitHub Actions
- pylint / flake8
- pytest
- IA para análise de logs

**Próximos Passos:**
1. Criar `.github/workflows/ci.yml`
2. Configurar lint + test + build
3. Integrar análise de logs com IA

---

### ⏳ Card 9: Detecção de Anomalias e Análise de Tendência de Falhas
**Status:** PENDENTE

**Descrição:** Implementar a análise de padrões irregulares nas chamadas de sistema e projetar estimativas simples de risco.

**Objetivo:** Identificar variações na taxa de erros ou latência da API e projetar probabilidade de falhas.

**Resultado Esperado:**
- Relatório de diagnóstico de anomalia
- Evidências de padrões irregulares
- Estimativa simples de tendência de falhas

**Próximos Passos:**
1. Coletar métricas de execução
2. Identificar padrões anormais
3. Gerar relatório com estimativas

---

### ⏳ Card 10: Automação Low-Code/ChatOps para Alertas de Urgência
**Status:** PENDENTE

**Descrição:** Conectar a aplicação a um fluxo visual no n8n ou Make acionado via webhook para enviar alertas.

**Objetivo:** Notificar instantaneamente a equipe do CAPS em um canal de comunicação sobre fichas com risco elevado.

**Resultado Esperado:**
- Workflow low-code funcional (n8n ou Make)
- Mensagens de alerta formatadas
- Integração com Discord/Slack

**Tecnologias:**
- n8n ou Make
- Webhooks
- Discord/Slack API

**Próximos Passos:**
1. Criar workflow no n8n/Make
2. Configurar webhook na aplicação
3. Testar envio de alertas

---

### ⏳ Card 11: Documentação no README.md, Refinamento e Vídeo
**Status:** PENDENTE

**Descrição:** Escrever o README.md completo, organizar as evidências na pasta /docs e gravar o vídeo demonstrativo.

**Objetivo:** Consolidar todas as instruções de execução, decisões de arquitetura e demonstrar os cenários exigidos.

**Resultado Esperado:**
- ✅ README.md completo
- ✅ `.env.example` presente
- ⏳ Pasta `/docs` com evidências
- ⏳ Vídeo demonstrativo (até 12 min)

**Conteúdo README:**
- Visão geral do projeto
- Arquitetura e componentes
- Instalação e setup
- Execução de testes
- Cenários demonstrados
- Contribuições e licença

**Próximos Passos:**
1. Escrever README.md
2. Organizar `/docs` com diagramas e evidências
3. Gravar e publicar vídeo

---

## 📊 Resumo de Progresso

```
Cards Concluídos:      5/11 (45%)
Cards Em Progresso:    0/11 (0%)
Cards Pendentes:       6/11 (55%)

Total de Testes:       80/80 PASSING ✅
- MCP Territorial:     33/33 ✅
- LangGraph:           17/17 ✅
- RAG Service:         29/29 ✅
- Security E2E:        18/18 ✅

Commits Atômicos:      16+ (incluindo Card 4 + Card 5)
Branches Ativas:       1
  - feature/rag-checkpointer (contém Card 4 + 5)
```

---

## 🎯 Prioridade Recomendada

**Curto Prazo (Próximos):**
1. Card 7 - Testes de Integração E2E (suporta avaliação)
2. Card 11 - Documentação final + Vídeo (entrega final)
3. Card 6 - Logs estruturados completos (observabilidade)

**Médio Prazo:**
4. Card 8 - CI/CD Pipeline
5. Card 9 - Anomalia detection
6. Card 10 - Low-Code alertas

**Longo Prazo (Documentação/Refinamento):**
7. Refinements e ajustes finais

---

## 🔗 Rastreabilidade

Todos os cards estão ligados a:
- ✅ Branches Git (`feature/*`)
- ✅ Commits atômicos (Conventional Commits)
- ✅ Testes automatizados
- ✅ Steerings documentados

Para manter rastreabilidade na avaliação:
- Criar issues no GitHub para cada card
- Linkar PRs aos cards/issues
- Adicionar commit hashes nos comentários das issues

---

## 📝 Notas Importantes

- **Sem documentação extra**: Seguir rigorosamente o steering (sem docs desnecessárias)
- **Commits atômicos**: Cada commit é uma unidade lógica isolada
- **Testes primeiro**: Implementar testes conforme o código é escrito
- **Logs estruturados**: JSON com trace_id em todas as operações
- **Segurança**: Validação em camadas, fallback em falhas

---

**Última Atualização:** 2026-09-02  
**Próximo Review:** Após Card 4 (RAG)
