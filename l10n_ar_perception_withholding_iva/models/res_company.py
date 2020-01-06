# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.addons import decimal_precision as dp
_logger = logging.getLogger(__name__)
import os


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def supplier_wh_iva_journal_id(self):
        companies = self.search([])
        if len(companies) != 1:
            wh_journal = False
        else:
            wh_journal = self.env.ref('l10n_ar_perception_withholding_iva.account_journal_withholding_iibb_iva',
                                      False)
            if not wh_journal:
                wh_journal = self.env['account.journal'].search([('code', '=', 'WHIVA')])
        return wh_journal and wh_journal.id or False

    @api.model
    def get_perc_iva_account_id(self):
        wh_account = self.env.ref('l10n_ar_perception_withholding_iva.account_account_20105012', False)
        return wh_account and wh_account.id or False


    calculate_perc_iva = fields.Boolean('Perception agent IVA', help="The company is perception agent.",
                                     default=True)

    perc_iva_account_id = fields.Many2one('account.account', 'Perception account IVA', default=get_perc_iva_account_id,
                                             help="Account where the value of the perception will be reflected in the customer invoice.")

    calculate_wh_iva = fields.Boolean('Withholding agent IVA', help="The company is withholding agent.",
                                     default=True)
    supplier_wh_iva_journal_id = fields.Many2one('account.journal', string="Withholding journal IVA",
                                                  domain=[('type', '=', 'bank')], default=supplier_wh_iva_journal_id)
    amount_exempt_iva = fields.Float(string='Amount exempt iva', digits=dp.get_precision('Account'))




