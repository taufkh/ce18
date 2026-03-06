from odoo import api, fields, models
from odoo.exceptions import ValidationError


class C18DmsDirectory(models.Model):
    _name = "c18.dms.directory"
    _description = "DMS Directory"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _parent_name = "parent_id"
    _parent_store = True
    _order = "complete_name"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one("c18.dms.directory", string="Parent Directory", ondelete="restrict")
    child_ids = fields.One2many("c18.dms.directory", "parent_id", string="Child Directories")
    parent_path = fields.Char(index=True)
    complete_name = fields.Char(compute="_compute_complete_name", store=True, recursive=True)
    department_id = fields.Many2one("hr.department", tracking=True)
    user_ids = fields.Many2many("res.users", string="Shared Users")
    tag_ids = fields.Many2many("c18.dms.tag", string="Tags")
    description = fields.Text()
    document_ids = fields.One2many("c18.dms.document", "directory_id", string="Documents")
    document_count = fields.Integer(compute="_compute_document_count")

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for directory in self:
            if directory.parent_id:
                directory.complete_name = f"{directory.parent_id.complete_name} / {directory.name}"
            else:
                directory.complete_name = directory.name

    def _compute_document_count(self):
        grouped = self.env["c18.dms.document"]._read_group(
            [("directory_id", "in", self.ids)],
            ["directory_id"],
            ["__count"],
        )
        counts = {directory.id: count for directory, count in grouped}
        for directory in self:
            directory.document_count = counts.get(directory.id, 0)

    @api.constrains("parent_id")
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError("Directories cannot be recursive.")
