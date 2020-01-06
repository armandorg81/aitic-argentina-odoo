# -*- coding: utf-8 -*-
# © 2018 AITIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import UserError
import odoo.addons.l10n_ar_account_group_withholding.models.number_to_letter as number_to_letter
from odoo.addons import decimal_precision as dp

class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"

    amount_base_withholding_iva = fields.Float(string='Withholding Base IVA', readonly=True, store=True,
                                           compute='_compute_withholding_amount_iva', digits=dp.get_precision('Account'))
    withholding_iva_id = fields.Many2one('account.withholding', string='Withholding',
                                     domain=[('type_aliquot', '=', 'iva')])
    withholding_amount_iva = fields.Float(string='Withholding Amount Iva', readonly=True, store=True,
                                           compute='_compute_withholding_amount_iva',
                                           digits=dp.get_precision('Account'))

    # @api.one
    # @api.depends('amount_payable', 'to_pay_move_line_ids')
    # def _compute_amount_base_withholding_iva(self):
    #     base_amount_withholding = 0.0
    #     for invoice in self.to_pay_move_line_ids.mapped('invoice_id'):
    #         if invoice.currency_id != self.currency_id:
    #             base_amount_withholding += invoice.currency_id._convert(invoice.no_withholding_amount_iva,
    #                                                                        self.currency_id, self.env.user.company_id,
    #                                                                        invoice.date or fields.Date.today())
    #         else:
    #             base_amount_withholding += invoice.no_withholding_amount_iva
    #     amount_withholding = 0.0
    #     if not self._context.get('no_update_withholding', False) and not self.is_canceled:
    #         amount_withholding = base_amount_withholding
    #     elif self._context.get('no_update_withholding', False) or self.is_canceled:
    #         amount_withholding = self.amount_base_withholding_iva
    #
    #     self.amount_base_withholding_iva = amount_withholding if amount_withholding >= 0.0 else 0.0
    def get_amount_withholding_iva(self, invoice, payment):
        aliquot = payment.partner_id._get_iva_update(payment.company_id, payment.date)
        base_amount_withholding = 0.0
        withholding_amount_iva = 0.0
        if invoice.amount_untaxed > payment.company_id.amount_exempt_iva:
            if invoice.tipo_comprobante.desc == 'M':
                if invoice.currency_id != self.currency_id:
                    amount_withholding = invoice.currency_id._convert(
                        invoice.no_withholding_amount_iva,
                        self.currency_id,
                        self.env.user.company_id,
                        invoice.date or fields.Date.today())
                else:
                    amount_withholding = invoice.no_withholding_amount_iva
                base_amount_withholding += amount_withholding
                withholding_amount_iva += amount_withholding
            elif aliquot:
                if invoice.currency_id != self.currency_id:
                    amount_withholding = invoice.currency_id._convert(
                        invoice.no_withholding_amount_iva,
                        self.currency_id,
                        self.env.user.company_id,
                        invoice.date or fields.Date.today())
                else:
                    amount_withholding = invoice.no_withholding_amount_iva
                base_amount_withholding += amount_withholding
                withholding_amount_iva += amount_withholding * aliquot.withholding_aliquot / 100
        return base_amount_withholding, withholding_amount_iva

    @api.multi
    @api.depends('amount_payable', 'to_pay_move_line_ids')
    def _compute_withholding_amount_iva(self):
        for rec in self:
            rec.withholding_amount_iva = 0.0
            if rec.company_id.calculate_wh_iva and not rec.exempt_withholding and rec.partner_type == "supplier":
                if not self._context.get('no_update_withholding') and not rec.is_canceled:
                    base_amount_withholding = 0.0
                    withholding_amount_iva = 0.0
                    for invoice in rec.to_pay_move_line_ids.mapped('invoice_id'):
                        base_withholding, withholding_iva = rec.get_amount_withholding_iva(invoice, rec)
                        base_amount_withholding += base_withholding
                        withholding_amount_iva += withholding_iva
                    if withholding_amount_iva < rec.amount_payable:
                        rec.withholding_amount_iva = withholding_amount_iva
                        rec.amount_base_withholding_iva = base_amount_withholding
                    else:
                        rec.withholding_amount_iva = rec.amount_payable
                        rec.amount_base_withholding_iva = rec.amount_payable

                else:
                    rec.withholding_amount_iva = rec._get_amount_iva_w_pay()

    @api.multi
    @api.onchange('to_pay_move_line_ids', 'amount_payable', 'state', 'withholding_base_amount',
                  'amount_arba_withholding', 'amount_agip_withholding','withholding_amount_iva')
    def _onchange_to_pay_amount(self):
        super(AccountPaymentGroup, self)._onchange_to_pay_amount()
        for rec in self:
            if not rec.is_canceled:
                rec.to_pay_amount -= rec.withholding_amount_iva

    @api.multi
    @api.depends('amount_payable', 'unreconciled_amount', 'partner_id', 'withholding_base_amount',
                 'amount_arba_withholding', 'amount_agip_withholding', 'withholding_amount_iva')
    def _compute_to_pay_amount(self):
        super(AccountPaymentGroup, self)._compute_to_pay_amount()
        for rec in self:
            if not rec.is_canceled:
                rec.to_pay_amount -= rec.withholding_amount_iva

    # @api.multi
    # @api.depends('amount_payable')
    # def _compute_payable_wtax(self):
    #     super(AccountPaymentGroup, self)._compute_payable_wtax()
    #     for rec in self:
    #         rec.amount_payable_wtax += rec.withholding_amount_iva

    @api.multi
    @api.depends('payments_amount', 'withholding_base_amount', 'withholding_amount_iva', 'state')
    def _compute_amount_total_payable(self):
        super(AccountPaymentGroup, self)._compute_amount_total_payable()
        for rec in self:
            if rec.state == "draft" and not rec.is_canceled:
                rec.amount_total_payable += rec.withholding_amount_iva

    def create_withholding_payments(self):
        super(AccountPaymentGroup, self).create_withholding_payments()
        if self.withholding_amount_iva > 0.0 and not self.mapped('payment_ids').filtered(lambda x: x.is_withholding and x.type_aliquot == 'iva'):
            journal_id = self.company_id.supplier_wh_iva_journal_id
            if not journal_id:
                raise UserError(_('You must configurate in the company the withholding IVA journal.'))
            payment_method_id = self.env.ref('account.account_payment_method_manual_out', False)
            currency = self.currency_id
            withholding_amount_iva = self.withholding_amount_iva
            currency_journal = journal_id.currency_id or journal_id.company_id.currency_id
            if currency_journal and currency_journal != currency:
                # withholding_amount_iva = currency._convert(self.withholding_amount_iva, currency_journal,
                #                                             self.env.user.company_id,
                #                                             self.date or fields.Date.today())
                withholding_amount_iva = self._convert_payment(currency,  self.withholding_amount_iva,
                                                               currency_journal, self.env.user.company_id,
                                                               self.date or fields.Date.today())
                currency = currency_journal
            vals = {
                'journal_id': journal_id.id,
                'payment_method_id': payment_method_id.id,
                'payment_date': self.date,
                'payment_type': 'outbound',
                'currency_id': currency.id,
                'communication': _("Withholding IVA"),
                'partner_id': self.partner_id.id,
                'partner_type': self.partner_type,
                'payment_group_company_id': self.company_id.id,
                # 'payment_group': True,
                'amount': withholding_amount_iva,
                'amount_aliquot_in_words': number_to_letter.to_word_no_decimal(withholding_amount_iva),
                'name': '',
                'is_withholding': True,
                'type_aliquot': 'iva',
                'state': 'draft'}

            self.payment_ids += self.env['account.payment'].create(vals)

    def _update_group_invoice_ids(self):
        if self.state == 'draft':
            self.group_invoice_ids = self.env['account.payment.group.invoice']
            for invoice in self.to_pay_move_line_ids.mapped('invoice_id'):
                base_withholding, withholding_iva = self.get_amount_withholding_iva(invoice, self)
                self.group_invoice_ids += self.env['account.payment.group.invoice'].new({
                                                                                        'invoice_id': invoice.id,
                                                                                        'withholding_tax_base': invoice.no_withholding_amount_iibb,
                                                                                        'withholding_tax_base_iva': base_withholding,
                                                                                        'withholding_tax_iva': withholding_iva,
                                                                                    })

    def _get_amount_iva_w_pay(self):
        self.ensure_one()
        return sum(pay.amount for pay in self.mapped('payment_ids').filtered(lambda x: x.is_withholding and
                                                                                       x.type_aliquot == 'iva'))

    def _get_is_aliquot(self):
        result = super(AccountPaymentGroup, self)._get_is_aliquot()
        if not result and self.withholding_amount_iva > 0.0:
            return True
        return result

    def generate_withholding_payments(self):
        res = super(AccountPaymentGroup, self).generate_withholding_payments()
        ctx = dict(res._context)
        ctx.update({'withholding_amount_iva': self.withholding_amount_iva})
        return res.with_context(ctx)

    def create_withholding(self):
        res = super(AccountPaymentGroup, self).create_withholding()
        for rec in self:
            if rec.withholding_amount_iva > 0.0 and rec.company_id.calculate_wh_iva:
                payment = self.mapped('payment_ids').filtered(lambda x: x.is_withholding and
                                                                        x.type_aliquot == 'iva')
                aliquot = rec.partner_id._get_iva_update(rec.company_id, rec.date)
                if payment:
                    if not rec.withholding_iva_id:
                        name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.date).next_by_code(
                            'account.payment.supplier.iva')
                        withholding = self.env['account.withholding'].create({'name': name,
                                                                              'withholding_amount': payment.amount,
                                                                              'withholding_iva_aliquot': aliquot.withholding_aliquot,
                                                                              'withholding_tax_base_real': rec.withholding_tax_base_real,
                                                                              'date': rec.date,
                                                                              'partner_id': rec.partner_id.id,
                                                                              'reference': rec.name,
                                                                              'payment_id': payment[0].id,
                                                                              'state': 'done',
                                                                              'type_aliquot': 'iva'})
                        rec.withholding_iva_id = withholding.id
                    else:
                        rec.withholding_iva_id.write({
                            'withholding_amount': payment.amount,
                            'withholding_iva_aliquot': aliquot.withholding_aliquot,
                            'withholding_tax_base_real': rec.withholding_tax_base_real,
                            'date': rec.date,
                            'partner_id': rec.partner_id.id,
                            'reference': rec.name,
                            'payment_id': payment[0].id,
                            'state': 'done' if rec.withholding_iva_id.state != 'declared' else 'declared',
                        })
        return res

    def _post_update_group_invoice_ids(self):
        withholding_tax_real_total = self.withholding_tax_base_real
        amount_base_withholding_iva_total = self.amount_base_withholding_iva
        for line in self.with_context({'payment_group_id': self.id,
                                       'matched_lines': True}).matched_move_line_ids.filtered(lambda x:
                                        x.invoice_id).sorted(key=lambda i: i.amount_residual_currency, reverse=True):
            group_invoice = self.group_invoice_ids.filtered(lambda x: x.invoice_id == line.invoice_id)
            if group_invoice:
                update = {}
                if withholding_tax_real_total > 0.0:
                    if withholding_tax_real_total > group_invoice[0].withholding_tax_base:
                        withholding_tax_real = group_invoice[0].withholding_tax_base
                    else:
                        withholding_tax_real = withholding_tax_real_total
                    withholding_tax_real_total -= withholding_tax_real
                    group_invoice['withholding_tax_real'] = withholding_tax_real
                if amount_base_withholding_iva_total > 0.0:
                    if amount_base_withholding_iva_total > group_invoice[0].withholding_tax_iva:
                        withholding_tax_iva = group_invoice[0].withholding_tax_iva
                    else:
                        withholding_tax_iva = amount_base_withholding_iva_total
                        withholding_tax_base_iva = withholding_tax_iva
                        tax_iva = group_invoice[0].withholding_tax_iva/group_invoice[0].withholding_tax_base_iva
                        if tax_iva < 1 and tax_iva > 0.0:
                            withholding_tax_base_iva = withholding_tax_iva * (1.00 / tax_iva)
                        elif tax_iva == 0.0:
                            withholding_tax_base_iva = 0.0
                        group_invoice['withholding_tax_iva'] = withholding_tax_iva
                        group_invoice['withholding_tax_base_iva'] = withholding_tax_base_iva
                    amount_base_withholding_iva_total -= withholding_tax_iva

                if update:
                    group_invoice[0].write(update)

    def update_payment_down(self):
        for rec in self:
            withholding_tax_real_total = rec.withholding_tax_base_real - sum(x.withholding_tax_real for x in rec.group_invoice_ids)
            for move in rec.matched_move_line_ids.with_context(payment_group_id=rec.id).sorted(key=lambda p: (p.date, p.id)):
                if move.invoice_id and not rec.group_invoice_ids.filtered(lambda x: x.invoice_id == move.invoice_id):
                    if withholding_tax_real_total > 0:
                        withholding_tax_real = withholding_tax_real_total if withholding_tax_real_total <  move.invoice_id.no_withholding_amount_iibb else move.invoice_id.no_withholding_amount_iibb
                        self.env['account.payment.group.invoice'].create({
                            'invoice_id': move.invoice_id.id,
                            'group_id': rec.id,
                            'withholding_tax_base': move.invoice_id.no_withholding_amount_iibb,
                            'withholding_tax_real': withholding_tax_real,
                        })
                        withholding_tax_real_total -= withholding_tax_real


    @api.multi
    def unlink(self):
        for rec in self:
            if rec.withholding_iva_id and rec.withholding_iva_id.state == 'declared':
                raise UserError(_(
                    "You cannot delete a payment with declared withholdings."))
            elif rec.withholding_iva_id:
                rec.withholding_iva_id.unlink()
        return super(AccountPaymentGroup, self).unlink()

    @api.multi
    def cancel(self):
        for rec in self:
            if rec.withholding_iva_id and rec.withholding_iva_id.state == 'done':
                rec.withholding_iva_id.action_annulled()
        super(AccountPaymentGroup, self).cancel()

class AccountPaymentGroupInvoice(models.Model):
    _inherit = "account.payment.group.invoice"

    withholding_tax_base_iva = fields.Float(string='withholding tax base',
                                        digits=dp.get_precision('Account'), default=0.0)
    withholding_tax_iva = fields.Float(string='withholding tax base',
                                        digits=dp.get_precision('Account'), default=0.0)
