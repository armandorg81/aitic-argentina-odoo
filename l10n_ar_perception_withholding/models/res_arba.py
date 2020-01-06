# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResArbaConfig(models.Model):
    _name = "res.arba.config"
    _description = 'ARBA Connection Config'

    name = fields.Char(string='Name', required=True)
    enviroment_type = fields.Selection([('homologation', 'Homologation'),
                                        ('production', 'Production')], string='Enviroment Type', required=True)
    url_connection = fields.Char('URL Connection', required=True)

class ResArbaActivity(models.Model):
    _name = "res.arba.activity"

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Number', required=True)
    period = fields.Selection([
        ('monthly', 'Monthly'),
        ('biweekly', 'Biweekly')],
        string='Period')
    type = fields.Selection([
        ('perception', 'Perception'),
        ('withholding', 'Withholding')],
        string='Type')

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = record.code + ' - ' + record.name
            result.append((record.id, name))
        return result


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
    )
    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    date_update = fields.Date(string='Update date', default=fields.Date.context_today)
    voucher_number = fields.Char(string='Voucher Number')
    hash_code = fields.Char(string='Hash Code')
    cuit_taxpayer = fields.Char(string='Cuit Taxpayer')
    perception_aliquot = fields.Float(string='Perception Aliquot', default=0.0)
    withholding_aliquot = fields.Float(string='Withholding Aliquot', default=0.0)
    perception_group = fields.Char(string='Perception Group')
    withholding_group = fields.Char(string='Withholding Group')
    type = fields.Selection([('arba', 'IIBB Prov. BS. AS.')], default='arba')
    active = fields.Boolean('Active', default=True)

class ResAliquotArba(models.Model):
    _name = 'res.aliquot.arba'

    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    date_update = fields.Date(string='Update date')
    cuit_taxpayer = fields.Char(string='Cuit Taxpayer')
    type_ci = fields.Char(string='Type of registered taxpayer')
    mark_hs = fields.Char(string='High brand')
    mark_aliq = fields.Char(string='Aliquot Brand')
    perception_aliquot = fields.Float(string='Perception Aliquot', default=0.0)
    withholding_aliquot = fields.Float(string='Withholding Aliquot', default=0.0)
    perception_group = fields.Char(string='Perception Group')
    withholding_group = fields.Char(string='Withholding Group')
