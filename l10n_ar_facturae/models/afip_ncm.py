# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductProduct(models.Model):
    _name = "afip.ncm"

    name = fields.Char(string='Código NCM')
    description = fields.Text(string='Descripción')
