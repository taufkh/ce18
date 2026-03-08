from odoo import _, fields, models
from odoo.exceptions import UserError


class CurrencyRateUpdateWizard(models.TransientModel):
    _name = 'currency.rate.update.wizard'
    _description = 'Currency Rate Update Wizard'

    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True)
    request_date = fields.Date(string='Request Date', required=True, default=fields.Date.context_today)

    def action_update_currency_rate(self):
        self.ensure_one()

        if not self.request_date:
            raise UserError(_('Request date is required.'))

        company_currency = self.company_id.currency_id
        target_currency = self.currency_id
        quote_rate = target_currency._fetch_rate_from_api(
            company_currency=company_currency,
            request_date=self.request_date,
        )

        company_rate = 1.0 / quote_rate if quote_rate else 0.0

        rate_model = self.env['res.currency.rate'].sudo()
        existing_rate = rate_model.search(
            [
                ('currency_id', '=', target_currency.id),
                ('company_id', '=', self.company_id.id),
                ('name', '=', self.request_date),
            ],
            limit=1,
        )

        values = {
            'name': self.request_date,
            'currency_id': target_currency.id,
            'company_id': self.company_id.id,
            'inverse_company_rate': quote_rate,
            'company_rate': company_rate,
        }

        if existing_rate:
            existing_rate.write(values)
        else:
            rate_model.create(values)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(
                    'Rate for %(currency)s has been updated for %(date)s.',
                    currency=target_currency.name,
                    date=self.request_date,
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
