#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.osv.expression import get_unaccent_wrapper
import re


class res_partner(models.Model):
    _description = "Partner registered turns"
    _name = 'res.partner'
    _inherit = ['res.partner', 'mail.thread', 'mail.activity.mixin']

    # Variables
    cuit = fields.Char("Número Documento")
    ingresos_brutos = fields.Char("Ingresos Brutos", size=20)
    tipo_ingresos_brutos = fields.Selection(
        [('M','Convenio Multilateral'),
         ('L','Local'),
         ('NI','No inscripto, obligado a inscribirse'),
         ('N','No inscripto, no obligado a inscribirse'),
         ('E','Exento')],
        'Tipo de Ingresos Brutos', size=1)
    sede_convenio = fields.Integer(string='Sede de convenio')
    responsability_id = fields.Many2one("condicion.venta",string="Tipo Responsable")
    documento_id = fields.Many2one('tipo.documento',string="Tipo Documento")
    inscripto = fields.Boolean('Retencion Ganancias',help="Indica si al proveedor se le realizan retenciones de ganancias")
    fan_name = fields.Char("Referencia")
    factura = fields.Boolean("Contacto para Facturar", help="Si está marcado se podrá facturar.")
    payment_cbu = fields.Char("CBU")
    payment_cuenta_bancaria = fields.Char("Cuenta Bancaria")
    company_type = fields.Selection(default='company')
    is_company = fields.Boolean(default=True)
    comprobante_default = fields.Many2one('tipo.comprobante', string='Usar Tipo Comprobante Especial')
    property_product_pricelist = fields.Many2one(store=True)

    @api.multi
    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None):
        return super(res_partner, self.sudo()).message_subscribe(partner_ids=partner_ids,
                                                                 channel_ids=channel_ids,
                                                                 subtype_ids=subtype_ids)

    @api.model
    def check_mail_message_access(self, res_ids, operation, model_name=None):
        return super(res_partner, self.sudo()).check_mail_message_access(res_ids, operation, model_name=model_name)

    @api.model
    def create(self, vals):
        if vals.get('parent_id', False):
            vals['company_type'] = 'person'
        return super(res_partner, self).create(vals)

    @api.onchange('company_type')
    def onchange_company_type(self):
        if self.company_type == 'company':
            document_type = self.env['tipo.documento'].search([('name','=','CUIT')])
            if document_type:
                self.documento_id = document_type.id

    @api.multi
    def _aux_set_cuit(self, cuit_vals=False):
        self.ensure_one()
        result = {}
        if self.documento_id.name not in ['CUIT', 'CUIL']:
            ok = True
        else:
            ok = False
        if not ok:
            ok = True
            cuit = cuit_vals or str(self.cuit)
            # Aca removemos guiones, espacios y puntos para poder trabajar
            cuit = cuit.replace("-", "")  # Borramos los guiones
            cuit = cuit.replace(" ", "")  # Borramos los espacios
            cuit = cuit.replace(".", "")  # Borramos los puntos
            # Si no tiene 11 caracteres lo descartamos
            if len(cuit) != 11:
                ok = False
            # Solo resta analizar si todos los caracteres son numeros
            if not cuit.isdigit():
                ok = False
            # Despues de estas validaciones podemos afirmar
            if ok:
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
        if not ok:
            result['warning'] = {
                'title': _('Error'),
                'message': _('El CUIT/CUIL ingresado es invalido.')}
        else:
            if self.documento_id.name in ['CUIT', 'CUIL']:
                position = len(cuit) - 1
                cuit = cuit[0:2] + '-' + cuit[2:position] + '-' + cuit[position:]
                result['cuit'] = cuit
            else:
                result['cuit'] = self.cuit or ''
        return result

    @api.multi
    @api.onchange('cuit', 'documento_id')
    def _comprueba_cuit(self):
        if self.cuit and self.documento_id and self.documento_id.id in [self.env.ref('l10n_ar_base.tipo_documento_80').id,self.env.ref('l10n_ar_base.tipo_documento_86').id]:
            res = self._aux_set_cuit()
            if not res.get('warning', False):
                self.cuit = res.get('cuit')
            else:
                return res

    def _check_cuit(self, vals):
        if vals.get('cuit') and vals.get('documento_id', self.documento_id.id) in [self.env.ref('l10n_ar_base.tipo_documento_80').id,self.env.ref('l10n_ar_base.tipo_documento_86').id]:
            if self:
                cuit = vals.get('cuit')
                cuit = self._aux_set_cuit(cuit)
            else:
                neww_partner = self.new(vals)
                cuit = neww_partner._aux_set_cuit()
            if not cuit.get('warning', False):
                vals['cuit'] = cuit.get('cuit')
            else:
                raise ValidationError(cuit.get('warning').get('message'))

    @api.multi
    def write(self, vals):
        self._check_cuit(vals)
        return super(res_partner, self).write(vals)

    @api.model
    def create(self, vals):
        self._check_cuit(vals)
        return super(res_partner, self).create(vals)

    @api.onchange('company_type')
    def _get_state_company_type(self):
        if self.company_type == 'company':
            self.factura = True
        else:
            self.factura = False

    def _get_cuit(self):
        if self.cuit:
            if len(self.cuit) == 13:
                return self.cuit
            elif len(self.cuit) == 11:
                return self.cuit[:2] + '-' + self.cuit[2:10] + "-" + self.cuit[10:]
            else:
                return self.cuit[:2] + '-' + self.cuit[2:]
        elif self.parent_id:
            return self.parent_id._get_cuit()
        else:
            return False

    def _get_name(self):
        #algunas veces el display el commercial_company_name no toma el valor correcto, por eso voy a tomar como primera
        #opcion el nombre del padre cuando sean individual.
        #en local no logro generar el error, creo que es cuando se pierde la conexion con el server y vuelva a reconectar
        partner = self
        name = partner.name or ''

        if partner.company_name or partner.parent_id:
            if not name and partner.type in ['invoice', 'delivery', 'other']:
                name = dict(self.fields_get(['type'])['type']['selection'])[partner.type]
            if not partner.is_company:
                name = "%s, %s" % (partner.parent_id.name or partner.commercial_company_name, name)
                return name
        return super(res_partner, self)._get_name()


        """ Utility method to allow name_get to be overrided without re-browse the partner """
        partner = self
        name = partner.name or ''

        if partner.company_name or partner.parent_id:
            if not name and partner.type in ['invoice', 'delivery', 'other']:
                name = dict(self.fields_get(['type'])['type']['selection'])[partner.type]
            if not partner.is_company:
                name = "%s, %s" % (partner.commercial_company_name or partner.parent_id.name, name)
