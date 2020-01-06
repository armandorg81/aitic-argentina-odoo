# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import models, fields, _
from odoo.addons import decimal_precision as dp

    
class AccountWithholding(models.Model):
    _inherit = "account.withholding"

    withholding_agip_aliquot = fields.Float(string='Withholding IIBB Capital Federal Aliquot', default=0.0, digits=(7, 4))
    type_aliquot = fields.Selection(selection_add=[('agip', 'IIBB Capital Federal')])
    regime_credit = fields.Boolean('Regime of Credit Invoice', default=True)
    acceptance = fields.Selection([('express', 'Express'),('tacit', 'Tacit'),('sd', 'S/D')], string="Acceptance", default='sd')
    date_acceptance = fields.Date(string='Express Acceptance date', required=True, default=fields.Date.today)
