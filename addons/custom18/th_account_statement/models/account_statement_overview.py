from odoo import api, fields, models


class AccountStatementOverview(models.TransientModel):
    _name = "account.statement.overview"
    _description = "Account Statement History Overview"

    as_of_date = fields.Date(
        string="As Of Date",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    line_ids = fields.One2many(
        "account.statement.overview.line",
        "overview_id",
        string="Overview Lines",
        readonly=True,
    )
    receivable_line_ids = fields.One2many(
        "account.statement.overview.line",
        "overview_id",
        string="Aged Receivable",
        domain=[("line_type", "=", "receivable")],
        readonly=True,
    )
    payable_line_ids = fields.One2many(
        "account.statement.overview.line",
        "overview_id",
        string="Aged Payable",
        domain=[("line_type", "=", "payable")],
        readonly=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        readonly=True,
    )

    receivable_total = fields.Monetary(
        string="Receivable Outstanding",
        currency_field="currency_id",
        compute="_compute_totals",
    )
    payable_total = fields.Monetary(
        string="Payable Outstanding",
        currency_field="currency_id",
        compute="_compute_totals",
    )

    receivable_not_due = fields.Monetary(
        string="Receivable Not Due",
        currency_field="currency_id",
        compute="_compute_totals",
    )
    receivable_1_30 = fields.Monetary(
        string="Receivable 1-30",
        currency_field="currency_id",
        compute="_compute_totals",
    )
    receivable_31_60 = fields.Monetary(
        string="Receivable 31-60",
        currency_field="currency_id",
        compute="_compute_totals",
    )
    receivable_61_90 = fields.Monetary(
        string="Receivable 61-90",
        currency_field="currency_id",
        compute="_compute_totals",
    )
    receivable_91_plus = fields.Monetary(
        string="Receivable 91+",
        currency_field="currency_id",
        compute="_compute_totals",
    )

    payable_not_due = fields.Monetary(
        string="Payable Not Due",
        currency_field="currency_id",
        compute="_compute_totals",
    )
    payable_1_30 = fields.Monetary(
        string="Payable 1-30",
        currency_field="currency_id",
        compute="_compute_totals",
    )
    payable_31_60 = fields.Monetary(
        string="Payable 31-60",
        currency_field="currency_id",
        compute="_compute_totals",
    )
    payable_61_90 = fields.Monetary(
        string="Payable 61-90",
        currency_field="currency_id",
        compute="_compute_totals",
    )
    payable_91_plus = fields.Monetary(
        string="Payable 91+",
        currency_field="currency_id",
        compute="_compute_totals",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._recompute_lines()
        return records

    @api.depends("line_ids.residual_amount", "line_ids.age_bucket", "line_ids.line_type")
    def _compute_totals(self):
        for rec in self:
            rec_lines = rec.line_ids.filtered(lambda l: l.line_type == "receivable")
            pay_lines = rec.line_ids.filtered(lambda l: l.line_type == "payable")

            rec.receivable_total = sum(rec_lines.mapped("residual_amount"))
            rec.payable_total = sum(pay_lines.mapped("residual_amount"))

            rec.receivable_not_due = sum(
                rec_lines.filtered(lambda l: l.age_bucket == "not_due").mapped("residual_amount")
            )
            rec.receivable_1_30 = sum(
                rec_lines.filtered(lambda l: l.age_bucket == "1_30").mapped("residual_amount")
            )
            rec.receivable_31_60 = sum(
                rec_lines.filtered(lambda l: l.age_bucket == "31_60").mapped("residual_amount")
            )
            rec.receivable_61_90 = sum(
                rec_lines.filtered(lambda l: l.age_bucket == "61_90").mapped("residual_amount")
            )
            rec.receivable_91_plus = sum(
                rec_lines.filtered(lambda l: l.age_bucket == "91_plus").mapped("residual_amount")
            )

            rec.payable_not_due = sum(
                pay_lines.filtered(lambda l: l.age_bucket == "not_due").mapped("residual_amount")
            )
            rec.payable_1_30 = sum(
                pay_lines.filtered(lambda l: l.age_bucket == "1_30").mapped("residual_amount")
            )
            rec.payable_31_60 = sum(
                pay_lines.filtered(lambda l: l.age_bucket == "31_60").mapped("residual_amount")
            )
            rec.payable_61_90 = sum(
                pay_lines.filtered(lambda l: l.age_bucket == "61_90").mapped("residual_amount")
            )
            rec.payable_91_plus = sum(
                pay_lines.filtered(lambda l: l.age_bucket == "91_plus").mapped("residual_amount")
            )

    @api.model
    def action_open_overview(self):
        overview = self.create({})
        return {
            "type": "ir.actions.act_window",
            "name": "Statement History",
            "res_model": self._name,
            "res_id": overview.id,
            "view_mode": "form",
            "target": "current",
            "views": [
                (
                    self.env.ref(
                        "th_account_statement.view_account_statement_overview_form"
                    ).id,
                    "form",
                )
            ],
        }

    def action_refresh(self):
        self.ensure_one()
        self._recompute_lines()
        return {
            "type": "ir.actions.act_window",
            "name": "Statement History",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def _compute_bucket(self, due_date):
        as_of = self.as_of_date or fields.Date.context_today(self)
        base_date = due_date or as_of
        days_overdue = (as_of - base_date).days

        if days_overdue <= 0:
            return "not_due", days_overdue
        if days_overdue <= 30:
            return "1_30", days_overdue
        if days_overdue <= 60:
            return "31_60", days_overdue
        if days_overdue <= 90:
            return "61_90", days_overdue
        return "91_plus", days_overdue

    def _prepare_lines_for_type(self, line_type):
        self.ensure_one()
        engine = self.env["account.statement.engine"]
        statement_type = "customer" if line_type == "receivable" else "vendor"
        move_types = engine._get_move_types(statement_type)

        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "=", "posted"),
            ("move_type", "in", move_types),
            ("payment_state", "!=", "paid"),
            ("amount_residual", "!=", 0.0),
            ("partner_id", "!=", False),
        ]
        moves = self.env["account.move"].search(
            domain, order="invoice_date_due asc, invoice_date asc, id asc"
        )

        values = []
        for move in moves:
            residual = engine._normalize_amount(
                statement_type, move.move_type, move.amount_residual
            )
            total = engine._normalize_amount(statement_type, move.move_type, move.amount_total)
            paid = total - residual
            age_bucket, days_overdue = self._compute_bucket(move.invoice_date_due)

            values.append(
                {
                    "overview_id": self.id,
                    "line_type": line_type,
                    "partner_id": move.partner_id.id,
                    "move_id": move.id,
                    "invoice_date": move.invoice_date,
                    "due_date": move.invoice_date_due,
                    "payment_state": move.payment_state,
                    "currency_id": move.currency_id.id or self.currency_id.id,
                    "total_amount": total,
                    "paid_amount": paid,
                    "residual_amount": residual,
                    "age_bucket": age_bucket,
                    "days_overdue": days_overdue,
                }
            )
        return values

    def _recompute_lines(self):
        self.ensure_one()
        self.line_ids.unlink()
        values = self._prepare_lines_for_type("receivable")
        values += self._prepare_lines_for_type("payable")
        if values:
            self.env["account.statement.overview.line"].create(values)


class AccountStatementOverviewLine(models.TransientModel):
    _name = "account.statement.overview.line"
    _description = "Account Statement History Overview Line"
    _order = "line_type, due_date asc, invoice_date asc, id asc"

    LINE_TYPE_SELECTION = [
        ("receivable", "Receivable"),
        ("payable", "Payable"),
    ]

    AGE_BUCKET_SELECTION = [
        ("not_due", "Not Due"),
        ("1_30", "1-30 Days"),
        ("31_60", "31-60 Days"),
        ("61_90", "61-90 Days"),
        ("91_plus", "91+ Days"),
    ]

    overview_id = fields.Many2one(
        "account.statement.overview", required=True, ondelete="cascade"
    )
    line_type = fields.Selection(LINE_TYPE_SELECTION, required=True, index=True)
    partner_id = fields.Many2one("res.partner", string="Partner", required=True, index=True)
    move_id = fields.Many2one("account.move", string="Transaction", required=True, index=True)
    invoice_date = fields.Date(string="Invoice/Bill Date")
    due_date = fields.Date(string="Due Date")
    payment_state = fields.Selection(
        selection=lambda self: self.env["account.move"]._fields["payment_state"].selection,
        string="Payment Status",
    )
    age_bucket = fields.Selection(AGE_BUCKET_SELECTION, string="Aging Bucket", index=True)
    days_overdue = fields.Integer(string="Days Overdue")
    currency_id = fields.Many2one("res.currency", string="Currency", required=True)
    total_amount = fields.Monetary(string="Total Amount", currency_field="currency_id")
    paid_amount = fields.Monetary(string="Paid Amount", currency_field="currency_id")
    residual_amount = fields.Monetary(string="Outstanding", currency_field="currency_id")
