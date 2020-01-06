# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class regimen_retencion(models.Model):
    _description = "Regimen de Retencion"
    _name = 'regimen.retencion'

    name = fields.Char('Código Régimen', translate=True)
    concepto = fields.Char('Conceptos sujeto a retención', translate=True)
    desc = fields.Text('Descripción', translate=True)
    por_ins = fields.Float('% para Inscriptos', translate=True)
    segun_escala_ins = fields.Boolean(string='Segun Escala Inscritos',default=False)
    por_no_ins = fields.Float('% para no Inscriptos', translate=True)
    segun_escala_nins = fields.Boolean(string='Segun Escala No Inscritos',default=False)
    montos_no_sujeto = fields.Float('Montos no sujetos a retención', translate=True)

    @api.multi
    def name_get(self):
        res = super(regimen_retencion, self).name_get()
        result = []
        for element in res:
            regimen_id = element[0]
            desc = self.browse(regimen_id).desc
            name = desc and '[%s] %s' % (element[1],desc) or '%s' % element[1]
            result.append((regimen_id, name))
        return result
