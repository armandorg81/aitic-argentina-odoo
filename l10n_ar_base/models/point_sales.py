# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError

class point_sales(models.Model):
    _description = "Puntos de Ventas"
    _name = 'point.sales'

    name = fields.Char('Código', translate=True, size=4)
    desc = fields.Char('Descripción', translate=True)
    default_invoice = fields.Boolean('Para facturas')
    default_picking = fields.Boolean('Para remitos')
    tax_assets = fields.Boolean('Bonos Fiscales Electrónicos')

    @api.constrains('name')
    def _check_codigo_point_sales(self):
        if len(self.name) < 4:
            raise ValidationError("El Punto de Venta tiene que tener 4 dígitos")

