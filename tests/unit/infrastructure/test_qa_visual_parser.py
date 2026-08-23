"""Unit tests for QA Visual model output parsing."""

from src.infrastructure.qa_visual.parser import ParseResult, parse_qa_analysis

VALID_JSON = """
{
  "page_title": "Login",
  "visible_texts": ["User", "Password", "Sign in"],
  "qa_issues": [],
  "accessibility": {"contrast_issues": [], "missing_alt": false, "missing_labels": []},
  "visual_regression": {"unexpected_whitespace": false, "overlapping_elements": false,
                        "cut_off_content": false, "misaligned": false},
  "overall_score": 92,
  "summary": "Clean login page."
}
"""


class TestExtractJson:
    def test_clean_json(self):
        result = parse_qa_analysis(VALID_JSON)
        assert result.parse_error is False
        assert result.analysis.overall_score == 92
        assert result.analysis.page_title == "Login"

    def test_markdown_fenced_json(self):
        fenced = "```json\n" + VALID_JSON + "\n```"
        result = parse_qa_analysis(fenced)
        assert result.parse_error is False
        assert result.analysis.overall_score == 92

    def test_markdown_fence_without_language_tag(self):
        fenced = "```\n" + VALID_JSON + "\n```"
        result = parse_qa_analysis(fenced)
        assert result.parse_error is False

    def test_json_with_leading_prose(self):
        with_prose = "Here is the analysis:\n" + VALID_JSON
        result = parse_qa_analysis(with_prose)
        assert result.parse_error is False
        assert result.analysis.overall_score == 92

    def test_empty_content(self):
        result = parse_qa_analysis("")
        assert result.parse_error is True
        assert result.analysis is None
        assert result.raw_content == ""

    def test_invalid_json(self):
        result = parse_qa_analysis("this is not json at all")
        assert result.parse_error is True
        assert result.analysis is None
        assert "not json" in result.raw_content

    def test_truncated_json(self):
        result = parse_qa_analysis('{"overall_score": 9')
        assert result.parse_error is True


class TestContractValidation:
    def test_missing_overall_score_fails_contract(self):
        result = parse_qa_analysis('{"page_title": "x", "summary": "no score"}')
        assert result.parse_error is True

    def test_score_out_of_bounds_fails_contract(self):
        result = parse_qa_analysis('{"overall_score": 150, "summary": "x"}')
        assert result.parse_error is True

    def test_unknown_severity_falls_back(self):
        payload = (
            '{"overall_score": 50, "summary": "x", "qa_issues": [{"severity": "catastrophic"}]}'
        )
        result = parse_qa_analysis(payload)
        # Unknown enum value must not crash the whole parse; error tolerance preferred
        assert result.parse_error is False
        assert result.analysis.qa_issues[0].severity.value == "info"


class TestParseResult:
    def test_parse_result_defaults(self):
        r = ParseResult(parse_error=True, raw_content="bad")
        assert r.analysis is None
        assert r.parse_error is True
        assert r.raw_content == "bad"
