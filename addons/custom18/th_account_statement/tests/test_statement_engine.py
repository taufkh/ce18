from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestStatementEngine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Statement Test Partner", "email": "partner@example.com"}
        )
        cls.engine = cls.env["account.statement.engine"]
        cls.wizard_model = cls.env["account.statement.wizard"]

        receivable = cls.env["account.account"].search(
            [("account_type", "=", "asset_receivable"), ("company_ids", "in", cls.env.company.id)],
            limit=1,
        )
        income = cls.env["account.account"].search(
            [("account_type", "=", "income"), ("company_ids", "in", cls.env.company.id)], limit=1
        )
        sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.env.company.id)], limit=1
        )
        assert receivable and income and sale_journal

        today = fields.Date.context_today(cls.env.user)
        cls.date_from = today.replace(day=1)
        cls.date_to = today

        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "invoice_date": today - timedelta(days=5),
                "invoice_date_due": today + timedelta(days=10),
                "journal_id": sale_journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Service",
                            "quantity": 1,
                            "price_unit": 100.0,
                            "account_id": income.id,
                        },
                    )
                ],
            }
        )
        cls.invoice.action_post()

        cls.refund = cls.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": cls.partner.id,
                "invoice_date": today - timedelta(days=3),
                "invoice_date_due": today + timedelta(days=5),
                "journal_id": sale_journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Refund",
                            "quantity": 1,
                            "price_unit": 20.0,
                            "account_id": income.id,
                        },
                    )
                ],
            }
        )
        cls.refund.action_post()

    def test_period_filter_custom(self):
        date_from, date_to = self.engine._get_period_date_range(
            "custom", self.date_from, self.date_to
        )
        self.assertEqual(date_from, self.date_from)
        self.assertEqual(date_to, self.date_to)

    def test_wizard_report_totals(self):
        wizard = self.wizard_model.create(
            {
                "statement_type": "customer",
                "partner_ids": [(6, 0, [self.partner.id])],
                "period_filter": "custom",
                "date_from": self.date_from,
                "date_to": self.date_to,
                "include_paid": True,
                "payment_status_filter": "all",
            }
        )
        data = wizard.get_all_report_data()
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertTrue(row["total_amount"] > 0)
        self.assertTrue(any(line["is_refund"] for line in row["invoices"]))
        self.assertAlmostEqual(
            row["total_due"], sum(line["amount_due"] for line in row["invoices"]), places=2
        )
