from odoo import fields, models


class C18DmsTag(models.Model):
    _name = "c18.dms.tag"
    _description = "Document Tag"
    _order = "name"

    name = fields.Char(required=True)
    color = fields.Integer()
    active = fields.Boolean(default=True)
