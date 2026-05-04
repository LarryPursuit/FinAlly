"""Tests for input validation."""

import pytest

from app.validation import validate_quantity, validate_side, validate_ticker


class TestValidateTicker:
    def test_valid_ticker(self):
        assert validate_ticker("AAPL") == "AAPL"

    def test_lowercase_uppercased(self):
        assert validate_ticker("aapl") == "AAPL"

    def test_mixed_case(self):
        assert validate_ticker("Aapl") == "AAPL"

    def test_with_dot(self):
        assert validate_ticker("BRK.B") == "BRK.B"

    def test_with_dash(self):
        assert validate_ticker("BF-B") == "BF-B"

    def test_single_char(self):
        assert validate_ticker("V") == "V"

    def test_with_whitespace(self):
        assert validate_ticker("  AAPL  ") == "AAPL"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            validate_ticker("")

    def test_too_long_raises(self):
        with pytest.raises(ValueError):
            validate_ticker("ABCDEF")

    def test_special_chars_raises(self):
        with pytest.raises(ValueError):
            validate_ticker("AA@L")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            validate_ticker("   ")


class TestValidateQuantity:
    def test_valid_int(self):
        assert validate_quantity(10) == 10

    def test_valid_float_whole(self):
        assert validate_quantity(10.0) == 10

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="positive"):
            validate_quantity(0)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="positive"):
            validate_quantity(-5)

    def test_fractional_raises(self):
        with pytest.raises(ValueError, match="fractional"):
            validate_quantity(1.5)

    def test_large_quantity(self):
        assert validate_quantity(1000000) == 1000000


class TestValidateSide:
    def test_buy(self):
        assert validate_side("buy") == "buy"

    def test_sell(self):
        assert validate_side("sell") == "sell"

    def test_uppercase(self):
        assert validate_side("BUY") == "buy"

    def test_with_whitespace(self):
        assert validate_side("  sell  ") == "sell"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="must be 'buy' or 'sell'"):
            validate_side("hold")
