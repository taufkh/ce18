import uuid

from odoo import _, api, fields, models


class C18DmsShareTokenWizard(models.TransientModel):
    _name = "c18.dms.share.token.wizard"
    _description = "Regenerate DMS Share Tokens"

    mode = fields.Selection(
        [("selected", "Selected Documents"), ("duplicates", "Duplicate Tokens"), ("all", "All Documents")],
        default="duplicates",
        required=True,
    )
    document_ids = fields.Many2many("c18.dms.document", string="Documents")
    document_count = fields.Integer(compute="_compute_document_count")

    @api.depends("mode", "document_ids")
    def _compute_document_count(self):
        for wizard in self:
            wizard.document_count = len(wizard._get_target_documents())

    def _get_target_documents(self):
        self.ensure_one()
        Document = self.env["c18.dms.document"]
        if self.mode == "selected":
            return self.document_ids
        if self.mode == "all":
            return Document.search([])
        self.env.cr.execute("""
            SELECT id
            FROM c18_dms_document
            WHERE share_token IN (
                SELECT share_token
                FROM c18_dms_document
                WHERE share_token IS NOT NULL
                GROUP BY share_token
                HAVING COUNT(*) > 1
            )
        """)
        ids = [row[0] for row in self.env.cr.fetchall()]
        return Document.browse(ids)

    def action_regenerate_tokens(self):
        self.ensure_one()
        documents = self._get_target_documents()
        for document in documents:
            document.write({"share_token": uuid.uuid4().hex})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Share Tokens Updated"),
                "message": _("%s documents received new share tokens.") % len(documents),
                "type": "success",
                "sticky": False,
            },
        }
