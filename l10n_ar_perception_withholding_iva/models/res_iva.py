# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResAliquot(models.Model):
    _name = 'res.aliquot'
    _inherit = "res.aliquot"

    type = fields.Selection(selection_add=[('iva', 'Perception/Withholding Iva')])
    calculate_perc_iva = fields.Boolean(related='company_id.calculate_perc_iva', readonly=True)
    calculate_wh_iva = fields.Boolean(related='company_id.calculate_wh_iva', readonly=True)


    @api.model
    def create(self, vals):
        res = super(ResAliquot, self).create(vals)
        if res.calculate_perc_iva and res.perception_aliquot > 0.0:
            tax_perception = self.env['account.tax'].search(
                [('is_perception', '=', True), ('type_aliquot', '=', 'iva'),
                 ('amount', '=', res.perception_aliquot)])
            if not tax_perception:
                self.env['account.tax'].create({
                    'name': _("Perception " + str(res.perception_aliquot) + "%"),
                    'is_perception': True,
                    'is_iva': False,
                    'type_tax_use': 'sale',
                    'description': "PIVA_" + str(res.perception_aliquot).replace('.', ''),
                    'amount': res.perception_aliquot,
                    'company_id': res.company_id.id,
                    'account_id': res.company_id.perc_iva_account_id.id,
                    'refund_account_id': res.company_id.perc_iva_account_id.id,
                    'type_aliquot': 'iva',
                })
        return res

    @api.multi
    def write(self, vals):
        result = super(ResAliquot, self).write(vals)
        for res in self:
            if vals.get('perception_aliquot', False):
                if res.calculate_perc_iva and res.perception_aliquot > 0.0:
                    tax_perception = self.env['account.tax'].search(
                        [('is_perception', '=', True), ('type_aliquot', '=', 'iva'),
                         ('amount', '=', res.perception_aliquot)])
                    if not tax_perception:
                        self.env['account.tax'].create({
                            'name': _("Perception " + str(res.perception_aliquot) + "%"),
                            'is_perception': True,
                            'is_iva': False,
                            'type_tax_use': 'sale',
                            'description': "PIVA_" + str(res.perception_aliquot).replace('.', ''),
                            'amount': res.perception_aliquot,
                            'company_id': res.company_id.id,
                            'account_id': res.company_id.perc_sf_account_id.id,
                            'refund_account_id': res.company_id.perc_sf_account_id.id,
                            'type_aliquot': 'iva',
                        })
        return res



