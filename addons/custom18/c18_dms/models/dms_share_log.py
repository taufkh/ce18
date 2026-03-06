from odoo import fields, models


class C18DmsShareLog(models.Model):
    _name = "c18.dms.share.log"
    _description = "DMS Share Access Log"
    _order = "accessed_at desc, id desc"

    document_id = fields.Many2one("c18.dms.document", required=True, ondelete="cascade")
    access_type = fields.Selection(
        [("page", "Page View"), ("download", "Download")],
        required=True,
    )
    accessed_at = fields.Datetime(default=fields.Datetime.now, required=True)
    access_ip = fields.Char()
    user_agent = fields.Char()
    access_name = fields.Char()
