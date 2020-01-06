# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class tipo_documento(models.Model):
    _description = "Tipo de Documento"
    _name = 'tipo.documento'
    _rec_name = "name"

    name = fields.Char('Nombre', translate=True)
    codigo = fields.Char('Codigo', translate=True)
