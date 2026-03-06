from odoo import _, fields, models


class C18DmsMultiUploadWizard(models.TransientModel):
    _name = "c18.dms.multi.upload.wizard"
    _description = "Upload Multiple DMS Documents"

    directory_id = fields.Many2one("c18.dms.directory", ondelete="restrict")
    department_id = fields.Many2one("hr.department")
    project_id = fields.Many2one("project.project")
    doc_type_id = fields.Many2one("c18.dms.type", required=True)
    tag_ids = fields.Many2many("c18.dms.tag", string="Tags")
    state = fields.Selection(
        [("draft", "Draft"), ("in_review", "In Review"), ("approved", "Approved")],
        default="draft",
        required=True,
    )
    expiry_date = fields.Date()
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "c18_dms_multi_upload_attachment_rel",
        "wizard_id",
        "attachment_id",
        string="Files",
        required=True,
    )

    def _prepare_document_vals(self, attachment):
        vals = {
            "name": attachment.name,
            "directory_id": self.directory_id.id,
            "project_id": self.project_id.id,
            "doc_type_id": self.doc_type_id.id,
            "attachment_id": attachment.id,
            "state": self.state,
            "expiry_date": self.expiry_date,
        }
        if self.department_id:
            vals["department_id"] = self.department_id.id
        if self.tag_ids:
            vals["tag_ids"] = [(6, 0, self.tag_ids.ids)]
        return vals

    def action_fill_from_directory(self):
        self.ensure_one()
        if self.directory_id:
            if not self.department_id and self.directory_id.department_id:
                self.department_id = self.directory_id.department_id
            if self.directory_id.tag_ids and not self.tag_ids:
                self.tag_ids = self.directory_id.tag_ids

    def action_create_documents(self):
        self.ensure_one()
        documents = self.env["c18.dms.document"]
        for attachment in self.attachment_ids:
            documents |= self.env["c18.dms.document"].create(self._prepare_document_vals(attachment))
        return {
            "type": "ir.actions.act_window",
            "name": _("Documents"),
            "res_model": "c18.dms.document",
            "view_mode": "kanban,list,form",
            "domain": [("id", "in", documents.ids)],
        }
