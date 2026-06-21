"""
EmbeddingProcessor: SemanticProcessor basado en TF-IDF + cosine similarity.

Implementacion ligera sin dependencias externas (sin numpy ni sklearn).
Adecuada para tests deterministicos y como fallback cuando no se dispone
de un modelo de embeddings neuronal.

Limitaciones documentadas:
- Bag-of-words: no captura orden ni contexto.
- Solo palabras exactas: no entiende sinonimos ni morfologia.
- Suficiente para la v1; para mayor precision debe sustituirse por una
  implementacion basada en sentence-transformers.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List

from src.domain.semantic_flow.interfaces import SemanticProcessor
from src.domain.semantic_flow.value_objects import SemanticMatch


_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def _tokenize(text: str) -> List[str]:
    """Tokeniza el texto en palabras en minusculas."""
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _term_frequency(tokens: List[str]) -> Dict[str, float]:
    """Frecuencia de cada term normalizada por la longitud."""
    if not tokens:
        return {}
    counter = Counter(tokens)
    total = len(tokens)
    return {term: count / total for term, count in counter.items()}


def _dot_product(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Producto escalar entre dos vectores sparse."""
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(term, 0.0) for term, weight in a.items())


def _magnitude(vec: Dict[str, float]) -> float:
    """Magnitud (norma L2) de un vector sparse."""
    return math.sqrt(sum(weight * weight for weight in vec.values()))


def _cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Similitud coseno entre dos vectores sparse, en [0, 1]."""
    mag_a = _magnitude(a)
    mag_b = _magnitude(b)
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    cosine = _dot_product(a, b) / (mag_a * mag_b)
    # Clamp a [0, 1] porque los pesos TF son no negativos pero por
    # seguridad numerica garantizamos el rango.
    return max(0.0, min(1.0, cosine))


class EmbeddingProcessor(SemanticProcessor):
    """
    SemanticProcessor basado en bag-of-words + cosine similarity.

    No requiere entrenamiento: computa TF en runtime. Para documents
    cortos (frases, etiquetas) funciona razonablemente bien.
    """

    def embed(self, text: str) -> List[float]:
        """
        Vectoriza el texto como lista de floats.

        Para consistencia con el contrato devuelve la representacion
        como lista de frecuencias ordenadas por term. Util sobre todo
        para depuracion; para comparar usar similarity() directamente.
        """
        return list(_term_frequency(_tokenize(text)).values())

    def similarity(self, a: str, b: str) -> float:
        """Similitud coseno en [0, 1] entre dos textos."""
        vec_a = _term_frequency(_tokenize(a))
        vec_b = _term_frequency(_tokenize(b))
        return _cosine_similarity(vec_a, vec_b)

    def best_match(
        self,
        query: str,
        candidates: List[str],
        threshold: float = 0.5,
    ) -> SemanticMatch:
        """
        Devuelve el candidato mas similar a la query.

        Args:
            query: Texto de referencia.
            candidates: Lista de candidatos.
            threshold: Umbral de aceptacion (el match.is_match sera True
                solo si score > threshold).

        Returns:
            SemanticMatch con query, candidate, score y threshold.
            Si candidates esta vacio, candidate es "" y score es 0.0.
        """
        if not candidates:
            return SemanticMatch(
                query=query,
                candidate="",
                score=0.0,
                threshold=threshold,
            )

        query_vec = _term_frequency(_tokenize(query))
        best_candidate = ""
        best_score = -1.0
        for candidate in candidates:
            cand_vec = _term_frequency(_tokenize(candidate))
            score = _cosine_similarity(query_vec, cand_vec)
            if score > best_score:
                best_score = score
                best_candidate = candidate

        return SemanticMatch(
            query=query,
            candidate=best_candidate,
            score=max(0.0, best_score),
            threshold=threshold,
        )
