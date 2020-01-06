# -*- coding: utf-8 -*-
# © 2018 AITIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero, date_utils
from odoo.exceptions import UserError

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    open_move_line_ids = fields.One2many(
        'account.move.line',
        compute='_compute_open_move_lines'
    )
    nc_ref_id = fields.Integer(string='Original Document', translate=True)

    payments_widget = fields.Text(compute='_get_payment_info_JSON')

    @api.one
    def _get_outstanding_info_JSON(self):
        self.outstanding_credits_debits_widget = json.dumps(False)
        if self.state == 'open':
            domain = [('account_id', '=', self.account_id.id),
                      ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
                      ('reconciled', '=', False),
                      '|',
                      '&', ('amount_residual_currency', '!=', 0.0), ('currency_id', '!=', None),
                      '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id', '=', None),
                      ('amount_residual', '!=', 0.0)]
            if self.type == 'out_invoice' or (self.type == 'in_refund' and self.refund_type == 'credit') or (
                    self.type == 'out_refund' and self.refund_type == 'debit'):
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = self.currency_id
            if len(lines) != 0:
                payment_lines = lines.filtered(lambda x: x.payment_id)
                lines_other = lines.filtered(lambda x: not x.payment_id)
                for payment in payment_lines.mapped('payment_id'):
                    payment_group_id = payment.payment_group_id
                    if payment.currency_id and payment.currency_id == self.currency_id:
                        amount_to_show = abs(payment.amount)
                    else:
                        amount_to_show = payment.currency_id._convert(abs(payment.amount),
                                                                      self.currency_id, payment.company_id,
                                                                      payment_group_id.date or fields.Date.today())
                    if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                        continue
                    info['content'].append({
                        'journal_name': payment.name,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': payment_group_id.id,
                        'payment': 1,
                        'position': currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })

                for line in lines_other:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == self.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        # amount_to_show = line.company_id.currency_id.with_context(date=line.date).compute(
                        #     abs(line.amount_residual), self.currency_id)
                        amount_to_show = line.company_id.currency_id._convert(abs(line.amount_residual),
                                                                              self.currency_id, line.company_id,
                                                                              line.date or fields.Date.today())
                    if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                        continue
                    info['content'].append({
                        'journal_name': line.move_id.name or line.ref,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'payment': 0,
                        'position': currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })
                info['title'] = type_payment
                info['different_company'] = 'no'
                self.outstanding_credits_debits_widget = json.dumps(info)
                self.has_outstanding = True

    @api.model
    def _get_payments_vals(self):
        if not self.payment_move_line_ids:
            return []
        payment_vals = []
        currency_id = self.currency_id
        currency_company_id = self.env.user.company_id.currency_id
        payment_lines = self.payment_move_line_ids.filtered(lambda x: x.payment_id)
        lines_other = self.payment_move_line_ids.filtered(lambda x: not x.payment_id)
        exchange = 'no'
        for payment in payment_lines:
            date_payment = payment.payment_id.payment_group_id.date
            if payment.payment_id.currency_id == currency_id and currency_id != currency_company_id:
                amount_to_show = payment.payment_id.amount
            else:
                amount_to_show = payment.payment_id.currency_id._convert(payment.payment_id.amount, currency_id,
                                                                         payment.payment_id.company_id,
                                                                         date_payment or fields.Date.today())
            if payment.payment_id.currency_id == currency_company_id:
                amount_company_to_show = payment.payment_id.amount
            else:
                amount_company_to_show = payment.payment_id.currency_id._convert(payment.payment_id.amount,
                                                                                 currency_company_id,
                                                                                 payment.payment_id.company_id,
                                                                                 date_payment or fields.Date.today())
            if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                continue
            payment_ref = payment.move_id.name
            if payment.move_id.ref:
                payment_ref += ' (' + payment.move_id.ref + ')'
            payment_vals.append({
                'name': payment.name,
                'journal_name': payment.journal_id.name,
                'amount': amount_to_show,
                'currency': currency_id.symbol,
                'position': currency_id.position,
                'amount_company': round(amount_company_to_show, 2),
                'currency_company': currency_company_id.symbol,
                'position_company': currency_company_id.position,
                'digits': [69, currency_id.decimal_places],
                'date': payment.date,
                'payment_id': payment.id,
                'account_payment_id': payment.payment_id.payment_group_id.id,
                'invoice_id': payment.invoice_id.id,
                'move_id': payment.move_id.id,
                'ref': payment_ref,
                'exchange': exchange,
            })
        for payment in lines_other:
            payment_currency_id = False
            if self.type == 'out_invoice' or (
                    self.type == 'out_refund' and self.refund_type == 'debit') or (
                    self.type == 'in_refund' and self.refund_type == 'credit'):
                amount = sum([p.amount for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                amount_currency = sum(
                    [p.amount_currency for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                if payment.matched_debit_ids:
                    payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in
                                               payment.matched_debit_ids]) and payment.matched_debit_ids[
                                              0].currency_id or False
            elif self.type == 'in_invoice' or (
                    self.type == 'in_refund' and self.refund_type == 'debit') or (
                    self.type == 'out_refund' and self.refund_type == 'credit'):
                amount = sum(
                    [p.amount for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_ids])
                amount_currency = sum([p.amount_currency for p in payment.matched_credit_ids if
                                       p.credit_move_id in self.move_id.line_ids])
                if payment.matched_credit_ids:
                    payment_currency_id = all([p.currency_id == payment.matched_credit_ids[0].currency_id for p in
                                               payment.matched_credit_ids]) and payment.matched_credit_ids[
                                              0].currency_id or False
            # get the payment value in invoice currency
            if payment_currency_id and payment_currency_id == self.currency_id  and amount_currency != 0.0:
                amount_to_show = amount_currency
            else:
                currency = payment.company_id.currency_id
                amount_to_show = currency._convert(amount, self.currency_id, payment.company_id, payment.date or fields.Date.today())
            amount_company_to_show = amount
            if payment.company_id.currency_id != currency_company_id:
                amount_company_to_show = payment.company_id.currency_id._convert(amount_company_to_show, currency_company_id, payment.company_id,
                                                   payment.date or fields.Date.today())
            if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                continue
            if payment.move_id.journal_id == payment.move_id.company_id.currency_exchange_journal_id:
                amount_to_show = 0.0
                exchange = 'no'
            payment_ref = payment.move_id.name
            if payment.move_id.ref:
                payment_ref += ' (' + payment.move_id.ref + ')'
            payment_vals.append({
                'name': payment.name,
                'journal_name': payment.journal_id.name,
                'amount': amount_to_show,
                'currency': currency_id.symbol,
                'position': currency_id.position,
                'amount_company': round(amount_company_to_show, 2),
                'currency_company': currency_company_id.symbol,
                'position_company': currency_company_id.position,
                'digits': [69, currency_id.decimal_places],
                'date': payment.date,
                'payment_id': payment.id,
                'account_payment_id': payment.payment_id.id,
                'invoice_id': payment.invoice_id.id,
                'move_id': payment.move_id.id,
                'ref': payment_ref,
                'exchange': exchange,
            })
        return payment_vals

    @api.one
    @api.depends('payment_move_line_ids.amount_residual')
    def _get_payment_info_JSON(self):
        self.payments_widget = json.dumps(False)
        if self.payment_move_line_ids:
            different_company = self.env.user.company_id.currency_id != self.currency_id and 'yes' or 'no'
            info = {'title': _('Less Payment'), 'outstanding': False, 'content': self._get_payments_vals(), 'different_company': different_company}
            self.payments_widget = json.dumps(info, default=date_utils.json_default)

    @api.multi
    def _get_tax_factor(self):
        self.ensure_one()
        return (self.amount_total and (self.amount_untaxed / self.amount_total) or 1.0)

    @api.multi
    def _compute_open_move_lines(self):
        for rec in self:
            rec.open_move_line_ids = rec.move_id.line_ids.filtered(
                lambda r: not r.reconciled and r.account_id.internal_type in (
                    'payable', 'receivable'))

    @api.multi
    def action_account_invoice_payment_group(self):
        self.ensure_one()
        if self.state != 'open':
            raise ValidationError(_(
                'You can only register payment if invoice is open'))
        return {
            'name': _('Register Payment Group'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment.group',
            'view_id': False,
            'target': 'current',
            # 'target': target,
            'type': 'ir.actions.act_window',
            # 'domain': [('id', 'in', aml.ids)],
            'context': {
                # 'invoice_ids': self.ids,
                'to_pay_move_line_ids': self.open_move_line_ids.ids,
                'pop_up': True,
                'default_company_id': self.company_id.id,
                'default_currency_id': self.currency_id and self.currency_id.id or self.company_id.currency_id.id,
            },
        }

    @api.multi
    def action_invoice_open(self):
        res = super(AccountInvoice, self).action_invoice_open()
        for record in self:
            if record.nc_ref_id and record.reconcile_credit_note:
                domain = [('account_id', '=', record.account_id.id),
                          ('partner_id', '=', self.env['res.partner']._find_accounting_partner(record.partner_id).id),
                          ('reconciled', '=', False), ('amount_residual', '!=', 0.0),
                          ('invoice_id', '=', record.nc_ref_id)]
                lines = self.env['account.move.line'].search(domain)
                paym = record.assign_outstanding_credit(lines.id, 0)
        return res

    @api.multi
    def assign_outstanding_credit(self, credit_aml_id, payment=0):
        self.ensure_one()
        domain = [('account_id', '=', self.account_id.id),
                  ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
                  ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0),
                  ('amount_residual_currency', '!=', 0.0)]
        if self.type == 'out_invoice' or (self.type == 'in_refund' and self.refund_type == 'credit') or (
                self.type == 'out_refund' and self.refund_type == 'debit'):
            domain.extend([('credit', '>', 0), ('debit', '=', 0)])
        else:
            domain.extend([('credit', '=', 0), ('debit', '>', 0)])
        lines = self.env['account.move.line'].search(domain)
        if payment == 1:
            payment_group_id = self.env['account.payment.group'].browse(credit_aml_id)
            for credit_aml in lines.filtered(lambda x:
                                             x.payment_id in payment_group_id.payment_ids).sorted(key=lambda i:
                                             i.amount_residual_currency, reverse=True):
                if self.residual:
                    if not credit_aml.currency_id and self.currency_id != self.company_id.currency_id:
                        credit_aml.with_context(allow_amount_currency=True, check_move_validity=False).write({
                            # 'amount_currency': self.company_id.currency_id.with_context(date=credit_aml.date).compute(
                            #     credit_aml.balance, self.currency_id),
                            'amount_currency': self.company_id.currency_id._convert(credit_aml.balance,
                                                                                    self.currency_id, self.company_id,
                                                                                    credit_aml.date or fields.Date.today()),
                            'currency_id': self.currency_id.id})
                        # aaa = self.company_id.currency_id._convert(credit_aml.balance, self.currency_id,
                        #                                         payment.company_id,
                        #                                         credit_aml.date or fields.Date.today())
                    if credit_aml.payment_id:
                        credit_aml.payment_id.write({'invoice_ids': [(4, self.id, None)]})
                    self.register_payment(credit_aml)
            payment_group_id.update_invoice_group_ids()
            payment_group_id.update_group_advance_move()

        else:
            credit_aml = self.env['account.move.line'].browse(credit_aml_id)
            if not credit_aml.currency_id and self.currency_id != self.company_id.currency_id:
                credit_aml.with_context(allow_amount_currency=True, check_move_validity=False).write({
                    # 'amount_currency': self.company_id.currency_id.with_context(date=credit_aml.date).compute(
                    #     credit_aml.balance, self.currency_id),
                    'amount_currency': self.company_id.currency_id._convert(credit_aml.balance, self.currency_id,
                                                                            self.company_id,
                                                                            credit_aml.date or fields.Date.today()),

                    'currency_id': self.currency_id.id})
            if credit_aml.payment_id:
                credit_aml.payment_id.write({'invoice_ids': [(4, self.id, None)]})
            self.register_payment(credit_aml)
            if credit_aml.payment_id and credit_aml.payment_id.payment_group_id:
                credit_aml.payment_id.payment_group_id.update_invoice_group_ids()
                credit_aml.payment_id.payment_group_id.update_group_advance_move()
        return True

    @api.multi
    def remove_move_reconcile(self):
        """ Undo a reconciliation """
        payment_id = self.env.context.get(
            'payment_id')
        group_payment_id = self.env.context.get(
            'group_payment_id', False)
        if group_payment_id:
            group = self.env['account.payment.group'].browse(self.env.context.get('group_payment_id', False))
            for payment in self.payment_move_line_ids.filtered(lambda x: x.payment_id and x.payment_id.payment_group_id.id == group_payment_id):
                payment.with_context(invoice_id=self.id).remove_move_reconcile()
            if group:
                group.update_invoice_group_ids()
        else:
            move_line = self.env['account.move.line'].browse(payment_id)
            exchange_journal = move_line.move_id.company_id.currency_exchange_journal_id
            if move_line.move_id.journal_id == exchange_journal:
                raise UserError(_('It must not break from here the conciliation by a difference instead.'))
            move_line.with_context(invoice_id=self.id).remove_move_reconcile()
            if move_line and move_line.payment_group_id:
                # payment = self.env['account.payment'].browse(move_line.payment_id)
                move_line.payment_group_id.update_invoice_group_ids()
        return True

class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    def invoice_refund(self):
        res = super(AccountInvoiceRefund, self).invoice_refund()
        invoice_id = self.env['account.invoice'].browse(self._context.get('active_id', False))
        if res.get('domain', False):
            nc_id = res['domain'][1][2]
            nc = self.env['account.invoice'].search([('id','=',int(nc_id[0]))])
            nc.write({'nc_ref_id':invoice_id.id})
            # if len(nc_id) > 1:
            #     new_inv = self.env['account.invoice'].search([('id', '=', int(nc_id[1]))])
            #     new_inv.journal_document_type_id = (
            #         new_inv._get_available_journal_document_types(
            #             new_inv.journal_id, new_inv.type, new_inv.partner_id
            #         ).get('journal_document_type'))
        return res

class AccountInvoiceGroup(models.Model):
    _name = "account.invoice.group"

    payment_group_id = fields.Many2one('account.payment.group', 'Payment Group', ondelete='cascade')
    invoice_id = fields.Many2one('account.invoice', 'Invoice')
    currency_id = fields.Many2one('res.currency', string='Currency')
    advance_amount = fields.Monetary(string='Amount Payable', currency_field='currency_id')
    company_id = fields.Many2one('res.company')
    company_currency_id = fields.Many2one('res.currency')
    advance_amount_company = fields.Monetary(string='Amount Payable Currency', currency_field='company_currency_id',
                                             compute='_compute_advance_amount_company')
    number = fields.Char(related='invoice_id.number', store=True, readonly=True, copy=False)
    partner_id = fields.Many2one(related='invoice_id.partner_id', string='Partner')
    date = fields.Date(related='invoice_id.date', string='Period')
    date_payment = fields.Date(related='payment_group_id.date', string='Period payment')
    num_comprobante = fields.Char(related='invoice_id.num_comprobante',string="Número de Comprobante", copy=False, size=8)
    tipo_comprobante = fields.Many2one(related='invoice_id.tipo_comprobante', string="Tipo Comprobante")
    residual = fields.Monetary(related='invoice_id.residual', store=True, help="Remaining amount due.")
    residual_company_signed = fields.Monetary(related='invoice_id.residual_company_signed', store=True, help="Remaining amount company currency due.")
    amount_untaxed = fields.Monetary(related='invoice_id.neto_gravado', string='Untaxed Amount')
    amount_tax = fields.Monetary(related='invoice_id.amount_tax', string='Tax')
    amount_total_signed = fields.Monetary(related='invoice_id.amount_total_signed', string='Total in Invoice Currency')
    amount_total_company_signed = fields.Monetary(related='invoice_id.amount_total_company_signed', string='Total in Company Currency',  currency_field='company_currency_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
    ], related='invoice_id.state', string='Status')
    is_parcial = fields.Boolean('Is parcial')
    # state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('posted', 'Posted')],
    #                          default='draft', copy=False, string="Status")

    @api.onchange('advance_amount')
    def _onchange_not_currency_company(self):
        if self.amount_total_signed > self.advance_amount:
            self.is_parcial = True

    @api.one
    @api.depends('advance_amount', 'date_payment', 'payment_group_id.date')
    def _compute_advance_amount_company(self):
        if self.currency_id != self.company_currency_id or (not self.currency_id and not self.company_currency_id):
            # self.advance_amount_company = self.currency_id.with_context(date=self.date_payment).compute(self.advance_amount,
            #                                                             self.company_currency_id)
            company_id = self.company_id or self.payment_group_id.company_id or self.env.user.company_id
            self.advance_amount_company = self.currency_id._convert(self.advance_amount, self.company_currency_id,
                                                                    company_id,
                                                                    self.date_payment or fields.Date.today())
        else:
            self.advance_amount_company = self.advance_amount

    def get_invoice_advance_amount_company(self):
        if self.currency_id != self.company_currency_id or (not self.currency_id and not self.company_currency_id):
            return self.currency_id._convert(self.advance_amount, self.company_currency_id,
                                                                    self.company_id,
                                                                    self.invoice_id._get_currency_rate_date() or fields.Date.today())
        else:
            return self.advance_amount
