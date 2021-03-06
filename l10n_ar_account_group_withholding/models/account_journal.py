# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_withholding = fields.Boolean("Withholding Journal", default=False)
