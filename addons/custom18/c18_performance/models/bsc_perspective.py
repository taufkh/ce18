from odoo import fields, models


class C18BscPerspective(models.Model):
    _name = "c18.bsc.perspective"
    _description = "Balanced Scorecard Perspective"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
