# -*- coding: utf-8 -*-
# © 2018 AITIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import UserError
import odoo.addons.l10n_ar_account_group_withholding.models.number_to_letter as number_to_letter
from odoo.addons import decimal_precision as dp

class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"

    amount_arba_withholding = fields.Float(string='Withhol. IIBB Prov. BS. AS.', readonly=True, store=True,
                                           compute='_compute_amount_arba_withholding', digits=dp.get_precision('Account'))
    withholding_arba_id = fields.Many2one('account.withholding', string='Withholding ARBA',
                                     domain=[('type_aliquot', '=', 'arba')])


    @api.multi
    @api.depends('to_pay_move_line_ids.amount_residual', 'date', 'amount_payable', 'exempt_withholding')
    def _compute_amount_arba_withholding(self):
        for rec in self:
            rec.amount_arba_withholding = 0.0
            if rec.company_id.calculate_pw_arba and not rec.exempt_withholding:
                aliquot = rec.partner_id._get_arba_update(rec.company_id, rec.date)
                if aliquot and rec.partner_type == "supplier":
                    if not self._context.get('no_update_withholding') and not rec.is_canceled:
                        #base_amount_arba_withholding = rec.calculate_base_amount_withholding()
                        base_amount_arba_withholding = rec.withholding_tax_base
                        if base_amount_arba_withholding > 0.0:
                            rec.amount_arba_withholding = base_amount_arba_withholding * aliquot.withholding_aliquot / 100
                    else:
                        rec.amount_arba_withholding = rec._get_amount_arba_w_pay()

    @api.multi
    @api.onchange('unreconciled_amount', 'amount_payable', 'state', 'withholding_base_amount', 'amount_arba_withholding')
    def _onchange_to_pay_amount(self):
        for rec in self:
            if not rec.is_canceled:
                rec.to_pay_amount = rec.amount_payable + rec.unreconciled_amount - rec.withholding_base_amount - self.amount_arba_withholding
            else:
                rec.to_pay_amount = rec.amount_payable + rec.unreconciled_amount

    @api.multi
    @api.depends('amount_payable', 'unreconciled_amount', 'partner_id', 'withholding_base_amount', 'amount_arba_withholding')
    def _compute_to_pay_amount(self):
        super(AccountPaymentGroup, self.sudo())._compute_to_pay_amount()
        for rec in self:
            if not rec.is_canceled:
                rec.to_pay_amount -= rec.amount_arba_withholding

    @api.multi
    @api.depends('payments_amount', 'withholding_base_amount', 'amount_arba_withholding', 'state')
    def _compute_amount_total_payable(self):
        super(AccountPaymentGroup, self)._compute_amount_total_payable()
        for rec in self:
            if rec.state == "draft" and not rec.is_canceled:
                rec.amount_total_payable += rec.amount_arba_withholding

    def create_withholding_payments(self):
        super(AccountPaymentGroup, self).create_withholding_payments()
        if self.amount_arba_withholding > 0.0 and not self.mapped('payment_ids').filtered(lambda x: x.is_withholding and x.type_aliquot == 'arba'):
            # journal_id = self.env.ref('l10n_ar_perception_withholding.account_journal_withholding_iibb', False)
            journal_id = self.company_id.supplier_wh_arba_journal_id
            if not journal_id:
                raise UserError(_('You must comfigurate in the company the withholding ARBA journal.'))
            payment_method_id = self.env.ref('account.account_payment_method_manual_out', False)
            currency = self.currency_id
            amount_arba_withholding = self.amount_arba_withholding
            currency_journal = journal_id.currency_id or journal_id.company_id.currency_id
            if currency_journal and currency_journal != currency:
                # amount_arba_withholding = currency._convert(self.amount_arba_withholding, currency_journal,
                #                                             self.env.user.company_id,
                #                                             self.date or fields.Date.today())
                amount_arba_withholding = self._convert_payment(currency, self.amount_arba_withholding,
                                                                currency_journal, self.env.user.company_id,
                                                                self.date or fields.Date.today())
                currency = currency_journal
            vals = {
                'journal_id': journal_id.id,
                'payment_method_id': payment_method_id.id,
                'payment_date': self.date,
                'payment_type': 'outbound',
                'currency_id': currency.id,
                'communication': _("Withholding IIBB Prov. BS. AS."),
                'partner_id': self.partner_id.id,
                'partner_type': self.partner_type,
                'payment_group_company_id': self.company_id.id,
                # 'payment_group': True,
                'amount': amount_arba_withholding,
                'amount_aliquot_in_words': number_to_letter.to_word_no_decimal(amount_arba_withholding),
                'name': '',
                'is_withholding': True,
                'type_aliquot': 'arba',
                'state': 'draft'}

            self.payment_ids += self.env['account.payment'].create(vals)

    def _get_amount_arba_w_pay(self):
        self.ensure_one()
        return sum(pay.amount for pay in self.mapped('payment_ids').filtered(lambda x:x.is_withholding and
                                                                                x.type_aliquot == 'arba'))
    def _get_is_aliquot(self):
        result = super(AccountPaymentGroup, self)._get_is_aliquot()
        if not result and self.amount_arba_withholding > 0.0:
            return True
        return result

    def generate_withholding_payments(self):
        res = super(AccountPaymentGroup, self).generate_withholding_payments()
        ctx = dict(res._context)
        ctx.update({'amount_arba_withholding': self.amount_arba_withholding})
        return res.with_context(ctx)

    def create_withholding(self):
        res = super(AccountPaymentGroup, self).create_withholding()
        for rec in self:
            if rec.amount_arba_withholding > 0.0 and rec.company_id.calculate_pw_arba:
                payment = self.mapped('payment_ids').filtered(lambda x:x.is_withholding and
                                                                                x.type_aliquot == 'arba')
                aliquot = rec.partner_id._get_arba_update(rec.company_id, rec.date)
                if payment:
                    if not rec.withholding_arba_id:
                        account_with = self.env['account.withholding'].search([('payment_id', '=', payment.id),
                                                                               ('type_aliquot', '=', 'arba')])
                        if not account_with:
                            name = self.env['ir.sequence'].with_context(ir_sequence_date=payment.payment_date).next_by_code(
                                                                            'account.payment.supplier.arba')
                            withholding = self.env['account.withholding'].create({'name': name,
                                                                                 'withholding_amount': payment.amount,
                                                                                 'withholding_arba_aliquot': aliquot.withholding_aliquot,
                                                                                 'withholding_tax_base_real': rec.withholding_tax_base_real,
                                                                                 'date': rec.date,
                                                                                 'partner_id': rec.partner_id.id,
                                                                                 'reference': rec.name,
                                                                                 'payment_id': payment[0].id,
                                                                                 'state': 'done',
                                                                                 'type_aliquot':'arba'})
                            rec.withholding_arba_id = withholding.id
                    else:
                        rec.withholding_arba_id.write({
                            'withholding_amount': payment.amount,
                             'withholding_arba_aliquot': aliquot.withholding_aliquot,
                             'withholding_tax_base_real': rec.withholding_tax_base_real,
                             'date': rec.date,
                             'partner_id': rec.partner_id.id,
                             'payment_id': payment[0].id,
                             'state': 'done' if rec.withholding_arba_id.state != 'declared' else 'declared',
                        })
        return res

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.withholding_arba_id and rec.withholding_arba_id.state == 'declared':
                raise UserError(_(
                    "You cannot delete a payment with declared withholdings."))
            elif rec.withholding_arba_id:
                rec.withholding_arba_id.unlink()
        return super(AccountPaymentGroup, self).unlink()

    @api.multi
    def cancel(self):
        for rec in self:
            if rec.withholding_arba_id and rec.withholding_arba_id.state == 'done':
                rec.withholding_arba_id.action_annulled()
        super(AccountPaymentGroup, self).cancel()



