# coding: utf-8
import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    type_aliquot = fields.Selection(selection_add=[('agip', 'IIBB Capital Federal')])





