from odoo import fields, models


class C18DmsHistory(models.Model):
    _name = "c18.dms.history"
    _description = "Document Version History"
    _order = "version_date desc, id desc"

    name = fields.Char(required=True)
    document_id = fields.Many2one("c18.dms.document", required=True, ondelete="cascade")
    attachment_id = fields.Many2one("ir.attachment", required=True)
    version_date = fields.Datetime(default=fields.Datetime.now, required=True)
    version_note = fields.Text()
    directory_id = fields.Many2one(related="document_id.directory_id", store=True, readonly=True)
    effective_department_id = fields.Many2one(
        related="document_id.effective_department_id",
        store=True,
        readonly=True,
    )

    def action_preview_attachment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.attachment_id.id}?download=false",
            "target": "new",
        }

    def action_download_attachment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.attachment_id.id}?download=true",
            "target": "self",
        }
