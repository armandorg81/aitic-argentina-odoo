# -*- coding: utf-8 -*-
# © 2018 AITIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)


class AccountConfigSsettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_choose_payment_type = fields.Boolean(
        'Choose Payment Type on Payments',
        help='Used if you want let user choose payment type (inbound or '
        'outbound) when registering a payment from a payment group',
        implied_group='account_payment_group.group_choose_payment_type'
    )
