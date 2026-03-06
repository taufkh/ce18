import logging
import base64

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.utils import ensure_db

_logger = logging.getLogger(__name__)


class C18DmsShareController(http.Controller):
    def _bootstrap_public_env(self):
        if request.env.uid is None:
            request.env["ir.http"]._auth_method_public()

    def _get_document(self, token):
        document = request.env["c18.dms.document"].sudo().search([("share_token", "=", token)], limit=1)
        _logger.info("C18 DMS share lookup token=%s found=%s state=%s allow_external=%s", token, bool(document), document.state if document else None, document.allow_external_share if document else None)
        if not document or not document._can_access_public_share():
            _logger.info("C18 DMS share denied token=%s", token)
            raise request.not_found()
        return document

    def _log_access(self, document, access_type):
        request.env["c18.dms.share.log"].sudo().create({
            "document_id": document.id,
            "access_type": access_type,
            "access_ip": request.httprequest.remote_addr,
            "user_agent": request.httprequest.user_agent.string,
            "access_name": request.httprequest.path,
        })

    @http.route("/c18_dms/share/<string:token>", type="http", auth="none", website=False, save_session=False)
    def c18_dms_share_page(self, token, **kwargs):
        ensure_db(db=kwargs.get("db"))
        self._bootstrap_public_env()
        _logger.info("C18 DMS share page request token=%s db=%s uid=%s", token, request.session.db, request.env.uid)
        document = self._get_document(token)
        self._log_access(document, "page")
        mimetype = document.attachment_id.mimetype or ""
        inline_preview = mimetype.startswith("image/") or mimetype == "application/pdf"
        values = {
            "document": document,
            "download_url": f"/c18_dms/share/{token}/download",
            "inline_preview": inline_preview,
            "preview_url": f"/web/content/{document.attachment_id.id}?download=false",
        }
        return request.render("c18_dms.portal_document_page", values)

    @http.route("/c18_dms/share/<string:token>/download", type="http", auth="none", website=False, save_session=False)
    def c18_dms_share_download(self, token, **kwargs):
        ensure_db(db=kwargs.get("db"))
        self._bootstrap_public_env()
        _logger.info("C18 DMS share download request token=%s db=%s uid=%s", token, request.session.db, request.env.uid)
        document = self._get_document(token)
        if not document.attachment_id:
            raise request.not_found()
        self._log_access(document, "download")
        content = base64.b64decode(document.attachment_id.datas or b"")
        headers = [
            ("Content-Type", document.attachment_id.mimetype or "application/octet-stream"),
            ("Content-Disposition", f'attachment; filename="{document.attachment_id.name or document.name}"'),
        ]
        return request.make_response(
            content,
            headers=headers,
        )
