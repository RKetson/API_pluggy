"""
tests/test_portfolio_analyzer.py
Testes unitários para o analisador de rentabilidade de carteira.

Testa:
    - Consolidação de portfólio (summary)
    - TWRR (Time-Weighted Rate of Return)
    - MWRR (Money-Weighted Rate of Return / TIR)
    - Benchmark vs CDI
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from models.db_models import Investment, InvestmentTransaction
from services.portfolio_analyzer import PortfolioAnalyzer


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def analyzer():
    return PortfolioAnalyzer()


def _make_investment(
    id: str = "inv-1",
    item_id: str = "item-1",
    name: str = "Tesouro IPCA+ 2035",
    inv_type: str = "FIXED_INCOME",
    amount: float = 11000.0,
    amount_original: float = 10000.0,
    amount_profit: float = 1000.0,
    quantity: float = 1.0,
    code: str = None,
    created_at: datetime = None,
) -> Investment:
    """Helper para criar investimento de teste."""
    inv = Investment()
    inv.id = id
    inv.item_id = item_id
    inv.name = name
    inv.type = inv_type
    inv.amount = amount
    inv.amount_original = amount_original
    inv.amount_profit = amount_profit
    inv.quantity = quantity
    inv.code = code
    inv.created_at = created_at or datetime(2025, 1, 1)
    return inv


def _make_inv_txn(
    id: str = "inv-txn-1",
    investment_id: str = "inv-1",
    txn_type: str = "BUY",
    txn_date: date = date(2025, 1, 15),
    amount: float = 10000.0,
    quantity: float = 1.0,
) -> InvestmentTransaction:
    """Helper para criar movimentação de investimento."""
    txn = InvestmentTransaction()
    txn.id = id
    txn.investment_id = investment_id
    txn.type = txn_type
    txn.date = txn_date
    txn.amount = amount
    txn.quantity = quantity
    return txn


# =====================================================================
# Testes: Consolidação de Portfólio
# =====================================================================

class TestPortfolioSummary:
    """Testes para consolidação do portfólio."""

    def test_empty_portfolio(self, analyzer):
        """Portfólio vazio retorna zeros."""
        session = MagicMock()
        session.query.return_value.all.return_value = []

        result = analyzer.compute_portfolio_summary(session)

        assert result.total_invested == 0.0
        assert result.total_current == 0.0
        assert result.total_return == 0.0

    def test_single_investment(self, analyzer):
        """Portfólio com um investimento."""
        inv = _make_investment(
            amount=11000.0, amount_original=10000.0
        )

        session = MagicMock()
        session.query.return_value.all.return_value = [inv]

        result = analyzer.compute_portfolio_summary(session)

        assert result.total_invested == 10000.0
        assert result.total_current == 11000.0
        assert result.total_return == 1000.0
        assert result.total_return_pct == 0.1  # 10%
        assert len(result.by_asset) == 1
        assert result.by_asset[0]["weight"] == 1.0

    def test_multiple_types(self, analyzer):
        """Portfólio com múltiplos tipos de investimento."""
        inv1 = _make_investment(
            id="inv-1", inv_type="FIXED_INCOME",
            amount=55000.0, amount_original=50000.0,
        )
        inv2 = _make_investment(
            id="inv-2", inv_type="EQUITY", name="PETR4",
            amount=25000.0, amount_original=20000.0,
        )
        inv3 = _make_investment(
            id="inv-3", inv_type="EQUITY", name="VALE3",
            amount=20000.0, amount_original=30000.0,  # prejuízo
        )

        session = MagicMock()
        session.query.return_value.all.return_value = [inv1, inv2, inv3]

        result = analyzer.compute_portfolio_summary(session)

        assert result.total_invested == 100000.0
        assert result.total_current == 100000.0
        assert result.total_return == 0.0
        assert result.total_return_pct == 0.0

        # Tipo FIXED_INCOME
        assert "FIXED_INCOME" in result.by_type
        assert result.by_type["FIXED_INCOME"]["invested"] == 50000.0
        assert result.by_type["FIXED_INCOME"]["current"] == 55000.0

        # Tipo EQUITY (soma)
        assert "EQUITY" in result.by_type
        assert result.by_type["EQUITY"]["invested"] == 50000.0
        assert result.by_type["EQUITY"]["current"] == 45000.0

    def test_zero_invested(self, analyzer):
        """Investimento com valor original zero não causa divisão por zero."""
        inv = _make_investment(amount=100.0, amount_original=0.0)

        session = MagicMock()
        session.query.return_value.all.return_value = [inv]

        result = analyzer.compute_portfolio_summary(session)

        assert result.total_return_pct == 0.0  # Sem divisão por zero


# =====================================================================
# Testes: TWRR
# =====================================================================

class TestTWRR:
    """Testes para Time-Weighted Rate of Return."""

    def test_no_transactions_simple_return(self, analyzer):
        """Sem transações, usa retorno simples."""
        inv = _make_investment(amount=11500.0, amount_original=10000.0)

        session = MagicMock()
        session.query.return_value.get.return_value = inv
        session.query.return_value.filter.return_value\
            .order_by.return_value.all.return_value = []

        result = analyzer.compute_return_twrr(session, "inv-1")

        assert result is not None
        assert abs(result - 0.15) < 0.001  # ~15%

    def test_nonexistent_investment(self, analyzer):
        """Investimento inexistente retorna None."""
        session = MagicMock()
        session.query.return_value.get.return_value = None

        result = analyzer.compute_return_twrr(session, "nonexistent")

        assert result is None


# =====================================================================
# Testes: MWRR
# =====================================================================

class TestMWRR:
    """Testes para Money-Weighted Rate of Return."""

    def test_no_transactions_returns_none(self, analyzer):
        """Sem transações, retorna None."""
        inv = _make_investment()

        session = MagicMock()
        session.query.return_value.get.return_value = inv
        session.query.return_value.filter.return_value\
            .order_by.return_value.all.return_value = []

        result = analyzer.compute_return_mwrr(session, "inv-1")

        assert result is None

    def test_nonexistent_investment(self, analyzer):
        """Investimento inexistente retorna None."""
        session = MagicMock()
        session.query.return_value.get.return_value = None

        result = analyzer.compute_return_mwrr(session, "nonexistent")

        assert result is None


# =====================================================================
# Testes: Benchmark vs CDI
# =====================================================================

class TestBenchmark:
    """Testes para benchmark vs CDI."""

    def test_no_investment_returns_nones(self, analyzer):
        """Investimento inexistente retorna Nones."""
        session = MagicMock()
        session.query.return_value.get.return_value = None

        result = analyzer.benchmark_vs_cdi(session, "nonexistent")

        assert result["asset_return"] is None
        assert result["cdi_return"] is None
        assert result["alpha"] is None

    def test_zero_invested(self, analyzer):
        """Investimento com zero original retorna None para CDI."""
        inv = _make_investment(amount=100.0, amount_original=0.0)

        session = MagicMock()
        session.query.return_value.get.return_value = inv

        result = analyzer.benchmark_vs_cdi(session, "inv-1")

        assert result["asset_return"] is None

    def test_positive_return_with_benchmark(self, analyzer):
        """Investimento com retorno positivo calculado com benchmark."""
        inv = _make_investment(
            amount=11500.0, amount_original=10000.0,
            created_at=datetime(2025, 6, 1),
        )

        first_txn = _make_inv_txn(txn_date=date(2025, 6, 1))

        session = MagicMock()
        session.query.return_value.get.return_value = inv
        session.query.return_value.filter.return_value\
            .order_by.return_value.first.return_value = first_txn

        result = analyzer.benchmark_vs_cdi(session, "inv-1")

        assert result["asset_return"] == 0.15  # 15%
        assert result["cdi_return"] is not None
        assert result["alpha"] is not None


# =====================================================================
# Testes: Retorno Completo
# =====================================================================

class TestFullReturn:
    """Testes para o cálculo completo de retorno."""

    def test_nonexistent(self, analyzer):
        """Investimento inexistente retorna defaults."""
        session = MagicMock()
        session.query.return_value.get.return_value = None

        result = analyzer.compute_full_return(session, "nonexistent")

        assert result.investment_id == "nonexistent"
        assert result.simple_return == 0.0
        assert result.twrr is None
