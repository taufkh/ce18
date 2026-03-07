from datetime import datetime

from odoo import fields, http
from odoo.http import request


class PortalStatementController(http.Controller):
    def _portal_enabled(self):
        value = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("th_account_statement.show_statement_portal_menu", "False")
        )
        return value == "True"

    def _get_portal_partner(self):
        return request.env.user.partner_id.commercial_partner_id

    def _to_date(self, value):
        if not value:
            return None
        try:
            return fields.Date.to_date(value)
        except Exception:
            return datetime.strptime(value, "%Y-%m-%d").date()

    def _build_wizard(
        self, partner, statement_type, period_filter="custom", date_from=None, date_to=None
    ):
        return (
            request.env["account.statement.wizard"]
            .sudo()
            .create(
                {
                    "statement_type": statement_type,
                    "partner_ids": [(6, 0, [partner.id])],
                    "period_filter": period_filter,
                    "date_from": date_from,
                    "date_to": date_to,
                    "include_paid": True,
                    "payment_status_filter": "all",
                }
            )
        )

    def _prepare_portal_data(self, partner, date_from, date_to):
        engine = request.env["account.statement.engine"].sudo()
        filtered_moves = engine.get_invoices(
            partner=partner,
            statement_type="customer",
            date_from=date_from,
            date_to=date_to,
            include_paid=True,
            payment_status_filter="all",
        )
        statement_from, statement_to = engine._get_period_date_range("this_year")
        normal_moves = engine.get_invoices(
            partner=partner,
            statement_type="customer",
            date_from=statement_from,
            date_to=statement_to,
            include_paid=True,
            payment_status_filter="all",
        )
        overdue_moves = engine.get_invoices(
            partner=partner,
            statement_type="customer_overdue",
            include_paid=True,
            payment_status_filter="all",
        )

        def _totals(moves):
            total_amount = sum(
                engine._normalize_amount("customer", move.move_type, move.amount_total)
                for move in moves
            )
            total_balance = sum(
                engine._normalize_amount("customer", move.move_type, move.amount_residual)
                for move in moves
            )
            total_paid = total_amount - total_balance
            return {
                "amount": total_amount,
                "paid": total_paid,
                "balance": total_balance,
            }

        return {
            "filtered_moves": filtered_moves,
            "filtered_totals": _totals(filtered_moves),
            "normal_moves": normal_moves,
            "normal_totals": _totals(normal_moves),
            "overdue_moves": overdue_moves,
            "overdue_totals": _totals(overdue_moves),
            "ageing": engine.get_ageing_data(partner, "customer_overdue"),
            "currency": partner.company_id.currency_id or request.env.company.currency_id,
            "opening_balance": engine.get_opening_balance(
                partner=partner,
                statement_type="customer",
                date_from=date_from,
            ),
        }

    def _get_shared_partner(self, partner_id, token):
        if not token:
            return None
        partner = request.env["res.partner"].sudo().browse(partner_id)
        if not partner.exists():
            return None
        commercial_partner = partner.commercial_partner_id
        if not commercial_partner.statement_share_token:
            return None
        if commercial_partner.statement_share_token != token:
            return None
        return commercial_partner

    @http.route(["/my/customer_statements"], type="http", auth="user", website=True)
    def portal_customer_statements(self, **kwargs):
        if not self._portal_enabled():
            return request.not_found()

        partner = self._get_portal_partner()
        date_from = self._to_date(kwargs.get("date_from"))
        date_to = self._to_date(kwargs.get("date_to"))
        if not date_from or not date_to:
            date_from, date_to = request.env["account.statement.engine"].sudo()._get_period_date_range(
                "this_month"
            )

        values = {
            "page_name": "customer_statements",
            "partner": partner,
            "date_from": date_from,
            "date_to": date_to,
            "message": kwargs.get("message"),
        }
        values.update(self._prepare_portal_data(partner, date_from, date_to))
        return request.render("th_account_statement.portal_customer_statements_page", values)

    @http.route(
        ["/my/customer_statements/download/<string:statement_kind>/<string:file_type>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_download_statement(self, statement_kind, file_type, **kwargs):
        if not self._portal_enabled():
            return request.not_found()

        partner = self._get_portal_partner()
        date_from = self._to_date(kwargs.get("date_from"))
        date_to = self._to_date(kwargs.get("date_to"))
        if not date_from or not date_to:
            date_from, date_to = request.env["account.statement.engine"].sudo()._get_period_date_range(
                "this_month"
            )

        if statement_kind == "filtered":
            wizard = self._build_wizard(
                partner, "customer", period_filter="custom", date_from=date_from, date_to=date_to
            )
            filename_prefix = "Filtered_Statement"
        elif statement_kind == "normal":
            wizard = self._build_wizard(partner, "customer", period_filter="this_year")
            filename_prefix = "Customer_Statement"
        elif statement_kind == "overdue":
            wizard = self._build_wizard(partner, "customer_overdue")
            filename_prefix = "Overdue_Statement"
        else:
            return request.not_found()

        if file_type == "pdf":
            pdf, _ = (
                request.env.ref("th_account_statement.action_report_account_statement")
                .sudo()
                ._render_qweb_pdf(wizard.ids)
            )
            headers = [
                ("Content-Type", "application/pdf"),
                ("Content-Disposition", f'attachment; filename="{filename_prefix}.pdf"'),
            ]
            return request.make_response(pdf, headers=headers)

        if file_type == "xlsx":
            content, filename = wizard._build_xlsx_binary(filename_prefix=filename_prefix)
            headers = [
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                ("Content-Disposition", f'attachment; filename="{filename}"'),
            ]
            return request.make_response(content, headers=headers)

        return request.not_found()

    @http.route(
        ["/my/customer_statements/send/<string:statement_kind>"],
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def portal_send_statement(self, statement_kind, **kwargs):
        if not self._portal_enabled():
            return request.not_found()

        partner = self._get_portal_partner()
        date_from = self._to_date(kwargs.get("date_from"))
        date_to = self._to_date(kwargs.get("date_to"))
        if not date_from or not date_to:
            date_from, date_to = request.env["account.statement.engine"].sudo()._get_period_date_range(
                "this_month"
            )

        if statement_kind == "filtered":
            wizard = self._build_wizard(
                partner, "customer", period_filter="custom", date_from=date_from, date_to=date_to
            )
            msg = "Filtered statement email triggered."
        elif statement_kind == "normal":
            wizard = self._build_wizard(partner, "customer", period_filter="this_year")
            msg = "Statement email triggered."
        elif statement_kind == "overdue":
            wizard = self._build_wizard(partner, "customer_overdue")
            msg = "Overdue statement email triggered."
        else:
            return request.not_found()

        wizard.action_send_email()
        return request.redirect(
            f"/my/customer_statements?message={msg}&date_from={date_from}&date_to={date_to}"
        )

    @http.route(
        ["/statement/share/<int:partner_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def public_statement_share_page(self, partner_id, **kwargs):
        token = kwargs.get("token")
        partner = self._get_shared_partner(partner_id, token)
        if not partner:
            return request.not_found()

        date_from = self._to_date(kwargs.get("date_from"))
        date_to = self._to_date(kwargs.get("date_to"))
        if not date_from or not date_to:
            date_from, date_to = request.env["account.statement.engine"].sudo()._get_period_date_range(
                "this_month"
            )

        values = {
            "partner": partner,
            "date_from": date_from,
            "date_to": date_to,
            "token": token,
        }
        values.update(self._prepare_portal_data(partner, date_from, date_to))
        return request.render("th_account_statement.portal_shared_statement_page", values)

    @http.route(
        ["/statement/share/<int:partner_id>/download/<string:statement_kind>/<string:file_type>"],
        type="http",
        auth="public",
        website=True,
    )
    def public_statement_share_download(self, partner_id, statement_kind, file_type, **kwargs):
        token = kwargs.get("token")
        partner = self._get_shared_partner(partner_id, token)
        if not partner:
            return request.not_found()

        date_from = self._to_date(kwargs.get("date_from"))
        date_to = self._to_date(kwargs.get("date_to"))
        if not date_from or not date_to:
            date_from, date_to = request.env["account.statement.engine"].sudo()._get_period_date_range(
                "this_month"
            )

        if statement_kind == "filtered":
            wizard = self._build_wizard(
                partner, "customer", period_filter="custom", date_from=date_from, date_to=date_to
            )
            filename_prefix = "Filtered_Statement"
        elif statement_kind == "normal":
            wizard = self._build_wizard(partner, "customer", period_filter="this_year")
            filename_prefix = "Customer_Statement"
        elif statement_kind == "overdue":
            wizard = self._build_wizard(partner, "customer_overdue")
            filename_prefix = "Overdue_Statement"
        else:
            return request.not_found()

        if file_type == "pdf":
            pdf, _ = (
                request.env.ref("th_account_statement.action_report_account_statement")
                .sudo()
                ._render_qweb_pdf(wizard.ids)
            )
            headers = [
                ("Content-Type", "application/pdf"),
                ("Content-Disposition", f'inline; filename="{filename_prefix}.pdf"'),
            ]
            return request.make_response(pdf, headers=headers)

        if file_type == "xlsx":
            content, filename = wizard._build_xlsx_binary(filename_prefix=filename_prefix)
            headers = [
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                ("Content-Disposition", f'attachment; filename="{filename}"'),
            ]
            return request.make_response(content, headers=headers)

        return request.not_found()
