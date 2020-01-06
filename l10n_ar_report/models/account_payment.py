# -*- coding: utf-8 -*-
import math
from odoo import api, fields, models, _
from .common import to_word

class L10nArReportAccountPayment(models.Model):
    _inherit = "account.payment"

    @api.multi
    @api.depends('amount')
    def _get_word_amount(self):
        for p in self:
            p.word_amount = to_word(math.floor(p.amount),None)
    
    word_amount = fields.Char('Importe de', compute="_get_word_amount",store=True)
