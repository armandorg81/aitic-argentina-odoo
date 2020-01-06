# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import base64
from odoo.tools import float_is_zero, float_round
import odoo.addons.decimal_precision as dp
from pyafipws3.wsaa import WSAA
from pyafipws3.wsfev1 import WSFEv1
from pyafipws3.wsfexv1 import WSFEX
from pyafipws3.wsbfev1 import WSBFEv1
from pyafipws3.pyi25 import PyI25
from odoo.exceptions import UserError, RedirectWarning, ValidationError, AccessError
from random import randint
import pytz
from pysimplesoap.client import SimpleXMLElement

class FacturaEAccountInvoice(models.Model):
    _inherit = "account.invoice"

    _sql_constraints = [
        ('number_uniq', 'unique(number, company_id, journal_id, type, refund_type, no_cae)', '¡El número de factura debe ser único por compañía!'),
    ]

    no_cae = fields.Char("CAE N°", size=20, copy=False)
    vence_date = fields.Date(string="Fecha de Vencimiento", copy=False)
    currency_rate = fields.Char('Tasa de Cambio', help="Tasa de cambio moneda, obtenida mediante webservice AFIP", readonly=True)
    state_dte = fields.Selection(
        [('created', 'Creado'),
         ('sent', 'Enviado'),
         ('accepted', 'Aceptado'),
         ('rejected', 'Rechazado'),
         ],
        string='Estatus DTE', index=True, readonly=True,
        default='created',
        track_visibility='onchange', copy=False,
        help=" * 'Created' Creadted in the system.\n"
             " * 'Impreso' Cuando se ha impreso el formulario de Registro de Viajeros.\n")
    requestXml = fields.Binary('Petición', attachment=True, help="Petición (.xml)", copy=False)
    requestXml_fname = fields.Char(string="Petición XML", copy=False)
    responseXml = fields.Binary('Respuesta', attachment=True, help="Respuesta (.xml)", copy=False)
    responseXml_fname = fields.Char(string="Respuesta XML", copy=False)
    cod_barra = fields.Char("Código", copy=False)
    off_cae = fields.Boolean('OffLine CAE', default=lambda self: self.env.user.company_id.off_cae)
    not_invoice = fields.Boolean(string='No Permitir Facturar', default=lambda self: self.env.user.company_id.not_invoice)
    port = fields.Char(string='Puerto')

    # Campos de Exportación

    es_exportacion = fields.Boolean('Es Exportación', compute='compute_es_exportacion')

    incoterms = fields.Selection(
        [('EXW', 'EXW'),
         ('FCA', 'FCA'),
         ('FAS', 'FAS'),
         ('FOB', 'FOB'),
         ('CFR', 'CFR'),
         ('CIF', 'CIF'),
         ('CPT', 'CPT'),
         ('CIP', 'CIP'),
         ('DAF', 'DAF'),
         ('DES', 'DES'),
         ('DEQ', 'DEQ'),
         ('DDU', 'DDU'),
         ('DDP', 'DDP'),
         ('DAP', 'DAP'),
         ('DAT', 'DAT')],
        'INCOTERMs', size=1, default='FOB')

    tipo_expo = fields.Selection(
        [('1', 'Exportación definitiva de Bienes'),
         ('2', 'Servicios'),
         ('4', 'Otros')],
        'Tipo de Exportación', size=1, default='1')

    permiso_existente = fields.Selection(
        [('S', 'Si'),
         ('N', 'No')],
        'Tiene Permiso de Embarque ', size=1, default='N', help='Indica si se posee documento aduanero de exportación (permiso de embarque)')

    amount_perception = fields.Monetary(string='Percep. IIBB',)
    anulacion = fields.Boolean(string='Anulación')
    comprobante_credito = fields.Boolean(string='Comprobante de Credito', compute='compute_comprobante_credito')

    @api.depends('tipo_comprobante')
    def compute_comprobante_credito(self):
        for invoice in self:
            invoice.comprobante_credito = invoice.tipo_comprobante and invoice.tipo_comprobante.comprobante_credito and True or False

    @api.depends('tipo_comprobante')
    def compute_es_exportacion(self):
        for invoice in self:
            if invoice.tipo_comprobante and invoice.tipo_comprobante.codigo in ['019','020','021']:
                invoice.es_exportacion = True
            else:
                invoice.es_exportacion = False

    @api.onchange('company_id')
    def onchange_off_cae(self):
        if self.company_id:
            self.off_cae = self.company_id.off_cae
            self.not_invoice = self.company_id.not_invoice
            self.online_mode_f = self.company_id.online_mode

    @api.onchange('punto_venta')
    def onchange_punto_venta(self):
        if not self.online_mode_f:
            self.num_comprobante = randint(11111111, 91111111)
            self.no_cae = randint(11111111111111111111, 91111111111111111111)
            self.vence_date = fields.Date.from_string(datetime.today())

    barcode_img = fields.Binary(
        copy=False,
        string='Código de Barras',
        help='Código de Barras PyI25')
    num_comprobante = fields.Char("Número de Comprobante", copy=False, size=8)
    online_mode_f = fields.Boolean('Online', default=lambda self: self.env.user.company_id.online_mode)
    cod_operacion = fields.Selection([
        ('0', 'No corresponde'),
        ('A', 'No alcanzado'),
        ('B', 'OPERAC CANJE / DEVOL IVA TURISTA'),
        ('E', 'OPERACIONES EXENTAS'),
        ('N', 'NO GRAVADO'),
        ('T', 'REINTEGRO DECRETO 1043/2016'),
        ('X', 'IMPORTACION DEL EXTERIOR'),
        ('Z', 'EXPORTACION ZONA FRANCA')
    ],
        string='Código Operación', index=True, default='0',
        track_visibility='onchange', copy=False)

    @api.multi
    def unlink(self):
        for invoice in self:
            if invoice.state not in ('draft', 'cancel'):
                raise UserError(_(
                    'No puede eliminar una factura que no sea borrador o cancelada. Deberías crear una nota de crédito en su lugar.'))
            elif (invoice.num_comprobante or invoice.no_cae) and invoice.type in ('out_invoice', 'out_refund'):
                raise UserError(_(
                    'No puede borrar una factura una vez validada (y que ha recibido un número). Puede devolverla a estado \"Borrador\", modificar su contenido y volverla a confirmar.'))
        return super(FacturaEAccountInvoice, self).unlink()

    @api.constrains('num_comprobante')
    def _check_comprobante(self):
        for inv in self:
            if inv.partner_id and inv.num_comprobante and inv.tipo_comprobante and inv.punto_venta_proveedor:
                invoices = inv.search([
                    ('partner_id', '=', inv.partner_id.id),
                    ('num_comprobante', '=', inv.num_comprobante),
                    ('type', 'in', ['in_invoice', 'in_refund']),
                    ('tipo_comprobante', '=', inv.tipo_comprobante.id),
                    ('punto_venta_proveedor', '=', inv.punto_venta_proveedor),
                ])
                if len([x.id for x in invoices]) > 1:
                    raise ValidationError(
                        "Ya existe un documento %s para este proveedor %s con punto de venta %s con el mismo numero de comprobante" % (
                        inv.tipo_comprobante.name, inv.partner_id.name, inv.punto_venta_proveedor))

    @api.model
    def get_concept_type(self, inv_lines):
        #  @param: lineas de factura
        #  @return 1: Productos, 2: Servicios, 3: Productos y Servicios
        #
        products = [x.product_id.id for x in inv_lines if (x.product_id.type in ['product', 'consu'])]
        service = [x.product_id.id for x in inv_lines if (x.product_id.type == 'service')]
        res = 3
        if len(products) > 0 and len(service) > 0:
            res = 3
        elif len(products) > 0 and len(service) == 0:
            res = 1
        elif len(products) == 0 and len(service) > 0:
            res = 2
        return res

    @api.model
    def check_path(self, path, flag):
        #  @param: path (ruta del archivo)
        #          flag (cert o key, indica a que ruta se refiere)
        #  @return True o error de validacion
        try:
            open(path)
        except:
            string = flag == 'cert' and 'del certificado' or 'de la llave privada'
            raise ValidationError("Error en la ruta %s" % string)
        return True

    @api.onchange('num_comprobante')
    def _check_num_comprobante(self):
        if self.num_comprobante:
            if len(self.num_comprobante) != 8:
                self.num_comprobante = self.num_comprobante.zfill(8)

    @api.multi
    def invoice_validate(self):
        res = super(FacturaEAccountInvoice, self).invoice_validate()
        if self.online_mode_f and self.type in ('out_invoice', 'out_refund') and not self.num_comprobante and not self.tipo_comprobante.not_book:
            try:
                res = self.enviar_dte()
            except Exception as e:
                if self.state == 'open':
                    update_journal = False
                    if not self.journal_id.update_posted:
                        self.journal_id.sudo().update_posted = True
                        update_journal = True
                    self.action_invoice_cancel()
                    if update_journal:
                        self.journal_id.sudo().update_posted = False
                    self.action_invoice_draft()
                    self._cr.commit()
                    raise UserError(e)
        if self.tipo_comprobante.not_book:
            self.online_mode_f = False
        self.chage_name_invoice()
        return res

    @api.multi
    def chage_name_invoice(self):
        new_name = False
        if self.type in ['out_invoice', 'out_refund'] and self.punto_venta and self.num_comprobante:
            new_name = self.tipo_comprobante and '(' + self.tipo_comprobante.codigo.zfill(4) + ') ' + self.punto_venta.name + '-' + self.num_comprobante.zfill(8) or self.punto_venta.name + '-' + self.num_comprobante.zfill(8)
        elif self.type in ['in_invoice', 'in_refund'] and self.punto_venta_proveedor and self.num_comprobante:
            new_name = self.tipo_comprobante and '(' + self.tipo_comprobante.codigo.zfill(4) + ') ' + self.punto_venta_proveedor + '-' + self.num_comprobante.zfill(8) or self.punto_venta_proveedor + '-' + self.num_comprobante.zfill(8)
        if new_name:
            self.move_id.name = new_name
            self.name = new_name
            self.move_name = new_name

    @api.one
    def enviar_dte(self):
        if self.type in ('out_invoice', 'out_refund') and self.env.user.company_id.invoice_line and self.invoice_line_count > self.env.user.company_id.invoice_line:
            raise UserError(u'Ha excedido de %d líneas para ésta factura.' % self.env.user.company_id.invoice_line)
        fmt = "%Y%m%d"
        ####Variables comunes
        wsaa_url = self.company_id.ambiente_produccion == 'T' and "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl" \
            or "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"
        cert = self.company_id.ruta_cert
        clave = self.company_id.pass_cert
        self.check_path(cert, 'cert')
        self.check_path(clave, 'key')
        companyCuit = self.company_id.cuit.replace("-", '')
        fecha_cbte = self.date_invoice.strftime("%Y%m%d")
        tipo_cbte = int(self.tipo_comprobante.codigo)
        punto_vta = int(self.punto_venta.name)
        if not self.date_invoice:
            raise ValidationError("Ingrese la fecha de la factura")
        moneda_id = "PES"
        moneda_ctz = '1.000'
        imp_tot_conc = 0.0
        partner_id = self.partner_id.commercial_partner_id
        if self.currency_id.name == 'USD':
            moneda_id = "DOL"
            if self.manual_currency_rate:
                moneda_ctz = self.currency_rate_invoice
            else:
                moneda_ctz = self.currency_id._get_actual_currency_rate(self.date_invoice)
        if self.currency_id.name == 'EUR':
            moneda_id = "060"
            if self.manual_currency_rate:
                moneda_ctz = self.currency_rate_invoice
            else:
                moneda_ctz = self.currency_id._get_actual_currency_rate(self.date_invoice)
        imp_total = self.amount_total ## Importe Total de la factura
        wsaa = WSAA()
        # five hours
        DEFAULT_TTL = 60 * 60 * 5
        tax_map = {'10.5': 4, '21.0': 5, '27.0': 6, '0.0': 3}  # 4: 10.5%, 5: 21%, 6: 27% (no enviar si es otra alicuota)
        if self.punto_venta.tax_assets:
            lines = self.invoice_line_ids.filtered(lambda l: not l.product_id.bfe_check or not l.product_id.bfe_ncm)
            if lines:
                raise UserError('Algunos productos no cuentan con codigo NCM, por favor verificar antes de enviar factura.')
            zona = 1
            # Generar un Ticket de Requerimiento de Acceso (TRA) para WSBFE
            solicitar = True
            session = self.env['afip.session'].search([('xml_tag', '=', 'wsbfe'),
                                                       ('environment', '=', self.company_id.ambiente_produccion),
                                                       ('company_id', '=', self.company_id.id)], order='id DESC', limit=1)
            if session and session.expirationTime:
                expiracion = session.expirationTime
                solicitar = wsaa.Expirado(expiracion)
            if solicitar:
                tra = WSAA().CreateTRA(service="wsbfe", ttl=DEFAULT_TTL)
                # Generar el mensaje firmado (CMS)
                cms = WSAA().SignTRA(tra, cert, clave)
                # Llamar al web service para autenticar
                wsaa.Conectar(None, wsaa_url, '')
                ta = wsaa.LoginCMS(cms)
                if ta:
                    session = self.env['afip.session'].sudo().create({'xml_tag': 'wsbfe',
                                                                      'environment': self.company_id.ambiente_produccion,
                                                                      'company_id': self.company_id.id,
                                                                      'sign': wsaa.ObtenerTagXml("sign"),
                                                                      'token': wsaa.ObtenerTagXml("token"),
                                                                      'expirationTime': wsaa.ObtenerTagXml("expirationTime")})
                    self._cr.commit()
            url = self.company_id.ambiente_produccion == 'T' and "https://wswhomo.afip.gov.ar/" \
                      or "https://servicios1.afip.gov.ar/"
            wsdl = "%swsbfev1/service.asmx?WSDL" % url
            wsbfe = WSBFEv1()
            ok = wsbfe.Conectar(cache=None, wsdl=wsdl)
            if not ok:
                raise ValidationError("Error conexión con libreria. WSBFEV1: %s" % wsbfe.Excepcion)
            wsbfe.LanzarExcepciones = True

            wsbfe.Cuit = companyCuit
            token = session.token
            sign = session.sign
            wsbfe.Token = token
            wsbfe.Sign = sign
            try:
                cbte_nro = wsbfe.GetLastCMP(tipo_cbte, punto_vta) is None and 1 or wsbfe.GetLastCMP(tipo_cbte, punto_vta) + 1
                cbt_id = wsbfe.GetLastID() and wsbfe.GetLastID() + 1 or 1
            except Exception as e:
                raise AccessError("Error de AFIP:" + str(e))
            if self.company_id.use_afip_rate:
                moneda_ctz = moneda_id != 'PES' and wsbfe.GetParamCtz(moneda_id) or '1.000'
                self.env['res.currency.rate'].create({
                            'name': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'rate': float(moneda_ctz),
                            'currency_id': self.currency_id.id
                        })
            self.currency_rate = moneda_ctz
            ## Cliente
            tipo_doc = int(partner_id.documento_id.codigo)
            nro_doc = partner_id.cuit.replace("-", '')
            imp_neto = str("%.2f" % abs(self.amount_untaxed))
            imp_iva = str("%.2f" % abs(self.amount_iva))
            imp_tot_conc = str("%.2f" % abs(self.no_gravado))
            impto_liq_rni = 0.0
            imp_op_ex = str("%.2f" % abs(self.amount_excempt))
            imp_perc = 0.0
            imp_iibb = 0.0
            imp_perc_mun = 0.0
            imp_internos = str("%.2f" % abs(self.amount_other_tax))
            fecha_venc_pago = None
            if self.tipo_comprobante.comprobante_credito and not self.type == 'out_refund':
                date_due = self.date_due and self.date_due or self.date_invoice
            if date_due:
                fecha_venc_pago = date_due.strftime("%Y%m%d")
            wsbfe.CrearFactura(
                        tipo_doc, nro_doc, zona, tipo_cbte, punto_vta,
                        cbte_nro, fecha_cbte, imp_total, imp_neto, imp_iva,
                        imp_tot_conc, impto_liq_rni, imp_op_ex, imp_perc, imp_iibb,
                        imp_perc_mun, imp_internos, moneda_id, moneda_ctz, fecha_venc_pago
                    )

            for line in self.invoice_line_ids:
                codigo = line.product_id.bfe_ncm.name
                sec = ""
                ds = line.name
                qty = line.quantity
                umed = 1
                precio = line.price_unit
                importe = line.price_subtotal
                # calculamos bonificacion haciendo teorico menos importe
                bonif = line.discount and (precio * qty - importe) or None
                iva_id = 2
                imp_iva = 0.0
                taxes = line.invoice_line_tax_ids.filtered(lambda t: t.is_iva)
                if taxes:
                    if tax_map.get(str(taxes[0].amount)):
                        iva_id = tax_map[str(taxes[0].amount)]
                        price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxesv = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity,
                                                                      line.product_id, partner_id)['taxes']
                        for t in taxesv:
                            if t['id'] == taxes[0].id:
                                imp_iva = t['amount']
                wsbfe.AgregarItem(
                        codigo, sec, ds, qty, umed, precio, bonif,
                        iva_id, importe + imp_iva)
            if self.tipo_comprobante.comprobante_credito and self.company_id.cbu and self.type != 'out_refund':
                wsbfe.AgregarOpcional(2101, self.company_id.cbu)
            if self.tipo_comprobante.comprobante_credito and self.company_id.cbu:
                oc = self.client_purchase_ref
                if not oc:
                    oc = self.refund_invoice_id and self.refund_invoice_id.client_purchase_ref and self.refund_invoice_id.client_purchase_ref or self.refund_invoice_id.name
                if not oc:
                    oc = 'N/A'
                wsbfe.AgregarOpcional(23, oc)
            if self.tipo_comprobante.comprobante_credito and self.type == 'out_refund':
                wsbfe.AgregarOpcional(22, self.anulacion and 'S' or 'N')
            wsbfe.Authorize(cbt_id)
            if not wsbfe.CAE:
                raise ValidationError("%s .%s" % (wsbfe.ErrMsg, wsbfe.Obs))
            else:
                # datos devueltos por AFIP:
                self.no_cae = wsbfe.CAE
                self._cr.commit()
                vence = wsbfe.Vencimiento
                self.vence_date = '%s-%s-%s' % (vence[6:10], vence[3:5], vence[0:2])
                path1 = "/tmp/xmlrequest.xml"
                open(path1, "wb").write(wsbfe.XmlRequest)
                self.requestXml = base64.encodestring(bytes(open(path1, 'r').read(), 'utf8'))
                self.requestXml_fname = 'peticion%s.xml' % wsbfe.CAE
                path2 = "/tmp/xmlresponse.xml"
                responseFile = open(path2, "wb").write(wsbfe.XmlResponse)
                self.num_comprobante = str(int(cbte_nro))
                self.responseXml = base64.encodestring(bytes(open(path2, 'r').read(), 'utf8'))
                self.responseXml_fname = 'respuesta%s.xml' % wsbfe.CAE
                digit = self.company_id.cuit.split('-')[1]
                barcode_str = '%s%s%s%s%s%s' % (
                    companyCuit, str(tipo_cbte).zfill(2), punto_vta, wsbfe.CAE, vence, digit)
                self.cod_barra = barcode_str
                self.message_post(body=("Factura Aceptada por la AFIP con No: %s" % str(cbte_nro)))
                if wsbfe.Resultado == 'A':
                    self.state_dte = 'accepted'
                    self._cr.commit()
                elif wsbfe.Resultado == 'R':
                    self.state_dte = 'rejected'
        else:
            if self.tipo_comprobante.codigo in ['019','020','021']:
                if not partner_id.country_id:
                    raise ValidationError("Debe asociar un país al cliente")
                aIva = float_is_zero(self.amount_iva, self.currency_id.rounding)
                aOther = float_is_zero(self.amount_other_tax, self.currency_id.rounding)
                if not aIva or not aOther:
                    raise ValidationError("La factura de exportacion es exenta de impuestos. Favor eliminar impuestos de las lineas de factura")
                #Generar un Ticket de Requerimiento de Acceso (TRA) para WSFEX
                solicitar = True
                session = self.env['afip.session'].search([('xml_tag', '=', 'wsfex'),
                                                           ('environment', '=', self.company_id.ambiente_produccion),
                                                           ('company_id', '=', self.company_id.id)], order='id DESC',
                                                          limit=1)
                if session and session.expirationTime:
                    expiracion = session.expirationTime
                    solicitar = wsaa.Expirado(expiracion)
                if solicitar:
                    tra = WSAA().CreateTRA(service="wsfex", ttl=DEFAULT_TTL)
                    # Generar el mensaje firmado (CMS)
                    cms = WSAA().SignTRA(tra, cert, clave)
                    # Llamar al web service para autenticar
                    wsaa.Conectar(None, wsaa_url, '')
                    ta = wsaa.LoginCMS(cms)
                    if ta:
                        session = self.env['afip.session'].sudo().create({'xml_tag': 'wsfex',
                                                                          'environment': self.company_id.ambiente_produccion,
                                                                          'company_id': self.company_id.id,
                                                                          'sign': wsaa.ObtenerTagXml("sign"),
                                                                          'token': wsaa.ObtenerTagXml("token"),
                                                                          'expirationTime': wsaa.ObtenerTagXml("expirationTime")})
                        self._cr.commit()
                # autenticarse frente a AFIP (obtención de ticket de acceso):
                # conectar al webservice de negocio
                url = self.company_id.ambiente_produccion == 'T' and "https://wswhomo.afip.gov.ar/" \
                      or "https://servicios1.afip.gov.ar/"
                wsdl = "%swsfexv1/service.asmx?WSDL" % url
                wsfex = WSFEX()
                ok = wsfex.Conectar(wsdl)
                if not ok:
                    raise ValidationError("Error conexión con libreria. WSFEX: %s" % wsfex.Excepcion)
                wsfex.LanzarExcepciones = True
                #Setear tocken y sing de autorización (pasos previos)
                #CUIT del emisor (debe estar registrado en la AFIP)
                wsfex.Cuit = companyCuit
                token = session.token
                sign = session.sign
                wsfex.Token = token
                wsfex.Sign = sign
                try:
                    cbte_nro = wsfex.GetLastCMP(tipo_cbte, punto_vta) is None and 1 or wsfex.GetLastCMP(tipo_cbte, punto_vta) + 1
                    cbt_id = wsfex.GetLastID() and wsfex.GetLastID() + 1 or 1
                except Exception as e:
                    raise AccessError("Error de AFIP:" + str(e))
                ## Tipo de Exportación
                tipo_expo = self.tipo_expo or 1
                if self.company_id.use_afip_rate:
                    moneda_ctz = moneda_id != 'PES' and wsfex.GetParamCtz(moneda_id) or '1.000'
                    self.env['res.currency.rate'].create({
                        'name': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'rate': float(moneda_ctz),
                        'currency_id': self.currency_id.id
                    })
                self.currency_rate = moneda_ctz
                ## Permiso
                permiso_existente = self.permiso_existente
                if self.tipo_comprobante.codigo in ['020','021']:
                    permiso_existente = ''
                    tipo_expo = '1'
                ## Pais Destino
                if not partner_id.country_id.cod_nacionalidad:
                    raise ValidationError("Ingrese el código de la nacionalidad")
                dst_cmp = partner_id.country_id.cod_nacionalidad
                ## Cliente
                cliente = partner_id.name
                ## Cuit del pais del cliente
                if partner_id.state_id == self.env.ref('base.state_ar_v', raise_if_not_found=False):
                    cuit_pais_cliente = partner_id.cuit.replace('-', '')
                else:
                    if not partner_id.country_id.cuit_pais:
                        raise ValidationError("Ingrese el cuit del pais")
                    cuit_pais_cliente = partner_id.country_id.cuit_pais.replace('-','')
                ## Direccion Cliente
                domicilio_cliente = partner_id.street
                ## id_impositivo
                id_impositivo = partner_id.cuit
                ## obs_comerciales
                obs_generales = self.comment and self.comment or ""
                forma_pago = self.payment_term_id and self.payment_term_id.name or ""
                obs_comerciales = forma_pago
                ## incoterms
                incoterms = self.incoterms and self.incoterms or "FOB"
                ## Idioma del Comprobante
                idioma_cbte = 1
                ##Creo una factura (internamente, no se llama al WebService):
                wsfex.CrearFactura(tipo_cbte, punto_vta, cbte_nro, fecha_cbte,
                        imp_total, tipo_expo, permiso_existente, dst_cmp,
                        cliente, cuit_pais_cliente, domicilio_cliente,
                        id_impositivo, moneda_id, moneda_ctz,
                        obs_comerciales, obs_generales, forma_pago, incoterms,
                        idioma_cbte)
                #Agregar items
                for line in self.invoice_line_ids:
                    umed = 1 #Ver tabla de parámetros (unidades de medida)
                    #lo agrego a la factura (internamente, no se llama al WebService):
                    discount = line.quantity*line.price_unit-line.price_subtotal
                    if discount > 0.00:
                        wsfex.AgregarItem(line.product_id.default_code, line.product_id.name, line.quantity, \
                                          umed, line.price_unit, line.price_subtotal,
                                          discount)
                    else:
                        wsfex.AgregarItem(line.product_id.default_code, line.product_id.name, line.quantity,\
                            umed, line.price_unit, line.price_subtotal)
                #Agrego un permiso (ver manual para el desarrollador)
                if permiso_existente == "S":
                    permiso_id = "99999AAXX999999A"
                    dst = 225  #país destino de la mercaderia
                    wsfex.AgregarPermiso(permiso_id, dst)
                #Agrego un comprobante asociado (ver manual para el desarrollador)
                if tipo_cbte != 19 and self.refund_invoice_id:
                    tipo_cbte_asoc = int(self.refund_invoice_id.tipo_comprobante.codigo)  # tipo de comprobante asociado
                    punto_vta_asoc = int(self.refund_invoice_id.punto_venta.name)  # punto de venta
                    cbte_nro_asoc = int(self.refund_invoice_id.num_comprobante)  # nro de comprobante asociado
                    wsfex.AgregarCmpAsoc(tipo_cbte_asoc, punto_vta_asoc, cbte_nro_asoc)
                wsfex.Authorize(cbt_id)
                if not wsfex.CAE:
                    raise ValidationError("%s .%s" % (wsfex.ErrMsg, wsfex.Obs))
                else:
                    # datos devueltos por AFIP:
                    self.no_cae = wsfex.CAE
                    self._cr.commit()
                    vence = wsfex.Vencimiento
                    self.vence_date = '%s-%s-%s' % (vence[6:10], vence[3:5], vence[0:2])
                    path1 = "/tmp/xmlrequest.xml"
                    open(path1, "wb").write(wsfex.XmlRequest)
                    self.requestXml = base64.encodestring(bytes(open(path1, 'r').read(), 'utf8')).decode("utf-8")
                    self.requestXml_fname = 'peticion%s.xml' % wsfex.CAE
                    path2 = "/tmp/xmlresponse.xml"
                    responseFile = open(path2, "wb").write(wsfex.XmlResponse)
                    self.num_comprobante = str(int(cbte_nro))
                    self.responseXml = base64.encodestring(bytes(open(path2, 'r').read(), 'utf8')).decode("utf-8")
                    self.responseXml_fname = 'respuesta%s.xml' % wsfex.CAE
                    digit = self.company_id.cuit.split('-')[1]
                    ve = '%s%s%s' % (vence[6:10], vence[3:5], vence[0:2])
                    barcode_str = '%s%s%s%s%s%s' % (
                    companyCuit, str(tipo_cbte).zfill(2), punto_vta, wsfex.CAE, ve, digit)
                    self.cod_barra = barcode_str
                    #imgPath = '/tmp/barcode.png'
                    #PyI25().GenerarImagen(barcode_str, imgPath)
                    #imgFile = open(imgPath, "rb")
                    #self.barcode_img = imgFile.read().encode("base64")
                    self.message_post(body=("Factura de Exportación Aceptada por la AFIP con No: %s" % str(cbte_nro)))
                    if wsfex.Resultado == 'A':
                        self.state_dte = 'accepted'
                        self._cr.commit()
                    elif wsfex.Resultado != 'A':
                        self.state_dte = 'rejected'
            else: #Factura Electrónica
                # instanciar el componente para factura electrónica mercado interno
                wsfev1 = WSFEv1()
                wsfev1.LanzarExcepciones = True
                # datos de conexión (cambiar URL para producción)
                cache = None
                url = self.company_id.ambiente_produccion == 'T' and "https://wswhomo.afip.gov.ar/" \
                      or "https://servicios1.afip.gov.ar/"
                wsdl = "%swsfev1/service.asmx?WSDL" % url
                # Iniciamos la conexion
                proxy = ""
                wrapper = ""  # "pycurl" para usar proxy avanzado / propietarios
                cacert = None  # "afip_ca_info.crt" para verificar canal seguro
                # conectar al webservice de negocio
                ok = wsfev1.Conectar(cache, wsdl, proxy, wrapper, cacert)
                if not ok:
                    raise ValidationError("Error conexión con libreria. WSFEv1: %s" % WSAA.Excepcion)
                solicitar = True
                session = self.env['afip.session'].search([('xml_tag', '=', 'wsfe'),
                                                           ('environment', '=', self.company_id.ambiente_produccion),
                                                           ('company_id', '=', self.company_id.id)], order='id DESC',
                                                          limit=1)
                if session and session.expirationTime:
                    expiracion = session.expirationTime
                    solicitar = wsaa.Expirado(expiracion)
                if solicitar:
                    # autenticarse frente a AFIP (obtención de ticket de acceso):
                    ta = WSAA().Autenticar("wsfe", cert, clave, wsaa_url, debug=True)
                    if not ta:
                        raise ValidationError("Error conexión con libreria. Error WSAA: %s" % WSAA.Excepcion)
                    # establecer credenciales (token y sign) y cuit emisor:
                    wsfev1.SetTicketAcceso(ta)
                    if ta:
                        wsfev1.xml = SimpleXMLElement(ta)
                        session = self.env['afip.session'].sudo().create({'xml_tag': 'wsfe',
                                                                          'environment': self.company_id.ambiente_produccion,
                                                                          'company_id': self.company_id.id,
                                                                          'sign': wsfev1.ObtenerTagXml("sign"),
                                                                          'token': wsfev1.ObtenerTagXml("token"),
                                                                          'expirationTime': wsfev1.ObtenerTagXml(
                                                                              "expirationTime")})
                        self._cr.commit()
                token = session.token
                sign = session.sign
                wsfev1.Token = token
                wsfev1.Sign = sign
                wsfev1.Cuit = companyCuit
                try:
                    cbte_nro = int(wsfev1.CompUltimoAutorizado(tipo_cbte, punto_vta) or 0)
                except Exception as e:
                    raise AccessError("Error de AFIP:" + str(e))
                if not partner_id.cuit:
                    raise ValidationError("El partner no posee CUIT asociado")
                concepto = self.get_concept_type(self.invoice_line_ids)
                tipo_doc = int(partner_id.documento_id.codigo)
                nro_doc = partner_id.cuit.replace("-", '')
                cbt_desde = cbte_nro + 1  # usar proximo numero de comprobante
                cbt_hasta = cbte_nro + 1  # desde y hasta distintos solo lotes factura B
                imp_tot_conc = str("%.2f" % abs(self.no_gravado)) # importe total conceptos no gravado?
                imp_neto = str("%.2f" % abs(self.neto_gravado))  # importe neto gravado (todas las alicuotas)
                imp_iva = str("%.2f" % abs(self.amount_iva))  # importe total iva liquidado (idem)
                imp_trib = self.amount_other_tax + self.amount_perception  # importe total otros conceptos?
                imp_trib = str("%.2f" % abs(imp_trib))
                imp_op_ex = str("%.2f" % abs(self.amount_excempt))  # importe total operaciones exentas
                date_due = self.date_due or ''
                if date_due < self.date_invoice:
                    date_due = self.date_invoice
                if date_due:
                    if not self.tipo_comprobante.comprobante_credito:
                        fecha_venc_pago = concepto != 1 and date_due.strftime("%Y%m%d") or ''
                    else:
                        fecha_venc_pago = date_due.strftime("%Y%m%d")
                else:
                    fecha_venc_pago = ''
                if concepto != 1 and not fecha_venc_pago and not self.tipo_comprobante.comprobante_credito:
                    fecha_venc_pago = fecha_cbte
                if not fecha_venc_pago and self.tipo_comprobante.comprobante_credito:
                    fecha_venc_pago = fecha_cbte
                if self.tipo_comprobante.comprobante_credito and self.type == 'out_refund':
                    fecha_venc_pago = ''
                # Fechas del período del servicio facturado (solo si concepto != 1)?
                fecha_serv_desde = concepto != 1 and fecha_cbte or ''
                fecha_serv_hasta = concepto != 1 and fecha_venc_pago or ''
                if concepto != 1 and not fecha_serv_hasta:
                    fecha_serv_hasta = fecha_cbte
                # inicializar la estructura de factura (interna)
                wsfev1.CrearFactura(concepto, tipo_doc, nro_doc, tipo_cbte, punto_vta,
                                    cbt_desde, cbt_hasta, str(imp_total), str(imp_tot_conc), str(imp_neto),
                                    str(imp_iva), str(imp_trib), str(imp_op_ex), fecha_cbte, fecha_venc_pago,
                                    fecha_serv_desde, fecha_serv_hasta, moneda_id, moneda_ctz)
                # agregar comprobantes asociados (solo para Notas de Débito y Cŕedito)
                if tipo_cbte not in (1, 6, 11) and self.refund_invoice_id:
                    tipo = int(self.refund_invoice_id.tipo_comprobante.codigo)  # tipo de comprobante asociado
                    pto_vta = int(self.refund_invoice_id.punto_venta.name)  # punto de venta
                    nro = int(self.refund_invoice_id.num_comprobante)  # nro de comprobante asociado
                    cuit = self.refund_invoice_id.company_id.cuit.replace("-", '')
                    fecha_cbte = self.refund_invoice_id.date_invoice.strftime("%Y%m%d")
                    wsfev1.AgregarCmpAsoc(tipo, pto_vta, nro, cuit, fecha_cbte)
                for tax in self.tax_line_ids:
                    t = tax.tax_id
                    base_imp = tax.base
                    if tax.base:
                        importe = round(t._compute_amount(tax.base, tax.base, 1), 2)
                    else:
                        importe = round(tax.amount, 2)
                    if t.is_iva:
                        # agregar subtotales por tasa de iva (repetir por cada alicuota):
                        if tax_map.get(str(t.amount)):
                            taxId = tax_map[str(t.amount)]
                            print ('%s: base(%s), imp(%s)' % (tax.name, tax.base, importe))
                            wsfev1.AgregarIva(taxId, base_imp, importe)
                    else:
                        # agregar otros impuestos (repetir por cada tributo diferente)
                        taxId = int(t.tipo_tributo)  # tipo de tributo (ver tabla)
                        desc = tax.name  # descripción del tributo
                        alic = t.amount  # alicuota iva
                        wsfev1.AgregarTributo(taxId, desc, base_imp, alic, importe)
                # llamar al webservice de AFIP para autorizar la factura y obtener CAE:
                if self.tipo_comprobante.comprobante_credito and self.company_id.cbu and self.type != 'out_refund':
                    wsfev1.AgregarOpcional(2101, self.company_id.cbu)
                if self.tipo_comprobante.comprobante_credito and self.company_id.cbu:
                    oc = self.client_purchase_ref
                    if not oc:
                        oc = self.refund_invoice_id and self.refund_invoice_id.client_purchase_ref and self.refund_invoice_id.client_purchase_ref or self.refund_invoice_id.name
                    if not oc:
                        oc = 'N/A'
                    wsfev1.AgregarOpcional(23, oc)
                if self.tipo_comprobante.comprobante_credito and self.company_id.cbu and self.type == 'out_refund':
                    wsfev1.AgregarOpcional(22, 'N')
                wsfev1.CAESolicitar()
                if not wsfev1.CAE:
                    raise ValidationError("%s .%s" % (wsfev1.ErrMsg, wsfev1.Obs))
                else:
                    # datos devueltos por AFIP:
                    self.no_cae = wsfev1.CAE
                    self._cr.commit()
                    vence = wsfev1.Vencimiento
                    self.vence_date = '%s-%s-%s' % (vence[0:4], vence[4:6], vence[6:8])
                    path1 = "/tmp/xmlrequest.xml"
                    open(path1, "wb").write(wsfev1.XmlRequest)
                    self.requestXml = base64.encodestring(bytes(open(path1, 'r').read(), 'utf8'))
                    self.requestXml_fname = 'peticion%s.xml' % wsfev1.CAE
                    path2 = "/tmp/xmlresponse.xml"
                    responseFile = open(path2, "wb").write(wsfev1.XmlResponse)
                    self.num_comprobante = str(cbt_desde)
                    self.responseXml = base64.encodestring(bytes(open(path2, 'r').read(), 'utf8'))
                    self.responseXml_fname = 'respuesta%s.xml' % wsfev1.CAE
                    digit = self.company_id.cuit.split('-')[1]
                    barcode_str = '%s%s%s%s%s%s' % (
                    companyCuit, str(tipo_cbte).zfill(2), punto_vta, wsfev1.CAE, vence, digit)
                    self.cod_barra = barcode_str
                    self.message_post(body=("Factura Aceptada por la AFIP con No: %s" % str(cbt_desde)))
                    if wsfev1.Resultado == 'A':
                        self.state_dte = 'accepted'
                        self._cr.commit()
                    elif wsfev1.Resultado == 'R':
                        self.state_dte = 'rejected'

    tipo_de_cambio = fields.Float(digits=dp.get_precision('Currency Rate'), string='Tipo de Cambio 1 U$S',
                                  readonly=True,
                                  compute='_compute_tipo_de_cambio')

    @api.depends('date_invoice')
    def _compute_tipo_de_cambio(self):
        for rec in self:
            currency = self.env['res.currency'].search([('id', '=', '3')])
            rate = 1
            if currency:
                date_order = None
                if rec.invoice_line_ids and rec.invoice_line_ids[0].sale_line_ids:
                    date_order = rec.invoice_line_ids[0].sale_line_ids[0].order_id.confirmation_date or \
                                 rec.invoice_line_ids[0].sale_line_ids[0].order_id.date_order
                date_invoice = fields.Datetime.to_string(fields.Datetime.from_string(rec._get_currency_rate_date()))
                rate = currency.with_context(date=date_invoice or date_order).rate
                if rate == 1:
                    rate = currency.rate
            rec.tipo_de_cambio = 1 / rate
