# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import io


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.multi
    def _post_pdf(self, save_in_attachment, pdf_content=None, res_ids=None):
        def close_streams(streams):
            for stream in streams:
                try:
                    stream.close()
                except Exception:
                    pass

        if len(res_ids) > 1 and self.model == 'account.invoice' and pdf_content:
            pdf_content_stream = io.BytesIO(pdf_content)
            # Build a record_map mapping id -> record
            record_map = {r.id: r for r in self.env[self.model].browse([res_id for res_id in res_ids if res_id])}
            if res_ids[0] in record_map and not res_ids[0] in save_in_attachment:
                new_stream = self.postprocess_pdf_report(record_map[res_ids[0]], pdf_content_stream)
                # If the buffer has been modified, mark the old buffer to be closed as well.
                if new_stream and new_stream != pdf_content_stream:
                    close_streams([pdf_content_stream])
                    pdf_content_stream = new_stream
            res = pdf_content_stream.getvalue()
        else:
            res = super(IrActionsReport, self)._post_pdf(save_in_attachment, pdf_content=pdf_content, res_ids=res_ids)
        return res
