from odoo import fields, models, tools


class C18DmsSpreadReport(models.Model):
    _name = "c18.dms.spread.report"
    _description = "DMS Spread Report"
    _auto = False
    _rec_name = "project_id"

    project_id = fields.Many2one("project.project", readonly=True)
    directory_id = fields.Many2one("c18.dms.directory", readonly=True)
    doc_type_id = fields.Many2one("c18.dms.type", readonly=True)
    department_id = fields.Many2one("hr.department", readonly=True)
    document_count = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    d.project_id AS project_id,
                    d.directory_id AS directory_id,
                    d.doc_type_id AS doc_type_id,
                    d.effective_department_id AS department_id,
                    COUNT(d.id) AS document_count
                FROM c18_dms_document d
                GROUP BY d.project_id, d.directory_id, d.doc_type_id, d.effective_department_id
            )
        """)


class C18DmsDirectoryDepartmentReport(models.Model):
    _name = "c18.dms.directory.department.report"
    _description = "DMS Directories by Department"
    _auto = False
    _rec_name = "department_id"

    department_id = fields.Many2one("hr.department", readonly=True)
    directory_count = fields.Integer(readonly=True)
    document_count = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    directory.department_id AS department_id,
                    COUNT(DISTINCT directory.id) AS directory_count,
                    COUNT(document.id) AS document_count
                FROM c18_dms_directory directory
                LEFT JOIN c18_dms_document document ON document.directory_id = directory.id
                GROUP BY directory.department_id
            )
        """)


class C18DmsRevisionActivityReport(models.Model):
    _name = "c18.dms.revision.activity.report"
    _description = "DMS Revision Activity"
    _auto = False
    _rec_name = "version_month"

    version_month = fields.Char(readonly=True)
    document_id = fields.Many2one("c18.dms.document", readonly=True)
    revision_count = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    TO_CHAR(history.version_date, 'YYYY-MM') AS version_month,
                    history.document_id AS document_id,
                    COUNT(history.id) AS revision_count
                FROM c18_dms_history history
                GROUP BY TO_CHAR(history.version_date, 'YYYY-MM'), history.document_id
            )
        """)


class C18DmsShareAuditReport(models.Model):
    _name = "c18.dms.share.audit.report"
    _description = "DMS Share Audit Report"
    _auto = False
    _rec_name = "document_id"

    document_id = fields.Many2one("c18.dms.document", readonly=True)
    access_type = fields.Selection([("page", "Page View"), ("download", "Download")], readonly=True)
    access_date = fields.Date(readonly=True)
    access_count = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    log.document_id AS document_id,
                    log.access_type AS access_type,
                    DATE(log.accessed_at) AS access_date,
                    COUNT(log.id) AS access_count
                FROM c18_dms_share_log log
                GROUP BY log.document_id, log.access_type, DATE(log.accessed_at)
            )
        """)


class C18DmsComplianceReport(models.Model):
    _name = "c18.dms.compliance.report"
    _description = "DMS Compliance Report"
    _auto = False
    _rec_name = "department_id"

    department_id = fields.Many2one("hr.department", readonly=True)
    doc_type_id = fields.Many2one("c18.dms.type", readonly=True)
    total_count = fields.Integer(readonly=True)
    approved_count = fields.Integer(readonly=True)
    review_overdue_count = fields.Integer(readonly=True)
    expiring_count = fields.Integer(readonly=True)
    expired_count = fields.Integer(readonly=True)
    retention_overdue_count = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    d.effective_department_id AS department_id,
                    d.doc_type_id AS doc_type_id,
                    COUNT(d.id) AS total_count,
                    SUM(CASE WHEN d.state = 'approved' THEN 1 ELSE 0 END)::INT AS approved_count,
                    SUM(CASE WHEN d.review_overdue = TRUE THEN 1 ELSE 0 END)::INT AS review_overdue_count,
                    SUM(CASE WHEN d.expiry_state = 'warning' THEN 1 ELSE 0 END)::INT AS expiring_count,
                    SUM(CASE WHEN d.expiry_state = 'expired' THEN 1 ELSE 0 END)::INT AS expired_count,
                    SUM(CASE WHEN d.lifecycle_status = 'retention_overdue' THEN 1 ELSE 0 END)::INT AS retention_overdue_count
                FROM c18_dms_document d
                GROUP BY d.effective_department_id, d.doc_type_id
            )
        """)
