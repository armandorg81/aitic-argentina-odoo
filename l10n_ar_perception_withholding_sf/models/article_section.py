# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ArticleSection(models.Model):
    _description = "Article/Section"
    _name = 'article.section'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    type = fields.Selection([
        ('partner', 'Partner'),
        ('company', 'Company')],
        default='partner',
        string="Type")
    concept = fields.Selection([
        ('perception', 'Perception'),
        ('withholding', 'Withholding'),
        ('both', 'Both')],
        default='partner',
        string="Type")
    active = fields.Boolean('Active', default=True)
    jurisdiction_id = fields.Many2one('jurisdiction', string='Jurisdiction')

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            name = rec.code and '[%s] %s' % (rec.code,rec.name) or '%s' % rec.name
            result.append((rec.id, name))
        return result

class Jurisdiction(models.Model):
    _description = "Jurisdiction"
    _name = 'jurisdiction'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    perception_design = fields.Selection([
        ('n_1', 'Design Nro 1'),
        ('n_2', 'Design Nro 2')],
        default='n_1',
        string="Perception design")
    withholding_design = fields.Selection([
        ('n_1', 'Design Nro 1'),
        ('n_2', 'Design Nro 2')],
        default='n_1',
        string="Withholding design")

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            name = rec.code and '[%s] %s' % (rec.code,rec.name) or '%s' % rec.name
            result.append((rec.id, name))
        return result


