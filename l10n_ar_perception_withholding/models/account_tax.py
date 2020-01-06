# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import ValidationError

class L10nArAccountTax(models.Model):
    _inherit = "account.tax"

    is_perception = fields.Boolean("Perception", help="Indicates if the tax is IIBB aliquot", default=False)
    type_aliquot = fields.Selection([('none', ''),('arba', 'IIBB Prov. BS. AS.')], default='none')
    # is_withholding = fields.Boolean("Withholding ARBA", help="Indicates if the tax is ARBA aliquot", default=False)
