# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('date')
    def _onchange_date(self):
        '''On the form view, a change on the date will trigger onchange() on account.move
        but not on account.move.line even the date field is related to account.move.
        Then, trigger the _onchange_amount_currency manually.
        '''
        self.line_ids._onchange_amount_currency()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('amount_currency', 'currency_id')
    def _onchange_amount_currency(self):
        '''Recompute the debit/credit based on amount_currency/currency_id and date.
        However, date is a related field on account.move. Then, this onchange will not be triggered
        by the form view by changing the date on the account.move.
        To fix this problem, see _onchange_date method on account.move.
        '''
        for line in self:
            amount = line.amount_currency
            if line.currency_id and line.currency_id != line.company_currency_id or line.move_id.company_id.currency_id and amount != 0.0:
                amount = line.currency_id.with_context(date=line.date).compute(amount, line.company_currency_id or line.move_id.company_id.currency_id)
                line.debit = amount > 0 and amount or 0.0
                line.credit = amount < 0 and -amount or 0.0

    @api.multi
    def _update_check(self):
        """ Raise Warning to cause rollback if the move is posted, some entries are reconciled or the move is older than the lock date"""
        move_ids = set()
        for line in self:
            err_msg = _('Move name (id): %s (%s)') % (line.move_id.name, str(line.move_id.id))
            if line.move_id.state != 'draft':
                raise UserError(_(
                    'You cannot do this modification on a posted journal entry, you can just change some non legal fields. You must revert the journal entry to cancel it.\n%s.') % err_msg)
            if line.move_id.state != 'draft' and line.reconciled and not (line.debit == 0 and line.credit == 0):
                raise UserError(_(
                    'You cannot do this modification on a reconciled entry. You can just change some non legal fields or you must unreconcile first.\n%s.') % err_msg)
            if line.move_id.id not in move_ids:
                move_ids.add(line.move_id.id)
        self.env['account.move'].browse(list(move_ids))._check_lock_date()
        return True
