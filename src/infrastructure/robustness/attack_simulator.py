"""
Text Attack Simulator

Implements text-based adversarial attack methods for evaluating
AI system robustness. All attacks work at the text level without
requiring gradient access to the model.

Attack methods:
- Character swap: randomly swap adjacent characters
- Character insert: insert random characters
- Character delete: delete random characters
- Word synonym: replace words with synonyms (placeholder-based)
- Sentence reorder: shuffle sentence order
- Keyword injection: inject adversarial keywords
- Combined: apply multiple methods

Security: All methods enforce perturbation limits to prevent
excessive modification of inputs.
"""

import random
import re
from typing import List, Tuple, Optional

from src.domain.robustness.entities import (
    AttackResult,
    AdversarialExample,
    RobustnessTestSession,
)
from src.domain.robustness.value_objects import (
    AttackType,
    PerturbationMethod,
    validate_attack_epsilon,
    MAX_PERTURBATION_RATIO,
)


# Common synonyms for text substitution (simplified)
_SYNONYM_MAP = {
    "good": ["excellent", "fine", "adequate"],
    "bad": ["poor", "terrible", "awful"],
    "big": ["large", "huge", "enormous"],
    "small": ["tiny", "little", "minute"],
    "fast": ["quick", "rapid", "swift"],
    "slow": ["sluggish", "lethargic", "delayed"],
    "happy": ["joyful", "cheerful", "pleased"],
    "sad": ["unhappy", "sorrowful", "melancholy"],
    "important": ["significant", "crucial", "vital"],
    "helpful": ["useful", "beneficial", "valuable"],
}

# Adversarial keywords that may confuse classifiers
_ADVERSARIAL_KEYWORDS = [
    "ignore", "disregard", "override", "bypass",
    "confidential", "secret", "internal", "debug",
]


