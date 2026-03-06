from odoo import api, fields, models
from odoo.exceptions import UserError


class C18OkrObjective(models.Model):
    _name = "c18.okr.objective"
    _description = "OKR Objective"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    cycle_id = fields.Many2one("c18.okr.cycle", required=True, tracking=True)
    objective_scope = fields.Selection(
        [("company", "Company"), ("department", "Department"), ("individual", "Individual")],
        default="department",
        required=True,
        tracking=True,
    )
    hierarchy_level = fields.Selection(
        [
            ("management", "Management"),
            ("manager", "Manager"),
            ("supervisor", "Supervisor"),
            ("staff", "Staff"),
        ],
        tracking=True,
    )
    department_id = fields.Many2one("hr.department", tracking=True)
    employee_id = fields.Many2one("hr.employee", tracking=True)
    perspective_id = fields.Many2one("c18.bsc.perspective", required=True, tracking=True)
    parent_objective_id = fields.Many2one("c18.okr.objective", ondelete="restrict", tracking=True)
    child_objective_ids = fields.One2many("c18.okr.objective", "parent_objective_id")
    alignment_weight = fields.Float(default=1.0, tracking=True)
    progress_method = fields.Selection(
        [("weighted", "Weighted"), ("equal", "Equal")],
        default="weighted",
        required=True,
        tracking=True,
    )
    owner_id = fields.Many2one("res.users", default=lambda self: self.env.user, tracking=True)
    kpi_ids = fields.One2many("c18.okr.kpi", "objective_id")
    is_my_department = fields.Boolean(compute="_compute_is_my_department", search="_search_is_my_department")
    total_progress = fields.Float(compute="_compute_total_progress", store=True, tracking=True)
    final_score = fields.Float(readonly=True, tracking=True)
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("locked", "Locked"), ("done", "Done")],
        default="draft",
        required=True,
        tracking=True,
    )
    is_locked = fields.Boolean(compute="_compute_is_locked", store=True)

    @api.depends("state", "cycle_id.state")
    def _compute_is_locked(self):
        for objective in self:
            objective.is_locked = objective.state == "locked" or objective.cycle_id.state in ("locked", "closed")

    @api.depends(
        "kpi_ids.weight",
        "kpi_ids.kpi_progress",
        "child_objective_ids.alignment_weight",
        "child_objective_ids.total_progress",
        "progress_method",
    )
    def _compute_total_progress(self):
        for objective in self:
            items = []
            for kpi in objective.kpi_ids:
                items.append((kpi.kpi_progress, kpi.weight or 1.0))
            for child in objective.child_objective_ids:
                items.append((child.total_progress, child.alignment_weight or 1.0))

            if not items:
                objective.total_progress = 0.0
                continue

            if objective.progress_method == "equal":
                objective.total_progress = sum(progress for progress, _weight in items) / len(items)
                continue

            weighted_total = sum(progress * weight for progress, weight in items if weight)
            total_weight = sum(weight for _progress, weight in items if weight)
            objective.total_progress = weighted_total / total_weight if total_weight else 0.0

    @api.depends("department_id")
    def _compute_is_my_department(self):
        department_ids = self.env.user.employee_ids.department_id.ids
        for objective in self:
            objective.is_my_department = objective.department_id.id in department_ids if objective.department_id else False

    def _search_is_my_department(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise UserError("Unsupported search for My Department filter.")
        domain = [("department_id", "in", self.env.user.employee_ids.department_id.ids)]
        if (operator == "=" and value) or (operator == "!=" and not value):
            return domain
        return ["|", ("department_id", "=", False), ("department_id", "not in", self.env.user.employee_ids.department_id.ids)]

    @api.onchange("objective_scope", "employee_id")
    def _onchange_objective_scope(self):
        for objective in self:
            if objective.objective_scope == "individual" and objective.employee_id:
                objective.department_id = objective.employee_id.department_id
            elif objective.objective_scope == "company":
                objective.department_id = False
                objective.employee_id = False

    @api.constrains("cycle_id", "parent_objective_id")
    def _check_parent_cycle_alignment(self):
        for objective in self:
            if objective.parent_objective_id and objective.parent_objective_id.cycle_id != objective.cycle_id:
                raise UserError("Parent objective and child objective must use the same OKR cycle.")

    @api.constrains("parent_objective_id")
    def _check_parent_not_self(self):
        for objective in self:
            if objective.parent_objective_id and objective.parent_objective_id == objective:
                raise UserError("An objective cannot be its own parent.")

    def action_activate(self):
        self.write({"state": "active"})

    def action_lock(self):
        for objective in self:
            pending_checkins = self.env["c18.kpi.checkin"].search_count([
                ("kpi_id.objective_id", "=", objective.id),
                ("approval_state", "=", "pending"),
            ])
            if pending_checkins:
                raise UserError("You cannot lock score while there are pending KPI check-ins awaiting approval.")
            objective.write({
                "state": "locked",
                "final_score": objective.total_progress,
            })

    def action_mark_done(self):
        for objective in self:
            objective.write({
                "state": "done",
                "final_score": objective.final_score or objective.total_progress,
            })

    def action_reset_draft(self):
        self.write({"state": "draft"})

    def write(self, vals):
        locked_fields = {
            "name",
            "cycle_id",
            "objective_scope",
            "hierarchy_level",
            "department_id",
            "employee_id",
            "perspective_id",
            "parent_objective_id",
            "alignment_weight",
            "progress_method",
            "owner_id",
        }
        if locked_fields.intersection(vals):
            for objective in self:
                if objective.is_locked:
                    raise UserError("Locked objectives cannot be modified. Unlock the cycle or objective first.")
        return super().write(vals)
