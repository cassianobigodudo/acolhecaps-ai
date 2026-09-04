# Prompt #001: Gerar HITLManager Service

**Tipo:** Feature Implementation  
**Data:** 2026-08-25  
**Status:** ✅ Implementado em `app/services/hitl_manager.py`  
**Commit:** `6a6eefb` (feat: implement real HITL without simulations)

---

## 📋 ESTRUTURA DO PROMPT

### **INSTRUÇÃO**
Crie um serviço para gerenciar fichas de saúde mental em estado "Human-in-the-Loop" (HITL), permitindo que profissionais de saúde aprovem ou corrijam a classificação da IA antes de finalizar a triagem.

### **OBJETIVO**
Implementar um `HITLManager` que:
1. Armazene fichas pendentes (status = "pendente")
2. Permita aprovação ou correção da ficha
3. Atualize metadados (profissional, data, observações)
4. Retorne mensagens formatadas para Discord

### **REGRAS**
1. Usar padrão Singleton para manter estado compartilhado
2. Não usar banco de dados (apenas dict em memória para MVP)
3. Sempre registrar trace_id para rastreabilidade
4. Validar prioridade (só permite: Alta, Média, Baixa)
5. Diferenciar aprovação (profissional concorda) de correção (profissional discorda)
6. Gerar mensagem Discord com status, prioridade, profissional e observações
7. Retornar cor do embed: Amarelo (Média), Vermelho (Alta)

### **EXEMPLO DE ENTRADA**
```json
{
  "trace_id": "trace-20260825120000-abc123",
  "ficha_triagem": {
    "nivel_prioridade": "Média",
    "fatores_risco": ["Depressão moderada", "Absenteísmo"],
    "encaminhamento_recomendado": "Psicólogo + Grupo de Apoio",
    "status_aprovacao": "pendente"
  }
}
```

### **EXEMPLO DE SAÍDA (Aprovação)**
```json
{
  "status": "sucesso",
  "trace_id": "trace-20260825120000-abc123",
  "ficha_triagem": {
    "nivel_prioridade": "Média",
    "status_aprovacao": "aprovado",
    "data_aprovacao": "2026-08-25T12:01:00",
    "profissional_aprovador": {
      "nome": "Dr. Silva",
      "profissao": "Psicólogo"
    },
    "observacoes": "Classificação validada pelo profissional"
  },
  "mensagem_discord": "⚠️ **HITL - Prioridade Média**\n\n**Status:** APROVADO\n**Encaminhamento:** Psicólogo + Grupo de Apoio\n...",
  "cor_discord": 16776960
}
```

---

## 📝 CÓDIGO GERADO

```python
class HITLManager:
    """Gerencia fichas em estado HITL (Human-in-the-Loop)."""

    def __init__(self):
        """Inicializa manager com dicionário de fichas pendentes."""
        self._fichas_pendentes: Dict[str, Dict] = {}

    def registrar_ficha_pendente(self, trace_id: str, ficha_triagem: Dict) -> None:
        """Registra uma ficha que está aguardando aprovação."""
        if ficha_triagem.get("status_aprovacao") == "pendente":
            self._fichas_pendentes[trace_id] = ficha_triagem.copy()
            logger.info(f"Ficha registrada como pendente | trace_id={trace_id}")

    def aprovar_ficha(self, trace_id: str, ...) -> Dict:
        """Aprova uma ficha pendente."""
        ficha = self._fichas_pendentes.get(trace_id)
        ficha["status_aprovacao"] = "aprovado"
        ficha["data_aprovacao"] = datetime.utcnow().isoformat()
        return ficha

    def corrigir_ficha(self, trace_id: str, nivel_prioridade_corrigido: str, ...) -> Dict:
        """Corrige uma ficha pendente (muda prioridade/encaminhamento)."""
        ficha = self._fichas_pendentes.get(trace_id)
        ficha["status_aprovacao"] = "corrigido"
        ficha["nivel_prioridade_original"] = ficha.get("nivel_prioridade")
        ficha["nivel_prioridade"] = nivel_prioridade_corrigido
        return ficha

    def gerar_mensagem_discord(self, trace_id: str, ficha: Dict) -> tuple:
        """Gera (mensagem_texto, cor_hex) para Discord."""
        status = ficha.get("status_aprovacao", "").upper()
        prioridade = ficha.get("nivel_prioridade")
        
        # Cores: Média → Amarelo (16776960), Alta → Vermelho (16711680)
        cores = {"Média": 16776960, "Alta": 16711680}
        cor = cores.get(prioridade, 9807270)
        
        mensagem = f"{'⚠️' if prioridade == 'Média' else '🚨'} **HITL - Prioridade {prioridade}**\n\n"
        mensagem += f"**Status:** {status}\n"
        mensagem += f"**Trace ID:** `{trace_id}`"
        
        return mensagem, cor
```

---

## ✅ VALIDAÇÃO

- ✅ Singleton implementado
- ✅ Métodos: registrar, obter, listar, aprovar, corrigir
- ✅ Mensagem Discord com cores
- ✅ Logging com trace_id
- ✅ Teste: `HITLManager` com 3 fichas, aprova 1, corrige 1
- ✅ Integrado em `main.py` endpoints

---

## 🔗 REFERÊNCIAS

- **Arquivo:** `app/services/hitl_manager.py` (linha 1-200)
- **Endpoint:** `POST /acolhimento/hitl` em `main.py` (linha 167-410)
- **Teste:** `test_hitl_e2e.py` - Validação end-to-end
- **Commit:** `6a6eefb` - Real HITL implementation

