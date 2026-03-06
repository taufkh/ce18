from datetime import date, timedelta

from odoo import fields, models


class AccountStatementEngine(models.AbstractModel):
    _name = "account.statement.engine"
    _description = "Account Statement Engine"

    PERIOD_FILTER_SELECTION = [
        ("this_month", "This Month"),
        ("last_month", "Last Month"),
        ("this_quarter", "This Quarter"),
        ("last_quarter", "Last Quarter"),
        ("this_year", "This Year"),
        ("last_year", "Last Year"),
        ("custom", "Custom"),
    ]

    PAYMENT_STATUS_SELECTION = [
        ("all", "All"),
        ("not_paid", "Not Paid"),
        ("paid", "Paid"),
        ("in_payment", "In Payment"),
        ("partial", "Partially Paid"),
        ("reversed", "Reversed"),
        ("invoicing_legacy", "Invoicing App Legacy"),
    ]

    def _get_move_types(self, statement_type):
        if statement_type in ("customer", "customer_overdue"):
            return ["out_invoice", "out_refund"]
        return ["in_invoice", "in_refund"]

    def _get_period_date_range(self, period_filter, date_from=None, date_to=None):
        today = fields.Date.context_today(self)
        period = period_filter or "custom"

        if period == "custom":
            return date_from, date_to

        if period == "this_month":
            return today.replace(day=1), today

        if period == "last_month":
            month_start = today.replace(day=1)
            last_month_end = month_start - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            return last_month_start, last_month_end

        if period == "this_quarter":
            quarter = (today.month - 1) // 3
            start_month = quarter * 3 + 1
            return today.replace(month=start_month, day=1), today

        if period == "last_quarter":
            quarter = (today.month - 1) // 3
            this_quarter_start_month = quarter * 3 + 1
            this_quarter_start = today.replace(month=this_quarter_start_month, day=1)
            last_quarter_end = this_quarter_start - timedelta(days=1)
            last_quarter_start_month = ((last_quarter_end.month - 1) // 3) * 3 + 1
            last_quarter_start = last_quarter_end.replace(
                month=last_quarter_start_month, day=1
            )
            return last_quarter_start, last_quarter_end

        if period == "this_year":
            return today.replace(month=1, day=1), today

        if period == "last_year":
            last_year = today.year - 1
            return date(last_year, 1, 1), date(last_year, 12, 31)

        return date_from, date_to

    def _get_payment_state_domain(self, payment_status_filter):
        state = payment_status_filter or "all"
        if state == "all":
            return []
        return [("payment_state", "=", state)]

    def _normalize_amount(self, statement_type, move_type, amount):
        del statement_type
        is_refund = move_type in ("out_refund", "in_refund")
        return -amount if is_refund else amount

    def _build_invoice_domain(
        self,
        partner,
        statement_type,
        date_from=None,
        date_to=None,
        include_paid=False,
        payment_status_filter="all",
    ):
        move_types = self._get_move_types(statement_type)
        today = fields.Date.context_today(self)

        domain = [
            ("partner_id", "child_of", partner.id),
            ("move_type", "in", move_types),
            ("state", "=", "posted"),
        ]

        if statement_type in ("customer", "vendor"):
            if date_from:
                domain.append(("invoice_date", ">=", date_from))
            if date_to:
                domain.append(("invoice_date", "<=", date_to))
            if not include_paid and (payment_status_filter or "all") == "all":
                domain.append(("payment_state", "!=", "paid"))

            domain += self._get_payment_state_domain(payment_status_filter)
        else:
            domain += [
                ("payment_state", "not in", ["paid", "in_payment"]),
                ("invoice_date_due", "<", today),
            ]

        return domain

    def get_invoices(
        self,
        partner,
        statement_type,
        date_from=None,
        date_to=None,
        include_paid=False,
        payment_status_filter="all",
    ):
        domain = self._build_invoice_domain(
            partner=partner,
            statement_type=statement_type,
            date_from=date_from,
            date_to=date_to,
            include_paid=include_paid,
            payment_status_filter=payment_status_filter,
        )
        return self.env["account.move"].search(domain, order="invoice_date asc, id asc")

    def get_opening_balance(self, partner, statement_type, date_from):
        if not date_from:
            return 0.0

        account_type = (
            "asset_receivable"
            if statement_type in ("customer", "customer_overdue")
            else "liability_payable"
        )
        move_lines = self.env["account.move.line"].search(
            [
                ("partner_id", "child_of", partner.id),
                ("parent_state", "=", "posted"),
                ("company_id", "=", self.env.company.id),
                ("account_id.account_type", "=", account_type),
                ("date", "<", date_from),
                ("amount_residual", "!=", 0.0),
            ]
        )
        amount = sum(move_lines.mapped("amount_residual"))
        return amount if statement_type in ("customer", "customer_overdue") else -amount

    def get_ageing_data(self, partner, statement_type):
        move_types = self._get_move_types(statement_type)
        today = fields.Date.context_today(self)

        outstanding = self.env["account.move"].search(
            [
                ("partner_id", "child_of", partner.id),
                ("move_type", "in", move_types),
                ("state", "=", "posted"),
                ("payment_state", "not in", ["paid", "in_payment"]),
                ("invoice_date_due", "!=", False),
            ]
        )

        result = {
            "not_due": 0.0,
            "0_30": 0.0,
            "31_60": 0.0,
            "61_90": 0.0,
            "91_plus": 0.0,
            "total": 0.0,
        }

        for inv in outstanding:
            amount = self._normalize_amount(statement_type, inv.move_type, inv.amount_residual)
            days = (today - inv.invoice_date_due).days

            if days < 0:
                result["not_due"] += amount
            elif days <= 30:
                result["0_30"] += amount
            elif days <= 60:
                result["31_60"] += amount
            elif days <= 90:
                result["61_90"] += amount
            else:
                result["91_plus"] += amount

            result["total"] += amount

        return result
