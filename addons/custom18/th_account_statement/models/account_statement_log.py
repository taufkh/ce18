from odoo import models, fields, api


class AccountStatementLog(models.Model):
    _name = 'account.statement.log'
    _description = 'Account Statement Log'
    _order = 'sent_date desc'

    STATEMENT_TYPE_SELECTION = [
        ('customer', 'Customer Statement'),
        ('customer_overdue', 'Customer Overdue Statement'),
        ('vendor', 'Vendor Statement'),
        ('vendor_overdue', 'Vendor Overdue Statement'),
    ]

    name = fields.Char('Reference', compute='_compute_name', store=True)
    partner_id = fields.Many2one(
        'res.partner', string='Partner', required=True, ondelete='cascade', index=True
    )
    statement_type = fields.Selection(
        STATEMENT_TYPE_SELECTION, string='Statement Type', required=True, index=True
    )
    date_from = fields.Date('Date From', index=True)
    date_to = fields.Date('Date To', index=True)
    period_filter = fields.Selection(
        selection=lambda self: self.env['account.statement.engine'].PERIOD_FILTER_SELECTION,
        string='Period Filter',
        index=True,
    )
    payment_status_filter = fields.Selection(
        selection=lambda self: self.env['account.statement.engine'].PAYMENT_STATUS_SELECTION,
        string='Payment Status',
        index=True,
    )
    sent_date = fields.Datetime(
        'Sent Date', default=fields.Datetime.now, required=True, index=True
    )
    sent_by = fields.Many2one(
        'res.users', string='Sent By', default=lambda self: self.env.user, index=True
    )
    email_to = fields.Char('Sent To (Email)')
    mail_subject = fields.Char('Mail Subject')
    mail_mail_id = fields.Many2one('mail.mail', string='Mail Reference')
    mail_status = fields.Selection(
        [
            ('outgoing', 'Outgoing'),
            ('sent', 'Sent'),
            ('received', 'Received'),
            ('exception', 'Delivery Failed'),
            ('cancel', 'Cancelled'),
        ],
        string='Mail Sent Status',
        index=True,
    )
    state = fields.Selection(
        [('sent', 'Sent'), ('failed', 'Failed')],
        string='Status',
        default='sent',
        required=True,
        index=True,
    )
    notes = fields.Text('Notes')

    @api.depends('partner_id', 'statement_type', 'sent_date')
    def _compute_name(self):
        for rec in self:
            type_label = dict(self.STATEMENT_TYPE_SELECTION).get(rec.statement_type, '')
            partner_name = rec.partner_id.name or ''
            date_str = str(rec.sent_date.date()) if rec.sent_date else ''
            rec.name = f"{partner_name} - {type_label} - {date_str}"
