import uuid
from datetime import timedelta
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class C18DmsDocument(models.Model):
    _name = "c18.dms.document"
    _description = "Active DMS Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _sql_constraints = [
        ("c18_dms_document_share_token_unique", "unique(share_token)", "Share token must be unique."),
    ]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    directory_id = fields.Many2one("c18.dms.directory", tracking=True, ondelete="restrict")
    department_id = fields.Many2one("hr.department", tracking=True)
    project_id = fields.Many2one("project.project", tracking=True)
    doc_type_id = fields.Many2one("c18.dms.type", required=True, tracking=True)
    tag_ids = fields.Many2many("c18.dms.tag", string="Tags")
    shared_user_ids = fields.Many2many("res.users", string="Shared Users")
    shared_partner_ids = fields.Many2many("res.partner", string="Shared Contacts")
    attachment_id = fields.Many2one("ir.attachment", required=True, tracking=True)
    share_token = fields.Char(copy=False, default=lambda self: uuid.uuid4().hex, index=True)
    share_url = fields.Char(compute="_compute_share_url")
    allow_external_share = fields.Boolean(tracking=True)
    share_active_until = fields.Date(tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_review", "In Review"),
            ("supervisor_review", "Supervisor Review"),
            ("manager_review", "Manager Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    review_sla_days = fields.Integer(default=3, tracking=True)
    supervisor_reviewer_id = fields.Many2one("res.users", tracking=True)
    manager_reviewer_id = fields.Many2one("res.users", tracking=True)
    submitted_by_id = fields.Many2one("res.users", readonly=True, tracking=True)
    submitted_date = fields.Datetime(readonly=True, tracking=True)
    supervisor_approved_by_id = fields.Many2one("res.users", readonly=True, tracking=True)
    supervisor_approved_date = fields.Datetime(readonly=True, tracking=True)
    manager_approved_by_id = fields.Many2one("res.users", readonly=True, tracking=True)
    manager_approved_date = fields.Datetime(readonly=True, tracking=True)
    rejected_by_id = fields.Many2one("res.users", readonly=True, tracking=True)
    rejected_date = fields.Datetime(readonly=True, tracking=True)
    reject_reason = fields.Text(tracking=True)
    review_deadline = fields.Date(tracking=True)
    last_sla_reminder_date = fields.Date()
    review_overdue = fields.Boolean(compute="_compute_review_overdue", store=True)
    last_review_date = fields.Date(tracking=True)
    next_review_date = fields.Date(tracking=True)
    retention_due_date = fields.Date(tracking=True)
    last_lifecycle_reminder_date = fields.Date()
    lifecycle_status = fields.Selection(
        [
            ("normal", "Normal"),
            ("review_due", "Review Due"),
            ("review_overdue", "Review Overdue"),
            ("retention_due", "Retention Due"),
            ("retention_overdue", "Retention Overdue"),
        ],
        compute="_compute_lifecycle_status",
        store=True,
    )
    expiry_date = fields.Date(tracking=True)
    color = fields.Integer()
    history_ids = fields.One2many("c18.dms.history", "document_id")
    expiry_state = fields.Selection(
        [("normal", "Normal"), ("warning", "Warning"), ("expired", "Expired")],
        compute="_compute_expiry_state",
        store=True,
    )
    effective_department_id = fields.Many2one(
        "hr.department",
        compute="_compute_effective_access",
        store=True,
    )
    effective_user_ids = fields.Many2many(
        "res.users",
        "c18_dms_document_effective_user_rel",
        "document_id",
        "user_id",
        compute="_compute_effective_access",
        store=True,
        string="Effective Users",
    )
    share_scope = fields.Selection(
        [("none", "Private"), ("internal", "Internal"), ("external", "External")],
        compute="_compute_share_scope",
        store=True,
    )
    public_share_status = fields.Selection(
        [("inactive", "Inactive"), ("active", "Active"), ("expiring", "Expiring"), ("expired", "Expired")],
        compute="_compute_public_share_status",
        store=True,
    )
    history_count = fields.Integer(compute="_compute_history_count")
    share_log_ids = fields.One2many("c18.dms.share.log", "document_id", string="Share Access Logs")
    share_log_count = fields.Integer(compute="_compute_share_log_count")

    @api.depends("expiry_date")
    def _compute_expiry_state(self):
        today = fields.Date.today()
        for document in self:
            if not document.expiry_date:
                document.expiry_state = "normal"
            elif document.expiry_date < today:
                document.expiry_state = "expired"
            elif (document.expiry_date - today).days < 30:
                document.expiry_state = "warning"
            else:
                document.expiry_state = "normal"

    @api.depends("share_token")
    def _compute_share_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        for document in self:
            document.share_url = f"{base_url}/c18_dms/share/{document.share_token}" if document.share_token else False

    @api.depends(
        "department_id",
        "directory_id.department_id",
        "directory_id.user_ids",
        "shared_user_ids",
        "shared_partner_ids",
    )
    def _compute_effective_access(self):
        for document in self:
            document.effective_department_id = document.department_id or document.directory_id.department_id
            document.effective_user_ids = document.directory_id.user_ids | document.shared_user_ids

    @api.depends("shared_partner_ids", "effective_user_ids")
    def _compute_share_scope(self):
        for document in self:
            if document.shared_partner_ids:
                document.share_scope = "external"
            elif document.effective_user_ids:
                document.share_scope = "internal"
            else:
                document.share_scope = "none"

    @api.depends("allow_external_share", "share_active_until", "expiry_date", "state")
    def _compute_public_share_status(self):
        today = fields.Date.today()
        for document in self:
            if not document.allow_external_share or document.state != "approved":
                document.public_share_status = "inactive"
                continue
            hard_end = document.share_active_until or document.expiry_date
            if hard_end and hard_end < today:
                document.public_share_status = "expired"
            elif hard_end and (hard_end - today).days <= 7:
                document.public_share_status = "expiring"
            else:
                document.public_share_status = "active"

    def _compute_history_count(self):
        grouped = self.env["c18.dms.history"]._read_group(
            [("document_id", "in", self.ids)],
            ["document_id"],
            ["__count"],
        )
        counts = {document.id: count for document, count in grouped}
        for document in self:
            document.history_count = counts.get(document.id, 0)

    def _compute_share_log_count(self):
        grouped = self.env["c18.dms.share.log"]._read_group(
            [("document_id", "in", self.ids)],
            ["document_id"],
            ["__count"],
        )
        counts = {document.id: count for document, count in grouped}
        for document in self:
            document.share_log_count = counts.get(document.id, 0)

    @api.depends("state", "review_deadline")
    def _compute_review_overdue(self):
        today = fields.Date.today()
        for document in self:
            document.review_overdue = document.state in ("in_review", "supervisor_review", "manager_review") and bool(
                document.review_deadline and document.review_deadline < today
            )

    @api.depends("state", "next_review_date", "retention_due_date")
    def _compute_lifecycle_status(self):
        today = fields.Date.today()
        for document in self:
            if document.state != "approved":
                document.lifecycle_status = "normal"
                continue
            if document.retention_due_date:
                if document.retention_due_date < today:
                    document.lifecycle_status = "retention_overdue"
                    continue
                if (document.retention_due_date - today).days <= 30:
                    document.lifecycle_status = "retention_due"
                    continue
            if document.next_review_date:
                if document.next_review_date < today:
                    document.lifecycle_status = "review_overdue"
                    continue
                if (document.next_review_date - today).days <= 14:
                    document.lifecycle_status = "review_due"
                    continue
            document.lifecycle_status = "normal"

    @api.onchange("directory_id")
    def _onchange_directory_id(self):
        for document in self:
            if document.directory_id:
                if not document.department_id and document.directory_id.department_id:
                    document.department_id = document.directory_id.department_id
                if document.directory_id.tag_ids:
                    document.tag_ids |= document.directory_id.tag_ids
            if not document.supervisor_reviewer_id or not document.manager_reviewer_id:
                supervisor_user, manager_user = document._derive_reviewers(author_user=self.env.user)
                if not document.supervisor_reviewer_id and supervisor_user:
                    document.supervisor_reviewer_id = supervisor_user
                if not document.manager_reviewer_id and manager_user:
                    document.manager_reviewer_id = manager_user

    def _derive_reviewers(self, author_user=None):
        self.ensure_one()
        author_user = author_user or self.env.user
        employee = author_user.employee_ids[:1]
        supervisor_user = employee.parent_id.user_id if employee and employee.parent_id else False
        manager_user = employee.parent_id.parent_id.user_id if employee and employee.parent_id and employee.parent_id.parent_id else False

        if not supervisor_user and self.department_id and self.department_id.manager_id:
            supervisor_user = self.department_id.manager_id.user_id
        if not manager_user and supervisor_user and supervisor_user.employee_ids[:1] and supervisor_user.employee_ids[:1].parent_id:
            manager_user = supervisor_user.employee_ids[:1].parent_id.user_id
        if not manager_user and self.department_id and self.department_id.parent_id and self.department_id.parent_id.manager_id:
            manager_user = self.department_id.parent_id.manager_id.user_id

        if supervisor_user and supervisor_user == author_user:
            supervisor_user = False
        if manager_user and manager_user == author_user:
            manager_user = False
        if manager_user and supervisor_user and manager_user == supervisor_user:
            manager_user = False
        return supervisor_user, manager_user

    def _send_email_template_to_user(self, template_xmlid, user):
        self.ensure_one()
        if not user or not user.partner_id or not user.partner_id.email:
            return False
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            return False
        template.send_mail(
            self.id,
            force_send=False,
            email_values={"email_to": user.partner_id.email},
        )
        return True

    def action_set_in_review(self):
        self.action_submit_for_review()

    def action_set_approved(self):
        self.action_approve_manager()

    def action_reset_to_draft(self):
        self.write({
            "state": "draft",
            "review_deadline": False,
            "last_sla_reminder_date": False,
            "reject_reason": False,
            "rejected_by_id": False,
            "rejected_date": False,
        })

    def action_submit_for_review(self):
        now = fields.Datetime.now()
        for document in self:
            if document.state not in ("draft", "rejected"):
                continue
            if not document.supervisor_reviewer_id or not document.manager_reviewer_id:
                supervisor_user, manager_user = document._derive_reviewers(author_user=self.env.user)
                vals = {}
                if not document.supervisor_reviewer_id and supervisor_user:
                    vals["supervisor_reviewer_id"] = supervisor_user.id
                if not document.manager_reviewer_id and manager_user:
                    vals["manager_reviewer_id"] = manager_user.id
                if vals:
                    document.write(vals)
            deadline = fields.Date.today() + timedelta(days=document.review_sla_days or 3)
            document.write({
                "state": "supervisor_review",
                "submitted_by_id": self.env.user.id,
                "submitted_date": now,
                "review_deadline": deadline,
                "last_sla_reminder_date": False,
                "reject_reason": False,
                "rejected_by_id": False,
                "rejected_date": False,
            })
            if document.supervisor_reviewer_id:
                document.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=document.supervisor_reviewer_id.id,
                    summary="DMS Approval Needed (Supervisor)",
                    note=f"Please review document: {document.name}",
                )
                document._send_email_template_to_user(
                    "c18_dms.mail_template_c18_dms_supervisor_review_request",
                    document.supervisor_reviewer_id,
                )

    def action_approve_supervisor(self):
        now = fields.Datetime.now()
        for document in self:
            if document.state not in ("in_review", "supervisor_review"):
                continue
            if document.supervisor_reviewer_id and self.env.user != document.supervisor_reviewer_id and not self.env.user.has_group("c18_dms.group_c18_dms_manager"):
                raise UserError("Only assigned supervisor reviewer or DMS manager can approve this stage.")
            document.write({
                "state": "manager_review",
                "supervisor_approved_by_id": self.env.user.id,
                "supervisor_approved_date": now,
                "review_deadline": fields.Date.today() + timedelta(days=document.review_sla_days or 3),
                "last_sla_reminder_date": False,
            })
            if document.manager_reviewer_id:
                document.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=document.manager_reviewer_id.id,
                    summary="DMS Approval Needed (Manager)",
                    note=f"Final approval needed for document: {document.name}",
                )
                document._send_email_template_to_user(
                    "c18_dms.mail_template_c18_dms_manager_review_request",
                    document.manager_reviewer_id,
                )

    def action_approve_manager(self):
        now = fields.Datetime.now()
        for document in self:
            if document.state not in ("manager_review", "in_review", "supervisor_review"):
                continue
            if document.manager_reviewer_id and self.env.user != document.manager_reviewer_id and not self.env.user.has_group("c18_dms.group_c18_dms_executive"):
                raise UserError("Only assigned manager reviewer or DMS executive can approve final stage.")
            vals = {
                "state": "approved",
                "manager_approved_by_id": self.env.user.id,
                "manager_approved_date": now,
                "review_deadline": False,
                "last_sla_reminder_date": False,
            }
            if not document.last_review_date:
                vals["last_review_date"] = fields.Date.today()
            document.write(vals)
            document._set_lifecycle_dates()

    def action_reject_review(self):
        now = fields.Datetime.now()
        for document in self:
            if document.state not in ("in_review", "supervisor_review", "manager_review"):
                continue
            document.write({
                "state": "rejected",
                "rejected_by_id": self.env.user.id,
                "rejected_date": now,
                "last_sla_reminder_date": False,
            })
            if document.submitted_by_id:
                document._send_email_template_to_user(
                    "c18_dms.mail_template_c18_dms_rejected_notice",
                    document.submitted_by_id,
                )

    def action_send_by_mail(self):
        self.ensure_one()
        ctx = {
            "default_model": self._name,
            "default_res_id": self.id,
            "default_composition_mode": "comment",
            "default_partner_ids": self.shared_partner_ids.ids,
            "default_subject": _("%s is shared with you") % self.name,
            "default_body": _(
                "<p>%s has been shared with you. Please review the attached document.</p>"
            )
            % self.name,
            "default_attachment_ids": [self.attachment_id.id],
        }
        return {
            "type": "ir.actions.act_window",
            "name": _("Send Document by Mail"),
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    def action_regenerate_share_link(self):
        for document in self:
            document.share_token = uuid.uuid4().hex

    def action_revoke_external_share(self):
        self.write({
            "allow_external_share": False,
            "share_active_until": False,
        })

    def action_set_share_expiry_7d(self):
        self.write({"share_active_until": fields.Date.today() + timedelta(days=7)})

    def action_set_share_expiry_30d(self):
        self.write({"share_active_until": fields.Date.today() + timedelta(days=30)})

    def action_open_share_link(self):
        self.ensure_one()
        if not self.allow_external_share:
            self.allow_external_share = True
        if not self.share_token:
            self.share_token = uuid.uuid4().hex
        return {
            "type": "ir.actions.act_url",
            "url": self.share_url,
            "target": "new",
        }

    def _can_access_public_share(self):
        self.ensure_one()
        today = fields.Date.today()
        if not self.allow_external_share:
            return False
        if self.state != "approved":
            return False
        if self.expiry_date and self.expiry_date < today:
            return False
        if self.share_active_until and self.share_active_until < today:
            return False
        return True

    @api.model
    def cron_auto_revoke_expired_shares(self):
        today = fields.Date.today()
        documents = self.search([
            ("allow_external_share", "=", True),
            ("share_active_until", "!=", False),
            ("share_active_until", "<", today),
        ])
        if not documents:
            return 0
        documents.write({"allow_external_share": False})
        for document in documents:
            document.message_post(body="External share was automatically revoked because Share Active Until has passed.")
        _logger.info("C18 DMS auto-revoked external share for %s documents.", len(documents))
        return len(documents)

    @api.model
    def cron_review_sla_reminder(self):
        today = fields.Date.today()
        overdue_documents = self.search([
            ("state", "in", ["in_review", "supervisor_review", "manager_review"]),
            ("review_deadline", "!=", False),
            ("review_deadline", "<", today),
            "|",
            ("last_sla_reminder_date", "=", False),
            ("last_sla_reminder_date", "<", today),
        ])
        for document in overdue_documents:
            reviewer = document.manager_reviewer_id if document.state == "manager_review" else document.supervisor_reviewer_id
            days_overdue = (today - document.review_deadline).days
            message = (
                f"SLA reminder: document '{document.name}' is overdue by {days_overdue} day(s) "
                f"at state '{document.state}'."
            )
            document.message_post(body=message)
            if reviewer:
                document.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=reviewer.id,
                    summary="DMS SLA Overdue",
                    note=message,
                )
                document._send_email_template_to_user(
                    "c18_dms.mail_template_c18_dms_sla_overdue",
                    reviewer,
                )
            document.last_sla_reminder_date = today
        if overdue_documents:
            _logger.info("C18 DMS SLA reminders sent for %s documents.", len(overdue_documents))
        return len(overdue_documents)

    @api.model
    def cron_review_retention_lifecycle(self):
        today = fields.Date.today()
        reviewed = self.search([
            ("state", "=", "approved"),
            ("next_review_date", "!=", False),
            ("next_review_date", "<=", today),
            "|",
            ("last_lifecycle_reminder_date", "=", False),
            ("last_lifecycle_reminder_date", "<", today),
        ])
        for document in reviewed:
            note = f"Periodic review due for '{document.name}' (due date: {document.next_review_date})."
            document.message_post(body=note)
            reviewer = document.supervisor_reviewer_id or document.manager_reviewer_id
            if reviewer:
                document.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=reviewer.id,
                    summary="DMS Periodic Review Due",
                    note=note,
                )
                document._send_email_template_to_user(
                    "c18_dms.mail_template_c18_dms_lifecycle_review_due",
                    reviewer,
                )
            document.last_lifecycle_reminder_date = today

        retention_due = self.search([
            ("state", "=", "approved"),
            ("retention_due_date", "!=", False),
            ("retention_due_date", "<", today),
            ("doc_type_id.auto_archive_on_retention", "=", True),
            ("active", "=", True),
        ])
        for document in retention_due:
            document.write({"active": False})
            document.message_post(body="Document automatically archived due to retention policy.")

        if reviewed or retention_due:
            _logger.info(
                "C18 DMS lifecycle run: review reminders=%s, auto-archived=%s.",
                len(reviewed),
                len(retention_due),
            )
        return len(reviewed) + len(retention_due)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("share_token", uuid.uuid4().hex)
            self._apply_directory_defaults(vals)
            if not vals.get("review_sla_days"):
                doc_type = self.env["c18.dms.type"].browse(vals.get("doc_type_id"))
                vals["review_sla_days"] = doc_type.default_review_sla_days or 3
        documents = super().create(vals_list)
        for document, vals in zip(documents, vals_list):
            updates = {}
            if not vals.get("supervisor_reviewer_id") or not vals.get("manager_reviewer_id"):
                supervisor_user, manager_user = document._derive_reviewers(author_user=document.create_uid)
                if not vals.get("supervisor_reviewer_id") and supervisor_user:
                    updates["supervisor_reviewer_id"] = supervisor_user.id
                if not vals.get("manager_reviewer_id") and manager_user:
                    updates["manager_reviewer_id"] = manager_user.id
            if updates:
                document.write(updates)
        documents._sync_followers()
        documents.filtered(lambda d: d.state == "approved")._set_lifecycle_dates()
        for document, vals in zip(documents, vals_list):
            attachment_id = vals.get("attachment_id")
            if attachment_id:
                document.message_post(body="Initial document uploaded.")
        return documents

    def write(self, vals):
        self._apply_directory_defaults(vals)
        track_attachment_change = "attachment_id" in vals
        previous_attachments = {}
        if track_attachment_change:
            for document in self:
                if document.attachment_id and document.attachment_id.id != vals.get("attachment_id"):
                    previous_attachments[document.id] = document.attachment_id.id

        result = super().write(vals)
        self._sync_followers()
        if "doc_type_id" in vals:
            self.filtered(lambda d: d.state == "approved")._set_lifecycle_dates()

        if track_attachment_change:
            for document in self:
                previous_attachment_id = previous_attachments.get(document.id)
                if previous_attachment_id:
                    self.env["c18.dms.history"].create({
                        "name": f"{document.name} - Previous Version",
                        "document_id": document.id,
                        "attachment_id": previous_attachment_id,
                        "version_note": "Auto-created from attachment replacement.",
                    })
                    document.message_post(body="A new version was uploaded. Previous version moved to history.")
        return result

    def _set_lifecycle_dates(self):
        today = fields.Date.today()
        for document in self:
            review_days = document.doc_type_id.review_interval_days or 0
            retention_days = document.doc_type_id.retention_days or 0
            document.write({
                "last_review_date": document.last_review_date or today,
                "next_review_date": today + timedelta(days=review_days) if review_days else False,
                "retention_due_date": today + timedelta(days=retention_days) if retention_days else False,
            })

    def _apply_directory_defaults(self, vals):
        directory_id = vals.get("directory_id")
        if directory_id:
            directory = self.env["c18.dms.directory"].browse(directory_id)
            if directory.exists():
                if not vals.get("department_id"):
                    vals["department_id"] = directory.department_id.id
                if directory.tag_ids and "tag_ids" not in vals:
                    vals["tag_ids"] = [(6, 0, directory.tag_ids.ids)]

    def _sync_followers(self):
        for document in self:
            partner_ids = (document.shared_partner_ids | document.effective_user_ids.partner_id).ids
            if partner_ids:
                document.message_subscribe(partner_ids=partner_ids)
