from datetime import date
from urllib.parse import quote_plus
from uuid import uuid4

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    company_currency_id = fields.Many2one(
        "res.currency",
        string="Company Currency",
        compute="_compute_company_currency_id",
    )
    statement_period_filter = fields.Selection(
        selection=lambda self: self.env["account.statement.engine"].PERIOD_FILTER_SELECTION,
        string="Statement Period",
        default="this_month",
    )
    statement_date_from = fields.Date(
        string="Date From",
        default=lambda self: date.today().replace(day=1),
    )
    statement_date_to = fields.Date(
        string="Date To",
        default=fields.Date.today,
    )
    statement_payment_status_filter = fields.Selection(
        selection=lambda self: self.env["account.statement.engine"].PAYMENT_STATUS_SELECTION,
        string="Payment Status",
        default="all",
    )
    statement_include_paid = fields.Boolean(string="Include Paid", default=False)

    statement_move_ids = fields.Many2many(
        "account.move",
        string="Customer Statements By Filter",
        compute="_compute_statement_dashboard_data",
    )
    statement_opening_balance = fields.Monetary(
        string="Opening Balance",
        currency_field="company_currency_id",
        compute="_compute_statement_dashboard_data",
    )
    statement_total_amount = fields.Monetary(
        string="Total Amount",
        currency_field="company_currency_id",
        compute="_compute_statement_dashboard_data",
    )
    statement_total_paid = fields.Monetary(
        string="Paid Amount",
        currency_field="company_currency_id",
        compute="_compute_statement_dashboard_data",
    )
    statement_total_balance = fields.Monetary(
        string="Balance",
        currency_field="company_currency_id",
        compute="_compute_statement_dashboard_data",
    )
    statement_closing_balance = fields.Monetary(
        string="Closing Balance",
        currency_field="company_currency_id",
        compute="_compute_statement_dashboard_data",
    )

    statement_overdue_move_ids = fields.Many2many(
        "account.move",
        string="Customer Overdue Statements",
        compute="_compute_statement_dashboard_data",
    )
    overdue_total_amount = fields.Monetary(
        string="Overdue Total Amount",
        currency_field="company_currency_id",
        compute="_compute_statement_dashboard_data",
    )
    overdue_total_paid = fields.Monetary(
        string="Overdue Paid Amount",
        currency_field="company_currency_id",
        compute="_compute_statement_dashboard_data",
    )
    overdue_total_balance = fields.Monetary(
        string="Overdue Balance",
        currency_field="company_currency_id",
        compute="_compute_statement_dashboard_data",
    )

    ageing_0_30 = fields.Monetary(
        string="0-30 Days",
        currency_field="company_currency_id",
        compute="_compute_statement_dashboard_data",
    )
    ageing_31_60 = fields.Monetary(
        string="31-60 Days",
        currency_field="company_currency_id",
        compute="_compute_statement_dashboard_data",
    )
    ageing_61_90 = fields.Monetary(
        string="61-90 Days",
        currency_field="company_currency_id",
        compute="_compute_statement_dashboard_data",
    )
    ageing_91_plus = fields.Monetary(
        string="90+ Days",
        currency_field="company_currency_id",
        compute="_compute_statement_dashboard_data",
    )
    ageing_total = fields.Monetary(
        string="Ageing Total",
        currency_field="company_currency_id",
        compute="_compute_statement_dashboard_data",
    )
    statement_share_token = fields.Char(
        string="Statement Share Token",
        copy=False,
        readonly=True,
    )
    statement_share_url = fields.Char(
        string="Statement Share URL",
        compute="_compute_statement_share_url",
    )

    @api.depends_context("allowed_company_ids")
    def _compute_company_currency_id(self):
        currency = self.env.company.currency_id
        for partner in self:
            partner.company_currency_id = currency

    @api.depends(
        "statement_period_filter",
        "statement_date_from",
        "statement_date_to",
        "statement_payment_status_filter",
        "statement_include_paid",
    )
    def _compute_statement_dashboard_data(self):
        engine = self.env["account.statement.engine"]
        empty_moves = self.env["account.move"]

        for partner in self:
            commercial_partner = partner.commercial_partner_id
            if not commercial_partner.id:
                partner.statement_move_ids = empty_moves
                partner.statement_overdue_move_ids = empty_moves
                partner.statement_opening_balance = 0.0
                partner.statement_total_amount = 0.0
                partner.statement_total_paid = 0.0
                partner.statement_total_balance = 0.0
                partner.statement_closing_balance = 0.0
                partner.overdue_total_amount = 0.0
                partner.overdue_total_paid = 0.0
                partner.overdue_total_balance = 0.0
                partner.ageing_0_30 = 0.0
                partner.ageing_31_60 = 0.0
                partner.ageing_61_90 = 0.0
                partner.ageing_91_plus = 0.0
                partner.ageing_total = 0.0
                continue

            date_from, date_to = engine._get_period_date_range(
                partner.statement_period_filter,
                partner.statement_date_from,
                partner.statement_date_to,
            )

            filtered_moves = engine.get_invoices(
                partner=commercial_partner,
                statement_type="customer",
                date_from=date_from,
                date_to=date_to,
                include_paid=partner.statement_include_paid,
                payment_status_filter=partner.statement_payment_status_filter,
            )
            overdue_moves = engine.get_invoices(
                partner=commercial_partner,
                statement_type="customer_overdue",
                include_paid=partner.statement_include_paid,
                payment_status_filter=partner.statement_payment_status_filter,
            )
            ageing = engine.get_ageing_data(
                partner=commercial_partner,
                statement_type="customer_overdue",
            )

            partner.statement_move_ids = filtered_moves
            partner.statement_overdue_move_ids = overdue_moves
            partner.statement_opening_balance = engine.get_opening_balance(
                partner=commercial_partner,
                statement_type="customer",
                date_from=date_from,
            )

            partner.statement_total_amount = sum(
                engine._normalize_amount("customer", mv.move_type, mv.amount_total)
                for mv in filtered_moves
            )
            partner.statement_total_balance = sum(
                engine._normalize_amount("customer", mv.move_type, mv.amount_residual)
                for mv in filtered_moves
            )
            partner.statement_total_paid = (
                partner.statement_total_amount - partner.statement_total_balance
            )
            partner.statement_closing_balance = (
                partner.statement_opening_balance + partner.statement_total_balance
            )

            partner.overdue_total_amount = sum(
                engine._normalize_amount("customer_overdue", mv.move_type, mv.amount_total)
                for mv in overdue_moves
            )
            partner.overdue_total_balance = sum(
                engine._normalize_amount("customer_overdue", mv.move_type, mv.amount_residual)
                for mv in overdue_moves
            )
            partner.overdue_total_paid = (
                partner.overdue_total_amount - partner.overdue_total_balance
            )

            partner.ageing_0_30 = ageing["0_30"]
            partner.ageing_31_60 = ageing["31_60"]
            partner.ageing_61_90 = ageing["61_90"]
            partner.ageing_91_plus = ageing["91_plus"]
            partner.ageing_total = ageing["total"]

    @api.depends("statement_share_token")
    def _compute_statement_share_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        db_name = self.env.cr.dbname
        for partner in self:
            commercial_partner = partner.commercial_partner_id
            token = commercial_partner.statement_share_token
            if base_url and commercial_partner.id and token:
                share_path = f"/statement/share/{commercial_partner.id}?token={token}"
                partner.statement_share_url = (
                    f"{base_url}/web/login?db={db_name}&redirect={quote_plus(share_path)}"
                )
            else:
                partner.statement_share_url = False

    def _create_statement_wizard(
        self,
        statement_type,
        period_filter=None,
        payment_status_filter=None,
    ):
        self.ensure_one()
        engine = self.env["account.statement.engine"]
        commercial_partner = self.commercial_partner_id
        selected_period = period_filter or self.statement_period_filter
        date_from, date_to = engine._get_period_date_range(
            selected_period,
            self.statement_date_from,
            self.statement_date_to,
        )
        selected_status = payment_status_filter or self.statement_payment_status_filter
        return self.env["account.statement.wizard"].create(
            {
                "statement_type": statement_type,
                "partner_ids": [(6, 0, [commercial_partner.id])],
                "period_filter": selected_period,
                "date_from": date_from,
                "date_to": date_to,
                "include_paid": self.statement_include_paid,
                "payment_status_filter": selected_status,
            }
        )

    def action_get_customer_statement(self):
        self.ensure_one()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_send_filter_customer_statement(self):
        self.ensure_one()
        wizard = self._create_statement_wizard("customer")
        return wizard.action_send_email()

    def action_print_filter_customer_statement(self):
        self.ensure_one()
        wizard = self._create_statement_wizard("customer")
        return wizard.action_print_pdf()

    def action_print_filter_customer_statement_xlsx(self):
        self.ensure_one()
        wizard = self._create_statement_wizard("customer")
        return wizard.action_export_xlsx()

    def action_send_customer_statement(self):
        self.ensure_one()
        wizard = self._create_statement_wizard(
            statement_type="customer",
            period_filter="this_year",
            payment_status_filter="all",
        )
        return wizard.action_send_email()

    def action_print_customer_statement(self):
        self.ensure_one()
        wizard = self._create_statement_wizard(
            statement_type="customer",
            period_filter="this_year",
            payment_status_filter="all",
        )
        return wizard.action_print_pdf()

    def action_print_customer_statement_xlsx(self):
        self.ensure_one()
        wizard = self._create_statement_wizard(
            statement_type="customer",
            period_filter="this_year",
            payment_status_filter="all",
        )
        return wizard.action_export_xlsx()

    def action_send_overdue_customer_statement(self):
        self.ensure_one()
        wizard = self._create_statement_wizard(
            statement_type="customer_overdue",
            payment_status_filter="all",
        )
        return wizard.action_send_email()

    def action_print_overdue_customer_statement(self):
        self.ensure_one()
        wizard = self._create_statement_wizard(
            statement_type="customer_overdue",
            payment_status_filter="all",
        )
        return wizard.action_print_pdf()

    def action_print_overdue_customer_statement_xlsx(self):
        self.ensure_one()
        wizard = self._create_statement_wizard(
            statement_type="customer_overdue",
            payment_status_filter="all",
        )
        return wizard.action_export_xlsx()

    def action_generate_statement_share_url(self):
        self.ensure_one()
        commercial_partner = self.commercial_partner_id
        if not commercial_partner.statement_share_token:
            commercial_partner.statement_share_token = uuid4().hex
            message = "Portal statement share URL has been generated."
        else:
            message = "Portal statement share URL is already available."
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Share URL Generated",
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }

    def action_open_statement_share_url(self):
        self.ensure_one()
        commercial_partner = self.commercial_partner_id
        if not commercial_partner.statement_share_token:
            commercial_partner.statement_share_token = uuid4().hex
        return {
            "type": "ir.actions.act_url",
            "url": commercial_partner.statement_share_url,
            "target": "new",
        }
