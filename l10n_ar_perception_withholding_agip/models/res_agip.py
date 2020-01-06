# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResAliquot(models.Model):
    _inherit = 'res.aliquot'

    type_ci = fields.Char(string='Type Contr Insc')
    mark_hs = fields.Char(string='High subject mark')
    mark_aliq = fields.Char(string='Aliquot mark')
    type = fields.Selection(selection_add=[('agip', 'IIBB Capital Federal')])

class ResAliquotAGIP(models.Model):
    _name = 'res.aliquot.agip'

    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    date_update = fields.Date(string='Update date')
    cuit_taxpayer = fields.Char(string='Cuit Taxpayer', select=True)
    type_ci = fields.Char(string='Type Contr Insc')
    mark_hs = fields.Char(string='High subject mark')
    mark_aliq = fields.Char(string='Aliquot mark')
    perception_aliquot = fields.Float(string='Perception Aliquot', default=0.0)
    withholding_aliquot = fields.Float(string='Withholding Aliquot', default=0.0)
    perception_group = fields.Char(string='Perception Group')
    withholding_group = fields.Char(string='Withholding Group')
