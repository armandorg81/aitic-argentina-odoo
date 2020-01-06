# -*- coding: utf-8 -*-
# © 2018 AITIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.multi
    def open_payments_action(self, payment_type, mode='tree'):
        ctx = self._context.copy()
        ctx.pop('group_by', None)
        ctx.update({
            'default_payment_type': payment_type,
            'default_journal_id': self.id,
            'journal_id': self.id,
            'is_create': True
        })
        if payment_type == 'transfer':
            # action_rec = self.env['ir.model.data'].xmlid_to_object(
            #     'account_payment_group.action_account_payments_transfer')
            # action = action_rec.read([])[0]
            [action] = self.env.ref('account_payment_group.action_account_payments_transfer').read()
            action['context'] = ctx
            action['domain'] = [('journal_id', '=', self.id),
                                ('payment_type', '=', payment_type)]
            if mode == 'form':
                action['views'] = [(self.env.ref('account_payment_group.view_account_payment_transfer_form').id, 'form')]
            return action
        else:
            if payment_type == 'outbound':
                action_ref = 'account.action_account_payments_payable'
            else:
                action_ref = 'account.action_account_payments'
            # action_rec = self.env['ir.model.data'].xmlid_to_object('account.action_account_payments')
            [action] = self.env.ref(action_ref).read()
            # if action_rec:
            # action = action_rec.read([])[0]
            action['context'] = ctx
            action['domain'] = [('journal_id', '=', self.id), ('payment_type', '=', payment_type)]
            if mode == 'form':
                action['views'] = [[False, 'form']]
            return action
