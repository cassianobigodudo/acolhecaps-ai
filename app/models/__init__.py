"""
Modelos de dados do AcolheCAPS AI.

Exporta as classes Pydantic para triagem e acolhimento.
"""

from app.models.acolhimento import (
    EntradaAcolhimento,
    EstadoAcolhimento,
    FichaTriagemCAPS,
)

__all__ = ["EntradaAcolhimento", "FichaTriagemCAPS", "EstadoAcolhimento"]
