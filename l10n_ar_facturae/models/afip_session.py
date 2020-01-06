# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductProduct(models.Model):
    _name = "afip.session"

    sign = fields.Char('Sign')
    token = fields.Char('Token')
    expirationTime = fields.Char('ExpirationTime')
    xml_tag = fields.Char('Tag')
    environment = fields.Selection([('T', 'Test'),
                                    ('P', 'Production')], string='Enviroment')
    company_id = fields.Many2one('res.company', 'Company',
        default=lambda self: self.env.user.company_id.id, index=1)
