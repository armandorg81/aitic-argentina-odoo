# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class cond_venta(models.Model):
    _inherit = 'condicion.venta'

    book_desc = fields.Char('Descripción en Libros')
