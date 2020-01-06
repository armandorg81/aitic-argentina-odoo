# -*- coding: utf-8 -*-
# © 2018 AITIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.osv import expression
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import float_is_zero, float_compare
from odoo.tools.safe_eval import safe_eval
from lxml import etree

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def remove_move_reconcile(self):
        """ Undo a reconciliation """
        res = super(AccountMoveLine, self).remove_move_reconcile()
        if self.env.context.get('invoice_id', False) and self.env.context.get('group_payment_id', False):
            payment_group_id =self.env['account.payment.group'].browse(self.env.context.get('group_payment_id'))
            if payment_group_id:
                payment_group_id.group_invoice_ids.filtered(lambda x:
                                                x.invoice_id.id == self.env.context.get('invoice_id')).unlink()
        return res
