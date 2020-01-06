# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    rejected_check_account_id = fields.Many2one(
        'account.account',
        'Rejected Check Account',
        help='Rejection Checks account, for eg. "Rejected Checks"',
    )
    deferred_check_account_id = fields.Many2one(
        'account.account',
        'Deferred Check Account',
        help='Deferred Checks account, for eg. "Deferred Checks"',
    )
    holding_check_account_id = fields.Many2one(
        'account.account',
        'Holding Check Account',
        help='Holding Checks account for third checks, '
        'for eg. "Holding Checks"',
    )
    sale_check_account_id = fields.Many2one(
        'account.account',
        'Account for the Sale of Check',
        help='Account where the balance of the debt contracted with the buyer of the check is recorded.',
    )

    @api.multi
    def _get_check_account(self, type):
        self.ensure_one()
        if type == 'holding':
            type_account = _('holding')
            account = self.holding_check_account_id
        elif type == 'rejected':
            type_account = _('rejected')
            account = self.rejected_check_account_id
        elif type == 'deferred':
            type_account = _('deferred')
            account = self.deferred_check_account_id
        elif type == 'selled':
            type_account = _('selled')
            account = self.sale_check_account_id
        else:
            raise UserError(_("Type %s not implemented!"))
        if not account:
            raise UserError(_(
                'No checks %s account defined for company %s'
            ) % (type_account, self.name))
        return account
