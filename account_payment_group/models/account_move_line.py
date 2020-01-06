# -*- coding: utf-8 -*-
# © 2018 AITIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from datetime import date
from odoo.tools import float_is_zero, float_compare
# from odoo.addons.account.models.account_move import AccountPartialReconcile as PartialReconcile


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    payment_group_matched_amount = fields.Monetary(compute='compute_payment_group_matched_amount',
                                                   currency_field='company_currency_id')
    payment_group_advance_amount = fields.Monetary(compute='compute_payment_group_advance_amount',
                                                   currency_field='company_currency_id', multi="payment_group_advance_amount")
    report_payment_group_advance_amount = fields.Monetary(compute='compute_payment_group_advance_amount',
                                                   currency_field='company_currency_id', multi="payment_group_advance_amount")
    payment_group_id = fields.Many2one(related='payment_id.payment_group_id', string='Payment Group')
    # amount_res_upd_save = fields.Monetary(string='Residual Amount',
    #                                     currency_field='company_currency_id',
    #                                      help="The residual amount on a journal item expressed in the company currency.")
    amount_residual_update = fields.Monetary(string='Residual Amount', currency_field='company_currency_id',
                                             compute='_compute_amount_residual_update')
    amount_residual_currency_update = fields.Monetary(string='Residual Amount Currency', currency_field='company_currency_id',
                                             compute='_compute_amount_residual_currency_update')
    report_pg_advance_amount_currency = fields.Monetary(compute='compute_payment_group_advance_amount',
                                                   currency_field='currency_id', multi="payment_group_advance_amount")


    @api.multi
    def action_open_related_invoice(self):
        self.ensure_one()
        record = self.invoice_id
        if not record:
            return False
        if record.type in ['in_refund', 'in_invoice']:
            view_id = self.env.ref('account.invoice_supplier_form').id
        else:
            view_id = self.env.ref('account.invoice_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': record._name,
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': record.id,
            'view_id': view_id,
        }

    @api.multi
    @api.depends('amount_residual')
    def compute_payment_group_matched_amount(self):
        """
        """
        payment_group_id = self._context.get('payment_group_id')
        if not payment_group_id:
            return False
        payments = self.env['account.payment.group'].browse(
            payment_group_id).payment_ids
        payment_move_lines = payments.mapped('move_line_ids')
        payment_partial_lines = self.env[
            'account.partial.reconcile'].search([
                '|',
                ('credit_move_id', 'in', payment_move_lines.ids),
                ('debit_move_id', 'in', payment_move_lines.ids),
            ])
        for rec in self:
            matched_amount = 0.0
            for pl in (rec.matched_debit_ids + rec.matched_credit_ids):
                if pl in payment_partial_lines:
                    matched_amount += pl.amount
            rec.payment_group_matched_amount = matched_amount

    @api.multi
    def compute_payment_group_advance_amount(self):
        payment_group_id = self._context.get('payment_group_id')
        if not payment_group_id:
            return False

        for rec in self:
            payments = self.env['payment.group.advance.move'].search([('move_line_id', '=', rec.id),
                                                                      ('payment_group_id', '=', payment_group_id)])
            if payments:
                rec.payment_group_advance_amount = sum(payments.mapped('payment_group_advance_amount'))
                pg_advance_amount_currency = sum(payments.mapped('pg_advance_amount_currency'))
                if pg_advance_amount_currency == 0.0 and rec.currency_id != rec.company_currency_id:
                    for pay in payments:
                        # pg_advance_amount_currency += rec.company_currency_id.with_context(
                        #     date=payments.payment_group_id.date).compute(
                        #     pay.payment_group_advance_amount, rec.currency_id)
                        company = pay.company_id or self.env.user.company_id
                        pg_advance_amount_currency += rec.company_currency_id._convert(pay.payment_group_advance_amount,
                                                                                       rec.currency_id, company,
                                                                                       pay.payment_group_id.date or fields.Date.today())

                if rec.invoice_id:
                    rec.report_payment_group_advance_amount = rec.payment_group_advance_amount > 0 and rec.payment_group_advance_amount or rec.payment_group_advance_amount*-1
                    rec.report_pg_advance_amount_currency = pg_advance_amount_currency > 0 and pg_advance_amount_currency or pg_advance_amount_currency * -1
                else:
                    rec.report_payment_group_advance_amount = rec.payment_group_advance_amount < 0 and rec.payment_group_advance_amount or rec.payment_group_advance_amount * -1
                    rec.report_pg_advance_amount_currency = pg_advance_amount_currency < 0 and pg_advance_amount_currency or pg_advance_amount_currency * -1


    @api.multi
    @api.depends('amount_residual')
    def _compute_amount_residual_update(self):
        payment_group_id = self._context.get('payment_group_id')
        for rec in self:
            amount_residual_update = rec.amount_residual
            if rec.invoice_id and payment_group_id:
                invoice_groups = self.env['account.invoice.group'].search([('invoice_id', '=', rec.invoice_id.id),
                                                                      ('payment_group_id', '=', payment_group_id)])
                payment_group = self.env['account.payment.group'].browse(payment_group_id)
                sign = payment_group.partner_type == 'supplier' and -1.0 or 1.0
                if invoice_groups:
                    advance_amount_company = invoice_groups.get_invoice_advance_amount_company()
                    if rec.payment_group_matched_amount:
                        advance_amount_company -= rec.payment_group_matched_amount

                    to_pay_move_line_ids = payment_group.to_pay_move_line_ids.filtered(lambda x:x != rec)
                    if rec.matched_debit_ids:
                        matched_debit_ids = rec.matched_debit_ids.filtered(lambda x:x.debit_move_id in to_pay_move_line_ids)
                        if matched_debit_ids:
                            for matched_debit in matched_debit_ids:
                                advance_amount_company -= matched_debit.amount
                    if rec.matched_credit_ids:
                        matched_credit_ids = rec.matched_credit_ids.filtered(lambda x:x.debit_move_id in to_pay_move_line_ids)
                        if matched_credit_ids:
                            for credit_move_id in matched_credit_ids:
                                advance_amount_company -= credit_move_id.amount
                    amount_residual_update = (advance_amount_company) * sign
            rec.amount_residual_update = amount_residual_update

    @api.multi
    @api.depends('amount_residual', 'amount_residual_update')
    def _compute_amount_residual_currency_update(self):
        for rec in self:
            if rec.currency_id and rec.amount_residual_update != rec.amount_residual:
                # rec.amount_residual_currency_update = rec.currency_id.with_context(date=rec.date).compute(rec.amount_residual_update,
                #                                                                     rec.company_id.currency_id)
                rec.amount_residual_currency_update = rec.currency_id._convert(rec.amount_residual_update,
                                                                               rec.company_id.currency_id,
                                                                               rec.company_id,
                                                                               rec.date or fields.Date.today())
            else:
                rec.amount_residual_currency_update = rec.amount_residual_currency

    def _get_pair_to_reconcile(self):
        if self[0].company_id.arg_sortdate:
            field = self[0].account_id.currency_id and 'amount_residual_currency' or 'amount_residual'
            rounding = self[0].company_id.currency_id.rounding
            if self[0].currency_id and all([x.amount_currency and x.currency_id == self[0].currency_id for x in self]):
                field = 'amount_residual_currency'
                rounding = self[0].currency_id.rounding
            if self._context.get('skip_full_reconcile_check') == 'amount_currency_excluded':
                field = 'amount_residual'
            elif self._context.get('skip_full_reconcile_check') == 'amount_currency_only':
                field = 'amount_residual_currency'
            sorted_moves = sorted(self, key=lambda a: a.date_maturity)
            debit = credit = False
            for aml in sorted_moves:
                if credit and debit:
                    break
                if float_compare(aml[field], 0, precision_rounding=rounding) == 1 and not debit:
                    debit = aml
                elif float_compare(aml[field], 0, precision_rounding=rounding) == -1 and not credit:
                    credit = aml
            return debit, credit
        else:
            return super(AccountMoveLine, self)._get_pair_to_reconcile()

    @api.multi
    def auto_reconcile_lines(self):
        # Create list of debit and list of credit move ordered by date-currency
        debit_moves = self.filtered(lambda r: r.debit != 0 or r.amount_currency > 0)
        credit_moves = self.filtered(lambda r: r.credit != 0 or r.amount_currency < 0)
        debit_moves = debit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
        credit_moves = credit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
        # Compute on which field reconciliation should be based upon:
        field = 'amount_residual_currency' if self[0].account_id.currency_id and self[0].account_id.currency_id != self[0].company_id.currency_id else 'amount_residual'
        # if all lines share the same currency, use amount_residual_currency to avoid currency rounding error
        if self[0].currency_id and all([x.amount_currency and x.currency_id == self[0].currency_id for x in self]):
            field = 'amount_residual_currency'
        #Si hay que reconciliar por las lineas modificadas del pago
        if self._context.get('field_reconcile', False):
            field = self._context['field_reconcile']
        # Reconcile lines
        ret = self._reconcile_lines(debit_moves, credit_moves, field)
        return ret

    @api.multi
    def _reconcile_lines(self, debit_moves, credit_moves, field):
        """ This function loops on the 2 recordsets given as parameter as long as it
            can find a debit and a credit to reconcile together. It returns the recordset of the
            account move lines that were not reconciled during the process.
        """
        (debit_moves + credit_moves).read([field])
        to_create = []
        cash_basis = debit_moves and debit_moves[0].account_id.internal_type in ('receivable', 'payable') or False
        cash_basis_percentage_before_rec = {}
        dc_vals = {}
        while (debit_moves and credit_moves):
            debit_move = debit_moves[0]
            credit_move = credit_moves[0]
            company_currency = debit_move.company_id.currency_id
            # We need those temporary value otherwise the computation might be wrong below
            if field == 'amount_residual_update':
                temp_amount_residual = min(debit_move.amount_residual_update, -credit_move.amount_residual_update)
                temp_amount_residual_currency = min(debit_move.amount_residual_currency_update,
                                                    -credit_move.amount_residual_currency_update)
            else:
                temp_amount_residual = min(debit_move.amount_residual, -credit_move.amount_residual)
                temp_amount_residual_currency = min(debit_move.amount_residual_currency,
                                                    -credit_move.amount_residual_currency)
            dc_vals[(debit_move.id, credit_move.id)] = (debit_move, credit_move, temp_amount_residual_currency)
            amount_reconcile = min(debit_move[field], -credit_move[field])

            # Remove from recordset the one(s) that will be totally reconciled
            # For optimization purpose, the creation of the partial_reconcile are done at the end,
            # therefore during the process of reconciling several move lines, there are actually no recompute performed by the orm
            # and thus the amount_residual are not recomputed, hence we have to do it manually.
            if amount_reconcile == debit_move[field]:
                debit_moves -= debit_move
            else:
                debit_moves[0].amount_residual -= temp_amount_residual
                debit_moves[0].amount_residual_currency -= temp_amount_residual_currency
                if field == 'amount_residual_update' and debit_move.account_id.internal_type == 'receivable':
                    debit_moves[0].amount_residual_update -= temp_amount_residual

            if amount_reconcile == -credit_move[field]:
                credit_moves -= credit_move
            else:
                credit_moves[0].amount_residual += temp_amount_residual
                credit_moves[0].amount_residual_currency += temp_amount_residual_currency
                if field == 'amount_residual_update' and debit_move.account_id.internal_type == 'payable':
                    credit_moves[0].amount_residual_update -= temp_amount_residual
            # Check for the currency and amount_currency we can set
            currency = False
            amount_reconcile_currency = 0
            if field == 'amount_residual_currency':
                currency = credit_move.currency_id.id
                amount_reconcile_currency = temp_amount_residual_currency
                amount_reconcile = temp_amount_residual

            if field == 'amount_residual_update' and temp_amount_residual_currency != 0.0:
                currency = credit_move.currency_id.id
                amount_reconcile_currency = temp_amount_residual_currency

            if cash_basis:
                tmp_set = debit_move | credit_move
                cash_basis_percentage_before_rec.update(tmp_set._get_matched_percentage())

            to_create.append({
                'debit_move_id': debit_move.id,
                'credit_move_id': credit_move.id,
                'amount': amount_reconcile,
                'amount_currency': amount_reconcile_currency,
                'currency_id': currency,
            })

        cash_basis_subjected = []
        part_rec = self.env['account.partial.reconcile']
        with self.env.norecompute():
            for partial_rec_dict in to_create:
                debit_move, credit_move, amount_residual_currency = dc_vals[
                    partial_rec_dict['debit_move_id'], partial_rec_dict['credit_move_id']]
                # /!\ NOTE: Exchange rate differences shouldn't create cash basis entries
                # i. e: we don't really receive/give money in a customer/provider fashion
                # Since those are not subjected to cash basis computation we process them first
                if not amount_residual_currency and debit_move.currency_id and credit_move.currency_id:
                    part_rec.create(partial_rec_dict)
                else:
                    cash_basis_subjected.append(partial_rec_dict)

            for after_rec_dict in cash_basis_subjected:
                new_rec = part_rec.create(after_rec_dict)
                if cash_basis:
                    new_rec.create_tax_cash_basis_entry(cash_basis_percentage_before_rec)
        self.recompute()

        return debit_moves + credit_moves

