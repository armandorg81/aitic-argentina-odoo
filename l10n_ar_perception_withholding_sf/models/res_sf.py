# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResAliquot(models.Model):
    _name = 'res.aliquot'

    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        ondelete='cascade',
        default=lambda self: self.env.user.company_id.id
    )
    date_update = fields.Date(string='Update date', default=fields.Date.today())
    perception_aliquot = fields.Float(string='Perception Aliquot', default=0.0)
    withholding_aliquot = fields.Float(string='Withholding Aliquot', default=0.0)
    type = fields.Selection([('sf', 'IIBB Santa Fe')], default='sf')
    article_perc_id = fields.Many2one('article.section', string='Perception Regimen')
    article_wh_id = fields.Many2one('article.section', string=' Withholding Regimen')
    active = fields.Boolean('Active', default=True)
    calculate_perc_sf = fields.Boolean(related='company_id.calculate_perc_sf', readonly=True)
    calculate_wh_sf = fields.Boolean(related='company_id.calculate_wh_sf', readonly=True)
    jurisdiction_id = fields.Many2one('jurisdiction', string='Jurisdiction', related='company_id.jurisdiction_id')

    @api.model
    def create(self, vals):
        res = super(ResAliquot, self).create(vals)
        if res.calculate_perc_sf and res.perception_aliquot > 0.0:
            tax_perception = self.env['account.tax'].search(
                [('is_perception', '=', True), ('type_aliquot', '=', 'sf'),
                 ('amount', '=', res.perception_aliquot)])
            if not tax_perception:
                self.env['account.tax'].create({
                    'name': _("Perception Santa Fe " + str(res.perception_aliquot) + "%"),
                    'is_perception': True,
                    'is_iva': False,
                    'type_tax_use': 'sale',
                    'description': "PSF_" + str(res.perception_aliquot).replace('.', ''),
                    'amount': res.perception_aliquot,
                    'company_id': res.company_id.id,
                    'account_id': res.company_id.perc_sf_account_id.id,
                    'refund_account_id': res.company_id.perc_sf_account_id.id,
                    'type_aliquot': 'sf',
                })
        return res

    @api.multi
    def write(self, vals):
        result = super(ResAliquot, self).write(vals)
        for res in self:
            if vals.get('perception_aliquot', False):
                if res.calculate_perc_sf and res.perception_aliquot > 0.0:
                    tax_perception = self.env['account.tax'].search(
                        [('is_perception', '=', True), ('type_aliquot', '=', 'sf'),
                         ('amount', '=', res.perception_aliquot)])
                    if not tax_perception:
                        self.env['account.tax'].create({
                            'name': _("Perception Santa Fe " + str(res.perception_aliquot) + "%"),
                            'is_perception': True,
                            'is_iva': False,
                            'type_tax_use': 'sale',
                            'description': "PSF_" + str(res.perception_aliquot).replace('.', ''),
                            'amount': res.perception_aliquot,
                            'company_id': res.company_id.id,
                            'account_id': res.company_id.perc_sf_account_id.id,
                            'refund_account_id': res.company_id.perc_sf_account_id.id,
                            'type_aliquot': 'sf',
                        })
        return res



