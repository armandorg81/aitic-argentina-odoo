# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import datetime

class account_abstract_payment(models.AbstractModel):
    _inherit = 'account.abstract.payment'

    journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True,
                                 domain=lambda self: [('type', 'in', ('bank', 'cash')), ('company_id.id', '=', self.env.user.company_id.id)])

class AccountPaymentBeelivery(models.Model):
    _inherit = "account.payment"

    comprobante_01_name = fields.Char("Comprobante 01")
    comprobante_02_name = fields.Char("Comprobante 02")

    comprobante_01 = fields.Binary(
        string=('Comprobante 01'),
        copy=False,
        help='Comprobante 01')

    comprobante_02 = fields.Binary(
        string=('Comprobante 02'),
        copy=False,
        help='Comprobante 02')