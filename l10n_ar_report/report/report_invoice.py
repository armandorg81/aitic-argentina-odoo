# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.tools import float_repr, float_round

class FormatInvoiceReport(models.AbstractModel):
    _name = 'report.l10n_ar_report.l10n_ar_report_invoice'

    def _get_columns(self, inv):
        currency = inv.currency_id.symbol or ''

        columns = [
            {'name': 'Código', 'style': 'width: 10%', 'class': 'text-left pr-1'},
            {'name': 'Producto / Servicio', 'style': 'width: 27%', 'class': 'text-left pr-1'},
            {'name': 'Cantidad', 'style': 'width: 7%', 'class': 'text-right pr-1'},
            {'name': 'Precio Unit.', 'style': 'width: 10%', 'class': 'text-right pr-1', 'currency': currency},
            {'name': 'Dto. (%)', 'style': 'width: 10%', 'class': 'text-right pr-1'}
        ]
        if inv.tipo_comprobante.desc != 'B' or (inv.tipo_comprobante.desc == 'B' and not inv.company_id.hide_afip_fields):
            columns.append({'name': 'Subtotal', 'style': 'width: 12%', 'class': 'text-right pr-1', 'currency': currency})
        if inv.tipo_comprobante.desc != 'B' and not inv.company_id.hide_afip_fields:
            columns += [
                {'name': 'Alicuota IVA', 'style': 'width: 12%', 'class': 'text-left pr-1'},
                {'name': 'Subtotal c/IVA', 'style': 'width: 12%', 'class': 'text-right pr-1', 'currency': currency}
            ]
        return columns

    def _get_lines(self, invoice_id):
        lines = []
        for l in invoice_id.invoice_line_ids:
            lines.append({
                'id': l.id,
                'Código': l.product_id.default_code or '',
                'Producto / Servicio': (l.name or '').replace("'", "\'"),
                'Cantidad': l.quantity,
                'Precio Unit.': self._compute_price(l),
                'Dto. (%)': l.discount,
                'Subtotal': self._compute_subtotal(l),
                'Alicuota IVA': ', '.join(l.invoice_line_tax_ids.filtered(lambda x: x.is_iva).mapped('name')),
                'Subtotal c/IVA': self._compute_iva_subtotal(l),
                'display_type': l.display_type or ''
            })
        return lines

    def _compute_subtotal(self, line):
        subtotal = 0
        if line.invoice_id.tipo_comprobante.desc != 'B':
            subtotal = line.price_subtotal
        elif not line.invoice_id.company_id.hide_afip_fields:
            if line.invoice_line_tax_ids:
                sumTax = 0
                for tl in line.invoice_line_tax_ids:
                    sumTax = sumTax + tl.compute_all((line.price_unit * (1 - (line.discount or 0.0) / 100.0)), line.invoice_id.currency_id, line.quantity, line.product_id)['taxes'][0]['amount']
                subtotal = line.price_subtotal + sumTax
            else:
                subtotal = line.price_subtotal

        return float_repr(float_round(subtotal, precision_digits=2), precision_digits=2)

    def _compute_iva_subtotal(self, line):
        subtotal = 0
        if not line.invoice_id.company_id.hide_afip_fields:
            if line.invoice_line_tax_ids:
                sumTax = 0
                for tl in line.invoice_line_tax_ids:
                    if line.invoice_id.tipo_comprobante.desc != 'B' and tl.is_iva:
                        sumTax = sumTax + tl.compute_all((line.price_unit * (1 - (line.discount or 0.0) / 100.0)), line.invoice_id.currency_id, line.quantity, line.product_id)['taxes'][0]['amount']
                subtotal = line.price_subtotal + sumTax
            else:
                subtotal = line.price_subtotal

        return float_repr(float_round(subtotal, precision_digits=2), precision_digits=2)

    def _compute_price(self, line):
        if not line.invoice_line_tax_ids or line.invoice_id.tipo_comprobante.desc != 'B':
            price_unit = line.price_unit
        else:
            sumTax = 0
            for tl in line.invoice_line_tax_ids:
                if line.invoice_id.tipo_comprobante.desc != 'B' and tl.is_iva:
                    sumTax = tl.compute_all((line.price_unit * (1 - (line.discount or 0.0) / 100.0)), line.invoice_id.currency_id, 1,
                                   line.product_id)['taxes'][0]['amount']
                elif line.invoice_id.tipo_comprobante.desc == 'B':
                    sumTax = sumTax + tl.compute_all((line.price_unit * (1 - (line.discount or 0.0) / 100.0)),
                                                     line.invoice_id.currency_id, line.quantity, line.product_id)['taxes'][0]['amount']
            price_unit = ((line.price_subtotal + sumTax) / line.quantity)

        return float_repr(float_round(price_unit, precision_digits=2), precision_digits=2)

    def _get_taxes_columns(self, inv):
        currency = inv.currency_id.symbol or ''
        columns = [
            {'name': 'Descripción', 'style': '', 'class': 'text-left'},
            {'name': 'Alic(%)', 'style': '', 'class': 'text-right'},
            {'name': 'Importe', 'style': '', 'class': 'text-right', 'currency': currency},
        ]
        return columns

    def _get_tax_lines(self, inv):
        lines = []
        if (inv.tipo_comprobante.desc != 'B' and inv.amount_other_tax > 0) or not inv.company_id.hide_afip_fields:
            tax_line_ids = inv.tax_line_ids.filtered(lambda tl: not tl.tax_id.is_iva)
            if tax_line_ids:
                lines.append({
                    'name': 'Otros Tributos',
                    'tax_line_ids': tax_line_ids
                })
        return lines

    def _get_taxes(self, inv):
        taxes = []
        tax_lines = self._get_tax_lines(inv)
        for line in tax_lines:
            values = []
            taxes.append({'name': line['name'], 'values': values})
            for tri in line['tax_line_ids']:
                values.append({
                    'Descripción': tri.name,
                    'Alic(%)': round(tri.tax_id.amount, 2),
                    'Importe': tri.amount
                })
        return taxes

    def _get_docs(self, docids):
        docs = []
        for record in docids:
            doc = {
                'inv': record,
                'lines': [],
                'columns': self._get_columns(record),
                'taxes_columns': self._get_taxes_columns(record),
                'taxes': self._get_taxes(record),
            }
            for line in self._get_lines(record):
                doc['lines'].append(line)
            docs.append(doc)
        return docs

    @api.multi
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.invoice'].browse(docids)
        get_param = self.env['ir.config_parameter'].sudo().get_param
        page_height = get_param('report.invoice.page_height')
        add_page_number = get_param('report.invoice.add_page_number')
        return {
            'doc_ids': docs.ids,
            'doc_model': 'account.invoice',
            'docs': self._get_docs(docs),
            'page_height': page_height,
            'add_page_number': add_page_number,
            'type': type
        }
