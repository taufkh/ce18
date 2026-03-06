import base64
from datetime import date

from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountStatementWizard(models.TransientModel):
    _name = 'account.statement.wizard'
    _description = 'Account Statement Wizard'

    STATEMENT_TYPE_SELECTION = [
        ('customer', 'Customer Statement'),
        ('customer_overdue', 'Customer Overdue Statement'),
        ('vendor', 'Vendor Statement'),
        ('vendor_overdue', 'Vendor Overdue Statement'),
    ]

    statement_type = fields.Selection(
        STATEMENT_TYPE_SELECTION,
        string='Statement Type',
        required=True,
        default='customer',
    )
    partner_ids = fields.Many2many(
        'res.partner',
        'th_account_statement_wizard_partner_rel',
        'wizard_id',
        'partner_id',
        string='Partners',
    )
    date_from = fields.Date(
        'Date From',
        required=True,
        default=lambda self: date.today().replace(day=1),
    )
    date_to = fields.Date(
        'Date To',
        required=True,
        default=fields.Date.today,
    )
    include_paid = fields.Boolean('Include Paid Invoices', default=False)

    # -------------------------------------------------------------------------
    # Onchange
    # -------------------------------------------------------------------------

    @api.onchange('statement_type')
    def _onchange_statement_type(self):
        self.partner_ids = False

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_move_types(self):
        if self.statement_type in ('customer', 'customer_overdue'):
            return ['out_invoice', 'out_refund']
        return ['in_invoice', 'in_refund']

    def _get_invoices(self, partner):
        move_types = self._get_move_types()
        today = date.today()

        domain = [
            ('partner_id', 'child_of', partner.id),
            ('move_type', 'in', move_types),
            ('state', '=', 'posted'),
        ]

        if self.statement_type in ('customer', 'vendor'):
            domain += [
                ('invoice_date', '>=', self.date_from),
                ('invoice_date', '<=', self.date_to),
            ]
            if not self.include_paid:
                domain += [('payment_state', 'not in', ['paid'])]
        else:
            # Overdue: unpaid/partial past due date
            domain += [
                ('payment_state', 'not in', ['paid', 'in_payment']),
                ('invoice_date_due', '<', today),
            ]

        return self.env['account.move'].search(domain, order='invoice_date asc, id asc')

    def _get_ageing_data(self, partner):
        move_types = self._get_move_types()
        today = date.today()

        outstanding = self.env['account.move'].search([
            ('partner_id', 'child_of', partner.id),
            ('move_type', 'in', move_types),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'in_payment']),
            ('invoice_date_due', '!=', False),
        ])

        result = {
            'not_due': 0.0,
            '0_30': 0.0,
            '31_60': 0.0,
            '61_90': 0.0,
            '91_plus': 0.0,
            'total': 0.0,
        }

        for inv in outstanding:
            amount = inv.amount_residual
            days = (today - inv.invoice_date_due).days

            if days < 0:
                result['not_due'] += amount
            elif days <= 30:
                result['0_30'] += amount
            elif days <= 60:
                result['31_60'] += amount
            elif days <= 90:
                result['61_90'] += amount
            else:
                result['91_plus'] += amount

            result['total'] += amount

        return result

    def get_all_report_data(self):
        """Called from the QWeb report template to get structured data per partner."""
        result = []
        currency = self.env.company.currency_id

        for partner in self.partner_ids:
            invoices = self._get_invoices(partner)
            ageing = self._get_ageing_data(partner)

            invoice_lines = []
            for inv in invoices:
                is_refund = inv.move_type in ('out_refund', 'in_refund')
                amount = -inv.amount_total if is_refund else inv.amount_total
                residual = -inv.amount_residual if is_refund else inv.amount_residual
                paid_amount = amount - residual

                inv_currency = inv.currency_id or currency

                invoice_lines.append({
                    'date': inv.invoice_date,
                    'due_date': inv.invoice_date_due,
                    'reference': inv.name or '',
                    'ref': inv.ref or '',
                    'amount': amount,
                    'paid': paid_amount,
                    'amount_due': residual,
                    'payment_state': inv.payment_state,
                    'currency': inv_currency,
                    'is_refund': is_refund,
                })

            total_amount = sum(l['amount'] for l in invoice_lines)
            total_paid = sum(l['paid'] for l in invoice_lines)
            total_due = sum(l['amount_due'] for l in invoice_lines)

            result.append({
                'partner': partner,
                'invoices': invoice_lines,
                'ageing': ageing,
                'total_amount': total_amount,
                'total_paid': total_paid,
                'total_due': total_due,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'statement_type': self.statement_type,
                'statement_type_label': dict(self.STATEMENT_TYPE_SELECTION).get(
                    self.statement_type, ''
                ),
                'currency': currency,
            })

        return result

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_print_pdf(self):
        self.ensure_one()
        if not self.partner_ids:
            raise UserError("Please select at least one partner.")
        return (
            self.env.ref('th_account_statement.action_report_account_statement')
            .report_action(self)
        )

    def action_send_email(self):
        self.ensure_one()
        if not self.partner_ids:
            raise UserError("Please select at least one partner.")

        sent_count = 0
        failed_list = []

        for partner in self.partner_ids:
            invoices = self._get_invoices(partner)

            if not partner.email:
                failed_list.append(f"{partner.name} (no email address)")
                self._create_log(partner, 'failed', notes='No email address')
                continue

            try:
                # Render PDF for all partners in wizard
                pdf_content, _ = (
                    self.env.ref('th_account_statement.action_report_account_statement')
                    ._render_qweb_pdf(self.ids)
                )

                # Attach PDF
                attachment = self.env['ir.attachment'].create({
                    'name': f'Account_Statement_{partner.name}.pdf',
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': self._name,
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })

                # Build and send email
                company = self.env.company
                mail_values = {
                    'subject': f'Account Statement - {partner.name}',
                    'body_html': (
                        f'<p>Dear {partner.name},</p>'
                        f'<p>Please find attached your account statement from <strong>{company.name}</strong>.</p>'
                        f'<p>Should you have any questions, please do not hesitate to contact us.</p>'
                        f'<p>Best regards,<br/>{company.name}</p>'
                    ),
                    'email_to': partner.email,
                    'email_from': company.email or self.env.user.email or '',
                    'attachment_ids': [(4, attachment.id)],
                }
                mail = self.env['mail.mail'].create(mail_values)
                mail.send()

                self._create_log(partner, 'sent')
                sent_count += 1

            except Exception as e:
                failed_list.append(f"{partner.name} ({str(e)})")
                self._create_log(partner, 'failed', notes=str(e))

        message = f"Successfully sent {sent_count} statement(s)."
        if failed_list:
            message += "\n\nFailed:\n" + "\n".join(f"- {f}" for f in failed_list)

        notif_type = 'success' if sent_count > 0 else 'warning'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Account Statement',
                'message': message,
                'type': notif_type,
                'sticky': True,
            },
        }

    def _create_log(self, partner, state, notes=None):
        vals = {
            'partner_id': partner.id,
            'statement_type': self.statement_type,
            'sent_by': self.env.user.id,
            'email_to': partner.email or '',
            'state': state,
        }
        if self.statement_type in ('customer', 'vendor'):
            vals.update({'date_from': self.date_from, 'date_to': self.date_to})
        if notes:
            vals['notes'] = notes
        self.env['account.statement.log'].create(vals)
