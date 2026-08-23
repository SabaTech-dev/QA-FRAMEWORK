"""
Requirement Parser

Parses requirements documents into structured format.
"""

import re
from typing import List


class MarkdownRequirementParser:
    """
    Parser for Markdown-formatted requirements documents.

    Extracts structured requirements from markdown format.
    """

    def parse(self, content: str) -> List[dict]:
        """Parse markdown content into requirements."""
        requirements = []

        # Split by headers (## or ###)
        sections = re.split(r"\n(?=##\s)", content)

        for section in sections:
            if not section.strip():
                continue

            requirement = self._parse_section(section)
            if requirement:
                requirements.append(requirement)

        return requirements

    def _parse_section(self, section: str) -> dict:
        """Parse a single section."""
        lines = section.strip().split("\n")

        if not lines:
            return None

        # Extract title (first ## header)
        title = ""
        for line in lines:
            if line.startswith("## "):
                title = line[3:].strip()
                break

        if not title:
            return None

        # Extract description
        description = self._extract_description(lines)

        # Extract preconditions
        preconditions = self._extract_list(lines, ["preconditions:", "given:", "prerequisites:"])

        # Extract steps
        steps = self._extract_list(lines, ["steps:", "when:", "procedure:"])

        # Extract expected results
        expected_results = self._extract_list(
            lines, ["expected:", "then:", "results:", "expected results:"]
        )

        # Extract priority
        priority = self._extract_priority(lines)

        # Extract tags
        tags = self._extract_tags(lines)

        return {
            "id": self._generate_id(title),
            "title": title,
            "description": description,
            "preconditions": preconditions,
            "steps": steps,
            "expected_results": expected_results,
            "priority": priority,
            "tags": tags,
        }

    def _extract_description(self, lines: List[str]) -> str:
        """Extract description from lines."""
        description_lines = []
        in_description = False

        for line in lines:
            # Skip headers
            if line.startswith("#"):
                in_description = False
                continue

            # Stop at labeled sections
            if any(
                label in line.lower()
                for label in ["preconditions:", "given:", "steps:", "when:", "expected:", "then:"]
            ):
                break

            # Collect description text
            if line.strip() and not in_description:
                in_description = True

            if in_description:
                description_lines.append(line.strip())

        return " ".join(description_lines).strip()

    def _extract_list(self, lines: List[str], labels: List[str]) -> List[str]:
        """Extract list items following a label."""
        items = []
        collecting = False

        for line in lines:
            line_lower = line.lower()

            # Check for label
            if any(label in line_lower for label in labels):
                collecting = True
                continue

            # Collect list items
            if collecting:
                if line.strip().startswith(("-", "*", "1.", "2.", "3.", "4.", "5.")):
                    # Extract text after bullet/number
                    item = re.sub(r"^[-\*\d\.]\s*", "", line.strip())
                    items.append(item)
                elif line.strip() and not line.startswith("#"):
                    # Non-bullet line - could be continuation or new section
                    if not any(
                        label in line_lower
                        for label in [
                            "preconditions:",
                            "given:",
                            "steps:",
                            "when:",
                            "expected:",
                            "then:",
                        ]
                    ):
                        items.append(line.strip())
                    else:
                        break
                elif not line.strip():
                    # Empty line might end the list
                    pass

        return items

    def _extract_priority(self, lines: List[str]) -> str:
        """Extract priority from lines."""
        for line in lines:
            if "priority:" in line.lower():
                priority = line.split(":", 1)[1].strip().lower()
                if priority in ["critical", "high", "medium", "low", "smoke"]:
                    return priority

        return "medium"

    def _extract_tags(self, lines: List[str]) -> List[str]:
        """Extract tags from lines."""
        for line in lines:
            if "tags:" in line.lower():
                tags_str = line.split(":", 1)[1].strip()
                # Parse comma-separated or space-separated tags
                tags = re.split(r"[,\\s]+", tags_str)
                return [t.strip().lstrip("#") for t in tags if t.strip()]

        return []

    def _generate_id(self, title: str) -> str:
        """Generate ID from title."""
        # Convert to snake_case
        id_str = title.lower().replace(" ", "_")
        id_str = re.sub(r"[^a-z0-9_]", "", id_str)
        return f"req_{id_str}"
