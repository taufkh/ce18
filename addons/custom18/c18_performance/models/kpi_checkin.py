from odoo import api, fields, models
from odoo.exceptions import UserError


class C18KpiCheckin(models.Model):
    _name = "c18.kpi.checkin"
    _description = "KPI Check-in"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "checkin_date desc, id desc"

    name = fields.Char(required=True, tracking=True)
    kpi_id = fields.Many2one("c18.okr.kpi", required=True, ondelete="cascade", tracking=True)
    department_id = fields.Many2one(
        "hr.department",
        related="kpi_id.department_id",
        store=True,
        index=True,
    )
    cycle_id = fields.Many2one("c18.okr.cycle", related="kpi_id.cycle_id", store=True, index=True)
    is_my_department = fields.Boolean(compute="_compute_is_my_department", search="_search_is_my_department")
    actual_value = fields.Float(required=True, tracking=True)
    checkin_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    period_date = fields.Date(
        required=True,
        default=lambda self: fields.Date.start_of(fields.Date.today(), "month"),
        tracking=True,
        help="Use the first day of the month for the reporting period.",
    )
    note = fields.Text()
    manager_comment = fields.Text(tracking=True)
    approval_state = fields.Selection(
        [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        default="pending",
        required=True,
        tracking=True,
    )
    approved_by = fields.Many2one("res.users", readonly=True, tracking=True)
    approved_date = fields.Datetime(readonly=True, tracking=True)
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment",
        "c18_kpi_checkin_ir_attachment_rel",
        "checkin_id",
        "attachment_id",
        string="Evidence Attachments",
    )

    @api.depends("department_id")
    def _compute_is_my_department(self):
        department_ids = self.env.user.employee_ids.department_id.ids
        for checkin in self:
            checkin.is_my_department = checkin.department_id.id in department_ids if checkin.department_id else False

    def _search_is_my_department(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise UserError("Unsupported search for My Department filter.")
        domain = [("department_id", "in", self.env.user.employee_ids.department_id.ids)]
        if (operator == "=" and value) or (operator == "!=" and not value):
            return domain
        return ["|", ("department_id", "=", False), ("department_id", "not in", self.env.user.employee_ids.department_id.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            kpi = self.env["c18.okr.kpi"].browse(vals.get("kpi_id"))
            if kpi.objective_id.is_locked:
                raise UserError("You cannot add a check-in to a locked objective.")
            if vals.get("period_date") and fields.Date.to_date(vals["period_date"]).day != 1:
                raise UserError("Check-in period must be set to the first day of the month.")
            if not vals.get("period_date"):
                base_date = fields.Date.to_date(vals.get("checkin_date") or fields.Date.today())
                vals["period_date"] = fields.Date.start_of(base_date, "month")
            if vals.get("approval_state") == "approved" and not vals.get("approved_by"):
                vals["approved_by"] = self.env.user.id
                vals["approved_date"] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        if vals:
            for checkin in self:
                if checkin.kpi_id.objective_id.is_locked:
                    raise UserError("You cannot modify a check-in under a locked objective.")
        if vals.get("period_date") and fields.Date.to_date(vals["period_date"]).day != 1:
            raise UserError("Check-in period must be set to the first day of the month.")
        if vals.get("approval_state") == "approved":
            vals.setdefault("approved_by", self.env.user.id)
            vals.setdefault("approved_date", fields.Datetime.now())
        elif vals.get("approval_state") in ("pending", "rejected"):
            vals.setdefault("approved_by", False)
            vals.setdefault("approved_date", False)
        return super().write(vals)

    def action_submit_for_approval(self):
        self.write({
            "approval_state": "pending",
            "approved_by": False,
            "approved_date": False,
        })

    def action_approve(self):
        self.write({
            "approval_state": "approved",
            "approved_by": self.env.user.id,
            "approved_date": fields.Datetime.now(),
        })

    def action_reject(self):
        self.write({
            "approval_state": "rejected",
            "approved_by": self.env.user.id,
            "approved_date": fields.Datetime.now(),
        })
