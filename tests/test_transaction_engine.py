"""
backend/tests/test_transaction_engine.py
Testes unitários para o motor de categorização e regras de negócio.

Testa:
    - Categorização por keywords
    - Detecção de investimentos
    - Filtragem de transferências internas
    - Cálculo de fluxo de caixa
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from backend.models.db_models import Account, Transaction
from backend.services.transaction_engine import TransactionEngine


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def engine():
    return TransactionEngine()


def _make_txn(
    id: str = "txn-1",
    account_id: str = "acc-1",
    txn_date: date = date(2026, 6, 1),
    description: str = "",
    description_raw: str = "",
    amount: float = -100.0,
    txn_type: str = "DEBIT",
    pluggy_category: str | None = None,
    custom_category: str | None = None,
) -> Transaction:
    """Helper para criar transações de teste."""
    txn = Transaction.__new__(Transaction)
    txn.id = id
    txn.account_id = account_id
    txn.date = txn_date
    txn.description = description
    txn.description_raw = description_raw
    txn.amount = amount
    txn.type = txn_type
    txn.pluggy_category = pluggy_category
    txn.pluggy_category_id = None
    txn.custom_category = custom_category
    txn.final_category = "Outros"
    txn.is_investment = False
    txn.is_internal_transfer = False
    txn.is_excluded_from_cashflow = False
    txn.transfer_pair_id = None
    txn.merchant_name = None
    txn.payment_method = None
    return txn


def _make_acc(
    id: str = "acc-1",
    item_id: str = "item-1",
    acc_type: str = "BANK",
    owner_doc_encrypted: bytes | None = None,
) -> Account:
    """Helper para criar contas de teste."""
    acc = Account.__new__(Account)
    acc.id = id
    acc.item_id = item_id
    acc.type = acc_type
    acc.subtype = "CHECKING_ACCOUNT"
    acc.name = "Conta Teste"
    acc.owner_doc_encrypted = owner_doc_encrypted
    acc.balance = 1000.0
    return acc


# =====================================================================
# Testes: Categorização
# =====================================================================

class TestCategorization:
    """Testes para categorização de transações."""

    def test_custom_category_has_priority(self, engine):
        """Custom category sobrescreve tudo."""
        txn = _make_txn(
            custom_category="Minha Categoria",
            pluggy_category="Alimentação",
            description_raw="ifood pedido",
        )
        assert engine.categorize(txn) == "Minha Categoria"

    def test_pluggy_category_over_keywords(self, engine):
        """Pluggy category tem prioridade sobre keywords."""
        txn = _make_txn(
            pluggy_category="Restaurantes",
            description_raw="uber viagem",
        )
        assert engine.categorize(txn) == "Restaurantes"

    def test_keyword_alimentacao(self, engine):
        """Detecta alimentação por keywords."""
        txn = _make_txn(description_raw="IFOOD *RESTAURANTE XYZ")
        assert engine.categorize(txn) == "Alimentação"

    def test_keyword_transporte(self, engine):
        """Detecta transporte por keywords."""
        txn = _make_txn(description_raw="UBER TRIP SAO PAULO")
        assert engine.categorize(txn) == "Transporte"

    def test_keyword_moradia(self, engine):
        """Detecta moradia por keywords."""
        txn = _make_txn(description_raw="PAGTO ALUGUEL JUN/2026")
        assert engine.categorize(txn) == "Moradia"

    def test_keyword_saude(self, engine):
        """Detecta saúde por keywords."""
        txn = _make_txn(description_raw="DROGASIL FARMACIA")
        assert engine.categorize(txn) == "Saúde"

    def test_keyword_lazer(self, engine):
        """Detecta lazer por keywords."""
        txn = _make_txn(description_raw="NETFLIX.COM")
        assert engine.categorize(txn) == "Lazer"

    def test_keyword_receita(self, engine):
        """Detecta receita por keywords."""
        txn = _make_txn(description_raw="SALÁRIO EMPRESA LTDA", amount=5000.0)
        assert engine.categorize(txn) == "Receita"

    def test_fallback_outros(self, engine):
        """Cai em 'Outros' quando nenhuma regra casa."""
        txn = _make_txn(description_raw="XYZABC DESCONHECIDO 123")
        assert engine.categorize(txn) == "Outros"

    def test_empty_description(self, engine):
        """Transação sem descrição cai em 'Outros'."""
        txn = _make_txn(description_raw="")
        assert engine.categorize(txn) == "Outros"

    def test_case_insensitive(self, engine):
        """Keywords são case-insensitive."""
        txn = _make_txn(description_raw="SUPERMERCADO ATACADÃO")
        assert engine.categorize(txn) == "Alimentação"


# =====================================================================
# Testes: Investimentos
# =====================================================================

class TestInvestmentDetection:
    """Testes para detecção de investimentos."""

    def test_investment_account_type(self, engine):
        """Conta do tipo INVESTMENT marca como investimento."""
        txn = _make_txn(description_raw="qualquer coisa")
        acc = _make_acc(acc_type="INVESTMENT")
        assert engine.is_investment_transaction(txn, acc) is True

    def test_pluggy_investment_category(self, engine):
        """Categoria Pluggy 'investment' marca como investimento."""
        txn = _make_txn(pluggy_category="investments")
        assert engine.is_investment_transaction(txn) is True

    def test_tesouro_direto_pattern(self, engine):
        """Detecta Tesouro Direto na descrição."""
        txn = _make_txn(description_raw="Aplicação Tesouro IPCA+ 2035")
        assert engine.is_investment_transaction(txn) is True

    def test_compra_acoes_pattern(self, engine):
        """Detecta compra de ações."""
        txn = _make_txn(description_raw="COMPRA DE AÇÕES - PETR4")
        assert engine.is_investment_transaction(txn) is True

    def test_cdb_pattern(self, engine):
        """Detecta aplicação em CDB."""
        txn = _make_txn(description_raw="Aplicação CDB Banco Inter 120% CDI")
        assert engine.is_investment_transaction(txn) is True

    def test_fundo_imobiliario_pattern(self, engine):
        """Detecta fundo imobiliário."""
        txn = _make_txn(description_raw="FUNDO IMOBILIÁRIO HGLG11")
        assert engine.is_investment_transaction(txn) is True

    def test_normal_purchase_not_investment(self, engine):
        """Compra normal NÃO é marcada como investimento."""
        txn = _make_txn(description_raw="AMAZON MARKETPLACE COMPRA")
        assert engine.is_investment_transaction(txn) is False

    def test_salary_not_investment(self, engine):
        """Salário NÃO é marcado como investimento."""
        txn = _make_txn(description_raw="SALÁRIO EMPRESA LTDA")
        assert engine.is_investment_transaction(txn) is False

    def test_etf_pattern(self, engine):
        """Detecta ETFs brasileiros."""
        txn = _make_txn(description_raw="B3 - COMPRA BOVA11")
        assert engine.is_investment_transaction(txn) is True

    def test_xp_aporte_pattern(self, engine):
        """Detecta aporte via XP."""
        txn = _make_txn(description_raw="XP - APLICAÇÃO FUNDO MULTIMERCADO")
        assert engine.is_investment_transaction(txn) is True


# =====================================================================
# Testes: Transferências Internas
# =====================================================================

class TestInternalTransfers:
    """Testes para detecção de transferências internas."""

    def test_same_item_transfer(self, engine):
        """Transferência entre contas do mesmo Item é detectada."""
        acc1 = _make_acc(id="acc-1", item_id="item-1")
        acc2 = _make_acc(id="acc-2", item_id="item-1")

        txn_out = _make_txn(
            id="txn-out",
            account_id="acc-1",
            amount=-1000.0,
            description_raw="PIX TRANSF CONTA INVEST",
            txn_date=date(2026, 6, 10),
        )
        txn_in = _make_txn(
            id="txn-in",
            account_id="acc-2",
            amount=1000.0,
            description_raw="PIX RECEBIDO",
            txn_date=date(2026, 6, 10),
        )

        session = MagicMock()
        pairs = engine.detect_internal_transfers(
            session, [txn_out, txn_in], [acc1, acc2]
        )

        assert len(pairs) == 1
        assert txn_out.is_internal_transfer is True
        assert txn_in.is_internal_transfer is True
        assert txn_out.is_excluded_from_cashflow is True

    def test_different_amounts_not_paired(self, engine):
        """Valores diferentes NÃO formam par de transferência."""
        acc1 = _make_acc(id="acc-1", item_id="item-1")
        acc2 = _make_acc(id="acc-2", item_id="item-1")

        txn_out = _make_txn(
            id="txn-out",
            account_id="acc-1",
            amount=-1000.0,
            description_raw="PIX TRANSF",
            txn_date=date(2026, 6, 10),
        )
        txn_in = _make_txn(
            id="txn-in",
            account_id="acc-2",
            amount=500.0,
            description_raw="PIX RECEBIDO",
            txn_date=date(2026, 6, 10),
        )

        session = MagicMock()
        pairs = engine.detect_internal_transfers(
            session, [txn_out, txn_in], [acc1, acc2]
        )

        assert len(pairs) == 0
        assert txn_out.is_internal_transfer is False

    def test_different_dates_not_paired(self, engine):
        """Datas com mais de 1 dia de diferença NÃO formam par."""
        acc1 = _make_acc(id="acc-1", item_id="item-1")
        acc2 = _make_acc(id="acc-2", item_id="item-1")

        txn_out = _make_txn(
            id="txn-out",
            account_id="acc-1",
            amount=-1000.0,
            description_raw="TED",
            txn_date=date(2026, 6, 1),
        )
        txn_in = _make_txn(
            id="txn-in",
            account_id="acc-2",
            amount=1000.0,
            description_raw="TED RECEBIDO",
            txn_date=date(2026, 6, 5),
        )

        session = MagicMock()
        pairs = engine.detect_internal_transfers(
            session, [txn_out, txn_in], [acc1, acc2]
        )

        assert len(pairs) == 0

    def test_same_account_not_paired(self, engine):
        """Transações na mesma conta NÃO formam par."""
        acc1 = _make_acc(id="acc-1", item_id="item-1")

        txn_out = _make_txn(
            id="txn-out",
            account_id="acc-1",
            amount=-500.0,
            txn_date=date(2026, 6, 10),
        )
        txn_in = _make_txn(
            id="txn-in",
            account_id="acc-1",
            amount=500.0,
            txn_date=date(2026, 6, 10),
        )

        session = MagicMock()
        pairs = engine.detect_internal_transfers(
            session, [txn_out, txn_in], [acc1]
        )

        assert len(pairs) == 0

    def test_single_account_no_detection(self, engine):
        """Com apenas uma conta, não tenta detectar transferências."""
        acc1 = _make_acc(id="acc-1", item_id="item-1")
        txn = _make_txn(id="txn-1", account_id="acc-1", amount=-500.0)

        session = MagicMock()
        pairs = engine.detect_internal_transfers(
            session, [txn], [acc1]
        )

        assert len(pairs) == 0


# =====================================================================
# Testes: Processamento Completo
# =====================================================================

class TestProcessTransactions:
    """Testes para o fluxo completo de processamento."""

    def test_full_processing(self, engine):
        """Processamento completo categoriza, isola investimentos e
        detecta transferências."""
        acc1 = _make_acc(id="acc-1", item_id="item-1")
        acc2 = _make_acc(id="acc-2", item_id="item-1")

        transactions = [
            # Gasto normal
            _make_txn(
                id="t1", account_id="acc-1",
                description_raw="SUPERMERCADO EXTRA",
                amount=-200.0,
                txn_date=date(2026, 6, 5),
            ),
            # Investimento
            _make_txn(
                id="t2", account_id="acc-1",
                description_raw="Aplicação Tesouro IPCA+ 2035",
                amount=-5000.0,
                txn_date=date(2026, 6, 10),
            ),
            # Transferência (par)
            _make_txn(
                id="t3", account_id="acc-1",
                description_raw="PIX TRANSF CONTA INVEST",
                amount=-1000.0,
                txn_date=date(2026, 6, 12),
            ),
            _make_txn(
                id="t4", account_id="acc-2",
                description_raw="PIX RECEBIDO",
                amount=1000.0,
                txn_date=date(2026, 6, 12),
            ),
            # Receita
            _make_txn(
                id="t5", account_id="acc-1",
                description_raw="SALÁRIO EMPRESA LTDA",
                amount=8000.0,
                txn_date=date(2026, 6, 1),
            ),
        ]

        session = MagicMock()
        result = engine.process_transactions(
            session, transactions, [acc1, acc2]
        )

        # t2 deve ser investimento
        assert transactions[1].is_investment is True
        assert transactions[1].final_category == "Investimentos"

        # t3+t4 devem ser transferência interna
        assert transactions[2].is_internal_transfer is True
        assert transactions[3].is_internal_transfer is True

        # t1 deve ser categorizado como Alimentação
        assert transactions[0].final_category == "Alimentação"

        # t5 deve ser categorizado como Receita
        assert transactions[4].final_category == "Receita"

        # Contadores
        assert result["investments"] >= 1
        assert result["transfer_pairs"] >= 1
        assert result["categorized"] >= 2
