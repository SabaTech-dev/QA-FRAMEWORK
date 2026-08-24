"""
Selector Generator Implementation

Generates candidate selectors from various sources.
"""

import re

from src.domain.self_healing.entities import Selector
from src.domain.self_healing.value_objects import HealingContext, SelectorMetadata, SelectorType


class SelectorGenerator:
    """
    Generates candidate selectors for healing.

    Uses multiple strategies:
    - Attribute-based generation
    - Context-based generation
    - Composite selector construction
    """

    def __init__(
        self,
        prefer_data_attributes: bool = True,
        max_selector_length: int = 150,
        avoid_indexed_selectors: bool = True,
    ):
        self.prefer_data_attributes = prefer_data_attributes
        self.max_selector_length = max_selector_length
        self.avoid_indexed_selectors = avoid_indexed_selectors

    def generate_from_attributes(
        self,
        attributes: dict,
        element_text: str | None = None,
    ) -> list[Selector]:
        """
        Generate candidate selectors from element attributes.

        Args:
            attributes: HTML element attributes
            element_text: Text content of the element

        Returns:
            List of candidate selectors
        """
        candidates = []

        if not attributes:
            return candidates

        # Priority 1: ID selector
        if attributes.get("id"):
            candidates.append(
                self._create_selector(
                    f"#{self._escape_css(attributes['id'])}",
                    SelectorType.ID,
                    "ID selector",
                )
            )

        # Priority 2: Data attributes
        if self.prefer_data_attributes:
            for attr_name, attr_value in attributes.items():
                if attr_name.startswith("data-") and attr_value:
                    candidates.append(
                        self._create_selector(
                            f'[{attr_name}="{self._escape_css(attr_value)}"]',
                            SelectorType.DATA_ATTRIBUTE,
                            f"Data attribute: {attr_name}",
                        )
                    )

        # Priority 3: Name attribute
        if attributes.get("name"):
            candidates.append(
                self._create_selector(
                    f"[name=\"{self._escape_css(attributes['name'])}\"]",
                    SelectorType.NAME,
                    "Name attribute",
                )
            )

        # Priority 4: ARIA attributes
        aria_selectors = self._generate_aria_selectors(attributes)
        candidates.extend(aria_selectors)

        # Priority 5: Class-based selectors
        if attributes.get("class"):
            class_selectors = self._generate_class_selectors(attributes["class"])
            candidates.extend(class_selectors)

        # Priority 6: Text-based selectors (if provided)
        if element_text:
            text_selectors = self._generate_text_selectors(element_text, attributes)
            candidates.extend(text_selectors)

        # Priority 7: Tag with attributes combination
        tag = attributes.get("tagName", "").lower()
        if tag:
            tag_selectors = self._generate_tag_selectors(tag, attributes)
            candidates.extend(tag_selectors)

        return candidates

    def generate_from_context(
        self,
        context: HealingContext,
    ) -> list[Selector]:
        """
        Generate candidate selectors from page context.

        Uses surrounding elements and structure to create candidates.
        """
        candidates = []

        # Use parent selector if available
        if context.parent_selector:
            parent = context.parent_selector

            # Try with element text
            if context.surrounding_text:
                text_escaped = self._escape_xpath(context.surrounding_text[:50])
                candidates.append(
                    self._create_selector(
                        f"{parent}//*[contains(text(), '{text_escaped}')]",
                        SelectorType.XPATH,
                        "Parent + text",
                    )
                )

            # Try with element attributes
            if context.element_attributes:
                tag = context.element_attributes.get("tagName", "*")
                classes = context.element_attributes.get("class", "").split()

                if classes:
                    class_selector = ".".join(f".{c}" for c in classes[:2])
                    candidates.append(
                        self._create_selector(
                            f"{parent} {tag}{class_selector}",
                            SelectorType.CSS,
                            "Parent + class",
                        )
                    )

        # Use sibling selectors
        if context.sibling_selectors:
            for sibling in context.sibling_selectors[:3]:
                # Adjacent sibling
                candidates.append(
                    self._create_selector(
                        f"{sibling} + *",
                        SelectorType.CSS,
                        "Adjacent sibling",
                    )
                )

                # General sibling
                candidates.append(
                    self._create_selector(
                        f"{sibling} ~ *",
                        SelectorType.CSS,
                        "General sibling",
                    )
                )

        return candidates

    def generate_composite(
        self,
        selectors: list[Selector],
    ) -> list[Selector]:
        """
        Generate composite selectors from multiple candidates.

        Combines selectors to increase specificity.
        """
        candidates = []

        if len(selectors) < 2:
            return candidates

        # Get selector values
        values = [s.value for s in selectors if s.value]

        # Combine class selectors
        class_values = [v for v in values if v.startswith(".") and " " not in v]
        if len(class_values) >= 2:
            combined = "".join(class_values[:3])
            if len(combined) <= self.max_selector_length:
                candidates.append(
                    self._create_selector(
                        combined,
                        SelectorType.CSS,
                        "Combined classes",
                    )
                )

        # Combine attribute selectors
        attr_values = [v for v in values if v.startswith("[") and v.endswith("]")]
        if len(attr_values) >= 2:
            combined = "".join(attr_values[:2])
            if len(combined) <= self.max_selector_length:
                candidates.append(
                    self._create_selector(
                        combined,
                        SelectorType.CSS,
                        "Combined attributes",
                    )
                )

        # Tag + attribute combinations
        tag_values = [v for v in values if not any(v.startswith(c) for c in ".[#")]
        if tag_values and attr_values:
            for tag in tag_values[:2]:
                for attr in attr_values[:2]:
                    combined = f"{tag}{attr}"
                    if len(combined) <= self.max_selector_length:
                        candidates.append(
                            self._create_selector(
                                combined,
                                SelectorType.CSS,
                                "Tag + attribute",
                            )
                        )

        return candidates

    def _create_selector(
        self,
        value: str,
        selector_type: SelectorType,
        description: str,
    ) -> Selector:
        """Create a selector with default metadata."""
        return Selector(
            value=value,
            selector_type=selector_type,
            description=description,
            metadata=SelectorMetadata(
                created_at=None,  # Will be set by entity
                updated_at=None,
                usage_count=0,
                success_rate=0.5,  # Neutral for new selectors
                last_successful=None,
                source="generated",
            ),
        )

    def _escape_css(self, value: str) -> str:
        """Escape special characters for CSS selectors."""
        # Escape quotes and backslashes
        value = value.replace("\\", "\\\\")
        value = value.replace('"', '\\"')
        return value

    def _escape_xpath(self, value: str) -> str:
        """Escape special characters for XPath."""
        if "'" not in value:
            return value
        # Use concat for strings with quotes
        parts = value.split("'")
        return "concat('', '" + "', '".join(parts) + "')"

    def _generate_aria_selectors(self, attributes: dict) -> list[Selector]:
        """Generate selectors based on ARIA attributes."""
        selectors = []

        aria_attrs = [
            "aria-label",
            "aria-labelledby",
            "aria-describedby",
            "role",
        ]

        for attr in aria_attrs:
            if attributes.get(attr):
                value = self._escape_css(attributes[attr])
                selectors.append(
                    self._create_selector(
                        f'[{attr}="{value}"]',
                        SelectorType.ARIA,
                        f"ARIA: {attr}",
                    )
                )

        return selectors

    def _generate_class_selectors(self, class_value: str) -> list[Selector]:
        """Generate selectors from class attribute."""
        selectors = []

        classes = class_value.split()

        # Skip if too many classes (likely dynamically generated)
        if len(classes) > 10:
            return selectors

        # Skip indexed classes if configured
        if self.avoid_indexed_selectors:
            classes = [c for c in classes if not re.search(r"\d{3,}", c)]

        # Individual class selectors
        for cls in classes[:5]:
            # Skip very short or generic classes
            if len(cls) < 3 or cls in ["active", "selected", "disabled", "hidden"]:
                continue

            selectors.append(
                self._create_selector(
                    f".{cls}",
                    SelectorType.CLASS,
                    f"Class: {cls}",
                )
            )

        # Combined class selector
        if len(classes) >= 2 and len(classes) <= 4:
            combined = "." + ".".join(classes[:3])
            if len(combined) <= self.max_selector_length:
                selectors.append(
                    self._create_selector(
                        combined,
                        SelectorType.CSS,
                        "Combined classes",
                    )
                )

        return selectors

    def _generate_text_selectors(
        self,
        text: str,
        attributes: dict,
    ) -> list[Selector]:
        """Generate text-based selectors."""
        selectors = []

        # Clean and truncate text
        text = text.strip()[:100]

        if not text:
            return selectors

        tag = attributes.get("tagName", "*").lower()

        # Exact text match
        if len(text) <= 50:
            escaped = self._escape_xpath(text)
            selectors.append(
                self._create_selector(
                    f"//{tag}[text()='{escaped}']",
                    SelectorType.XPATH,
                    "Exact text match",
                )
            )

        # Contains text
        words = text.split()[:5]  # First 5 words
        if words:
            search_text = " ".join(words)
            escaped = self._escape_xpath(search_text)
            selectors.append(
                self._create_selector(
                    f"//{tag}[contains(text(), '{escaped}')]",
                    SelectorType.XPATH,
                    "Contains text",
                )
            )

        return selectors

    def _generate_tag_selectors(
        self,
        tag: str,
        attributes: dict,
    ) -> list[Selector]:
        """Generate tag-based selectors with attributes."""
        selectors = []

        # Tag with single attribute
        for attr in ["type", "placeholder", "title", "alt"]:
            if attributes.get(attr):
                value = self._escape_css(attributes[attr])
                selectors.append(
                    self._create_selector(
                        f'{tag}[{attr}="{value}"]',
                        SelectorType.CSS,
                        f"{tag} with {attr}",
                    )
                )

        return selectors
