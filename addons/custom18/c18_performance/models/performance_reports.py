from odoo import fields, models, tools


class C18PerformanceKpiStatusReport(models.Model):
    _name = "c18.performance.kpi.status.report"
    _description = "KPI Status Report"
    _auto = False
    _rec_name = "department_id"

    department_id = fields.Many2one("hr.department", readonly=True)
    cycle_id = fields.Many2one("c18.okr.cycle", readonly=True)
    objective_scope = fields.Selection(
        [("company", "Company"), ("department", "Department"), ("individual", "Individual")],
        readonly=True,
    )
    rag_status = fields.Selection(
        [("red", "Red"), ("amber", "Amber"), ("green", "Green")],
        readonly=True,
    )
    kpi_count = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    k.department_id AS department_id,
                    k.cycle_id AS cycle_id,
                    k.objective_scope AS objective_scope,
                    k.rag_status AS rag_status,
                    COUNT(k.id) AS kpi_count
                FROM c18_okr_kpi k
                GROUP BY k.department_id, k.cycle_id, k.objective_scope, k.rag_status
            )
        """)


class C18PerformanceDepartmentReport(models.Model):
    _name = "c18.performance.department.report"
    _description = "Department Progress Report"
    _auto = False
    _rec_name = "department_id"

    department_id = fields.Many2one("hr.department", readonly=True)
    cycle_id = fields.Many2one("c18.okr.cycle", readonly=True)
    objective_scope = fields.Selection(
        [("company", "Company"), ("department", "Department"), ("individual", "Individual")],
        readonly=True,
    )
    total_progress = fields.Float(readonly=True)
    objective_count = fields.Integer(readonly=True)
    kpi_count = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    o.department_id AS department_id,
                    o.cycle_id AS cycle_id,
                    o.objective_scope AS objective_scope,
                    COALESCE(AVG(o.total_progress), 0.0) AS total_progress,
                    COUNT(DISTINCT o.id) AS objective_count,
                    COUNT(k.id) AS kpi_count
                FROM c18_okr_objective o
                LEFT JOIN c18_okr_kpi k ON k.objective_id = o.id
                GROUP BY o.department_id, o.cycle_id, o.objective_scope
            )
        """)


class C18PerformanceCycleScorecardReport(models.Model):
    _name = "c18.performance.cycle.scorecard.report"
    _description = "Cycle Scorecard Report"
    _auto = False
    _rec_name = "cycle_id"

    cycle_id = fields.Many2one("c18.okr.cycle", readonly=True)
    objective_scope = fields.Selection(
        [("company", "Company"), ("department", "Department"), ("individual", "Individual")],
        readonly=True,
    )
    objective_count = fields.Integer(readonly=True)
    avg_progress = fields.Float(readonly=True)
    red_kpi_count = fields.Integer(readonly=True)
    green_kpi_count = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    o.cycle_id AS cycle_id,
                    o.objective_scope AS objective_scope,
                    COUNT(DISTINCT o.id) AS objective_count,
                    COALESCE(AVG(o.total_progress), 0.0) AS avg_progress,
                    COALESCE(SUM(CASE WHEN k.rag_status = 'red' THEN 1 ELSE 0 END), 0) AS red_kpi_count,
                    COALESCE(SUM(CASE WHEN k.rag_status = 'green' THEN 1 ELSE 0 END), 0) AS green_kpi_count
                FROM c18_okr_objective o
                LEFT JOIN c18_okr_kpi k ON k.objective_id = o.id
                GROUP BY o.cycle_id, o.objective_scope
            )
        """)


class C18PerformanceOwnerScorecardReport(models.Model):
    _name = "c18.performance.owner.scorecard.report"
    _description = "Owner Scorecard Report"
    _auto = False
    _rec_name = "owner_id"

    cycle_id = fields.Many2one("c18.okr.cycle", readonly=True)
    owner_id = fields.Many2one("res.users", readonly=True)
    department_id = fields.Many2one("hr.department", readonly=True)
    objective_scope = fields.Selection(
        [("company", "Company"), ("department", "Department"), ("individual", "Individual")],
        readonly=True,
    )
    objective_count = fields.Integer(readonly=True)
    avg_progress = fields.Float(readonly=True)
    achievement_rate = fields.Float(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    o.cycle_id AS cycle_id,
                    o.owner_id AS owner_id,
                    o.department_id AS department_id,
                    o.objective_scope AS objective_scope,
                    COUNT(DISTINCT o.id) AS objective_count,
                    COALESCE(AVG(o.total_progress), 0.0) AS avg_progress,
                    COALESCE(AVG(k.achievement_rate), 0.0) AS achievement_rate
                FROM c18_okr_objective o
                LEFT JOIN c18_okr_kpi k ON k.objective_id = o.id
                GROUP BY o.cycle_id, o.owner_id, o.department_id, o.objective_scope
            )
        """)


class C18PerformanceMonthlyTrendReport(models.Model):
    _name = "c18.performance.monthly.trend.report"
    _description = "Monthly KPI Trend Report"
    _auto = False
    _rec_name = "kpi_id"

    kpi_id = fields.Many2one("c18.okr.kpi", readonly=True)
    objective_id = fields.Many2one("c18.okr.objective", readonly=True)
    cycle_id = fields.Many2one("c18.okr.cycle", readonly=True)
    owner_id = fields.Many2one("res.users", readonly=True)
    department_id = fields.Many2one("hr.department", readonly=True)
    period_date = fields.Date(readonly=True)
    target_value = fields.Float(readonly=True)
    actual_value = fields.Float(readonly=True)
    variance_value = fields.Float(readonly=True)
    approval_state = fields.Selection(
        [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    c.kpi_id AS kpi_id,
                    k.objective_id AS objective_id,
                    k.cycle_id AS cycle_id,
                    k.owner_id AS owner_id,
                    k.department_id AS department_id,
                    c.period_date AS period_date,
                    COALESCE(t.target_value, k.target_value) AS target_value,
                    c.actual_value AS actual_value,
                    c.actual_value - COALESCE(t.target_value, k.target_value) AS variance_value,
                    c.approval_state AS approval_state
                FROM c18_kpi_checkin c
                JOIN c18_okr_kpi k ON k.id = c.kpi_id
                LEFT JOIN c18_kpi_target_line t
                    ON t.kpi_id = c.kpi_id
                   AND t.period_date = c.period_date
            )
        """)
