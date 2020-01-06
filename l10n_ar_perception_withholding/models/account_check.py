# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)





class L10nArAccountCheck(models.Model):
    _inherit = 'account.check'

    def update_invoice_value(self, inv_vals):
        inv_vals.update({
                    'not_commission': True,
                    'exempt_percep': True,
                })
        return inv_vals
