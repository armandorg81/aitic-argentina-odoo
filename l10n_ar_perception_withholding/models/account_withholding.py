# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import models, fields, _
from odoo.addons import decimal_precision as dp

    
class AccountWithholding(models.Model):
    _inherit = "account.withholding"

    withholding_arba_aliquot = fields.Float(string='Withholding IIBB Prov. BS. AS. Aliquot', default=0.0, digits=(7, 4))
    type_aliquot = fields.Selection(selection_add=[('arba', 'IIBB Prov. BS. AS.')])