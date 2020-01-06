# -*- coding: utf-8 -*-

import json
from odoo import models,fields,api, _
from odoo.tools import float_is_zero


class DebitCreditAccountInvoice(models.Model):
    _inherit = "account.invoice"

    neto_gravado_signed = fields.Monetary(string='Base Imponible', compute='_compute_sign')
    amount_excempt_signed = fields.Monetary(string='Monto Exento', compute='_compute_sign')

    def _compute_sign(self):
        for invoice in self:
            sign = invoice.type in ['in_refund', 'out_refund'] and invoice.refund_type == 'credit' and -1 or 1
            invoice.neto_gravado_signed = invoice.neto_gravado * sign
            invoice.amount_excempt_signed = invoice.amount_excempt * sign

    @api.model
    def create(self, values):
        if self.env.context.get('active_model', False) == 'account.check.action.wizard':
            objct = self.env['account.check.action.wizard'].browse(self.env.context.get('active_id'))
            if objct.action_type in ['customer_return','claim']:
                self = self.with_context(journal_type='sale')
        if values.get('refund_type'):
            values['type'] = self.env.context.get('journal_type', False) == 'sale' and 'out_refund' or 'in_refund'
        invoice = super(DebitCreditAccountInvoice, self).create(values)
        return invoice

    @api.model
    def write(self, values):
        if self.env.context.get('active_model', False) == 'account.check.action.wizard':
            objct = self.env['account.check.action.wizard'].browse(self.env.context.get('active_id'))
            if objct.action_type in ['customer_return','claim']:
                self = self.with_context(journal_type='sale')
        if values.get('refund_type'):
            values['type'] = self.env.context.get('journal_type', False) == 'sale' and 'out_refund' or 'in_refund'
        invoice = super(DebitCreditAccountInvoice, self).write(values)
        return invoice

    def _compute_sign_taxes(self):
        for invoice in self:
            sign = invoice.type in ['in_refund', 'out_refund'] and invoice.refund_type == 'credit' and -1 or 1
            invoice.amount_untaxed_invoice_signed = invoice.amount_untaxed * sign
            invoice.amount_tax_signed = invoice.amount_tax * sign

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 
                  'company_id', 'date_invoice', 'refund_type', 'move_id.line_ids.amount_currency', 'move_id.line_ids.currency_id')
    def _compute_amount(self):
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_tax = sum(line.amount for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self._get_currency_rate_date())
            amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = (self.type in ['in_refund','out_refund'] and self.refund_type == 'credit') and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign

    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line_ids.price_subtotal',
        'move_id.line_ids.amount_residual',
        'move_id.line_ids.currency_id')
    def _compute_residual(self):
        residual = 0.0
        residual_company_signed = 0.0
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        if self.type in ['out_refund', 'in_refund'] and self.refund_type == 'debit':
            sign = 1
        for line in self.sudo().move_id.line_ids:
            if line.account_id.internal_type in ('receivable', 'payable'):
                residual_company_signed += line.amount_residual
                if line.currency_id == self.currency_id:
                    residual += line.amount_residual_currency if line.currency_id else line.amount_residual
                else:
                    from_currency = (line.currency_id and line.currency_id.with_context(
                        date=line.date)) or line.company_id.currency_id.with_context(date=line.date)
                    residual += from_currency.compute(line.amount_residual, self.currency_id)
        self.residual_company_signed = abs(residual_company_signed) * sign
        self.residual_signed = abs(residual) * sign
        self.residual = abs(residual)
        digits_rounding_precision = self.currency_id.rounding
        if float_is_zero(self.residual, precision_rounding=digits_rounding_precision):
            self.reconciled = True
        else:
            self.reconciled = False

    @api.one
    def _get_outstanding_info_JSON(self):
        self.outstanding_credits_debits_widget = json.dumps(False)
        if self.state == 'open':
            domain = [('account_id', '=', self.account_id.id),
                      ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
                      ('reconciled', '=', False), ('amount_residual', '!=', 0.0)]
            if self.type in ('out_invoice', 'in_refund') or (self.type in ('out_refund') and self.refund_type == 'debit'):
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = self.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == self.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        amount_to_show = line.company_id.currency_id.with_context(date=line.date).compute(
                            abs(line.amount_residual), self.currency_id)
                    if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                        continue
                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })
                info['title'] = type_payment
                self.outstanding_credits_debits_widget = json.dumps(info)
                self.has_outstanding = True

    child_ids = fields.One2many(
        'account.invoice',
        'refund_invoice_id',
        'Debit and Credit Notes',
        readonly=True, copy=False,
        states={'draft': [('readonly', False)]},
        help='These are all credit and debit to this invoice')

    refund_type = fields.Selection(
        [('debit', 'Debit Note'),
         ('credit', 'Credit Note')], index=True,
        string='Refund type',
        track_visibility='always')

    reconcile_credit_note = fields.Boolean(string='Conciliar NC?', default=True)

    @api.model
    def line_get_convert(self, line, part):
        res = super(DebitCreditAccountInvoice, self).line_get_convert(line, part)
        if self.type in ['in_refund','out_refund'] and self.refund_type == 'debit':
            debit = res.get('debit')
            credit = res.get('credit')
            res.update({'debit': credit, 'credit': debit})
        return res

    @api.onchange('tipo_comprobante')
    def onchange_tipo_comprob(self):
        vals = {}
        if self.env.context.get('active_model', False) == 'account.check.action.wizard':
            objct = self.env['account.check.action.wizard'].browse(self.env.context.get('active_id'))
            if objct.action_type in ['customer_return','claim']:
                self = self.with_context(journal_type='sale')
        if self.tipo_comprobante.type == 'invoice':
            vals['refund_type'] = False
            vals['type'] = self.env.context.get('journal_type', False) == 'sale' and 'out_invoice' or 'in_invoice'
        elif self.tipo_comprobante.type == 'credit_note':
            vals['refund_type'] = 'credit'
            vals['type'] = self.env.context.get('journal_type', False) == 'sale' and 'out_refund' or 'in_refund'
        elif self.tipo_comprobante.type == 'debit_note':
            vals['refund_type'] = 'debit'
            vals['type'] = self.env.context.get('journal_type', False) == 'sale' and 'out_refund' or 'in_refund'
        self.update(vals)

    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Factura'),
            'in_invoice': _('Factura de proveedor'),
            'out_refund': _('Nota de crédito'),
            'out_refund_d': _('Nota de débito'),
            'in_refund': _('Nota de crédito de proveedor'),
            'in_refund_d': _('Nota de débito de proveedor'),
        }
        result = []
        for inv in self:
            type_f = inv.type
            if type_f == 'out_refund' and inv.refund_type == 'debit':
                type_f = 'out_refund_d'
            elif type_f == 'in_refund' and inv.refund_type == 'debit':
                type_f = 'in_refund_d'
            name = inv.number or inv.name or ''
            result.append((inv.id, "%s" % (name or TYPES[type_f])))
        return result


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
                 'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
                 'invoice_id.date_invoice', 'invoice_id.date')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id,
                                                          partner=self.invoice_id.partner_id)
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        self.price_total = taxes['total_included'] if taxes else self.price_subtotal
        if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.with_context(
                date=self.invoice_id._get_currency_rate_date()).compute(price_subtotal_signed,
                                                                        self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and self.invoice_id.refund_type == 'credit' and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign
