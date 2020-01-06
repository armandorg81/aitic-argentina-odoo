# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import models, fields, _
from odoo.addons import decimal_precision as dp

    
class AccountWithholding(models.Model):
    _inherit = "account.withholding"

    article_id = fields.Many2one('article.section')
    withholding_sf_aliquot = fields.Float(string='Withholding Santa Fe Aliquot', default=0.0, digits=(7, 4))
    type_aliquot = fields.Selection(selection_add=[('sf', 'IIBB Santa Fe')])
    company_id = fields.Many2one('res.company', related = 'payment_group_id.company_id')
    jurisdiction_id = fields.Many2one('jurisdiction', string='Jurisdiction', related='company_id.jurisdiction_id')
