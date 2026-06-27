"""
Unit tests for healing_service.py (self-healing service).

Tests selector CRUD, the heal stub and session/result listing with a mocked
DB session. Mirrors the patterns in test_suite_service.py.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _make_selector(
    id=1,
    value="#submit-button",
    selector_type="id",
    confidence_score=0.95,
    usage_count=10,
    success_rate=0.9,
    is_active=True,
):
    sel = MagicMock()
    sel.id = id
    sel.value = value
    sel.selector_type = selector_type
    sel.description = None
    sel.confidence_score = confidence_score
    sel.confidence_level = "high"
    sel.is_active = is_active
    sel.usage_count = usage_count
    sel.success_rate = success_rate
    return sel


# ─── Create selector ──────────────────────────────────────────────
class TestCreateSelectorService:
    @pytest.mark.asyncio
    async def test_create_selector_success(self):
        from services.healing_service import create_selector_service

        mock_db = AsyncMock()
        data = MagicMock()
        data.value = ".btn"
        data.selector_type = "css"
        data.description = "Submit button"
        data.confidence_score = 0.8
        data.is_active = True
        data.usage_count = 0
        data.success_rate = 0.0

        result = await create_selector_service(data, db=mock_db)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result.value == ".btn"
        assert result.confidence_level == "high"

    @pytest.mark.asyncio
    async def test_create_selector_classifies_confidence(self):
        from services.healing_service import create_selector_service

        mock_db = AsyncMock()
        data = MagicMock()
        data.value = "//div"
        data.selector_type = "xpath"
        data.description = None
        data.confidence_score = 0.3
        data.is_active = True
        data.usage_count = 0
        data.success_rate = 0.0

        result = await create_selector_service(data, db=mock_db)
        assert result.confidence_level == "low"


# ─── List selectors ───────────────────────────────────────────────
class TestListSelectorsService:
    @pytest.mark.asyncio
    async def test_list_selectors_returns_rows(self):
        from services.healing_service import list_selectors_service

        mock_db = AsyncMock()
        rows = [_make_selector(id=1), _make_selector(id=2)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows
        mock_db.execute.return_value = mock_result

        result = await list_selectors_service(skip=0, limit=100, db=mock_db)
        assert result == rows

    @pytest.mark.asyncio
    async def test_list_selectors_empty(self):
        from services.healing_service import list_selectors_service

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await list_selectors_service(db=mock_db)
        assert result == []


# ─── Get selector ─────────────────────────────────────────────────
class TestGetSelectorById:
    @pytest.mark.asyncio
    async def test_get_selector_found(self):
        from services.healing_service import get_selector_by_id

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_selector(id=5)
        mock_db.execute.return_value = mock_result

        result = await get_selector_by_id(5, mock_db)
        assert result.id == 5

    @pytest.mark.asyncio
    async def test_get_selector_not_found_raises_404(self):
        from services.healing_service import get_selector_by_id

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await get_selector_by_id(999, mock_db)
        assert exc.value.status_code == 404


# ─── Update selector ──────────────────────────────────────────────
class TestUpdateSelectorService:
    @pytest.mark.asyncio
    async def test_update_selector_fields(self):
        from services.healing_service import update_selector_service

        mock_db = AsyncMock()
        sel = _make_selector(id=1, value="old", selector_type="css")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sel
        mock_db.execute.return_value = mock_result

        upd = MagicMock()
        upd.value = "[data-testid='x']"
        upd.selector_type = "data_attribute"
        upd.description = "updated"
        upd.confidence_score = 0.9
        upd.confidence_level = None
        upd.is_active = True
        upd.success_rate = None

        result = await update_selector_service(1, upd, mock_db)
        assert result.value == "[data-testid='x']"
        assert result.selector_type == "data_attribute"
        assert result.confidence_level == "high"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_selector_not_found(self):
        from services.healing_service import update_selector_service

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        upd = MagicMock()
        upd.value = None
        upd.selector_type = None
        upd.description = None
        upd.confidence_score = None
        upd.confidence_level = None
        upd.is_active = None
        upd.success_rate = None

        with pytest.raises(HTTPException) as exc:
            await update_selector_service(9, upd, mock_db)
        assert exc.value.status_code == 404


# ─── Delete selector ──────────────────────────────────────────────
class TestDeleteSelectorService:
    @pytest.mark.asyncio
    async def test_delete_selector_soft_delete(self):
        from services.healing_service import delete_selector_service

        mock_db = AsyncMock()
        sel = _make_selector(id=1, is_active=True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sel
        mock_db.execute.return_value = mock_result

        await delete_selector_service(1, mock_db)
        assert sel.is_active is False
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_selector_not_found(self):
        from services.healing_service import delete_selector_service

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await delete_selector_service(9, mock_db)
        assert exc.value.status_code == 404


# ─── heal_selector (core stub) ────────────────────────────────────
class TestHealSelectorService:
    @pytest.mark.asyncio
    async def test_heal_low_confidence_returns_success(self):
        from services.healing_service import heal_selector_service

        mock_db = AsyncMock()
        sel = _make_selector(id=1, value=".flaky", confidence_score=0.3)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sel
        mock_db.execute.return_value = mock_result

        healing_result = await heal_selector_service(1, mock_db)

        assert healing_result.status == "success"
        assert healing_result.healed_selector_value is not None
        assert healing_result.original_selector_value == ".flaky"
        assert healing_result.attempts >= 1
        assert mock_db.add.call_count >= 2  # session + result
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_heal_high_confidence_returns_skipped(self):
        from services.healing_service import heal_selector_service

        mock_db = AsyncMock()
        sel = _make_selector(id=2, value="#stable", confidence_score=0.92)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sel
        mock_db.execute.return_value = mock_result

        healing_result = await heal_selector_service(2, mock_db)
        assert healing_result.status == "skipped"
        assert healing_result.healed_selector_value is None

    @pytest.mark.asyncio
    async def test_heal_selector_not_found(self):
        from services.healing_service import heal_selector_service

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await heal_selector_service(99, mock_db)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_heal_updates_selector_usage_stats(self):
        from services.healing_service import heal_selector_service

        mock_db = AsyncMock()
        sel = _make_selector(id=1, value=".flaky", confidence_score=0.3, usage_count=5)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sel
        mock_db.execute.return_value = mock_result

        await heal_selector_service(1, mock_db)
        assert sel.usage_count == 6


# ─── Sessions ─────────────────────────────────────────────────────
class TestSessionService:
    @pytest.mark.asyncio
    async def test_list_sessions(self):
        from services.healing_service import list_sessions_service

        mock_db = AsyncMock()
        s1 = MagicMock(id=1, status="success")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [s1]
        mock_db.execute.return_value = mock_result

        result = await list_sessions_service(skip=0, limit=10, db=mock_db)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_session_found(self):
        from services.healing_service import get_session_by_id

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(id=3, status="partial")
        mock_db.execute.return_value = mock_result

        result = await get_session_by_id(3, mock_db)
        assert result.id == 3

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        from services.healing_service import get_session_by_id

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await get_session_by_id(404, mock_db)
        assert exc.value.status_code == 404


# ─── Results ──────────────────────────────────────────────────────
class TestResultsService:
    @pytest.mark.asyncio
    async def test_list_results_with_selector_filter(self):
        from services.healing_service import list_results_service

        mock_db = AsyncMock()
        r = MagicMock(id=1, selector_id=7)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [r]
        mock_db.execute.return_value = mock_result

        result = await list_results_service(selector_id=7, db=mock_db)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_results_no_filter(self):
        from services.healing_service import list_results_service

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await list_results_service(db=mock_db)
        assert result == []


# ─── Confidence helpers ───────────────────────────────────────────
class TestConfidenceHelpers:
    def test_classify_high(self):
        from services.healing_service import classify_confidence

        assert classify_confidence(0.9) == "high"
        assert classify_confidence(0.7) == "high"

    def test_classify_medium(self):
        from services.healing_service import classify_confidence

        assert classify_confidence(0.69) == "medium"
        assert classify_confidence(0.5) == "medium"

    def test_classify_low(self):
        from services.healing_service import classify_confidence

        assert classify_confidence(0.49) == "low"
        assert classify_confidence(0.0) == "low"
