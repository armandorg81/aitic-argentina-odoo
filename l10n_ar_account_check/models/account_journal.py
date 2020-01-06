# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    checkbook_ids = fields.One2many(
        'account.checkbook',
        'journal_id',
        'Checkbooks',
    )

    @api.model
    def create(self, vals):
        rec = super(AccountJournal, self).create(vals)
        own_checks = self.env.ref(
            'l10n_ar_account_check.account_payment_method_own_check')
        if (own_checks in rec.outbound_payment_method_ids and
                not rec.checkbook_ids):
            rec._create_checkbook()
        return rec

    @api.one
    def _create_checkbook(self):
        """ Create a check sequence for the journal """
        checkbook = self.checkbook_ids.create({
            'journal_id': self.id,
        })
        checkbook.state = 'active'

    @api.model
    def _enable_own_check_on_bank_journals(self):
        """ Enables own checks payment method
            Called upon module installation via data file.
        """
        own_checks = self.env.ref(
            'l10n_ar_account_check.account_payment_method_own_check')
        domain = [('type', '=', 'bank')]
        force_company_id = self._context.get('force_company_id')
        if force_company_id:
            domain += [('company_id', '=', force_company_id)]
        bank_journals = self.search(domain)
        for bank_journal in bank_journals:
            if not bank_journal.checkbook_ids:
                bank_journal._create_checkbook()
            bank_journal.write({
                'outbound_payment_method_ids': [(4, own_checks.id, None)],
            })
