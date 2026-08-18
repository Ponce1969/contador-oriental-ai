from unittest.mock import MagicMock

import pytest

from models.errors import AppError
from repositories.household.household_repository import HouseholdRepository
from repositories.household.link_repository import SharedExpenseLinkRepository
from repositories.household.member_repository import HouseholdMemberRepository
from services.domain.household.balance_service import HouseholdBalanceService
from services.domain.household.household_service import HouseholdService


class TestHouseholdService:
    def setup_method(self):
        self.repo = MagicMock(spec=HouseholdRepository)
        self.member_repo = MagicMock(spec=HouseholdMemberRepository)
        self.link_repo = MagicMock(spec=SharedExpenseLinkRepository)
        self.balance_service = MagicMock(spec=HouseholdBalanceService)
        self.service = HouseholdService(
            household_repo=self.repo,
            member_repo=self.member_repo,
            link_repo=self.link_repo,
            balance_service=self.balance_service
        )

    def test_create_household_success(self):
        # Arrange
        self.member_repo.get_active_membership.return_value = None
        mock_household = MagicMock()
        mock_household.id = 1
        self.repo.create.return_value = mock_household
        
        # Act
        result = self.service.create_household("Viaje a Rocha", 10)
        
        # Assert
        assert result.id == 1
        self.repo.create.assert_called_once_with("Viaje a Rocha")
        self.member_repo.add_member.assert_called_once_with(1, 10, role="admin")

    def test_create_household_invalid_name(self):
        # Arrange
        self.member_repo.get_active_membership.return_value = None
        
        # Act & Assert
        with pytest.raises(AppError) as exc_info:
            self.service.create_household("  ", 10)
        assert "vacío" in exc_info.value.message.lower()

    def test_get_current_household_exists(self):
        # Arrange
        mock_membership = MagicMock()
        mock_membership.household_id = 1
        self.member_repo.get_active_membership.return_value = mock_membership
        
        mock_household = MagicMock()
        mock_household.id = 1
        self.repo.get_by_id.return_value = mock_household
        
        # Act
        result = self.service.get_household_for_familia(10)
        
        # Assert
        assert result.id == 1

    def test_get_current_household_not_found(self):
        # Arrange
        self.member_repo.get_active_membership.return_value = None
        
        # Act
        result = self.service.get_household_for_familia(10)
        
        # Assert
        assert result is None
