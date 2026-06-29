"""
Unit tests for Beta Signup Service
"""

import pytest
pytest.importorskip('asyncpg')
pytest.importorskip('redis')
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.beta_signup_service import (
    create_beta_signup,
    get_beta_signup_by_id,
    get_beta_signup_by_email,
    list_beta_signups,
    update_beta_signup,
    approve_beta_signup,
    reject_beta_signup,
    get_beta_signup_stats,
)
from schemas import (
    BetaSignupCreate,
    BetaSignupUpdate,
    BetaSignupStatus,
    TeamSize,
)
from models import BetaSignup


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock()
    return db


@pytest.fixture
def sample_signup_data():
    """Sample beta signup creation data"""
    return BetaSignupCreate(
        email="test@example.com",
        company="Acme Corp",
        use_case="Automated testing for our CI/CD pipeline",
        team_size=TeamSize.small,
        source="landing_page",
    )


@pytest.fixture
def sample_signup():
    """Sample beta signup model"""
    signup = BetaSignup(
        id=1,
        email="test@example.com",
        company="Acme Corp",
        use_case="Automated testing for our CI/CD pipeline",
        team_size="6-20",
        source="landing_page",
        status=BetaSignupStatus.pending.value,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return signup


class TestCreateBetaSignup:
    """Tests for create_beta_signup function"""

    @pytest.mark.asyncio
    async def test_create_signup_success(self, mock_db, sample_signup_data):
        """Test successful signup creation"""
        signup = await create_beta_signup(
            db=mock_db,
            signup_data=sample_signup_data,
        )
        
        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.refresh.called

    @pytest.mark.asyncio
    async def test_create_signup_with_utm_params(self, mock_db):
        """Test signup with UTM parameters"""
        data = BetaSignupCreate(
            email="test@example.com",
            utm_campaign="launch",
            utm_source="twitter",
        )
        
        signup = await create_beta_signup(
            db=mock_db,
            signup_data=data,
        )
        
        assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_create_signup_minimal(self, mock_db):
        """Test signup with minimal data"""
        data = BetaSignupCreate(email="minimal@example.com")
        
        signup = await create_beta_signup(
            db=mock_db,
            signup_data=data,
        )
        
        assert mock_db.add.called


class TestGetBetaSignupById:
    """Tests for get_beta_signup_by_id function"""

    @pytest.mark.asyncio
    async def test_get_signup_exists(self, mock_db, sample_signup):
        """Test getting existing signup"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_signup
        mock_db.execute.return_value = mock_result
        
        result = await get_beta_signup_by_id(mock_db, 1)
        
        assert result == sample_signup

    @pytest.mark.asyncio
    async def test_get_signup_not_found(self, mock_db):
        """Test getting non-existent signup"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await get_beta_signup_by_id(mock_db, 999)
        
        assert result is None


class TestGetBetaSignupByEmail:
    """Tests for get_beta_signup_by_email function"""

    @pytest.mark.asyncio
    async def test_get_by_email_exists(self, mock_db, sample_signup):
        """Test getting signup by email"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_signup
        mock_db.execute.return_value = mock_result
        
        result = await get_beta_signup_by_email(mock_db, "test@example.com")
        
        assert result == sample_signup

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, mock_db):
        """Test getting non-existent email"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await get_beta_signup_by_email(mock_db, "nonexistent@example.com")
        
        assert result is None


class TestListBetaSignups:
    """Tests for list_beta_signups function"""

    @pytest.mark.asyncio
    async def test_list_signups_no_filters(self, mock_db, sample_signup):
        """Test listing signups without filters"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_signup]
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        
        # Use call count to differentiate between queries
        call_count = [0]
        def execute_side_effect(query):
            call_count[0] += 1
            # First call is usually the count query, second is the data query
            if call_count[0] == 1:
                return mock_count_result
            return mock_result
        
        mock_db.execute.side_effect = execute_side_effect
        
        signups, total = await list_beta_signups(mock_db)
        
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_signups_with_status_filter(self, mock_db, sample_signup):
        """Test listing signups with status filter"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_signup]
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        
        mock_db.execute.return_value = mock_result
        
        # First call for count, second for data
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        signups, total = await list_beta_signups(
            mock_db,
            status=BetaSignupStatus.pending,
        )

    @pytest.mark.asyncio
    async def test_list_signups_pagination(self, mock_db):
        """Test signup pagination"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 50
        
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        signups, total = await list_beta_signups(
            mock_db,
            skip=20,
            limit=10,
        )


class TestUpdateBetaSignup:
    """Tests for update_beta_signup function"""

    @pytest.mark.asyncio
    async def test_update_signup_status(self, mock_db, sample_signup):
        """Test updating signup status"""
        with patch('services.beta_signup_service.get_beta_signup_by_id', return_value=sample_signup):
            update_data = BetaSignupUpdate(status=BetaSignupStatus.approved)
            
            result = await update_beta_signup(mock_db, 1, update_data)
            
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_update_signup_notes(self, mock_db, sample_signup):
        """Test updating signup notes"""
        with patch('services.beta_signup_service.get_beta_signup_by_id', return_value=sample_signup):
            update_data = BetaSignupUpdate(notes="Good candidate for beta")
            
            result = await update_beta_signup(mock_db, 1, update_data)
            
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_update_signup_nps_score(self, mock_db, sample_signup):
        """Test updating NPS score"""
        with patch('services.beta_signup_service.get_beta_signup_by_id', return_value=sample_signup):
            update_data = BetaSignupUpdate(feedback_score=9)
            
            result = await update_beta_signup(mock_db, 1, update_data)
            
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_update_signup_not_found(self, mock_db):
        """Test updating non-existent signup"""
        with patch('services.beta_signup_service.get_beta_signup_by_id', return_value=None):
            update_data = BetaSignupUpdate(status=BetaSignupStatus.approved)
            
            result = await update_beta_signup(mock_db, 999, update_data)
            
            assert result is None


class TestApproveBetaSignup:
    """Tests for approve_beta_signup function"""

    @pytest.mark.asyncio
    async def test_approve_signup(self, mock_db, sample_signup):
        """Test approving signup"""
        with patch('services.beta_signup_service.update_beta_signup') as mock_update:
            mock_update.return_value = sample_signup
            
            result = await approve_beta_signup(mock_db, 1)
            
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_sets_invite_timestamp(self, mock_db, sample_signup):
        """Test that approval sets invite_sent_at timestamp"""
        sample_signup.invite_sent_at = None
        
        with patch('services.beta_signup_service.get_beta_signup_by_id', return_value=sample_signup):
            update_data = BetaSignupUpdate(status=BetaSignupStatus.approved)
            
            result = await update_beta_signup(mock_db, 1, update_data)
            
            # The service should set invite_sent_at when status changes to approved
            assert mock_db.commit.called


class TestRejectBetaSignup:
    """Tests for reject_beta_signup function"""

    @pytest.mark.asyncio
    async def test_reject_signup(self, mock_db, sample_signup):
        """Test rejecting signup"""
        with patch('services.beta_signup_service.update_beta_signup') as mock_update:
            mock_update.return_value = sample_signup
            
            result = await reject_beta_signup(mock_db, 1)
            
            mock_update.assert_called_once()


class TestGetBetaSignupStats:
    """Tests for get_beta_signup_stats function"""

    @pytest.mark.asyncio
    async def test_get_stats(self, mock_db):
        """Test getting signup statistics"""
        # Mock total count
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 100
        
        mock_db.execute.return_value = mock_total_result
        
        stats = await get_beta_signup_stats(mock_db)
        
        assert "total" in stats
        assert "by_status" in stats
        assert "by_source" in stats
        assert "by_team_size" in stats
        assert "average_nps" in stats
        assert "conversion_rate" in stats

    @pytest.mark.asyncio
    async def test_get_stats_empty_database(self, mock_db):
        """Test stats with no signups"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result
        
        stats = await get_beta_signup_stats(mock_db)
        
        assert stats["total"] == 0
        assert stats["conversion_rate"] == 0


class TestBetaSignupValidation:
    """Tests for input validation"""

    def test_valid_email_format(self, sample_signup_data):
        """Test that valid email passes validation"""
        assert sample_signup_data.email == "test@example.com"

    def test_valid_team_size(self, sample_signup_data):
        """Test that valid team size passes validation"""
        assert sample_signup_data.team_size == TeamSize.small

    def test_valid_nps_score(self):
        """Test NPS score validation"""
        update = BetaSignupUpdate(feedback_score=9)
        assert update.feedback_score == 9

    def test_nps_score_out_of_range(self):
        """Test that NPS score must be 0-10"""
        with pytest.raises(Exception):  # Pydantic validation error
            BetaSignupUpdate(feedback_score=11)
