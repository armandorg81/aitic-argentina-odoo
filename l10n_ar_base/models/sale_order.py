# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    invoice_line_count = fields.Integer('Cantidad de líneas', compute='_compute_lines_count')
    not_book = fields.Boolean(string='FX')

    @api.multi
    def _prepare_invoice(self):
        self.ensure_one()
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['tipo_comprobante'] = self.partner_id.responsability_id and self.partner_id.responsability_id.comprobante_default and self.partner_id.responsability_id.comprobante_default.id or False
        if self.not_book:
            tipo_comprobante = self.env['tipo.comprobante'].search([('not_book', '=', True), ('permitido_venta', '=', True)])
            if tipo_comprobante:
                invoice_vals['tipo_comprobante'] = tipo_comprobante[0].id
        if invoice_vals.get('tipo_comprobante', False):
            journal = self.env['account.journal'].search([
                ('comprobante_id', '=', invoice_vals['tipo_comprobante']),
                ('company_id', '=', self.env.user.company_id.id),
                ('type', '=', 'sale')
            ])
            if len(journal) > 0:
                invoice_vals['journal_id'] = journal[0].id
        return invoice_vals

    @api.multi
    @api.depends('order_line')
    def _compute_lines_count(self):
        for record in self:
            record.invoice_line_count = len(record.order_line)

    @api.onchange('order_line')
    def onchange_order_lines(self):
        if self.env.user.company_id.invoice_line and self.invoice_line_count > self.env.user.company_id.invoice_line:
            return {
                'warning': {
                    'title': u'Aviso',
                    'message': u'Posiblemente este excediendo de %d líneas al querer facturar.' % self.env.user.company_id.invoice_line
                }
            }



