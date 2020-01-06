# -*- coding: utf-8 -*-
# © 2018 AITIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import UserError
import odoo.addons.l10n_ar_account_group_withholding.models.number_to_letter as number_to_letter
from odoo.addons import decimal_precision as dp

class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"

    amount_sf_withholding = fields.Float(string='Withhol. Santa Fe', readonly=True, store=True,
                                           compute='_compute_amount_sf_withholding', digits=dp.get_precision('Account'))
    withholding_sf_id = fields.Many2one('account.withholding', string='Withholding Santa Fe',
                                     domain=[('type_aliquot', '=', 'sf')])
    # article_id = fields.Many2one('article.section')
    # withholding_sf_aliquot = fields.Float(string='Withholding Santa Fe Aliquot', default=0.0)


    @api.multi
    @api.depends('to_pay_move_line_ids.amount_residual', 'amount_payable', 'exempt_withholding', 'withholding_tax_base')
    def _compute_amount_sf_withholding(self):
        for rec in self:
            rec.amount_sf_withholding = 0.0
            if rec.company_id.calculate_wh_sf and not rec.exempt_withholding:
                aliquot = rec.partner_id._get_sf_update(rec.company_id, rec.date)
                if aliquot and rec.partner_type == "supplier":
                    # rec.article_id = aliquot.article_wh_id
                    # rec.withholding_sf_aliquot = aliquot.withholding_aliquot
                    if not self._context.get('no_update_withholding') and not rec.is_canceled:
                        base_amount_sf_withholding = rec.withholding_tax_base
                        if base_amount_sf_withholding > 0.0 and (rec.company_id.amount_exempt_sf == 0.0 or (rec.amount_payable > rec.company_id.amount_exempt_sf)):
                            rec.amount_sf_withholding = base_amount_sf_withholding * aliquot.withholding_aliquot / 100
                    else:
                        rec.amount_sf_withholding = rec._get_amount_sf_w_pay()

    @api.multi
    @api.onchange('to_pay_move_line_ids', 'amount_payable', 'state', 'withholding_base_amount', 'amount_sf_withholding')
    def _onchange_to_pay_amount(self):
        super(AccountPaymentGroup, self.sudo())._onchange_to_pay_amount()
        for rec in self:
            if not rec.is_canceled:
                rec.to_pay_amount -= rec.amount_sf_withholding

    @api.multi
    @api.depends('amount_payable', 'unreconciled_amount', 'partner_id', 'withholding_base_amount', 'amount_sf_withholding')
    def _compute_to_pay_amount(self):
        super(AccountPaymentGroup, self.sudo())._compute_to_pay_amount()
        for rec in self:
            if not rec.is_canceled:
                rec.to_pay_amount -= rec.amount_sf_withholding

    #@api.multi
    #@api.onchange('selected_debt')
    #def _onchange_selected_debt(self):
    #    super(AccountPaymentGroup, self)._onchange_selected_debt()
    #    for rec in self:
    #        rec.selected_debt -= rec.amount_sf_withholding
    #        rec._onchange_amount_payable()

    @api.multi
    @api.depends('amount_payable')
    def _compute_payable_wtax(self):
        super(AccountPaymentGroup, self)._compute_payable_wtax()
        for rec in self:
            rec.amount_payable_wtax += rec.amount_sf_withholding

    @api.multi
    @api.depends('payments_amount', 'withholding_base_amount', 'amount_sf_withholding', 'state')
    def _compute_amount_total_payable(self):
        super(AccountPaymentGroup, self)._compute_amount_total_payable()
        for rec in self:
            if rec.state == "draft" and not rec.is_canceled:
                rec.amount_total_payable += rec.amount_sf_withholding

    def create_withholding_payments(self):
        super(AccountPaymentGroup, self).create_withholding_payments()
        if self.amount_sf_withholding > 0.0 and not self.mapped('payment_ids').filtered(lambda x: x.is_withholding and x.type_aliquot == 'sf'):
            # journal_id = self.env.ref('l10n_ar_perception_withholding.account_journal_withholding_iibb', False)
            journal_id = self.company_id.supplier_wh_sf_journal_id
            if not journal_id:
                raise UserError(_('You must configurate in the company the withholding Santa Fe journal.'))
            payment_method_id = self.env.ref('account.account_payment_method_manual_out', False)
            currency = self.currency_id
            amount_sf_withholding = self.amount_sf_withholding
            currency_journal = journal_id.currency_id or journal_id.company_id.currency_id
            if currency_journal and currency_journal != currency:
                # amount_sf_withholding = currency._convert(self.amount_sf_withholding, currency_journal,
                #                                             self.env.user.company_id,
                #                                             self.date or fields.Date.today())
                amount_sf_withholding = self._convert_payment(currency, self.amount_sf_withholding, currency_journal,
                                                              self.env.user.company_id, self.date or fields.Date.today())

            vals = {
                'journal_id': journal_id.id,
                'payment_method_id': payment_method_id.id,
                'payment_date': self.date,
                'payment_type': 'outbound',
                'currency_id': self.currency_id.id,
                'communication': _("Withholding IIBB Santa Fe"),
                'partner_id': self.partner_id.id,
                'partner_type': self.partner_type,
                'payment_group_company_id': self.company_id.id,
                # 'payment_group': True,
                'amount': amount_sf_withholding,
                'amount_aliquot_in_words': number_to_letter.to_word_no_decimal(amount_sf_withholding),
                'name': '',
                'is_withholding': True,
                'type_aliquot': 'sf',
                'state': 'draft'}

            self.payment_ids += self.env['account.payment'].create(vals)

    def _get_amount_sf_w_pay(self):
        self.ensure_one()
        return sum(pay.amount for pay in self.mapped('payment_ids').filtered(lambda x:x.is_withholding and
                                                                                x.type_aliquot == 'sf'))
    def _get_is_aliquot(self):
        result = super(AccountPaymentGroup, self)._get_is_aliquot()
        if not result and self.amount_sf_withholding > 0.0:
            return True
        return result

    def generate_withholding_payments(self):
        res = super(AccountPaymentGroup, self).generate_withholding_payments()
        ctx = dict(res._context)
        ctx.update({'amount_sf_withholding': self.amount_sf_withholding})
        return res.with_context(ctx)

    def create_withholding(self):
        res = super(AccountPaymentGroup, self).create_withholding()
        for rec in self:
            if rec.amount_sf_withholding > 0.0 and rec.company_id.calculate_wh_sf:
                payment = self.mapped('payment_ids').filtered(lambda x:x.is_withholding and
                                                                                x.type_aliquot == 'sf')
                aliquot = rec.partner_id._get_sf_update(rec.company_id, rec.date)
                if payment:
                    if not rec.withholding_sf_id:
                        name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.date).next_by_code(
                                                                                        'account.payment.supplier.sf')
                        withholding = self.env['account.withholding'].create({'name': name,
                                                                             'withholding_amount': payment.amount,
                                                                             'withholding_sf_aliquot': aliquot.withholding_aliquot,
                                                                             'withholding_tax_base_real': rec.withholding_tax_base_real,
                                                                             'date': rec.date,
                                                                             'partner_id': rec.partner_id.id,
                                                                             'reference': rec.name,
                                                                             'payment_id': payment[0].id,
                                                                             'state': 'done',
                                                                             'type_aliquot':'sf',
                                                                             'article_id':aliquot.article_wh_id.id})
                        rec.withholding_sf_id = withholding.id
                    else:
                        rec.withholding_sf_id.write({
                            'withholding_amount': payment.amount,
                            'withholding_sf_aliquot': aliquot.withholding_aliquot,
                            'withholding_tax_base_real': rec.withholding_tax_base_real,
                            'date': rec.date,
                            'partner_id': rec.partner_id.id,
                            'reference': rec.name,
                            'payment_id': payment[0].id,
                            'state': 'done' if rec.withholding_sf_id.state != 'declared' else 'declared',
                            'article_id':aliquot.article_wh_id.id
                        })
        return res

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.withholding_sf_id and rec.withholding_sf_id.state == 'declared':
                raise UserError(_(
                    "You cannot delete a payment with declared withholdings."))
            elif rec.withholding_sf_id:
                rec.withholding_sf_id.unlink()
        return super(AccountPaymentGroup, self).unlink()

    @api.multi
    def cancel(self):
        for rec in self:
            if rec.withholding_sf_id and rec.withholding_sf_id.state == 'done':
                rec.withholding_sf_id.action_annulled()
        super(AccountPaymentGroup, self).cancel()


