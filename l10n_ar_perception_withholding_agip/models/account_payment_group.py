# -*- coding: utf-8 -*-
# © 2018 AITIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import math
from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.l10n_ar_account_group_withholding.models.number_to_letter as number_to_letter
from odoo.addons import decimal_precision as dp

class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"

    amount_agip_withholding = fields.Float(string='Withhol. IIBB  Capital Federal', readonly=True, store=True,
                                           compute='_compute_amount_agip_withholding', digits=dp.get_precision('Account'))
    # withholding_agip_aliquot = fields.Float(string='Withholding AGIP Aliquot', default=0.0)
    withholding_agip_id = fields.Many2one('account.withholding', string='Withholding AGIP',
                                     domain=[('type_aliquot', '=', 'agip')])


    @api.multi
    @api.depends('to_pay_move_line_ids.amount_residual', 'amount_payable', 'exempt_withholding', 'withholding_tax_base')
    def _compute_amount_agip_withholding(self):
        for rec in self:
            rec.amount_agip_withholding = 0.0
            if rec.company_id.calculate_pw_agip and not rec.exempt_withholding:
                aliquot = rec.partner_id._get_agip_update(rec.company_id, rec.date)
                if aliquot and rec.partner_type == "supplier":
                    if not self._context.get('no_update_withholding') and not rec.is_canceled:
                        #base_amount_agip_withholding = rec.calculate_base_amount_withholding()
                        base_amount_agip_withholding = rec.withholding_tax_base
                        if base_amount_agip_withholding > 0.0:
                            rec.amount_agip_withholding = base_amount_agip_withholding * aliquot.withholding_aliquot / 100
                    else:
                        rec.amount_agip_withholding = rec._get_amount_agip_w_pay()


    @api.multi
    @api.onchange('to_pay_move_line_ids', 'amount_payable', 'state', 'withholding_base_amount', 'amount_arba_withholding', 'amount_agip_withholding')
    def _onchange_to_pay_amount(self):
        super(AccountPaymentGroup, self)._onchange_to_pay_amount()
        for rec in self:
            if not rec.is_canceled:
                rec.to_pay_amount -= rec.amount_agip_withholding

    @api.multi
    @api.depends('amount_payable', 'unreconciled_amount', 'withholding_base_amount', 'amount_arba_withholding', 'amount_agip_withholding')
    def _compute_to_pay_amount(self):
        super(AccountPaymentGroup, self)._compute_to_pay_amount()
        for rec in self:
            if not rec.is_canceled:
                rec.to_pay_amount -= rec.amount_agip_withholding

    @api.multi
    @api.depends('payments_amount', 'withholding_base_amount', 'amount_arba_withholding', 'amount_agip_withholding','state')
    def _compute_amount_total_payable(self):
        super(AccountPaymentGroup, self)._compute_amount_total_payable()
        for rec in self:
            if rec.state == "draft" and not rec.is_canceled:
                rec.amount_total_payable += rec.amount_agip_withholding

    def create_withholding_payments(self):
        super(AccountPaymentGroup, self).create_withholding_payments()
        if self.amount_agip_withholding > 0.0 and not self.mapped('payment_ids').filtered(lambda x: x.is_withholding and x.type_aliquot == 'agip'):
            # self.write({'withholding_agip_aliquot':self.partner_id._get_agip_update(self.company_id, self.date).withholding_aliquot})
            # journal_id = self.env.ref('l10n_ar_perception_withholding_agip.account_journal_withholding_iibb_agip', False)
            journal_id = self.company_id.supplier_wh_agip_journal_id
            if not journal_id:
                raise UserError(_('You must comfigurate in the company the withholding AGIP journal.'))
            payment_method_id = self.env.ref('account.account_payment_method_manual_out', False)
            currency = self.currency_id
            amount_agip_withholding = self.amount_agip_withholding
            currency_journal = journal_id.currency_id or journal_id.company_id.currency_id
            if currency_journal and currency_journal != currency:
                # amount_agip_withholding = currency._convert(self.amount_agip_withholding, currency_journal, self.env.user.company_id,
                #                   self.date or fields.Date.today())
                amount_agip_withholding = self._convert_payment(currency, self.amount_agip_withholding,
                                                                currency_journal, self.env.user.company_id,
                                                                self.date or fields.Date.today())
                currency = currency_journal
            vals = {
                'journal_id': journal_id.id,
                'payment_method_id': payment_method_id.id,
                'payment_date': self.date,
                'payment_type': 'outbound',
                'currency_id': currency.id,
                'communication': _("Withholding IIBB Capital Federal"),
                'partner_id': self.partner_id.id,
                'partner_type': self.partner_type,
                'payment_group_company_id': self.company_id.id,
                # 'payment_group': True,
                'amount': amount_agip_withholding,
                'amount_aliquot_in_words': number_to_letter.to_word_no_decimal(amount_agip_withholding),
                'name': '',
                'is_withholding': True,
                'type_aliquot': 'agip',
                'state': 'draft'}

            self.payment_ids += self.env['account.payment'].create(vals)

    def _get_amount_agip_w_pay(self):
        self.ensure_one()
        amount = 0.0
        for rec in self.mapped('payment_ids').filtered(lambda x:x.is_withholding and
                                                                                x.type_aliquot == 'agip'):
            if rec.currency_id != self.currency_id:
                amount += rec.currency_id._convert(rec.amount, self.currency_id, self.env.user.company_id,
                                  self.date or fields.Date.today())
            else:
                amount += rec.amount
        return amount

    def _get_is_aliquot(self):
        result = super(AccountPaymentGroup, self)._get_is_aliquot()
        if not result and self.amount_agip_withholding > 0.0:
            return True
        return result

    def generate_withholding_payments(self):
        res = super(AccountPaymentGroup, self).generate_withholding_payments()
        ctx = dict(res._context)
        ctx.update({'amount_agip_withholding': self.amount_agip_withholding})
        return res.with_context(ctx)

    def create_withholding(self):
        res = super(AccountPaymentGroup, self).create_withholding()
        for rec in self:
            if rec.amount_agip_withholding > 0.0 and rec.company_id.calculate_pw_agip:
                payment = self.mapped('payment_ids').filtered(lambda x:x.is_withholding and
                                                                                x.type_aliquot == 'agip')
                aliquot = rec.partner_id._get_agip_update(rec.company_id, rec.date)
                if payment:
                    invoices = rec.matched_move_line_ids.mapped('invoice_id')
                    regime_credit =  False
                    if invoices and not invoices.filtered(lambda x: not x.tipo_comprobante.comprobante_credito):
                        regime_credit = True
                    if not rec.withholding_agip_id:
                        name = self.env['ir.sequence'].with_context(ir_sequence_date=payment.payment_date).next_by_code(
                                                                        'account.payment.supplier.agip')
                        withholding = self.env['account.withholding'].create({'name': name,
                                                                             'withholding_amount':payment.amount,
                                                                             'withholding_agip_aliquot': aliquot.withholding_aliquot,
                                                                             'withholding_tax_base_real': rec.withholding_tax_base_real,
                                                                             'date': rec.date,
                                                                             'partner_id': rec.partner_id.id,
                                                                             'reference': rec.name,
                                                                             'payment_id': payment[0].id,
                                                                             'state': 'done',
                                                                             'type_aliquot':'agip',
                                                                             'regime_credit':regime_credit})
                        rec.withholding_agip_id = withholding.id
                    else:
                        rec.withholding_agip_id.write({
                            'withholding_amount': payment.amount,
                            'withholding_agip_aliquot': aliquot.withholding_aliquot,
                            'withholding_tax_base_real': rec.withholding_tax_base_real,
                            'date': rec.date,
                            'partner_id': rec.partner_id.id,
                            'reference': rec.name,
                            'payment_id': payment[0].id,
                            'state': 'done' if rec.withholding_agip_id.state != 'declared' else 'declared',
                            'regime_credit':regime_credit
                        })
        return res

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.withholding_agip_id and rec.withholding_agip_id.state == 'declared':
                raise UserError(_(
                    "You cannot delete a payment with declared withholdings."))
            elif rec.withholding_agip_id:
                rec.withholding_agip_id.unlink()
        return super(AccountPaymentGroup, self).unlink()

    @api.multi
    def cancel(self):
        for rec in self:
            if rec.withholding_agip_id and rec.withholding_agip_id.state == 'done':
                rec.withholding_agip_id.action_annulled()
        super(AccountPaymentGroup, self).cancel()


