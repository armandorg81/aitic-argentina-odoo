# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import float_is_zero
from odoo import api
from odoo import SUPERUSER_ID


def update_invoice_residual(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    invoices = env['account.invoice'].search([('type', 'in', ['out_invoice', 'out_refund']),
                                              ('residual', '!=', 0)])
    for invoice in invoices:
        invoice._compute_residual()
        digits_rounding_precision = invoice.currency_id.rounding
        if float_is_zero(invoice.residual, precision_rounding=digits_rounding_precision):
            invoice.write({'state': 'paid'})

def migrate(cr, version):
    update_invoice_residual(cr)
