# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class cond_venta(models.Model):
    _description = "Tipo de Responsable"
    _name = 'condicion.venta'

    name = fields.Char('Nombre', translate=True)
    codigo = fields.Char('Codigo', translate=True)
    for_company = fields.Boolean('Permitido para Compañía')
    for_partner = fields.Boolean('Permitido para Cliente/Proveedor')
    comprobante_default = fields.Many2one('tipo.comprobante', string='Comprobante por Defecto')
    comprobante_ids = fields.Many2many(comodel_name="tipo.comprobante",relation='condicion_venta_tipo_comprobante_rel',
        id1='condicion_id',id2='comprobante_id',string="Comprobantes Permitidos Receptor")
    validar_cuit = fields.Boolean(string='Validar No. Documento', default=True)
