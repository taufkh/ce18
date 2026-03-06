from odoo import fields, models


class C18KpiCheckinWizard(models.TransientModel):
    _name = "c18.kpi.checkin.wizard"
    _description = "KPI Quick Check-in Wizard"

    kpi_id = fields.Many2one("c18.okr.kpi", required=True)
    objective_id = fields.Many2one("c18.okr.objective", related="kpi_id.objective_id", readonly=True)
    cycle_id = fields.Many2one("c18.okr.cycle", related="kpi_id.cycle_id", readonly=True)
    department_id = fields.Many2one("hr.department", related="kpi_id.department_id", readonly=True)
    employee_id = fields.Many2one("hr.employee", related="kpi_id.employee_id", readonly=True)
    owner_id = fields.Many2one("res.users", related="kpi_id.owner_id", readonly=True)
    current_actual_value = fields.Float(related="kpi_id.actual_value", readonly=True)
    target_value = fields.Float(related="kpi_id.target_value", readonly=True)
    current_target_value = fields.Float(related="kpi_id.current_target_value", readonly=True)
    name = fields.Char(required=True)
    actual_value = fields.Float(required=True)
    checkin_date = fields.Date(required=True, default=fields.Date.context_today)
    period_date = fields.Date(required=True, default=lambda self: fields.Date.start_of(fields.Date.today(), "month"))
    note = fields.Text()
    evidence_attachment_ids = fields.Many2many("ir.attachment", string="Evidence Attachments")

    def action_submit_checkin(self):
        self.ensure_one()
        self.env["c18.kpi.checkin"].create({
            "name": self.name,
            "kpi_id": self.kpi_id.id,
            "actual_value": self.actual_value,
            "checkin_date": self.checkin_date,
            "period_date": self.period_date,
            "note": self.note,
            "approval_state": "pending",
            "evidence_attachment_ids": [(6, 0, self.evidence_attachment_ids.ids)],
        })
        return {"type": "ir.actions.act_window_close"}
