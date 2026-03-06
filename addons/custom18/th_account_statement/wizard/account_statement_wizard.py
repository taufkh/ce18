import base64
import io
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
    period_filter = fields.Selection(
        selection=lambda self: self.env['account.statement.engine'].PERIOD_FILTER_SELECTION,
        string='Period Filter',
        default='custom',
    )
    payment_status_filter = fields.Selection(
        selection=lambda self: self.env['account.statement.engine'].PAYMENT_STATUS_SELECTION,
        string='Payment Status',
        default='all',
    )

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
        return self.env['account.statement.engine']._get_move_types(self.statement_type)

    def _resolve_period_range(self):
        return self.env['account.statement.engine']._get_period_date_range(
            self.period_filter, self.date_from, self.date_to
        )

    def _get_invoices(self, partner):
        date_from, date_to = self._resolve_period_range()
        return self.env['account.statement.engine'].get_invoices(
            partner=partner,
            statement_type=self.statement_type,
            date_from=date_from,
            date_to=date_to,
            include_paid=self.include_paid,
            payment_status_filter=self.payment_status_filter,
        )

    def _get_ageing_data(self, partner):
        return self.env['account.statement.engine'].get_ageing_data(
            partner=partner,
            statement_type=self.statement_type,
        )

    def get_all_report_data(self):
        """Called from the QWeb report template to get structured data per partner."""
        result = []
        currency = self.env.company.currency_id
        date_from, date_to = self._resolve_period_range()

        for partner in self.partner_ids:
            invoices = self._get_invoices(partner)
            ageing = self._get_ageing_data(partner)
            opening_balance = self.env['account.statement.engine'].get_opening_balance(
                partner=partner,
                statement_type=self.statement_type,
                date_from=date_from,
            )

            invoice_lines = []
            for inv in invoices:
                amount = self.env['account.statement.engine']._normalize_amount(
                    self.statement_type, inv.move_type, inv.amount_total
                )
                residual = self.env['account.statement.engine']._normalize_amount(
                    self.statement_type, inv.move_type, inv.amount_residual
                )
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
                    'is_refund': inv.move_type in ('out_refund', 'in_refund'),
                })

            total_amount = sum(l['amount'] for l in invoice_lines)
            total_paid = sum(l['paid'] for l in invoice_lines)
            total_due = sum(l['amount_due'] for l in invoice_lines)

            result.append({
                'partner': partner,
                'invoices': invoice_lines,
                'ageing': ageing,
                'opening_balance': opening_balance,
                'total_amount': total_amount,
                'total_paid': total_paid,
                'total_due': total_due,
                'date_from': date_from,
                'date_to': date_to,
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

    def action_export_xlsx(self):
        self.ensure_one()
        if not self.partner_ids:
            raise UserError("Please select at least one partner.")

        content, filename = self._build_xlsx_binary()
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(content),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

    def _build_xlsx_binary(self, filename_prefix="Account_Statement"):
        try:
            import xlsxwriter
        except ImportError as exc:
            raise UserError("XLS export dependency is missing: xlsxwriter") from exc

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        title_fmt = workbook.add_format({"bold": True, "font_size": 16, "align": "center"})
        header_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#D9D9D9", "border": 1, "align": "center"}
        )
        cell_fmt = workbook.add_format({"border": 1})
        date_fmt = workbook.add_format({"border": 1, "num_format": "yyyy-mm-dd"})
        amount_fmt = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        total_label_fmt = workbook.add_format(
            {"bold": True, "border": 1, "bg_color": "#EFEFEF", "align": "right"}
        )
        total_amount_fmt = workbook.add_format(
            {"bold": True, "border": 1, "bg_color": "#EFEFEF", "num_format": "#,##0.00"}
        )

        all_data = self.get_all_report_data()

        for idx, data in enumerate(all_data, start=1):
            partner = data["partner"]
            sheet_name = f"{partner.name or 'Statement'}"[:31]
            sheet = workbook.add_worksheet(sheet_name)
            row = 0

            sheet.set_column("A:A", 18)
            sheet.set_column("B:B", 18)
            sheet.set_column("C:C", 14)
            sheet.set_column("D:D", 14)
            sheet.set_column("E:G", 16)

            sheet.merge_range(row, 0, row, 6, data["statement_type_label"], title_fmt)
            row += 1
            sheet.merge_range(row, 0, row, 6, partner.name or "-", header_fmt)
            row += 2

            if data["date_from"] and data["date_to"]:
                sheet.write(row, 0, "Date From", header_fmt)
                sheet.write_datetime(row, 1, fields.Datetime.to_datetime(data["date_from"]), date_fmt)
                sheet.write(row, 2, "Date To", header_fmt)
                sheet.write_datetime(row, 3, fields.Datetime.to_datetime(data["date_to"]), date_fmt)
                row += 2

            headers = [
                "Number",
                "Account",
                "Date",
                "Due Date",
                "Total Amount",
                "Paid Amount",
                "Balance",
            ]
            for col, head in enumerate(headers):
                sheet.write(row, col, head, header_fmt)
            row += 1

            sheet.write(row, 0, "Opening Balance", cell_fmt)
            sheet.write(row, 6, data["opening_balance"], amount_fmt)
            row += 1

            for line in data["invoices"]:
                account_name = "Account Receivable"
                sheet.write(row, 0, line["reference"] or "", cell_fmt)
                sheet.write(row, 1, account_name, cell_fmt)
                if line["date"]:
                    sheet.write_datetime(
                        row, 2, fields.Datetime.to_datetime(line["date"]), date_fmt
                    )
                else:
                    sheet.write(row, 2, "", cell_fmt)
                if line["due_date"]:
                    sheet.write_datetime(
                        row, 3, fields.Datetime.to_datetime(line["due_date"]), date_fmt
                    )
                else:
                    sheet.write(row, 3, "", cell_fmt)
                sheet.write_number(row, 4, line["amount"], amount_fmt)
                sheet.write_number(row, 5, line["paid"], amount_fmt)
                sheet.write_number(row, 6, line["amount_due"], amount_fmt)
                row += 1

            sheet.write(row, 3, "TOTAL", total_label_fmt)
            sheet.write_number(row, 4, data["total_amount"], total_amount_fmt)
            sheet.write_number(row, 5, data["total_paid"], total_amount_fmt)
            sheet.write_number(row, 6, data["total_due"], total_amount_fmt)
            row += 2

            sheet.write(row, 0, "Gap Between Days", header_fmt)
            sheet.write(row, 1, "0-30(Days)", header_fmt)
            sheet.write(row, 2, "31-60(Days)", header_fmt)
            sheet.write(row, 3, "61-90(Days)", header_fmt)
            sheet.write(row, 4, "90+(Days)", header_fmt)
            sheet.write(row, 5, "Total", header_fmt)
            row += 1
            sheet.write(row, 0, "Balance Amount", cell_fmt)
            sheet.write_number(row, 1, data["ageing"]["0_30"], amount_fmt)
            sheet.write_number(row, 2, data["ageing"]["31_60"], amount_fmt)
            sheet.write_number(row, 3, data["ageing"]["61_90"], amount_fmt)
            sheet.write_number(row, 4, data["ageing"]["91_plus"], amount_fmt)
            sheet.write_number(row, 5, data["ageing"]["total"], total_amount_fmt)

            if idx < len(all_data):
                # Keep gap-like effect between sheets by setting active row.
                sheet.freeze_panes(1, 0)

        workbook.close()
        output.seek(0)
        filename = f"{filename_prefix}_{fields.Date.today()}.xlsx"
        return output.getvalue(), filename

    def _get_template(self):
        param_key = 'th_account_statement.customer_mail_template_id'
        if self.statement_type in ('customer_overdue', 'vendor_overdue'):
            param_key = 'th_account_statement.overdue_mail_template_id'
        template_id = self.env['ir.config_parameter'].sudo().get_param(param_key)
        if not template_id:
            return self.env['mail.template']
        try:
            template_id = int(template_id)
        except (TypeError, ValueError):
            return self.env['mail.template']
        return self.env['mail.template'].browse(template_id).exists()

    def _render_partner_pdf(self, partner):
        single_wizard = self.copy(
            {
                'partner_ids': [(6, 0, [partner.id])],
            }
        )
        pdf_content, _ = (
            self.env.ref('th_account_statement.action_report_account_statement')
            ._render_qweb_pdf(single_wizard.ids)
        )
        single_wizard.unlink()
        return pdf_content

    def action_send_email(self):
        self.ensure_one()
        if not self.partner_ids:
            raise UserError("Please select at least one partner.")

        sent_count = 0
        failed_list = []
        template = self._get_template()

        for partner in self.partner_ids:
            invoices = self._get_invoices(partner)
            filter_only_unpaid = self.env['ir.config_parameter'].sudo().get_param(
                'th_account_statement.filter_only_unpaid', 'True'
            )
            if filter_only_unpaid == 'True' and not invoices:
                self._create_log(
                    partner,
                    'failed',
                    notes='No open items to send',
                    mail_status='cancel',
                )
                failed_list.append(f"{partner.name} (no open items)")
                continue

            if not partner.email:
                failed_list.append(f"{partner.name} (no email address)")
                self._create_log(
                    partner,
                    'failed',
                    notes='No email address',
                    mail_status='exception',
                )
                continue

            try:
                pdf_content = self._render_partner_pdf(partner)

                # Attach PDF
                attachment = self.env['ir.attachment'].create({
                    'name': f'Account_Statement_{partner.name}.pdf',
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': self._name,
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })

                company = self.env.company
                if template:
                    mail_values = template.generate_email(partner.id)
                    mail_values.update(
                        {
                            'email_to': partner.email,
                            'attachment_ids': [(4, attachment.id)],
                        }
                    )
                else:
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
                mail_status = mail.state or 'outgoing'

                self._create_log(
                    partner,
                    'sent',
                    mail_subject=mail.subject,
                    mail_mail_id=mail.id,
                    mail_status=mail_status,
                )
                sent_count += 1

            except Exception as e:
                failed_list.append(f"{partner.name} ({str(e)})")
                self._create_log(
                    partner,
                    'failed',
                    notes=str(e),
                    mail_status='exception',
                )

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

    def _create_log(
        self,
        partner,
        state,
        notes=None,
        mail_subject=None,
        mail_mail_id=None,
        mail_status=None,
    ):
        date_from, date_to = self._resolve_period_range()
        vals = {
            'partner_id': partner.id,
            'statement_type': self.statement_type,
            'sent_by': self.env.user.id,
            'email_to': partner.email or '',
            'state': state,
            'period_filter': self.period_filter,
            'payment_status_filter': self.payment_status_filter,
            'mail_subject': mail_subject,
            'mail_mail_id': mail_mail_id,
            'mail_status': mail_status,
        }
        if self.statement_type in ('customer', 'vendor'):
            vals.update({'date_from': date_from, 'date_to': date_to})
        if notes:
            vals['notes'] = notes
        self.env['account.statement.log'].create(vals)
