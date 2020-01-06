# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import datetime


class company_turns(models.Model):

    _description = "Company registered"
    _inherit = 'res.company'

    cuit = fields.Char("C.U.I.T", size=13)
    ingresos_brutos = fields.Char("Ingresos Brutos", size=12)
    start_date = fields.Date(string="Inicio de Actividades")
    tipo_responsable = fields.Many2one("condicion.venta",string="Tipo Responsable")
    documento_id = fields.Many2one('tipo.documento',string="Tipo Documento")
    invoice_line = fields.Integer(string='Max. Lineas en Facturas de Ventas', default=0, required=True)
    is_check_price_total = fields.Boolean(string='Checkear precio total de la linea', default=True)

    @api.multi
    @api.onchange('cuit')
    def _comprueba_cuit(self):
        ok = False
        if self.cuit:
            cuit = str(self.cuit)
            # Aca removemos guiones, espacios y puntos para poder trabajar
            cuit = cuit.replace("-", "")  # Borramos los guiones
            cuit = cuit.replace(" ", "")  # Borramos los espacios
            cuit = cuit.replace(".", "")  # Borramos los puntos
            # Si no tiene 11 caracteres lo descartamos
            if len(cuit) != 11:
                return False, cuit
            # Solo resta analizar si todos los caracteres son numeros
            if not cuit.isdigit():
                return False, cuit
            # Despues de estas validaciones podemos afirmar
            #   que contamos con 11 numeros
            # Aca comienza la magia
            base = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
            aux = 0
            for i in range(10):
                aux += int(cuit[i]) * base[i]
            aux = 11 - (aux % 11)
            if aux == 11:
                aux = 0
            elif aux == 10:
                aux = 9
            if int(cuit[10]) == aux:
                ok = True
            else:
                ok = False

            position = len(cuit) - 1
            cuit =  cuit[0:2] + '-' + cuit[2:position] + '-' + cuit[position:]
        if not ok:
            self.cuit = ''
        else:
            self.cuit = cuit

