from odoo import api, fields, models
from odoo.exceptions import UserError


class C18OkrKpi(models.Model):
    _name = "c18.okr.kpi"
    _description = "OKR KPI"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(required=True, tracking=True)
    objective_id = fields.Many2one("c18.okr.objective", required=True, ondelete="cascade", tracking=True)
    cycle_id = fields.Many2one("c18.okr.cycle", related="objective_id.cycle_id", store=True, index=True)
    objective_scope = fields.Selection(
        related="objective_id.objective_scope",
        store=True,
        index=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        related="objective_id.department_id",
        store=True,
        index=True,
    )
    employee_id = fields.Many2one("hr.employee", related="objective_id.employee_id", store=True, index=True)
    is_my_department = fields.Boolean(compute="_compute_is_my_department", search="_search_is_my_department")
    kr_type = fields.Selection(
        [("numeric", "Numeric"), ("percentage", "Percentage"), ("milestone", "Milestone")],
        default="numeric",
        required=True,
        tracking=True,
    )
    start_value = fields.Float(default=0.0, tracking=True)
    target_value = fields.Float(required=True, tracking=True)
    target_mode = fields.Selection(
        [("overall", "Overall Target"), ("periodic", "Periodic Target")],
        default="overall",
        required=True,
        tracking=True,
    )
    weight = fields.Float(default=1.0, tracking=True)
    is_lower_better = fields.Boolean()
    owner_id = fields.Many2one("res.users", default=lambda self: self.env.user, tracking=True)
    data_source = fields.Selection(
        [
            ("manual", "Manual Check-in"),
            ("employees_count", "Total Employees"),
            ("department_employees_count", "Department Employees"),
            ("sale_order_amount", "Confirmed Sales Amount"),
            ("sale_order_count", "Confirmed Sales Count"),
            ("project_task_done", "Done Tasks"),
        ],
        default="manual",
        required=True,
        tracking=True,
    )
    auto_checkin_enabled = fields.Boolean(default=False, tracking=True)
    target_line_ids = fields.One2many("c18.kpi.target.line", "kpi_id")
    checkin_ids = fields.One2many("c18.kpi.checkin", "kpi_id")
    latest_checkin_id = fields.Many2one("c18.kpi.checkin", compute="_compute_latest_checkin", store=True)
    actual_value = fields.Float(compute="_compute_latest_checkin", store=True)
    checkin_date = fields.Date(compute="_compute_latest_checkin", store=True)
    current_target_value = fields.Float(compute="_compute_current_target_value", store=True)
    is_checkin_overdue = fields.Boolean(compute="_compute_is_checkin_overdue", search="_search_is_checkin_overdue")
    kpi_progress = fields.Float(compute="_compute_kpi_progress", store=True)
    achievement_rate = fields.Float(compute="_compute_kpi_progress", store=True)
    state = fields.Selection(
        [("new", "New"), ("in_progress", "In Progress"), ("successful", "Successful"), ("failed", "Failed")],
        compute="_compute_kpi_progress",
        store=True,
    )
    rag_status = fields.Selection(
        [("red", "Red"), ("amber", "Amber"), ("green", "Green")],
        compute="_compute_kpi_progress",
        store=True,
    )

    @api.depends("checkin_ids.checkin_date", "checkin_ids.actual_value", "checkin_ids.create_date")
    def _compute_latest_checkin(self):
        for kpi in self:
            latest = False
            if kpi.checkin_ids:
                latest = kpi.checkin_ids.sorted(
                    key=lambda record: (
                        record.checkin_date or fields.Date.today(),
                        record.create_date or fields.Datetime.now(),
                    ),
                    reverse=True,
                )[:1]
                latest = latest[0]
            kpi.latest_checkin_id = latest
            kpi.actual_value = latest.actual_value if latest else 0.0
            kpi.checkin_date = latest.checkin_date if latest else False

    @api.depends("target_mode", "target_value", "target_line_ids.period_date", "target_line_ids.target_value", "checkin_date")
    def _compute_current_target_value(self):
        for kpi in self:
            target_value = kpi.target_value
            if kpi.target_mode == "periodic" and kpi.checkin_date and kpi.target_line_ids:
                period_date = fields.Date.start_of(kpi.checkin_date, "month")
                target_line = kpi.target_line_ids.filtered(lambda line: line.period_date == period_date)[:1]
                if target_line:
                    target_value = target_line.target_value
            kpi.current_target_value = target_value

    @api.depends("department_id")
    def _compute_is_my_department(self):
        department_ids = self.env.user.employee_ids.department_id.ids
        for kpi in self:
            kpi.is_my_department = kpi.department_id.id in department_ids if kpi.department_id else False

    @api.depends("checkin_date")
    def _compute_is_checkin_overdue(self):
        today = fields.Date.today()
        deadline = today.replace(day=1) if today.day > 7 else today
        for kpi in self:
            kpi.is_checkin_overdue = not kpi.checkin_date or kpi.checkin_date < deadline

    def _search_is_checkin_overdue(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise UserError("Unsupported search for overdue KPI filter.")
        today = fields.Date.today()
        deadline = today.replace(day=1) if today.day > 7 else today
        overdue_domain = [
            "|",
            ("checkin_date", "=", False),
            ("checkin_date", "<", deadline),
        ]
        if (operator == "=" and value) or (operator == "!=" and not value):
            return overdue_domain
        return [
            ("checkin_date", "!=", False),
            ("checkin_date", ">=", deadline),
        ]

    def _search_is_my_department(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise UserError("Unsupported search for My Department filter.")
        domain = [("department_id", "in", self.env.user.employee_ids.department_id.ids)]
        if (operator == "=" and value) or (operator == "!=" and not value):
            return domain
        return ["|", ("department_id", "=", False), ("department_id", "not in", self.env.user.employee_ids.department_id.ids)]

    @api.depends("target_value", "current_target_value", "actual_value", "start_value", "is_lower_better", "kr_type")
    def _compute_kpi_progress(self):
        for kpi in self:
            effective_target = kpi.current_target_value or kpi.target_value
            if kpi.kr_type in ("percentage", "milestone"):
                progress = min(max(kpi.actual_value, 0.0), 100.0)
            elif not effective_target and not kpi.start_value:
                progress = 0.0
            elif kpi.is_lower_better:
                progress = (effective_target / kpi.actual_value * 100.0) if kpi.actual_value else 0.0
            else:
                baseline = kpi.start_value or 0.0
                denominator = effective_target - baseline
                progress = ((kpi.actual_value - baseline) / denominator) * 100.0 if denominator else 0.0
            kpi.kpi_progress = max(progress, 0.0)
            kpi.achievement_rate = max(progress, 0.0)
            if progress < 50:
                kpi.rag_status = "red"
                kpi.state = "failed"
            elif progress < 80:
                kpi.rag_status = "amber"
                kpi.state = "in_progress"
            else:
                kpi.rag_status = "green"
                kpi.state = "successful"
            if not kpi.actual_value and progress == 0.0:
                kpi.state = "new"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            objective = self.env["c18.okr.objective"].browse(vals.get("objective_id"))
            if objective.is_locked:
                raise UserError("You cannot add a key result to a locked objective.")
        return super().create(vals_list)

    def write(self, vals):
        protected_fields = {
            "name",
            "objective_id",
            "kr_type",
            "start_value",
            "target_value",
            "target_mode",
            "weight",
            "is_lower_better",
            "owner_id",
            "data_source",
            "auto_checkin_enabled",
        }
        if protected_fields.intersection(vals):
            for kpi in self:
                if kpi.objective_id.is_locked:
                    raise UserError("You cannot modify a key result under a locked objective.")
        return super().write(vals)

    def action_open_quick_checkin(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Quick Check-in",
            "res_model": "c18.kpi.checkin.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_kpi_id": self.id,
                "default_name": f"{self.name} Check-in",
                "default_actual_value": self.actual_value,
                "default_period_date": fields.Date.start_of(fields.Date.today(), "month"),
            },
        }

    def cron_notify_missing_checkin(self):
        today = fields.Date.today()
        deadline = today.replace(day=1) if today.day > 7 else today
        stale_kpis = self.search([
            "|",
            ("checkin_date", "=", False),
            ("checkin_date", "<", deadline),
        ])
        todo_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        for kpi in stale_kpis:
            user = kpi.owner_id or kpi.objective_id.owner_id
            if not user or not todo_type:
                continue
            existing = self.env["mail.activity"].search([
                ("res_model", "=", self._name),
                ("res_id", "=", kpi.id),
                ("activity_type_id", "=", todo_type.id),
                ("user_id", "=", user.id),
                ("summary", "=", "KPI check-in overdue"),
            ], limit=1)
            if existing:
                continue
            kpi.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=user.id,
                summary="KPI check-in overdue",
                note="Please update the KPI with a new check-in.",
            )

    def _get_auto_checkin_value(self):
        self.ensure_one()
        if self.data_source == "employees_count":
            domain = [("active", "=", True)]
            if self.objective_scope == "individual" and self.employee_id:
                domain.append(("id", "=", self.employee_id.id))
            return float(self.env["hr.employee"].search_count(domain))

        if self.data_source == "department_employees_count":
            domain = [("active", "=", True)]
            if self.department_id:
                domain.append(("department_id", "=", self.department_id.id))
            return float(self.env["hr.employee"].search_count(domain))

        if self.data_source in {"sale_order_amount", "sale_order_count"}:
            if "sale.order" not in self.env:
                return False
            domain = [("state", "in", ["sale", "done"])]
            if self.cycle_id.date_start:
                domain.append(("date_order", ">=", fields.Datetime.to_datetime(self.cycle_id.date_start)))
            if self.cycle_id.date_end:
                domain.append(("date_order", "<=", fields.Datetime.to_datetime(f"{self.cycle_id.date_end} 23:59:59")))
            if self.data_source == "sale_order_amount":
                orders = self.env["sale.order"].search(domain)
                return float(sum(orders.mapped("amount_total")))
            return float(self.env["sale.order"].search_count(domain))

        if self.data_source == "project_task_done":
            if "project.task" not in self.env:
                return False
            domain = [("state", "=", "1_done")]
            if self.department_id and "department_id" in self.env["project.task"]._fields:
                domain.append(("department_id", "=", self.department_id.id))
            return float(self.env["project.task"].search_count(domain))

        return False

    def cron_generate_auto_checkins(self):
        today = fields.Date.today()
        auto_kpis = self.search([
            ("auto_checkin_enabled", "=", True),
            ("data_source", "!=", "manual"),
            ("objective_id.is_locked", "=", False),
        ])
        for kpi in auto_kpis:
            value = kpi._get_auto_checkin_value()
            if value is False:
                continue
            existing = self.env["c18.kpi.checkin"].search([
                ("kpi_id", "=", kpi.id),
                ("checkin_date", "=", today),
                ("note", "=", "Auto-generated from Odoo data source."),
            ], limit=1)
            if existing:
                existing.write({"actual_value": value, "name": f"{kpi.name} Auto Check-in"})
                continue
            self.env["c18.kpi.checkin"].create({
                "name": f"{kpi.name} Auto Check-in",
                "kpi_id": kpi.id,
                "actual_value": value,
                "checkin_date": today,
                "note": "Auto-generated from Odoo data source.",
            })
