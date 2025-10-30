"""Test suite for production_library module."""
import pytest
import production_library as pl

def test_text_processor():
    proc = pl.TextProcessor("Hello world! This is a test.")
    stats = proc.stats()
    assert stats.word_count == 6

def test_word_frequency():
    proc = pl.TextProcessor("the cat and the dog")
    freq = proc.word_frequency()
    assert freq["the"] == 2

def test_most_common():
    proc = pl.TextProcessor("a a a b b c")
    common = proc.most_common(2)
    assert common[0][0] == "a"
    assert common[0][1] == 3

def test_utility_functions():
    assert pl.count_words("hello world") == 2
    assert pl.reverse_text("abc") == "cba"
    assert pl.is_palindrome("A man a plan a canal Panama")
    assert pl.reading_time("word " * 200) == 1.0

def test_extract_urls():
    text = "Check https://example.com and http://test.org"
    urls = pl.extract_urls(text)
    assert len(urls) == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
