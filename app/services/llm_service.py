"""
Configuração e inicialização do cliente Groq para AcolheCAPS AI.

Este módulo centraliza a configuração do Groq LLM, permitindo usar
diferentes modelos conforme necessidade e facilitando testes com mocks.
"""

import logging
from functools import lru_cache
from typing import Optional

from groq import Groq
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class GroqSettings(BaseSettings):
    """
    Configurações de ambiente para Groq.

    Atributos:
        groq_api_key: Chave de API do Groq
        llm_provider: Provedor de LLM (groq, openai, etc)
        llm_model: Modelo a usar (mixtral-8x7b-32768, llama2-70b, etc)
        llm_temperature: Temperatura do modelo (0-1)
        llm_max_tokens: Máximo de tokens na resposta
    """

    groq_api_key: str
    llm_provider: str = "groq"
    llm_model: str = "openai/gpt-oss-120b"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignora campos extras do .env (como N8N_WEBHOOK_URL)


@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    """
    Obtém ou cria o cliente Groq singleton.

    Returns:
        Groq: Cliente Groq configurado

    Raises:
        ValueError: Se GROQ_API_KEY não estiver definida
    """
    settings = GroqSettings()

    if not settings.groq_api_key:
        raise ValueError(
            "GROQ_API_KEY não definida. " "Configure a variável de ambiente GROQ_API_KEY"
        )

    logger.info(
        f"Inicializando cliente Groq | "
        f"modelo={settings.llm_model} | "
        f"temperatura={settings.llm_temperature}"
    )

    return Groq(api_key=settings.groq_api_key)


@lru_cache(maxsize=1)
def get_groq_settings() -> GroqSettings:
    """
    Obtém as configurações do Groq.

    Returns:
        GroqSettings: Configurações carregadas
    """
    return GroqSettings()