class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    @api.model
    def create_exchange_rate_entry(self, aml_to_fix, move):
        """
        Automatically create a journal items to book the exchange rate
        differences that can occur in multi-currencies environment. That
        new journal item will be made into the given `move` in the company
        `currency_exchange_journal_id`, and one of its journal items is
        matched with the other lines to balance the full reconciliation.

        :param aml_to_fix: recordset of account.move.line (possible several
            but sharing the same currency)
        :param move: account.move
        :return: tuple.
            [0]: account.move.line created to balance the `aml_to_fix`
            [1]: recordset of account.partial.reconcile created between the
                tuple first element and the `aml_to_fix`
        """
        partial_rec = self.env['account.partial.reconcile']
        aml_model = self.env['account.move.line']

        created_lines = self.env['account.move.line']
        for aml in aml_to_fix:
            # create the line that will compensate all the aml_to_fix
            line_to_rec = aml_model.with_context(check_move_validity=False).create({
                'name': _('Currency exchange rate difference'),
                'debit': aml.amount_residual < 0 and -aml.amount_residual or 0.0,
                'credit': aml.amount_residual > 0 and aml.amount_residual or 0.0,
                'account_id': aml.account_id.id,
                'move_id': move.id,
                'currency_id': aml.currency_id.id,
                'amount_currency': 0.0,
                'partner_id': aml.partner_id.id,
            })
            # create the counterpart on exchange gain/loss account
            exchange_journal = move.company_id.currency_exchange_journal_id
            aml_model.with_context(check_move_validity=False).create({
                'name': _('Currency exchange rate difference'),
                'debit': aml.amount_residual > 0 and aml.amount_residual or 0.0,
                'credit': aml.amount_residual < 0 and -aml.amount_residual or 0.0,
                'account_id': aml.amount_residual > 0 and exchange_journal.default_debit_account_id.id or exchange_journal.default_credit_account_id.id,
                'move_id': move.id,
                'currency_id': aml.currency_id.id,
                'amount_currency': 0.0,
                'partner_id': aml.partner_id.id,
            })

            # reconcile all aml_to_fix
            partial_rec |= self.create(
                self._prepare_exchange_diff_partial_reconcile(
                    aml=aml,
                    line_to_reconcile=line_to_rec,
                    currency=aml.currency_id or False)
            )
            created_lines |= line_to_rec
        return created_lines, partial_rec




