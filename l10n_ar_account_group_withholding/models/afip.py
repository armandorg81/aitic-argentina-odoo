# -*- coding: utf-8 -*-
from odoo import models, fields


class AfipAliquotsAmountWithholdingTable(models.Model):
    _name = 'afip.gain.withholding'

    amount_from = fields.Float(string='Monto Desde', required=True)

    amount_to = fields.Float(string='Monto Hasta', required=True)

    amount = fields.Float(string='Monto', required=True)

    rate = fields.Float(string='Mas el %', required=True)

    excess_amount = fields.Float(string='S/Exced. de', required=True)