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
    def supplier_wh_sf_journal_id(self):
        companies = self.search([])
        if len(companies) != 1:
            wh_journal = False
        else:
            wh_journal = self.env.ref('l10n_ar_perception_withholding_sf.account_journal_withholding_iibb_sf',
                                      False)
            if not wh_journal:
                wh_journal = self.env['account.journal'].search([('code', '=', 'WHSF')])
        return wh_journal and wh_journal.id or False

    @api.model
    def get_perc_sf_account_id(self):
        wh_account = self.env.ref('l10n_ar_perception_withholding_sf.account_account_201050110', False)
        return wh_account and wh_account.id or False

    jurisdiction_id = fields.Many2one('jurisdiction', string='Jurisdiction')
    calculate_perc_sf = fields.Boolean('Santa Fe perception agent', help="The company is Santa Fe perception agent.",
                                     default=False)
    article_perception_id = fields.Many2one('article.section', string='Article/Section by retaining',
                                             domain=[('type', '=', 'company'), ('concept', '=', 'perception')])
    perc_sf_account_id = fields.Many2one('account.account', 'Perception account  IIBB Santa fe', default=get_perc_sf_account_id,
                                             help="Account where the value of the Santa Fe perception will be reflected in the customer invoice.")
    amount_exempt_perc_sf = fields.Float(string='Amount exempt sf', digits=dp.get_precision('Account'))
    # amount_exempt_sf = fields.Float(string='Amount exempt sf', digits=dp.get_precision('Account'))

    calculate_wh_sf = fields.Boolean('Santa Fe withholding agent', help="The company is Santa Fe withholding agent.",
                                     default=True)
    supplier_wh_sf_journal_id = fields.Many2one('account.journal', string="Withholding journal IIBB Santa Fe",
                                                  domain=[('type', '=', 'bank')], default=supplier_wh_sf_journal_id)
    article_withholding_id = fields.Many2one('article.section', string='Article/Section by retaining',
                                             domain=[('type', '=', 'company'), ('concept', '=', 'withholding')])
    amount_exempt_sf = fields.Float(string='Amount exempt sf', digits=dp.get_precision('Account'))



