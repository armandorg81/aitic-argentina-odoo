# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)


class L10nArAccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount')
    def _compute_amount_perception_iva(self):
        self.amount_perception_iva = sum(line.amount for line in self.tax_line_ids if (line.tax_id.is_perception is True
                                                                                      and line.tax_id.type_aliquot == 'iva'))

    @api.one
    @api.depends('amount_total', 'residual', 'neto_gravado', 'group_invoice_ids',
                 'group_invoice_ids.withholding_tax_base_iva')
    def _compute_no_withholding_amount_iva(self):
        base_withholding = sum(x.withholding_tax_base_iva for x in self.payment_move_line_ids.mapped(
            'payment_id.payment_group_id.group_invoice_ids').filtered(
            lambda x: x.invoice_id == self))
        base_withholding += sum(x.amount_iva for x in self.payment_move_line_ids.mapped('invoice_id'))
        self.no_withholding_amount_iva = (self.amount_iva - base_withholding) * -1 if self.refund_type == 'credit' and self.type in [
            'in_refund', 'out_refund'] else (self.amount_iva - base_withholding)

    amount_perception_iva = fields.Monetary(string='Percep. IVA', store=True, readonly=True,
                                           compute='_compute_amount_perception_iva', track_visibility='always')
    no_withholding_amount_iva = fields.Monetary(string='Withholding Iva', copy=False, store=True, readonly=True,
                                                 compute='_compute_no_withholding_amount_iva',
                                                 track_visibility='always',
                                                 digits=dp.get_precision('Account'))

    @api.multi
    def get_taxes_perception_values(self):
        taxes_perception = super(L10nArAccountInvoice, self).get_taxes_perception_values()
        if not self.partner_id.get_exempt_agip(self.date_invoice) and self.company_id.calculate_pw_agip:
            aliquot = self.partner_id._get_iva_update(self.company_id, self.date_invoice)
            if aliquot:
                taxes = self.env['account.tax'].search([('is_perception', '=', True), ('type_aliquot', '=', 'iva'),
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