class GroqLLM:
    """
    Wrapper simplificado para usar Groq no LangGraph.
    """

    def __init__(self):
        """Inicializa o wrapper com cliente e settings."""
        self.client = get_groq_client()
        self.settings = get_groq_settings()

    def invoke(self, prompt: str, trace_id: Optional[str] = None) -> str:
        """
        Executa uma chamada ao Groq LLM.

        Args:
            prompt: Prompt para enviar ao modelo
            trace_id: ID de rastreabilidade (opcional)

        Returns:
            str: Resposta do modelo

        Raises:
            Exception: Se houver erro na chamada ao Groq
        """
        try:
            logger.info(
                f"[GROQ] Iniciando chamada LLM | "
                f"modelo={self.settings.llm_model} | "
                f"trace_id={trace_id}"
            )

            message = self.client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é um assistente especializado em triagem de "
                            "saúde mental para CAPS."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.llm_max_tokens,
            )

            resposta = message.choices[0].message.content

            tokens_info = message.usage.total_tokens if message.usage else "N/A"
            logger.info(
                f"[GROQ] Resposta recebida com sucesso | "
                f"tokens_usados={tokens_info} | "
                f"trace_id={trace_id}"
            )

            return resposta

        except Exception as e:
            logger.error(
                f"[GROQ] Erro na chamada ao modelo | " f"erro={str(e)} | trace_id={trace_id}"
            )
            raise

    def extrair_pontos_chave(self, relato: str, trace_id: Optional[str] = None) -> list[str]:
        """
        Extrai pontos-chave de um relato usando Groq.

        Args:
            relato: Relato do paciente
            trace_id: ID de rastreabilidade (opcional)

        Returns:
            list[str]: Lista de pontos-chave identificados
        """
        prompt = f"""
Analise o seguinte relato de acolhimento e extraia os pontos-chave principais.
Retorne apenas uma lista de pontos-chave separados por vírgula.

Relato:
{relato}

Pontos-chave:
"""

        resposta = self.invoke(prompt, trace_id)
        pontos = [p.strip() for p in resposta.split(",")]
        return pontos

    def avaliar_nivel_prioridade(
        self, relato: str, contexto_rag: Optional[str] = None, trace_id: Optional[str] = None
    ) -> tuple[str, list[str]]:
        """
        Avalia o nível de prioridade e fatores de risco usando Groq.
        Inclui contexto do PDF protocolo na avaliação.

        Args:
            relato: Relato do paciente
            contexto_rag: Contexto de diretrizes clínicas (DO PDF PROTOCOLO)
            trace_id: ID de rastreabilidade (opcional)

        Returns:
            tuple: (nivel_prioridade, fatores_risco)
        """
        # Indicator que mostra se contexto vem do PDF
        contexto_indicator = "[CONTEXTO DO PROTOCOLO PDF]" if contexto_rag else "[SEM CONTEXTO]"
        
        contexto_part = f"""{contexto_indicator}

Contexto do Protocolo Oficial:
{contexto_rag}

---

""" if contexto_rag else ""

        prompt = f"""
{contexto_part}
PROTOCOLO OFICIAL DE CLASSIFICAÇÃO DE RISCO EM SAÚDE MENTAL (Secretaria ES)

VERMELHO - Emergência/Risco Grave (atendimento imediato):
- Tentativa de suicídio em qualquer circunstância
- Episódio depressivo grave COM ideação suicida e planejamento ou histórico de tentativa
- Episódio maníaco COM comportamento inadequado e risco para si/terceiros
- Autonegligência grave com comorbidades
- Intoxicação aguda por substâncias
- Quadro psicótico com delírios/alucinações e risco
- Automutilação (cutting) com risco de morte
- Agitação psicomotora com ideação/planejamento de homicídio/suicídio
- Dependência química com agitação/agressividade e múltiplas tentativas prévias de tratamento

LARANJA - Urgência/Risco Elevado (atendimento clínico especializado):
- Quadro depressivo GRAVE COM ideação suicida SEM planejamento e sem apoio familiar
- Quadro psicótico agudo SEM agitação mas SEM apoio familiar
- Autonegligência grave
- Alcoolismo/dependência com abstinência leve/moderada sem êxito em tratamento
- Quadros refratários ao ambulatório
- Episódios conversivos/dissociativos com risco

AMARELO - Urgência/Risco Moderado (CAPS, ambulatório especializado):
- Quadro depressivo MODERADO com apoio sociofamiliar para tratamento
- Quadro psicótico agudo SEM agitação COM apoio sociofamiliar
- Dependência com abstinência leve e capacidade de participar de programa ambulatorial
- Histórico de tentativa de suicídio/homicídio E internação prévia

VERDE - Risco Baixo (Atenção Primária):
- Síndromes depressivas LEVES
- Transtorno bipolar: episódio depressivo/maníaco SEM risco para si/terceiros
- Insônia
- Transtornos conversivos/dissociativos SEM risco
- Sintomas psicossomáticos, crises de ansiedade
- Uso nocivo/abusivo de álcool ou substâncias
- Luto, reação adaptativa

AZUL - Não urgente (Acompanhamento ambulatorial):
- Condições psiquiátricas crônicas estabilizadas
- Manutenção de acompanhamento com medicação estabilizada
- Demandas administrativas

---

Avalie o relato seguinte RIGOROSAMENTE segundo o Protocolo acima:

Relato:
{relato}

Responda EXATAMENTE no seguinte formato:
PRIORIDADE: [Crítica|Alta|Média|Baixa]
FATORES_RISCO: [fator1, fator2, fator3]

IMPORTANTE: Use APENAS os critérios do Protocolo. Não adicione regras extras.

Resposta:
"""

        resposta = self.invoke(prompt, trace_id)

        # Parse resposta
        linhas = resposta.strip().split("\n")
        prioridade = "Baixa"  # default
        fatores_risco = []

        for linha in linhas:
            if "PRIORIDADE:" in linha:
                # Remove "PRIORIDADE:" e limpa espaços em branco
                prioridade_raw = linha.split("PRIORIDADE:")[1].strip()
                # Remove colchetes se presentes
                prioridade_raw = prioridade_raw.replace("[", "").replace("]", "")
                # Extrai apenas a palavra-chave (Crítica, Alta, Média, Baixa)
                for nivel in ["Crítica", "Alta", "Média", "Baixa"]:
                    if nivel in prioridade_raw:
                        prioridade = nivel
                        break
            elif "FATORES_RISCO:" in linha:
                fatores_str = linha.split("FATORES_RISCO:")[1].strip()
                # Remove colchetes se presentes
                fatores_str = fatores_str.replace("[", "").replace("]", "")
                # Se a string estiver vazia ou for apenas "[]", retorna lista vazia
                if fatores_str and fatores_str != "":
                    fatores_risco = [f.strip() for f in fatores_str.split(",") if f.strip()]

        return prioridade, fatores_risco

    def gerar_encaminhamento(
        self, relato: str, nivel_prioridade: str, fatores_risco: list[str], trace_id: Optional[str] = None
    ) -> str:
        """
        Gera recomendação de encaminhamento para profissional baseado no diagnóstico.

        Args:
            relato: Relato do paciente
            nivel_prioridade: Nível de prioridade (Alta, Média, Baixa)
            fatores_risco: Lista de fatores de risco identificados
            trace_id: ID de rastreabilidade (opcional)

        Returns:
            str: Recomendação de encaminhamento (ex: "Psicólogo + Grupo de Apoio")
        """
        fatores_str = ", ".join(fatores_risco) if fatores_risco else "Sem fatores específicos"

        prompt = f"""
Com base no seguinte relato de triagem, recomende o MELHOR encaminhamento profissional 
para o atendimento do paciente.

Nível de Prioridade: {nivel_prioridade}
Fatores de Risco: {fatores_str}

Relato:
{relato}

GUIA DE ENCAMINHAMENTO:

Para PRIORIDADE ALTA ou com risco suicida/homicida:
→ Encaminhe para: Psiquiatra + Psicólogo (atendimento urgente)

Para DEPRESSÃO SEVERA:
→ Encaminhe para: Psiquiatra (avaliação de medicação) + Psicólogo (terapia)

Para DEPRESSÃO MODERADA/CRÔNICA:
→ Encaminhe para: Psicólogo + Grupo de Apoio para Depressão

Para ANSIEDADE:
→ Encaminhe para: Psicólogo + Grupo de Apoio para Ansiedade

Para ABUSO DE SUBSTÂNCIA:
→ Encaminhe para: Especialista em Dependência + Grupo de Suporte

Para TRAUMA/PTSD:
→ Encaminhe para: Psicólogo especializado em trauma + Terapia de Grupo

Para TRANSTORNO BIPOLAR:
→ Encaminhe para: Psiquiatra + Psicólogo

Para ISOLAMENTO SOCIAL/LUTO:
→ Encaminhe para: Assistente Social + Grupo de Apoio + Psicólogo

Para STRESS OCUPACIONAL:
→ Encaminhe para: Psicólogo + Orientação Profissional

Para PRIORIDADE BAIXA (sem urgência):
→ Encaminhe para: Psicólogo + Acompanhamento em grupo

Forneça UMA ÚNICA linha com a recomendação de encaminhamento mais apropriada:
"""

        resposta = self.invoke(prompt, trace_id)
        # Limpa a resposta
        encaminhamento = resposta.strip()
        # Se começar com "→ Encaminhe para:" remove isso
        if "→ Encaminhe para:" in encaminhamento:
            encaminhamento = encaminhamento.split("→ Encaminhe para:")[1].strip()
        return encaminhamento


# Singleton para uso simplificado
_groq_llm_instance: Optional[GroqLLM] = None


def get_groq_llm() -> GroqLLM:
    """
    Obtém a instância singleton do wrapper GroqLLM.

    Returns:
        GroqLLM: Instância do wrapper
    """
    global _groq_llm_instance
    if _groq_llm_instance is None:
        _groq_llm_instance = GroqLLM()
    return _groq_llm_instance


if __name__ == "__main__":
    # Teste de configuração
    import logging

    logging.basicConfig(level=logging.INFO)

    try:
        llm = get_groq_llm()
        print("✓ Cliente Groq inicializado com sucesso")
        print(f"  Modelo: {llm.settings.llm_model}")
        print(f"  Temperatura: {llm.settings.llm_temperature}")
        print(f"  Max tokens: {llm.settings.llm_max_tokens}")
    except ValueError as e:
        print(f"✗ Erro na configuração: {e}")
