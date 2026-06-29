"""
Simple test to verify basic functionality without external API calls.
"""

import pytest


def test_basic_math():
    """Test basic mathematical operations."""
    assert 1 + 1 == 2
    assert 2 * 2 == 4
    assert 10 / 2 == 5


def test_string_operations():
    """Test string operations."""
    text = "hello world"
    assert text.upper() == "HELLO WORLD"
    assert len(text) == 11
    assert "hello" in text


class TestSimpleClass:
    """Simple class tests."""
    
    def test_instance_creation(self):
        """Test class instance creation."""
        class TestClass:
            def __init__(self, value):
                self.value = value
        
        instance = TestClass(42)
        assert instance.value == 42
    
    def test_method_call(self):
        """Test method call."""
        class TestClass:
            def get_value(self):
                return 100
        
        instance = TestClass()
        assert instance.get_value() == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])