# -*- coding: utf-8 -*-

from odoo import models, fields


class TipoComprobante(models.Model):
    _inherit = 'tipo.comprobante'

    comprobante_credito = fields.Boolean(string='Comprobante de Credito')