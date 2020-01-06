# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import ValidationError

class L10nArAccountTax(models.Model):
    _inherit = "account.tax"

    type_aliquot = fields.Selection(selection_add=[('agip', 'IIBB Capital Federal')])
