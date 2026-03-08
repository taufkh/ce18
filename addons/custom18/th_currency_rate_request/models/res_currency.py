import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def action_open_currency_rate_update_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Currency Rate'),
            'res_model': 'currency.rate.update.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_currency_id': self.id,
                'default_company_id': self.env.company.id,
                'default_request_date': fields.Date.context_today(self),
            },
        }

    def _fetch_rate_from_api(self, company_currency, request_date):
        self.ensure_one()

        if self == company_currency:
            return 1.0

        api_url = (
            'https://api.frankfurter.app/'
            f'{request_date}?from={company_currency.name}&to={self.name}'
        )
        request = Request(
            api_url,
            headers={
                'User-Agent': 'odoo-th-currency-rate-request/1.0',
                'Accept': 'application/json',
            },
        )

        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            _logger.exception('Currency rate request failed: %s', exc)
            raise UserError(
                _('Unable to fetch exchange rate from provider. Please try again later.')
            ) from exc

        rate = payload.get('rates', {}).get(self.name)
        if not rate:
            raise UserError(
                _(
                    'No exchange rate found for %(target)s on %(date)s.',
                    target=self.name,
                    date=request_date,
                )
            )
        return float(rate)
