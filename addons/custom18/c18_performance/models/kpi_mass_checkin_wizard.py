from odoo import api, fields, models
from odoo.exceptions import UserError


class C18KpiMassCheckinWizard(models.TransientModel):
    _name = "c18.kpi.mass.checkin.wizard"
    _description = "KPI Mass Monthly Check-in Wizard"

    period_date = fields.Date(required=True, default=lambda self: fields.Date.start_of(fields.Date.today(), "month"))
    checkin_date = fields.Date(required=True, default=fields.Date.context_today)
    department_scope = fields.Boolean(default=False)
    line_ids = fields.One2many("c18.kpi.mass.checkin.wizard.line", "wizard_id")

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        period_date = result.get("period_date") or fields.Date.start_of(fields.Date.today(), "month")
        user = self.env.user
        domain = [("state", "!=", "done"), ("objective_id.is_locked", "=", False)]
        if self.env.context.get("default_department_scope"):
            domain.append(("is_my_department", "=", True))
        else:
            domain.append(("owner_id", "=", user.id))
        kpis = self.env["c18.okr.kpi"].search(domain)
        result["line_ids"] = [
            (0, 0, {
                "kpi_id": kpi.id,
                "current_actual_value": kpi.actual_value,
                "target_value": kpi.current_target_value or kpi.target_value,
                "name": f"{kpi.name} Check-in",
                "period_date": period_date,
            })
            for kpi in kpis
        ]
        return result

    def action_submit_mass_checkin(self):
        self.ensure_one()
        valid_lines = self.line_ids.filtered(lambda line: line.submit and line.actual_value is not False)
        if not valid_lines:
            raise UserError("Select at least one KPI line to submit.")
        for line in valid_lines:
            self.env["c18.kpi.checkin"].create({
                "name": line.name,
                "kpi_id": line.kpi_id.id,
                "actual_value": line.actual_value,
                "checkin_date": self.checkin_date,
                "period_date": self.period_date,
                "note": line.note,
                "approval_state": "pending",
            })
        return {"type": "ir.actions.act_window_close"}


class C18KpiMassCheckinWizardLine(models.TransientModel):
    _name = "c18.kpi.mass.checkin.wizard.line"
    _description = "KPI Mass Monthly Check-in Wizard Line"

    wizard_id = fields.Many2one("c18.kpi.mass.checkin.wizard", required=True, ondelete="cascade")
    submit = fields.Boolean(default=True)
    kpi_id = fields.Many2one("c18.okr.kpi", required=True, readonly=True)
    objective_id = fields.Many2one("c18.okr.objective", related="kpi_id.objective_id", readonly=True)
    department_id = fields.Many2one("hr.department", related="kpi_id.department_id", readonly=True)
    period_date = fields.Date(readonly=True)
    current_actual_value = fields.Float(readonly=True)
    target_value = fields.Float(readonly=True)
    name = fields.Char(required=True)
    actual_value = fields.Float()
    note = fields.Text()
