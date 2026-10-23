"""TDD tests for the deterministic parallel regex engine (S3)."""

from src.security.pii_masking.regex_engine import (
    Detection,
    StructuredRegexScrubber,
)


class TestStructuredRegexScrubber:
    """S3: deterministic regex in parallel for structured isolated fields."""

    def setup_method(self):
        self.scrubber = StructuredRegexScrubber()

    def test_masks_luhn_valid_card(self):
        out = self.scrubber.scrub("Card: 4111 1111 1111 1111 end")
        assert "4111" not in out.text and "[CREDIT_CARD_1]" in out.text

    def test_ignores_luhn_invalid_digit_sequence(self):
        text = "Order 1234567812345678 shipped"
        assert self.scrubber.scrub(text).text == text

    def test_masks_email(self):
        out = self.scrubber.scrub("Contact john@example.com now")
        assert "john@example.com" not in out.text
        assert "[EMAIL_1]" in out.text

    def test_masks_jwt(self):
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        out = self.scrubber.scrub(f"token {jwt} ok")
        assert jwt not in out.text and "[JWT_1]" in out.text

    def test_masks_iban_with_mod97(self):
        out = self.scrubber.scrub("pay to ES9121000418450200051332 today")
        assert "ES9121000418450200051332" not in out.text
        assert "[IBAN_1]" in out.text

    def test_ignores_invalid_iban(self):
        text = "code ES0012345678654321 nope"
        assert self.scrubber.scrub(text).text == text

    def test_placeholders_are_numbered_per_type(self):
        out = self.scrubber.scrub("a@x.com then b@y.com then card 4111111111111111")
        assert "[EMAIL_1]" in out.text and "[EMAIL_2]" in out.text
        assert "[CREDIT_CARD_1]" in out.text

    def test_detections_report_offsets_and_originals(self):
        out = self.scrubber.scrub("mail bob@example.com here")
        dets = [d for d in out.detections if d.label == "email"]
        assert len(dets) == 1
        assert dets[0].original == "bob@example.com"

    def test_parallel_runs_match_sequential_results(self):
        texts = [
            f"user{i}@example.com card 4111111111111111 jwt {j}"
            for i in range(5)
            for j in [
                "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
            ]
        ]
        parallel = self.scrubber.scrub_many(texts)
        sequential = [self.scrubber.scrub(t).text for t in texts]
        assert [r.text for r in parallel] == sequential

    def test_scrub_many_uses_parallel_workers(self):
        texts = ["x" * 10] * 8
        results = self.scrubber.scrub_many(texts, max_workers=4)
        assert len(results) == 8

    def test_no_false_positive_on_plain_text(self):
        text = "Plain transcript with no sensitive data at all."
        assert self.scrubber.scrub(text).text == text

    def test_api_key_masked(self):
        # Built at runtime: avoid push-protection secret-scanner false positive.
        fake_stripe = "sk_live_" + "A1b2C3d4" * 4
        out = self.scrubber.scrub(f"key {fake_stripe}")
        assert "sk_live_" not in out.text


class TestDetectionModel:
    def test_detection_fields(self):
        d = Detection(label="email", original="a@b.com", start=0, end=7)
        assert d.label == "email" and d.original == "a@b.com"
