from odoo import api, fields, models


class C18OkrCycle(models.Model):
    _name = "c18.okr.cycle"
    _description = "OKR Cycle"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc, id desc"

    name = fields.Char(required=True, tracking=True)
    period_type = fields.Selection(
        [("annual", "Annual"), ("quarterly", "Quarterly"), ("custom", "Custom")],
        default="quarterly",
        required=True,
        tracking=True,
    )
    date_start = fields.Date(required=True, tracking=True)
    date_end = fields.Date(required=True, tracking=True)
    review_date = fields.Date(tracking=True)
    state = fields.Selection(
        [("draft", "Draft"), ("open", "Open"), ("locked", "Locked"), ("closed", "Closed")],
        default="draft",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)
    objective_ids = fields.One2many("c18.okr.objective", "cycle_id")

    def action_open_cycle(self):
        self.write({"state": "open"})

    def action_lock_cycle(self):
        self.write({"state": "locked"})

    def action_close_cycle(self):
        self.write({"state": "closed"})

    @api.model
    def sync_demo_user_links(self):
        mapping = {
            "hr.employee_niv": "c18_performance.user_c18_management_demo",
            "hr.employee_vad": "c18_performance.user_c18_hr_manager_demo",
            "hr.employee_al": "c18_performance.user_c18_rd_supervisor_demo",
            "hr.employee_jve": "c18_performance.user_c18_project_staff_demo",
        }
        for employee_xmlid, user_xmlid in mapping.items():
            employee = self.env.ref(employee_xmlid, raise_if_not_found=False)
            user = self.env.ref(user_xmlid, raise_if_not_found=False)
            if not employee or not user:
                continue
            values = {"user_id": user.id}
            if user.email:
                values["work_email"] = user.email
            employee.write(values)
