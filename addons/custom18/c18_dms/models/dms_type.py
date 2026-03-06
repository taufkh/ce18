from odoo import fields, models


class C18DmsType(models.Model):
    _name = "c18.dms.type"
    _description = "Document Type"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    default_review_sla_days = fields.Integer(default=3)
    review_interval_days = fields.Integer(default=180)
    retention_days = fields.Integer(default=1095)
    auto_archive_on_retention = fields.Boolean(default=False)
