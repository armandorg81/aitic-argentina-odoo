# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class L10nArAccountJournal(models.Model):
    _inherit = 'account.journal'

    comprobante_id = fields.Many2one('tipo.comprobante', string="Comprobante")
    voucher_control = fields.Boolean(string='Comprobante Obligatorio', default=True)
    use_account_invoice = fields.Boolean(string='Sobreescribir cuenta en Facturas')
    account_product_id = fields.Many2one('account.account', string='Cuenta Productos Doc. Internos',
                                         domain=[('deprecated', '=', False)])
    account_service_id = fields.Many2one('account.account', string='Cuenta Servicios Doc. Internos',
                                         domain=[('deprecated', '=', False)])