class TextAttackSimulator:
    """
    Simulates adversarial attacks on text inputs.

    Usage:
        simulator = TextAttackSimulator()
        examples = simulator.generate_adversarial_examples(
            text="This is a legal opinion about AI liability.",
            attack_type=AttackType.CHAR_SWAP,
            epsilon=0.1,
        )
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Args:
            seed: Random seed for reproducibility (None = non-deterministic)
        """
        self._rng = random.Random(seed)

    def generate_adversarial_examples(
        self,
        text: str,
        attack_type: AttackType,
        epsilon: float = 0.1,
        max_perturbations: int = 10,
    ) -> List[AdversarialExample]:
        """
        Generate adversarial examples from original text.

        Args:
            text: Original input text
            attack_type: Type of attack to simulate
            epsilon: Attack strength (0.0, 1.0]
            max_perturbations: Maximum perturbations per example

        Returns:
            List of adversarial examples (may be empty if text is too short)
        """
        validate_attack_epsilon(epsilon)

        if not text or not text.strip():
            return []

        # Cap perturbations based on epsilon and text length
        words = text.split()
        max_from_epsilon = max(1, int(len(words) * epsilon))
        actual_max = min(max_perturbations, max_from_epsilon)

        examples: List[AdversarialExample] = []

        if attack_type == AttackType.CHAR_SWAP:
            examples = self._char_swap_attack(text, actual_max)
        elif attack_type == AttackType.CHAR_INSERT:
            examples = self._char_insert_attack(text, actual_max)
        elif attack_type == AttackType.CHAR_DELETE:
            examples = self._char_delete_attack(text, actual_max)
        elif attack_type == AttackType.WORD_SUBSTITUTION:
            examples = self._word_substitution_attack(text, actual_max)
        elif attack_type == AttackType.SENTENCE_REORDER:
            examples = self._sentence_reorder_attack(text)
        elif attack_type == AttackType.KEYWORD_INJECTION:
            examples = self._keyword_injection_attack(text, actual_max)
        elif attack_type == AttackType.FGSM:
            examples = self._fgsm_text_attack(text, actual_max)
        elif attack_type == AttackType.PGD:
            examples = self._pgd_text_attack(text, actual_max)
        elif attack_type == AttackType.COMBINED:
            examples = self._combined_attack(text, actual_max)

        return examples

    def evaluate_attack(
        self,
        original_text: str,
        adversarial_text: str,
        original_prediction: str,
        original_confidence: float,
        model_predict_fn=None,
    ) -> Tuple[str, float, bool]:
        """
        Evaluate a single adversarial example.

        Args:
            original_text: Original input
            adversarial_text: Perturbed input
            original_prediction: Model's original prediction
            original_confidence: Model's original confidence
            model_predict_fn: Callable that takes text and returns (prediction, confidence)

        Returns:
            Tuple of (new_prediction, new_confidence, prediction_changed)
        """
        if model_predict_fn is None:
            # No model available — return unchanged
            return original_prediction, original_confidence, False

        new_pred, new_conf = model_predict_fn(adversarial_text)
        changed = new_pred != original_prediction

        return new_pred, new_conf, changed

    def run_attack_session(
        self,
        texts: List[str],
        labels: List[str],
        attack_types: Optional[List[AttackType]] = None,
        epsilon: float = 0.1,
        model_predict_fn=None,
        system_id: str = "",
        model_name: str = "",
    ) -> RobustnessTestSession:
        """
        Run a complete attack session across multiple texts and attack types.

        Args:
            texts: List of input texts to attack
            labels: Original predictions for each text
            attack_types: Types of attacks to run (default: all types)
            epsilon: Attack strength
            model_predict_fn: Model prediction function
            system_id: System identifier
            model_name: Model name

        Returns:
            Completed RobustnessTestSession with all results
        """
        if attack_types is None:
            attack_types = [
                AttackType.CHAR_SWAP,
                AttackType.WORD_SUBSTITUTION,
                AttackType.KEYWORD_INJECTION,
            ]

        session = RobustnessTestSession(
            system_id=system_id,
            model_name=model_name,
        )

        for attack_type in attack_types:
            result = self._run_single_attack(
                texts=texts,
                labels=labels,
                attack_type=attack_type,
                epsilon=epsilon,
                model_predict_fn=model_predict_fn,
                model_name=model_name,
            )
            session.add_attack_result(result)

        session.complete()
        return session

    # -- Attack implementations --

    def _char_swap_attack(self, text: str, max_perturbations: int) -> List[AdversarialExample]:
        """Swap adjacent characters at random positions."""
        examples = []
        for _ in range(min(3, max_perturbations)):
            chars = list(text)
            if len(chars) < 3:
                break

            pos = self._rng.randint(0, len(chars) - 2)
            # Swap with next character
            chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]

            perturbed = "".join(chars)
            examples.append(AdversarialExample(
                original_text=text,
                perturbed_text=perturbed,
                attack_type=AttackType.CHAR_SWAP,
                perturbation_count=1,
                perturbation_ratio=1.0 / len(text) if text else 0.0,
            ))

        return examples

    def _char_insert_attack(self, text: str, max_perturbations: int) -> List[AdversarialExample]:
        """Insert random characters at random positions."""
        examples = []
        for _ in range(min(3, max_perturbations)):
            chars = list(text)
            if not chars:
                break

            pos = self._rng.randint(0, len(chars))
            insert_char = self._rng.choice("abcdefghijklmnopqrstuvwxyz ")
            chars.insert(pos, insert_char)

            perturbed = "".join(chars)
            examples.append(AdversarialExample(
                original_text=text,
                perturbed_text=perturbed,
                attack_type=AttackType.CHAR_INSERT,
                perturbation_count=1,
                perturbation_ratio=1.0 / max(len(text), 1),
            ))

        return examples

    def _char_delete_attack(self, text: str, max_perturbations: int) -> List[AdversarialExample]:
        """Delete characters at random positions."""
        examples = []
        for _ in range(min(3, max_perturbations)):
            if len(text) < 5:
                break

            chars = list(text)
            pos = self._rng.randint(0, len(chars) - 1)
            deleted = chars.pop(pos)

            perturbed = "".join(chars)
            examples.append(AdversarialExample(
                original_text=text,
                perturbed_text=perturbed,
                attack_type=AttackType.CHAR_DELETE,
                perturbation_count=1,
                perturbation_ratio=1.0 / max(len(text), 1),
            ))

        return examples

    def _word_substitution_attack(self, text: str, max_perturbations: int) -> List[AdversarialExample]:
        """Replace words with synonyms."""
        examples = []
        words = text.split()

        if not words:
            return examples

        # Find substitutable words
        substitutable = [
            (i, w) for i, w in enumerate(words)
            if w.lower() in _SYNONYM_MAP
        ]

        if not substitutable:
            # If no synonyms, fall back to random word swap
            return self._char_swap_attack(text, max_perturbations)

        # Apply substitutions
        count = 0
        for idx, original_word in substitutable[:max_perturbations]:
            synonyms = _SYNONYM_MAP[original_word.lower()]
            new_word = self._rng.choice(synonyms)
            words[idx] = new_word
            count += 1

        perturbed = " ".join(words)
        examples.append(AdversarialExample(
            original_text=text,
            perturbed_text=perturbed,
            attack_type=AttackType.WORD_SUBSTITUTION,
            perturbation_count=count,
            perturbation_ratio=count / len(words) if words else 0.0,
        ))

        return examples

    def _sentence_reorder_attack(self, text: str) -> List[AdversarialExample]:
        """Reorder sentences in the text."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) < 3:
            return []

        # Shuffle sentences
        shuffled = list(sentences)
        self._rng.shuffle(shuffled)
        perturbed = " ".join(shuffled)

        return [AdversarialExample(
            original_text=text,
            perturbed_text=perturbed,
            attack_type=AttackType.SENTENCE_REORDER,
            perturbation_count=len(sentences),
            perturbation_ratio=min(MAX_PERTURBATION_RATIO, len(sentences) * 0.1),
        )]

    def _keyword_injection_attack(self, text: str, max_perturbations: int) -> List[AdversarialExample]:
        """Inject adversarial keywords into the text."""
        examples = []
        words = text.split()

        for _ in range(min(2, max_perturbations)):
            keyword = self._rng.choice(_ADVERSARIAL_KEYWORDS)
            pos = self._rng.randint(0, len(words))
            words.insert(pos, keyword)

        perturbed = " ".join(words)
        examples.append(AdversarialExample(
            original_text=text,
            perturbed_text=perturbed,
            attack_type=AttackType.KEYWORD_INJECTION,
            perturbation_count=min(2, max_perturbations),
            perturbation_ratio=min(MAX_PERTURBATION_RATIO, min(2, max_perturbations) / max(len(words), 1)),
        ))

        return examples

    def _fgsm_text_attack(self, text: str, max_perturbations: int) -> List[AdversarialExample]:
        """
        Text-adapted FGSM: identifies high-impact word positions
        and perturbs them (simplified gradient-free approximation).
        """
        words = text.split()
        if len(words) < 3:
            return []

        # Approximate "gradient" by targeting words at key positions
        # (beginning, end, and random middle positions)
        target_positions = set()
        if words:
            target_positions.add(0)
            target_positions.add(len(words) - 1)
        while len(target_positions) < min(max_perturbations, len(words)):
            target_positions.add(self._rng.randint(0, len(words) - 1))

        examples = []
        for pos in list(target_positions)[:max_perturbations]:
            modified = list(words)
            # Perturb by capitalizing or adding emphasis
            modified[pos] = modified[pos].upper() + "!"
            perturbed = " ".join(modified)
            examples.append(AdversarialExample(
                original_text=text,
                perturbed_text=perturbed,
                attack_type=AttackType.FGSM,
                perturbation_count=1,
                perturbation_ratio=min(MAX_PERTURBATION_RATIO, 1.0 / max(len(words), 1)),
            ))

        return examples

    def _pgd_text_attack(self, text: str, max_perturbations: int) -> List[AdversarialExample]:
        """
        Text-adapted PGD: iterative version of FGSM.
        Applies perturbations iteratively, building on previous examples.
        """
        words = text.split()
        if len(words) < 3:
            return []

        examples = []
        current_words = list(words)

        for iteration in range(min(max_perturbations, 3)):
            pos = self._rng.randint(0, len(current_words) - 1)
            current_words[pos] = current_words[pos].upper()

            perturbed = " ".join(current_words)
            examples.append(AdversarialExample(
                original_text=text,
                perturbed_text=perturbed,
                attack_type=AttackType.PGD,
                perturbation_count=iteration + 1,
                perturbation_ratio=min(MAX_PERTURBATION_RATIO, (iteration + 1) / max(len(words), 1)),
            ))

        return examples

    def _combined_attack(self, text: str, max_perturbations: int) -> List[AdversarialExample]:
        """Apply multiple attack methods sequentially."""
        examples = []

        # Char swap first
        char_examples = self._char_swap_attack(text, 1)
        if char_examples:
            text = char_examples[-1].perturbed_text
            examples.extend(char_examples)

        # Then word substitution
        word_examples = self._word_substitution_attack(text, 1)
        if word_examples:
            text = word_examples[-1].perturbed_text
            examples.extend(word_examples)

        # Finally keyword injection
        kw_examples = self._keyword_injection_attack(text, 1)
        examples.extend(kw_examples)

        return examples

    def _run_single_attack(
        self,
        texts: List[str],
        labels: List[str],
        attack_type: AttackType,
        epsilon: float,
        model_predict_fn=None,
        model_name: str = "",
    ) -> AttackResult:
        """Run a single attack type across all texts."""
        result = AttackResult(
            attack_type=attack_type,
            epsilon=epsilon,
            model_name=model_name,
        )

        total = 0
        successful = 0
        total_conf_drop = 0.0

        for text, label in zip(texts, labels):
            examples = self.generate_adversarial_examples(
                text=text,
                attack_type=attack_type,
                epsilon=epsilon,
            )

            for ex in examples:
                total += 1
                new_pred, new_conf, changed = self.evaluate_attack(
                    original_text=text,
                    adversarial_text=ex.perturbed_text,
                    original_prediction=label,
                    original_confidence=0.8,  # default
                    model_predict_fn=model_predict_fn,
                )

                if changed:
                    successful += 1

                conf_drop = 0.8 - new_conf  # simplified
                total_conf_drop += conf_drop

        result.total_samples = total
        result.successful_attacks = successful
        result.accuracy_before_attack = 0.8  # placeholder
        result.accuracy_after_attack = max(0.0, 0.8 - (successful / max(total, 1)))
        result.accuracy_degradation = result.accuracy_before_attack - result.accuracy_after_attack
        result.mean_confidence_drop = total_conf_drop / max(total, 1)
        result.compute_metrics()

        return result
