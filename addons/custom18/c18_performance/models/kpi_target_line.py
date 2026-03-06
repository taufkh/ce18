from odoo import api, fields, models
from odoo.exceptions import UserError


class C18KpiTargetLine(models.Model):
    _name = "c18.kpi.target.line"
    _description = "KPI Period Target"
    _order = "period_date asc, id asc"

    kpi_id = fields.Many2one("c18.okr.kpi", required=True, ondelete="cascade", index=True)
    period_date = fields.Date(required=True, default=lambda self: fields.Date.start_of(fields.Date.today(), "month"))
    name = fields.Char(compute="_compute_name", store=True)
    target_value = fields.Float(required=True)
    weight = fields.Float(default=1.0)
    note = fields.Text()

    _sql_constraints = [
        ("c18_kpi_target_line_unique_period", "unique(kpi_id, period_date)", "Each KPI can only have one target per period."),
    ]

    @api.depends("period_date", "kpi_id.name")
    def _compute_name(self):
        for line in self:
            if line.period_date:
                line.name = f"{line.kpi_id.name} - {fields.Date.to_date(line.period_date).strftime('%b %Y')}"
            else:
                line.name = line.kpi_id.name or "Period Target"

    @api.constrains("period_date")
    def _check_period_date(self):
        for line in self:
            if line.period_date and fields.Date.to_date(line.period_date).day != 1:
                raise UserError("Period target date must be the first day of the month.")
