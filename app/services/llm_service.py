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

        Args:
            relato: Relato do paciente
            contexto_rag: Contexto de diretrizes clínicas (opcional)
            trace_id: ID de rastreabilidade (opcional)

        Returns:
            tuple: (nivel_prioridade, fatores_risco)
        """
        contexto_part = f"Contexto de diretrizes: {contexto_rag}\n\n" if contexto_rag else ""

        prompt = f"""
{contexto_part}
CRITÉRIOS DE CLASSIFICAÇÃO PARA TRIAGEM EM CAPS:

PRIORIDADE CRÍTICA (risco iminente):
- Ideação/tentativa de suicídio ATIVA com plano definido
- Ideação/tentativa de homicídio ativa
- Psicose desorganizada ou catatonia
- Intoxicação ou abuso de substância grave
- Risco imediato de dano a si ou outros

PRIORIDADE ALTA (risco significativo):
- Ideação suicida/homicida sem plano específico mas com intenção
- História prévia de tentativa de suicídio
- Episódio maníaco ou transtorno bipolar não controlado
- Transtorno de personalidade borderline com comportamento destrutivo
- Alucinações ou delírios persecutórios
- Abuso de substância com comprometimento importante
- Depressão severa com sintomas incapacitantes

PRIORIDADE MÉDIA (sofrimento psíquico moderado):
- Ansiedade generalizada com impacto na vida diária
- Depressão leve a moderada COM comprometimento funcional
- Depressão CRÔNICA (indústria, falta de energia, absenteísmo)
- Transtorno de relacionamento significativo
- Histórico de trauma não resolvido
- Stress ocupacional severo
- Pacientes que já fazem ou fizeram tratamento psicológico
- Isolamento social moderado

PRIORIDADE BAIXA (sofrimento mínimo):
- Dificuldades de adaptação leves e transitórias
- Preocupações situacionais normais (luto recente, mudança de vida)
- Queixa somática sem clareza de causa psicológica
- Pacientes com suporte adequado e funcionamento preservado

---

Avalie o relato seguinte RIGOROSAMENTE segundo os critérios acima:

Relato:
{relato}

Responda EXATAMENTE no seguinte formato:
PRIORIDADE: [Alta|Média|Baixa]
FATORES_RISCO: [fator1, fator2, fator3]

IMPORTANTE: Depressão crônica é SEMPRE Média ou superior. Isolamento social é sinal de Média. 
Absenteísmo do trabalho indica comprometimento funcional = Média no mínimo.

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
                # Extrai apenas a palavra-chave (Alta, Média, Baixa)
                for nivel in ["Alta", "Média", "Baixa"]:
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
