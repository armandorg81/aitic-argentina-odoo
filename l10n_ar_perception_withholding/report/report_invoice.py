# -*- coding: utf-8 -*-

from odoo import api, models


class FormatInvoiceReport(models.AbstractModel):
    _inherit = 'report.l10n_ar_report.l10n_ar_report_invoice'

    def _get_tax_lines(self, inv):
        lines = super(FormatInvoiceReport, self)._get_tax_lines(inv)
        for line in lines:
            if line['name'] == 'Otros Tributos':
                line['tax_line_ids'] = line['tax_line_ids'].filtered(lambda tl: not tl.tax_id.is_perception)

        if (inv.tipo_comprobante.desc != 'B' and inv.amount_other_tax > 0) or not inv.company_id.hide_afip_fields:
            tax_line_ids = inv.tax_line_ids.filtered(lambda tl: tl.tax_id.is_perception)
            if tax_line_ids:
                lines.append({
                    'name': 'Percepciones IIBB',
                    'tax_line_ids': tax_line_ids
                })
        return lines
