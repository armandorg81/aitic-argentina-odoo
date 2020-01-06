# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class L10nArAccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.one
    @api.depends('amount_tax','amount_iva')
    def _compute_other(self):
        self.amount_other_tax = sum(line.amount for line in self.tax_line_ids if (line.tax_id.is_excempt is False and
                                                                                  line.tax_id.is_iva is False and
                                                                                  line.tax_id.is_perception is False))
    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount')
    def _compute_amount_perception_arba(self):
        self.amount_perception_arba = sum(line.amount for line in self.tax_line_ids if (line.tax_id.is_perception is True
                                                                                        and line.tax_id.type_aliquot == 'arba'))

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount')
    def _compute_amount_perception(self):
        self.amount_perception = sum(line.amount for line in self.tax_line_ids if (line.tax_id.is_perception is True))


    amount_other_tax = fields.Monetary(string='Otros Impuestos', store=True, readonly=True,
                        compute='_compute_other', track_visibility='always')
    exempt_percep = fields.Boolean(string="Without perception", default=False)
    amount_perception = fields.Monetary(string='Percep. IIBB',store=True, readonly=True,
                        compute='_compute_amount_perception'
                                        )
    amount_perception_arba = fields.Monetary(string='Percep. IIBB Prov. BS. AS.', store=True, readonly=True,
                        compute='_compute_amount_perception_arba', track_visibility='always')
    is_total_withholding_iibb = fields.Boolean(string="Is total IIBB withholding",
                                           default=False, copy=False)


    @api.onchange('invoice_line_ids', 'date_invoice', 'exempt_percep')
    def _onchange_invoice_line_ids(self):
        result = super(L10nArAccountInvoice, self)._onchange_invoice_line_ids()
        if self.type in ['out_invoice', 'out_refund'] and self.tipo_comprobante and not self.exempt_percep:
            taxes_perception = self.get_taxes_perception_values()
            tax_lines = self.tax_line_ids
            if taxes_perception:
                for tax in taxes_perception.values():
                    tax_lines += tax_lines.new(tax)
            self.tax_line_ids = tax_lines
        return result

    @api.multi
    def get_taxes_perception_values(self):
        taxes_perception = {}
        if not self.partner_id.get_exempt_arba(self.date_invoice) and self.company_id.calculate_pw_arba:
            aliquot = self.partner_id._get_arba_update(self.company_id, self.date_invoice)
            if aliquot:
                taxes = self.env['account.tax'].search([('is_perception', '=', True), ('type_aliquot', '=', 'arba'),
                                                    ('amount', '=', aliquot.perception_aliquot)])
                if taxes:
                    for line in self.invoice_line_ids:
                        price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxes_values = taxes.compute_all(price_unit, self.currency_id, line.quantity, line.product_id,
                                                                      self.partner_id)['taxes']
                        for tax in taxes_values:
                            val = self._prepare_tax_line_vals(line, tax)
                            key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)
                            if key not in taxes_perception:
                                taxes_perception[key] = val
                            else:
                                taxes_perception[key]['amount'] += val['amount']
                                taxes_perception[key]['base'] += val['base']
        return taxes_perception

    @api.multi
    def compute_taxes(self):
        """Function used in other module to compute the taxes on a fresh invoice created (onchanges did not applied)"""
        account_invoice_tax = self.env['account.invoice.tax']
        ctx = dict(self._context)
        for invoice in self:
            # Delete non-manual tax lines
            self._cr.execute("DELETE FROM account_invoice_tax WHERE invoice_id=%s AND manual is False", (invoice.id,))
            self.invalidate_cache()

            # Generate one tax line per tax, however many invoice lines it's applied to
            tax_grouped = invoice.get_taxes_values()

            # Generate aliquot IIBB
            if not invoice.exempt_percep:
                tax_grouped.update(invoice.get_taxes_perception_values())

            # Create new tax lines
            for tax in tax_grouped.values():
                account_invoice_tax.create(tax)

        # dummy write on self to trigger recomputations
        return self.with_context(ctx).write({'invoice_line_ids': []})

