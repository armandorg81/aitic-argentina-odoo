# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
import logging
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)


class AccountCheckbook(models.Model):

    _name = 'account.checkbook'
    _description = 'Account Checkbook'

    name = fields.Char(
        compute='_compute_name',
    )
    next_number = fields.Integer(
        'Next Number')
    own_check_subtype = fields.Selection(
        [('deferred', 'Deferred'), ('currents', 'Currents'), ('electronic','Electronic')],
        string='Own Check Subtype',
        #readonly=True,
        required=True,
        default='deferred',
        #states={'draft': [('readonly', False)]}
    )

    journal_id = fields.Many2one(
        'account.journal', 'Journal',
        help='Journal where it is going to be used',
        readonly=True,
        required=True,
        domain=[('type', '=', 'bank')],
        ondelete='cascade',
        context={'default_type': 'bank'},
        states={'draft': [('readonly', False)]}
    )
    to_number = fields.Integer(
        'To Number',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='If you set a number here, this checkbook will be automatically'
        ' set as used when this number is raised.'
    )
    own_check_ids = fields.One2many(
        'account.check',
        'checkbook_id',
        string='Own Checks',
        readonly=True,
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('active', 'In Use'), ('used', 'Used')],
        string='State',
        # readonly=True,
        default='draft',
        copy=False
    )
    block_manual_number = fields.Boolean(
        default=True,
        string='Block manual number?',
        help='Block user to enter manually another number than the suggested'
    )

    @api.one
    def update_next_number(self):
        next_number = self.next_number + 1
        if next_number > self.to_number and self.own_check_subtype != 'electronic':
            self.state = 'used'
        self.next_number = next_number

    @api.multi
    def _compute_name(self):
        for rec in self:
            if rec.own_check_subtype == 'deferred':
                name = _('Deferred Checks')
            elif rec.own_check_subtype == 'currents':
                name = _('Currents Checks')
            else:
                name = _('Electronic Checks')
            if rec.to_number:
                name += _(' up to %s') % rec.to_number
            rec.name = name

    @api.model
    def create(self, vals):
        if vals.get('own_check_subtype') and vals['own_check_subtype']:
            vals['block_manual_number'] = False
        rec = super(AccountCheckbook, self).create(vals)
        return rec

    @api.one
    def unlink(self):
        if self.mapped('own_check_ids'):
            raise ValidationError(
                _('You can drop a checkbook if it has been used on checks!'))
        return super(AccountCheckbook, self).unlink()
