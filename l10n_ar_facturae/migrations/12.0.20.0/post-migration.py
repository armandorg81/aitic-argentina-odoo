# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api
from odoo import SUPERUSER_ID

def update_number_name(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    invoices = env['account.invoice'].search([('move_id', '!=', False)])
    for invoice in invoices:
        new_name = ''
        if invoice.type in ['out_invoice', 'out_refund'] and invoice.punto_venta and invoice.num_comprobante:
            new_name = invoice.tipo_comprobante and '(' + invoice.tipo_comprobante.codigo.zfill(4) + ') ' + invoice.punto_venta.name + '-' + invoice.num_comprobante.zfill(8) or invoice.punto_venta.name + '-' + invoice.num_comprobante.zfill(8)
        elif invoice.type in ['in_invoice', 'in_refund'] and invoice.punto_venta_proveedor and invoice.num_comprobante:
            new_name = invoice.tipo_comprobante and '(' + invoice.tipo_comprobante.codigo.zfill(4) + ') ' + invoice.punto_venta_proveedor + '-' + invoice.num_comprobante.zfill(8) or invoice.punto_venta_proveedor + '-' + invoice.num_comprobante.zfill(8)
        if new_name:
            invoice.move_id.name = new_name
            invoice.name = new_name
            invoice.move_name = new_name

def migrate(cr, version):
    update_number_name(cr)

