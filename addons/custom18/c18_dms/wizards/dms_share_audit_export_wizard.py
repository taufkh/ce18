import base64
import csv
from io import BytesIO, StringIO

from odoo import _, fields, models
from odoo.tools.misc import xlsxwriter


class C18DmsShareAuditExportWizard(models.TransientModel):
    _name = "c18.dms.share.audit.export.wizard"
    _description = "Export DMS Share Audit"

    date_from = fields.Date()
    date_to = fields.Date()
    export_format = fields.Selection(
        [("csv", "CSV"), ("xlsx", "XLSX")],
        default="xlsx",
        required=True,
    )

    def _build_domain(self):
        self.ensure_one()
        domain = []
        if self.date_from:
            domain.append(("access_date", ">=", self.date_from))
        if self.date_to:
            domain.append(("access_date", "<=", self.date_to))
        return domain

    def _collect_rows(self):
        records = self.env["c18.dms.share.audit.report"].search(
            self._build_domain(),
            order="access_date desc, document_id",
        )
        rows = []
        for record in records:
            rows.append([
                record.access_date.isoformat() if record.access_date else "",
                record.document_id.display_name or "",
                dict(record._fields["access_type"].selection).get(record.access_type, ""),
                str(record.access_count or 0),
            ])
        return rows

    def _generate_csv(self, rows):
        stream = StringIO()
        writer = csv.writer(stream)
        writer.writerow(["Access Date", "Document", "Access Type", "Access Count"])
        writer.writerows(rows)
        return stream.getvalue().encode("utf-8"), "text/csv", "c18_share_audit.csv"

    def _generate_xlsx(self, rows):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream, {"in_memory": True})
        sheet = workbook.add_worksheet("Share Audit")
        header_format = workbook.add_format({"bold": True, "bg_color": "#E2E8F0"})
        for col, title in enumerate(["Access Date", "Document", "Access Type", "Access Count"]):
            sheet.write(0, col, title, header_format)
        for row_idx, row in enumerate(rows, start=1):
            for col_idx, value in enumerate(row):
                sheet.write(row_idx, col_idx, value)
        sheet.set_column(0, 0, 14)
        sheet.set_column(1, 1, 36)
        sheet.set_column(2, 2, 16)
        sheet.set_column(3, 3, 14)
        workbook.close()
        return stream.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "c18_share_audit.xlsx"

    def action_export(self):
        self.ensure_one()
        rows = self._collect_rows()
        if self.export_format == "csv":
            file_bytes, mimetype, filename = self._generate_csv(rows)
        else:
            file_bytes, mimetype, filename = self._generate_xlsx(rows)
        attachment = self.env["ir.attachment"].create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(file_bytes),
            "mimetype": mimetype,
            "res_model": self._name,
            "res_id": self.id,
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
