# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import float_is_zero
from odoo import api
from odoo import SUPERUSER_ID


def update_cuit(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    partner_ids = env['res.partner'].search([
        ('documento_id', '=', env.ref('l10n_ar_base.tipo_documento_80').id),
        ('cuit', 'not like', '-')
    ])

    for p in partner_ids:
        p._comprueba_cuit()

def migrate(cr, version):
    update_cuit(cr)
