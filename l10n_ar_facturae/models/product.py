# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = "product.template"

    bfe_check = fields.Boolean(string='Producto para BFE')
    bfe_ncm = fields.Many2one('afip.ncm', string='NCM del Producto (Bonos Fiscales)')
