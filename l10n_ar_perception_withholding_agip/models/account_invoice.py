# -*- coding: utf-8 -*-

import time
from odoo import api, fields, models
from datetime import date,datetime
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero, float_compare
import odoo.addons.decimal_precision as dp

class L10nArAccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount')
    def _compute_amount_perception_agip(self):
        self.amount_perception_agip = sum(
            line.amount for line in self.tax_line_ids if (line.tax_id.is_perception is True
                                                          and line.tax_id.type_aliquot == 'agip'))

    # exempt_agip_partner_percep = fields.Boolean(related="partner_id.exempt_agip", string="Exempt IIBB Capital Federal",
    #                                             default=False)
    amount_perception_agip = fields.Monetary(string='Percep. IIBB Capital Federal', store=True, readonly=True,
                                             compute='_compute_amount_perception_agip', track_visibility='always')


    @api.multi
    def get_taxes_perception_values(self):
        taxes_perception = super(L10nArAccountInvoice, self).get_taxes_perception_values()
        if not self.partner_id.get_exempt_agip(self.date_invoice) and self.company_id.calculate_pw_agip:
            aliquot = self.partner_id._get_agip_update(self.company_id, self.date_invoice)
            if aliquot:
                taxes = self.env['account.tax'].search([('is_perception', '=', True), ('type_aliquot', '=', 'agip'),
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

