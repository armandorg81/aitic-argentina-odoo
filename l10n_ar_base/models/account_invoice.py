# -*- coding: utf-8 -*-

import time
from odoo import api, fields, models, _
from datetime import date
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_is_zero

class L10nArAccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def create(self, vals):
        if vals.get('tipo_comprobante', False) and vals.get('company_id', False):
            type = vals.get('type', False) in ('in_invoice', 'in_refund') and 'purchase' or 'sale'
            journal = self.env['account.journal'].search([
                ('comprobante_id', '=', vals.get('tipo_comprobante')),
                ('company_id', '=', vals.get('company_id')),
                ('type', '=', type)
            ], limit=1)
            vals['journal_id'] = journal and journal.id or False
        if not vals.get('punto_venta') and vals.get('type', False) in ('out_invoice', 'out_refund') and vals.get('tipo_comprobante', False):
            tipo_comprobante = self.env['tipo.comprobante'].browse(vals.get('tipo_comprobante'))
            if tipo_comprobante.punto_venta_ids:
                vals['punto_venta'] = tipo_comprobante.punto_venta_ids[0].id
        res = super(L10nArAccountInvoice, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        if not vals.get('journal_id', False) and vals.get('tipo_comprobante', False):
            type = self.type in ('in_invoice', 'in_refund') and 'purchase' or 'sale'
            journal = self.env['account.journal'].search([
                ('comprobante_id', '=', vals.get('tipo_comprobante')),
                ('company_id', '=', self.company_id.id),
                ('type', '=', type)
            ], limit=1)
            vals['journal_id'] = journal and journal.id or False
        res = super(L10nArAccountInvoice, self).write(vals)
        return res

    @api.one
    @api.depends('invoice_line_ids.price_subtotal','tax_line_ids.amount')
    def _compute_excempt(self):
        if self.type not in ['out_invoice', 'out_refund'] and self.tipo_comprobante and self.tipo_comprobante.is_exempt:
            self.amount_excempt = 0.0
        else:
            if self.type in ['in_invoice', 'in_refund'] and self.tipo_comprobante.desc not in ['B', 'C']:
                self.amount_excempt = sum(line.base for line in self.tax_line_ids if (line.tax_id.is_excempt is True))
            elif self.type in ['out_invoice', 'out_refund']:
                self.amount_excempt = sum(line.base for line in self.tax_line_ids if (line.tax_id.is_excempt is True))
            else:
                self.amount_excempt = 0.0

    @api.multi
    def action_invoice_cancel(self):
        if self.filtered(lambda inv: inv.state in ['paid']) and float_is_zero(self.amount_total, precision_digits=2):
            res = self.action_cancel()
        else:
            res = super(L10nArAccountInvoice, self).action_invoice_cancel()
        return res

    @api.one
    @api.depends('tax_line_ids.amount')
    def _compute_iva(self):
        self.amount_iva = sum(line.amount for line in self.tax_line_ids if (line.tax_id.is_iva is True))

    @api.one
    @api.depends('tax_line_ids.amount')
    def _compute_neto(self):
        account_precision = self.env['decimal.precision'].precision_get('Account')
        self.neto_gravado = sum(line.base for line in self.tax_line_ids \
                                if (line.tax_id.is_iva is True and not float_is_zero(line.amount, account_precision)))

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id', 'date_invoice', 'type', 'team_id')
    def _compute_no_gravado(self):
        if self.type not in ['out_invoice', 'out_refund'] and self.tipo_comprobante and self.tipo_comprobante.is_exempt:
            no_gravado = 0.0
        else:
            no_gravado = sum(line.price_subtotal for line in self.invoice_line_ids if
                             (not line.invoice_line_tax_ids and not line.invoice_id.tipo_comprobante.is_exempt))
            if self.type in ['in_invoice', 'in_refund'] and self.tipo_comprobante.desc in ['B', 'C']:
                no_gravado = 0.0
        self.no_gravado = no_gravado

    @api.one
    @api.depends('amount_tax','amount_iva')
    def _compute_other(self):
        self.amount_other_tax = sum(line.amount for line in self.tax_line_ids if (line.tax_id.is_excempt is False and line.tax_id.is_iva is False))

    @api.model
    def default_get(self, fields):
        res = super(L10nArAccountInvoice, self).default_get(fields)
        if 'date_invoice' not in res:
            res['date_invoice'] = date.today().strftime('%Y-%m-%d')
        if res.get('type', 'out_invoice') in ['out_invoice']:
            res['partner_bank_id'] = False
        return res

    @api.model
    def _get_default_punto_venta(self):
        punto = self.env['point.sales'].search([('default_invoice', '=', True)], limit=1)
        return punto

    punto_venta = fields.Many2one('point.sales', "Punto de Venta", default=_get_default_punto_venta, copy=False) #'Punto Venta'
    tipo_comprobante = fields.Many2one('tipo.comprobante', "Tipo Comprobante")
    desc = fields.Char('Código Comprobante', related="tipo_comprobante.desc", readonly=True, invisible=True)
    punto_venta_proveedor = fields.Char("Punto Venta", size=4)
    amount_excempt = fields.Monetary(string='Monto Exento', readonly=True,
                                     compute='_compute_excempt', track_visibility='always')
    amount_iva = fields.Monetary(string='IVA',store=True, readonly=True,
                                 compute='_compute_iva', track_visibility='always')
    amount_other_tax = fields.Monetary(string='Otros Impuestos', store=True, readonly=True,
                                       compute='_compute_other', track_visibility='always')
    neto_gravado = fields.Monetary(string='Base Imponible',store=True, readonly=True,
                                   compute='_compute_neto', track_visibility='always',help="Base Imponible o Neto Gravado")
    no_gravado = fields.Monetary(string='No Gravado', readonly=True,
                                 compute='_compute_no_gravado', track_visibility='always')
    provincia = fields.Char('Provincia', related='partner_id.state_id.name', store=True)

    comprobante_01_name = fields.Char("Factura Escaneada")

    comprobante_01 = fields.Binary(
        string=('Factura Escaneada'),
        copy=False,
        help='Comprobante 01')

    voucher_control = fields.Boolean(related='journal_id.voucher_control')

    other_info = fields.Text(string='Información', copy=False)

    invoice_line_count = fields.Integer('Cantidad de líneas', compute='_compute_lines_count')

    @api.multi
    @api.depends('invoice_line_ids')
    def _compute_lines_count(self):
        for record in self:
            record.invoice_line_count = len(record.invoice_line_ids)

    @api.onchange('invoice_line_ids')
    def onchange_invoice_lines(self):
        if self.type in ('out_invoice', 'out_refund') and self.env.user.company_id.invoice_line and self.invoice_line_count > self.env.user.company_id.invoice_line:
            return {
                'warning': {
                    'title': u'Aviso',
                    'message': u'Ha excedido de %d líneas para ésta factura.' % self.env.user.company_id.invoice_line
                }
            }

    @api.multi
    def action_invoice_open(self):
        for record in self:
            for line in record.invoice_line_ids:
                if not line.display_type and line.company_id.is_check_price_total and float_is_zero(line.price_total, precision_digits=2):
                    raise UserError('El total es 0 para el producto (%s)' %line.product_id.name)
            if record.type in ('out_invoice', 'out_refund') and self.env.user.company_id.invoice_line and record.invoice_line_count > self.env.user.company_id.invoice_line:
                raise UserError(u'Ha excedido de %d líneas para ésta factura.' % self.env.user.company_id.invoice_line)
            if record.journal_id.use_account_invoice and record.journal_id.default_debit_account_id:
                record.account_id = record.journal_id.default_debit_account_id
                for line in record.invoice_line_ids:
                    if line.product_id and line.product_id.type != 'service' and record.journal_id.account_product_id:
                        line.account_id = record.journal_id.account_product_id
                    if line.product_id and line.product_id.type == 'service' and record.journal_id.account_service_id:
                        line.account_id = record.journal_id.account_service_id
        return super(L10nArAccountInvoice, self).action_invoice_open()


    @api.onchange('partner_id', 'company_id')
    def onchange_partner_comprobante(self):
        if self.partner_id:
            self.tipo_comprobante = self.partner_id.responsability_id and self.partner_id.responsability_id.comprobante_default or False
            if self.partner_id.comprobante_default:
                self.tipo_comprobante = self.partner_id.comprobante_default
            self.onchange_comprobante()


    @api.constrains('amount_excempt', 'no_gravado', 'amount_other_tax')
    def _check_amounts(self):
        account_precision = self.env['decimal.precision'].precision_get('Account')
        for rec in self:
            if rec.state in ['in_invoice']:
                if rec.tipo_comprobante.desc in ['B', 'C'] and not float_is_zero(rec.no_gravado, account_precision):
                    raise ValidationError('EL CAMPO IMPORTE NO GRAVADO DEBE SER IGUAL A CERO CUANDO SON COMPROBANTES B Ó C')
                if rec.tipo_comprobante.desc in ['B', 'C'] and not float_is_zero(rec.amount_excempt, account_precision):
                    raise ValidationError('EL CAMPO IMPORTE EXENTO DEBE SER IGUAL A CERO CUANDO SON COMPROBANTES B Ó C')

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        super(L10nArAccountInvoice, self)._onchange_partner_id()
        partner = self.partner_id.parent_id and self.partner_id.parent_id or self.partner_id
        if partner.responsability_id:
            if self.type in ['out_refund','out_invoice']:
                cmp_ids = [x.id for x in partner.responsability_id.comprobante_ids]
                return {'domain':{'tipo_comprobante': [('id','in',cmp_ids),('permitido_venta','=',True)]}}
            else:
                return {}

    @api.onchange('tipo_comprobante', 'company_id')
    def onchange_comprobante(self):
        for rec in self:
            if rec.tipo_comprobante:
                journal_obj = rec.env['account.journal']
                if rec.type in ['out_invoice','out_refund']:
                    journal = journal_obj.search([
                        ('comprobante_id','=',rec.tipo_comprobante.id),
                        ('company_id','=',rec.env.user.company_id.id),
                        ('type','=','sale')
                    ])
                    if len(journal) > 0:
                        rec.journal_id = journal[0].id
                    else:
                        rec.journal_id = False
                    if rec.tipo_comprobante.punto_venta_ids:
                        return {'domain': {'punto_venta': [('id','in',[x.id for x in rec.tipo_comprobante.punto_venta_ids])]}}
                    else:
                        return {'domain': {'punto_venta': [('id','in',[])]}}
                else:
                    journal = journal_obj.search([
                        ('comprobante_id','=',rec.tipo_comprobante.id),
                        ('company_id','=',rec.env.user.company_id.id),
                        ('type','=','purchase')
                    ])
                    if len(journal) > 0:
                        rec.journal_id = journal[0].id
                    else:
                        rec.journal_id = False

    # function intervention to not allow change the type of currency!
    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        pass
        # if self.journal_id and not self._context.get('default_currency_id'):
        #     self.currency_id = self.journal_id.currency_id.id or self.journal_id.company_id.currency_id.id

    @api.onchange('punto_venta_proveedor')
    def _check_punto_venta_proveedor(self):
        if self.punto_venta_proveedor:
            if len(self.punto_venta_proveedor) != 4:
                self.punto_venta_proveedor = self.punto_venta_proveedor.zfill(4)

class L10nArAccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.constrains('invoice_line_tax_ids')
    def _check_invoice_line_tax(self):
        for line in self:
            if len([x.id for x in line.invoice_line_tax_ids if(x.is_iva is True)]) > 1:
                raise ValidationError("No es posible agregar mas de dos impuestos IVA a un mismo item")
