"""
Tests for Shopping functionality.
"""
from datetime import date

import pytest
from pydantic import ValidationError as PydanticError

from models.shopping_model import ShoppingItem


class TestShoppingItem:
    """Test cases for ShoppingItem model."""

    def test_shopping_item_creation(self):
        """Test basic shopping item creation."""
        item = ShoppingItem(
            name="Leche",
            price=150.50,
            category="Alimentos",
        )
        assert item.name == "Leche"
        assert item.price == 150.50
        assert item.category == "Alimentos"
        assert item.purchased is False
        assert item.purchase_date is None

    def test_shopping_item_purchased(self):
        """Test shopping item marked as purchased."""
        item = ShoppingItem(
            name="Pan",
            price=80.00,
            category="Alimentos",
            purchased=True,
            purchase_date=date.today(),
        )
        assert item.purchased is True
        assert item.purchase_date == date.today()

    def test_shopping_item_validation(self):
        """Test shopping item validation."""
        # Empty name should fail
        with pytest.raises(PydanticError):
            ShoppingItem(name="", price=100.00, category="Test")

        # Negative price should fail
        with pytest.raises(PydanticError):
            ShoppingItem(name="Test", price=-50.00, category="Test")

        # Zero price should fail
        with pytest.raises(PydanticError):
            ShoppingItem(name="Test", price=0, category="Test")
