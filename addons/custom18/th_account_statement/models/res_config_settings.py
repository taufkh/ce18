from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    show_statement_portal_menu = fields.Boolean(
        string="Show Customer Statement Menu in Portal",
        config_parameter="th_account_statement.show_statement_portal_menu",
        default=False,
    )
    enable_customer_mail_log = fields.Boolean(
        string="Customer Statement Mail Log History",
        config_parameter="th_account_statement.enable_customer_mail_log",
        default=True,
    )
    enable_overdue_mail_log = fields.Boolean(
        string="Customer Overdue Statement Mail Log History",
        config_parameter="th_account_statement.enable_overdue_mail_log",
        default=True,
    )
    enable_customer_auto_send = fields.Boolean(
        string="Customer Statement Auto Send",
        config_parameter="th_account_statement.enable_customer_auto_send",
        default=False,
    )
    enable_overdue_auto_send = fields.Boolean(
        string="Customer Overdue Statement Auto Send",
        config_parameter="th_account_statement.enable_overdue_auto_send",
        default=False,
    )
    filter_only_unpaid = fields.Boolean(
        string="Filter Only Unpaid",
        help="When enabled, skip sending statements if all invoices are paid.",
        config_parameter="th_account_statement.filter_only_unpaid",
        default=True,
    )
    customer_auto_send_frequency = fields.Selection(
        selection=[
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
        ],
        string="Customer Statement Auto Send Frequency",
        config_parameter="th_account_statement.customer_auto_send_frequency",
        default="daily",
    )
    overdue_auto_send_frequency = fields.Selection(
        selection=[
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
        ],
        string="Customer Overdue Statement Auto Send Frequency",
        config_parameter="th_account_statement.overdue_auto_send_frequency",
        default="daily",
    )
    customer_mail_template_id = fields.Many2one(
        "mail.template",
        string="Customer Statement Mail Template",
        config_parameter="th_account_statement.customer_mail_template_id",
        domain="[('model', '=', 'res.partner')]",
    )
    overdue_mail_template_id = fields.Many2one(
        "mail.template",
        string="Customer Overdue Statement Mail Template",
        config_parameter="th_account_statement.overdue_mail_template_id",
        domain="[('model', '=', 'res.partner')]",
    )
