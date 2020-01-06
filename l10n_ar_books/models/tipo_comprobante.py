# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class tipo_comprobante(models.Model):
    _inherit = 'tipo.comprobante'

    book_desc = fields.Char('Descripción en Libros')