# Prompts - Ciclos de Desenvolvimento com IA

Este diretório documenta os prompts utilizados para gerar e refatorar componentes importantes do projeto AcolheCAPS AI, seguindo o padrão **Instrução → Objetivo → Regras → Exemplo**.

## 📋 Prompts Documentados

### 1. [001 - Gerar HITLManager](./001-gerar-hitl-manager.md)
**Tipo**: Criação de código novo  
**Componente**: `app/services/hitl_manager.py`  
**Objetivo**: Implementar gerenciamento de fluxo de aprovação humana no loop

Demonstra como utilizar IA para gerar um serviço complexo que:
- Gerencia fila de aprovações
- Implementa timeout e retry
- Integra com webhook/callback
- Mantém rastreabilidade de decisões

### 2. [002 - Refatorar Observabilidade](./002-refatorar-observabilidade.md)
**Tipo**: Refatoração e melhoria  
**Componente**: `app/services/observability.py`  
**Objetivo**: Aprimorar sistema de observabilidade com sinais correlacionados

Demonstra como utilizar IA para:
- Revisar código existente
- Identificar gaps em observabilidade
- Implementar correlação de traces
- Adicionar métricas de negócio

## 🎯 Padrão de Documentação

Cada prompt segue a estrutura:

```markdown
# [Número] - [Título do Prompt]

## 📌 Metadados
- **Tipo**: Criação / Refatoração / Melhoria
- **Componente**: Path do arquivo afetado
- **Data**: Data da criação/refatoração
- **Status**: Implementado / Em Progresso / Planejado

## 🎯 Objetivo
[Descrição clara do que se deseja alcançar]

## 📋 Instrução
[Prompt exato enviado para IA]

## 🔧 Regras Aplicadas
[Restrições e padrões a seguir]

## 📊 Exemplo
[Antes e depois, ou trecho de resultado]

## ✅ Resultado
[O que foi alcançado]
```

## 🚀 Como Usar Esta Documentação

1. **Para reproduzir**: Copie a instrução do prompt e use em seu LLM favorito
2. **Para aprender**: Estude o padrão de prompting para suas próprias tarefas
3. **Para auditar**: Verifique a rastreabilidade do desenvolvimento IA-assistido

## 📚 Próximos Prompts a Documentar

- RAG Service Refinement
- Anomaly Detection Algorithm
- Security Validation Pipeline
- Test Generation for Edge Cases

---

**Mantido por**: Equipe de Desenvolvimento  
**Última atualização**: Setembro 2026
