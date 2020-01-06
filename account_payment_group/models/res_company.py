# -*- coding: utf-8 -*-
# © 2018 AITIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    double_validation = fields.Boolean(
        'Double Validation on Payments?',
        translate=True,
        help='Use two steps validation on payments to suppliers'
    )
    arg_sortdate = fields.Boolean(string="Sort Date payments based on Due Date",translate=True)
