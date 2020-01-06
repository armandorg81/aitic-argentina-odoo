# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class unidades_medida(models.Model):
    _description = "Unidades Medida"
    _name = 'unidades.medida'

    name = fields.Char('Nombre', translate=True)
    cod = fields.Char('Codigo', translate=True)