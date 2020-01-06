# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from datetime import datetime

class ResCompanyWithholding(models.Model):
    _inherit="res.company"

    # @api.model
    # def _get_supplier_wh_account(self):
    #     journal = self.env['account.journal'].browse(self._get_supplier_wh_account)
    #     if journal and journal.default_debit_account_id:
    #         wh_account = journal.default_debit_account_id.id
    #     else:
    #         wh_account = self.env.ref('account_account214000',False)
    #         if not wh_account:
    #             wh_account = self.env['account.account'].search([('code','=','214000')])
    #         return wh_account and wh_account.id or False
    branch_number = fields.Char(string='Branch number withholding')

    @api.model
    def _get_supplier_wh_journal(self):
        companies = self.search([])
        if len(companies) != 1:
            wh_journal = False
        else:
            wh_journal = self.env.ref('l10n_ar_account_group_withholding.account_journal_withholding',False)
            if not wh_journal:
                wh_journal = self.env['account.account'].search([('code','=','WH'), ('company_id','=',self.id)])
        return wh_journal and wh_journal.id or False

    # supplier_wh_account_id = fields.Many2one('account.account', 'Cuenta de retención', default=_get_supplier_wh_account,
    #     help="Cuenta donde se reflejará el valor de la retención en el pago de proveedor")
    supplier_wh_journal_id = fields.Many2one('account.journal', string="Retention journal",
                                                   domain=[('type', '=', 'bank')], default=_get_supplier_wh_journal)

    calculate_wh = fields.Boolean('Calculate withholding', help="Calculate withholding in payment to suppliers", default=True)
    regime_wh = fields.Boolean('Regime withholding', help="Mark if the calculation of monthly accumulated retention is by regime", default=False)
