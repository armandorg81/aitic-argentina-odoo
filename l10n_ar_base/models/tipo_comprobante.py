# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class tipo_comprobante(models.Model):
    _description = "Tipo de Comprobante"
    _name = 'tipo.comprobante'

    name = fields.Char('Nombre', translate=True)
    codigo = fields.Char('Codigo', translate=True)
    desc = fields.Char('Descripción', translate=True)
    permitido_venta = fields.Boolean('Permitido Venta')
    referencia_id = fields.Many2one('tipo.comprobante', string='Referencia')
    is_import = fields.Boolean(string='Comprobante para importacion (Aduanero)')
    is_exempt = fields.Boolean(string='Comprobante exento de impuesto')
    not_book = fields.Boolean(string='No mostrar en libros')
    not_date_due = fields.Boolean(string='No informar Fecha de Vencimiento')
    type = fields.Selection([
                    ('invoice','Facturas'),
                    ('credit_note','Notas de Créditos'),
                    ('debit_note','Notas de Débitos'),
                    ('other','Otros')],
                    string="Tipo")
    punto_venta_ids = fields.Many2many('point.sales',relation='punto_venta_tipo_comprobante_rel',
        id1='punto_venta_id',id2='comprobante_id',string="Puntos de Venta")
    sale_journal_ids = fields.One2many('account.journal','comprobante_id',
        domain=[('type', '=', 'sale')],string="Diarios de Venta")
    purchase_journal_ids = fields.One2many('account.journal','comprobante_id',
        domain=[('type', '=', 'purchase')],string="Diarios de Compra")
