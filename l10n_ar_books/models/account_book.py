# -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import odoo.addons.decimal_precision as dp
from itertools import groupby
from calendar import monthrange
import base64
import unicodedata
import csv
import xlwt
import re
from io import BytesIO
from io import StringIO

class AccountBook(models.Model):
    _name = "account.book"
    _rec_name = 'name'

    def clean_accents(self, text):
        text = str(text)
        string = ''.join((c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn'))
        return string

    @api.multi
    @api.depends('invoice_ids')
    def _count_docs(self):
        for book in self:
            book.count_docs = len(book.invoice_ids)

    @api.multi
    @api.depends('date')
    def _get_period(self):
        for book in self:
            book.period = '%s-%s'%(book.date.year, str(book.date.month).zfill(2))

    @api.model
    def get_parent(self, partner):
        return partner.commercial_partner_id

    @api.model
    def format_float(self, amount):
        strAmount = '%.2f' %amount
        return strAmount.replace('.','').zfill(15)

    @api.model
    def create(self, vals):
        op = vals['operation'] == 'sale' and 'VENTAS' or 'COMPRAS'
        date = datetime.strptime(vals['date'],'%Y-%m-%d')
        period = '%s-%s'%(date.year,str(date.month).zfill(2))
        vals['name'] = '%s %s'%(op,period)
        return super(AccountBook, self).create(vals)

    @api.multi
    def write(self, vals):
        for book in self:
            if 'date' in vals:
                op = book.operation == 'sale' and 'VENTAS' or 'COMPRAS'
                date = datetime.strptime(vals['date'],'%Y-%m-%d')
                period = '%s-%s'%(date.year,str(date.month).zfill(2))
                vals['name'] = '%s %s'%(op,period)
        return super(AccountBook, self).write(vals)

    @api.one
    @api.depends('invoice_ids')
    def _amount_all(self):
        self.amount_iva = sum(inv.amount_iva * inv.rate for inv in self.invoice_ids)
        self.amount_excempt = sum((inv._get_no_excempt_book() + inv._get_no_gravado_book()) * inv.rate for inv in self.invoice_ids)
        self.amount_total = sum(inv.amount_total_company_signed for inv in self.invoice_ids)

    name = fields.Char(string="Nombre",default="Nuevo")
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('not_sent', 'Cargado')],
        string='Estado', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help="")
    company_id = fields.Many2one('res.company', string="Compañía", required=True,
                                 default=lambda self: self.env.user.company_id.id,
                                 readonly=True,states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Moneda", readonly=True)
    date = fields.Date(string="Fecha", default= fields.Date.today, help="Seleccione una fecha para definir el periodo del libro")
    period = fields.Char(string='Período', readonly=True, compute="_get_period")
    invoice_ids = fields.One2many('account.invoice', 'book_id', string="Documentos")
    operation = fields.Selection([
        ('purchase','Compra'),
        ('sale','Venta')],
        string="Tipo Operación",default="sale",
        required=True,readonly=True,states={'draft': [('readonly', False)]})
    count_docs = fields.Integer('Cantidad Doc.', compute="_count_docs")
    amount_iva = fields.Monetary(string='Importe IVA',store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_excempt = fields.Monetary(string='Importe Exento',store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_total = fields.Monetary(string='Importe Total',store=True, readonly=True, compute='_amount_all', track_visibility='always')
    csv_file = fields.Binary('Archivo .csv', attachment=True, help="Archivo .csv con la información de los documentos del periodo")
    csv_file_name = fields.Char(string="CSV Filename")
    company_id = fields.Many2one('res.company', string='Compañía', change_default=True,
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=lambda self: self.env['res.company']._company_default_get('account.book'))

    is_locked = fields.Boolean('Bloqueado')
    date_lock = fields.Date('Fecha de bloqueo')

    @api.one
    def get_invoices(self):
        invoice_obj = self.env['account.invoice']
        type_domain = {'sale': ['out_refund','out_invoice'], 'purchase': ['in_refund','in_invoice']}
        date = self.date
        end_of_month = monthrange(date.year, date.month)[1]
        start_period = '%s-%s-01'%(date.year, date.month)
        end_period = '%s-%s-%s'%(date.year, date.month, end_of_month)
        if self.operation == 'sale':
            invoices = invoice_obj.search([
                    ('state','in',['open','paid']),
                    ('type','in', type_domain[self.operation]),
                    ('date_invoice','>=',start_period),
                    ('date_invoice','<=',end_period),
                    ('company_id','=',self.company_id.id),
                    ('tipo_comprobante.not_book', '=', False)
            ], order='date_invoice')
        else:
            invoices = invoice_obj.search([
                ('state', 'in', ['open', 'paid']),
                ('type', 'in', type_domain[self.operation]),
                ('date', '>=', start_period),
                ('date', '<=', end_period),
                ('company_id', '=', self.company_id.id),
                ('tipo_comprobante.not_book', '=', False),
                ('amount_total', '!=', 0.0),
            ], order='date')
        self.invoice_ids = invoices

    @api.one
    def validate(self):
        self.state = 'not_sent'

    @api.multi
    def print_pdf(self):
        self.ensure_one()
        return self.env.ref('l10n_ar_books.l10n_ar_account_books').report_action(self)

    def get_fecha_comprobante(self, invoice):
        return datetime.strftime(self.operation == 'sale' and invoice.date_invoice or invoice.date, '%d/%m/%Y')
    
    @api.multi
    def print_xls(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        today = datetime.today().strftime("%d/%m/%Y")
        header_style1 = xlwt.easyxf('font: bold on, height 180; align: wrap on, horiz center, vert center;')
        header_style2 = xlwt.easyxf('pattern: pattern solid, pattern_fore_colour pale_blue, pattern_back_colour pale_blue; font: bold on, height 160; align: wrap on, horiz center, vert center;')
        title_style = xlwt.easyxf('pattern: pattern solid, pattern_fore_colour gray25, pattern_back_colour gray25; font: bold on, height 160; align: wrap on, horiz center, vert center; border: top medium, right medium, bottom medium, left medium;')
        res_style = xlwt.easyxf('font: bold on, height 180; align: wrap yes, horiz right, vert center; border: top medium;',num_format_str='$#,##0.00')
        title_res_style = xlwt.easyxf('font: bold on, height 180; align: wrap on, horiz left, vert center; border: top medium;')
        title_style_left = xlwt.easyxf('font: bold on, height 180; align: wrap on, horiz left, vert center; border: top medium, right medium, bottom medium, left medium;')
        base_style = xlwt.easyxf('font: height 140; align: wrap on, horiz center')
        base_style_left = xlwt.easyxf('font: height 140; align: wrap on, horiz left')
        decimal_style = xlwt.easyxf('font: height 140; align: wrap yes, horiz right',num_format_str='$#,##0.00')
        decimal_style1 = xlwt.easyxf('font: height 160; align: wrap yes, horiz right',num_format_str='$#,##0.00')
        date_style = xlwt.easyxf('font: height 140; align: wrap yes; font: bold on; align: wrap on, horiz center, vert center;', num_format_str='DD-MM-YYYY')
        date_style_title = xlwt.easyxf('font: bold on, height 160; align: wrap yes; font: bold on; align: wrap on, horiz center, vert center;', num_format_str='DD-MM-YYYY')
        datetime_style = xlwt.easyxf('font: height 140; align: wrap yes', num_format_str='YYYY-MM-DD HH:mm:SS')
        columns = ['Fecha','Tipo Comp.','Comprobante','Tipo Resp.','C.U.I.T.','Razon Social','Neto Gravado',
                   'No Gravado']
        op = self.operation == 'sale' and 'Ventas' or 'Compras'
        name = 'Libro de %s'%op
        worksheet = workbook.add_sheet(name)
        worksheet.write_merge(0, 3, 0, 5, '%s\n %s\nPeriodo: %s\nFecha Impresion: %s'%(name,self.company_id.name,self.period,today),
                              header_style1)
        all_taxes_in_book = self.get_grouped_taxes()['iva'] + self.get_grouped_taxes()['other']
        columns += [x.name or 'Otros Imp.' for x in all_taxes_in_book]
        columns += ['Total IVA','Total Otros Imp.','Total']
        for i, fieldname in enumerate(columns):
            worksheet.write(5, i, fieldname or '', title_style)
        row_index = 6
        tGravado = tExento = tIva = tOtro = tTotal = 0.0
        for inv in self.invoice_ids.sorted(key=lambda x: x.date_invoice):
            partner = self.get_parent(inv.partner_id)
            if not partner.cuit:
                raise ValidationError('El partner %s no posee C.U.I.T.'%partner.name)
            if not partner.responsability_id:
                raise ValidationError('El partner %s no posee Tipo de Responsabilidad asignada'%partner.name)
            signe = 1
            if inv.type in ('in_refund', 'out_refund') and inv.refund_type == 'credit':
                signe = -1
            tGravado += inv.neto_gravado * inv.rate * signe
            tGravado = round(tGravado, 2)
            tExento += (inv._get_no_excempt_book() + inv._get_no_gravado_book()) * inv.rate * signe
            tExento = round(tExento, 2)
            tIva += inv.amount_iva * inv.rate * signe
            tIva = round(tIva, 2)
            tOtro += inv.amount_other_tax * inv.rate * signe
            tOtro += inv.amount_perception * inv.rate * signe
            tOtro = round(tOtro, 2)
            tTotal += round(inv.amount_total_company_signed, 2)
            tTotal = round(tTotal, 2)
            punto_venta = inv.type in ['out_refund','out_invoice'] and inv.punto_venta.name or inv.punto_venta_proveedor
            fecha_comprobante = self.get_fecha_comprobante(inv)
            worksheet.write(row_index, 0, re.sub("\r", " ", fecha_comprobante), base_style_left)
            worksheet.write(row_index, 1, re.sub("\r", " ", self.clean_accents(inv.tipo_comprobante.book_desc and inv.tipo_comprobante.book_desc or inv.tipo_comprobante.name)), base_style_left)
            if inv.num_comprobante:
                worksheet.write(row_index, 2, re.sub("\r", " ", '%s%s-%s'%(inv.tipo_comprobante.desc,punto_venta,inv.num_comprobante.zfill(8))), base_style_left)
            else:
                num_comprobante = '00'
                worksheet.write(row_index, 2, re.sub("\r", " ", '%s%s-%s' % (inv.tipo_comprobante.desc, inv.punto_venta.name, num_comprobante.zfill(8))), base_style_left)

            worksheet.write(row_index, 3, re.sub("\r", " ", self.clean_accents(partner.responsability_id.book_desc and partner.responsability_id.book_desc or partner.responsability_id.name)), base_style_left)
            worksheet.write(row_index, 4, re.sub("\r", " ", partner.cuit), base_style_left)
            name = partner.name.encode("ascii", errors="ignore").decode()
            worksheet.write(row_index, 5, re.sub("\r", " ", self.clean_accents(name)), base_style_left)
            worksheet.write(row_index, 6, re.sub("\r", " ", str(round(inv.neto_gravado * inv.rate * signe, 2))), decimal_style)
            excempt = ((inv._get_no_excempt_book() + inv._get_no_gravado_book()) * inv.rate * signe)
            worksheet.write(row_index, 7, re.sub("\r", " ", str(round(excempt, 2))), decimal_style)
            col_index = 8
            for t in all_taxes_in_book:
                tAmount = sum(round(x.amount * inv.rate * signe, 2) for x in inv.tax_line_ids if(x.tax_id.id == t.id))
                worksheet.write(row_index, col_index, re.sub("\r", " ", str(round(tAmount,2))), decimal_style)
                col_index+= 1
            worksheet.write(row_index, col_index, re.sub("\r", " ", str(round(inv.amount_iva * inv.rate * signe, 2))), decimal_style)
            other_tax_inv = inv.amount_other_tax * inv.rate * signe
            other_tax_inv += inv.amount_perception * inv.rate * signe
            worksheet.write(row_index, (col_index + 1), re.sub("\r", " ", str(round(other_tax_inv, 2))), decimal_style)
            worksheet.write(row_index, (col_index + 2), re.sub("\r", " ", str(round(inv.amount_total_company_signed, 2))), decimal_style)
            row_index += 1
        worksheet.write(row_index, 5, re.sub("\r", " ", 'Totales'), title_res_style)
        worksheet.write(row_index, 6, re.sub("\r", " ", str(round(tGravado, 2))), res_style)
        worksheet.write(row_index, 7, re.sub("\r", " ", str(round(tExento, 2))), res_style)
        col_index = 8
        for t in all_taxes_in_book:
            totalTax = self.get_total_taxes(t)
            worksheet.write(row_index, col_index, re.sub("\r", " ", str(round(totalTax[t.id], 2))), res_style)
            col_index += 1
        worksheet.write(row_index, (col_index), re.sub("\r", " ", str(round(tIva, 2))), res_style)
        worksheet.write(row_index, (col_index+1), re.sub("\r", " ", str(round(tOtro, 2))), res_style)
        worksheet.write(row_index, (col_index+2), re.sub("\r", " ", str(round(tTotal, 2))), res_style)
        for i in range(len(columns)):
            if i == 3:
                worksheet.col(i).width = 6000
            elif i == 5:
                worksheet.col(i).width = 7000
            else:
                worksheet.col(i).width = 4000

        worksheet2 = workbook.add_sheet('Totales Agrupados %s'%self.period)
        worksheet2.write_merge(0, 1, 0, 3, 'TOTALES POR RESPONSABILIDAD PERIODO %s'%self.period, header_style1)
        row_index = 2
        for tipoR in self.grouped_tipo_responsable():
            worksheet2.write(row_index, 0, re.sub("\r", " ", tipoR.name), title_style)
            worksheet2.write(row_index, 1, re.sub("\r", " ", 'IVA Facturas'), title_style)
            worksheet2.write(row_index, 2, re.sub("\r", " ", 'Gravado Facturas'), title_style)
            worksheet2.write(row_index, 3, re.sub("\r", " ", 'IVA Nota Debito'), title_style)
            worksheet2.write(row_index, 4, re.sub("\r", " ", 'Gravado Nota Debito'), title_style)
            worksheet2.write(row_index, 5, re.sub("\r", " ", 'IVA Nota Crebito'), title_style)
            worksheet2.write(row_index, 6, re.sub("\r", " ", 'Gravado Nota Crebito'), title_style)
            row_index2 = row_index + 1
            for groupTax in self.get_grouped_taxes()['iva']:
                line = self.taxes_by_responsability(tipoR, groupTax)
                worksheet2.write(row_index2, 0, re.sub("\r", " ", float_is_zero(groupTax.amount, precision_digits=2) and 'No Gravado' or groupTax.name), header_style1)
                worksheet2.write(row_index2, 1, re.sub("\r", " ", str(round(line['invoice_tax'], 2))), decimal_style1)
                worksheet2.write(row_index2, 2, re.sub("\r", " ", str(round(line['invoice_base'], 2))), decimal_style1)
                worksheet2.write(row_index2, 3, re.sub("\r", " ", str(round(line['debitnote_tax'], 2))), decimal_style1)
                worksheet2.write(row_index2, 4, re.sub("\r", " ", str(round(line['debitnote_base'], 2))), decimal_style1)
                worksheet2.write(row_index2, 5, re.sub("\r", " ", str(round(line['creditnote_tax'], 2))), decimal_style1)
                worksheet2.write(row_index2, 6, re.sub("\r", " ", str(round(line['creditnote_base'], 2))), decimal_style1)
                row_index2 += 1
                row_index = row_index2
            row_index+=1
        for i in range(7):
            worksheet2.col(i).width = 6000

        worksheet3 = workbook.add_sheet('Totales %s'%self.period)
        worksheet3.write_merge(0, 1, 0, 3, 'TOTALES PERIODO %s'%self.period, header_style1)
        worksheet3.write_merge(2, 2, 0, 1, 'TOTALES IVA', title_style)
        worksheet3.write_merge(2, 2, 2, 3, 'TOTALES OTROS CONCEPTOS', title_style)
        worksheet3.write(3, 0, re.sub("\r", " ", 'Total No Gravado (Exento)'), title_style)
        worksheet3.write(3, 1, re.sub("\r", " ", str(tExento)), decimal_style1)
        row_index = 4
        row_index2 = 5
        for groupTax in self.get_grouped_taxes()['iva']:
            if not float_is_zero(groupTax.amount, precision_digits=2):
                totalTaxIva = self.get_total_taxes(groupTax)
                totalIvaBases = self.get_total_tax_bases(groupTax)
                worksheet3.write(row_index, 0, re.sub("\r", " ", groupTax.name), title_style)
                worksheet3.write(row_index, 1, re.sub("\r", " ", str(round(totalTaxIva[groupTax.id], 2))), decimal_style1)
                worksheet3.write(row_index2, 0, re.sub("\r", " ", 'Total Gravado %s'%groupTax.name), title_style)
                worksheet3.write(row_index2, 1, re.sub("\r", " ", str(round(totalIvaBases[groupTax.id], 2))), decimal_style1)
                row_index+= 2
                row_index2+= 2
        row_index3 = 3
        for groupTax in self.get_grouped_taxes()['other']:
            totalTaxOther = self.get_total_taxes(groupTax)
            worksheet3.write(row_index3, 2, re.sub("\r", " ", groupTax.name or ''), title_style)
            worksheet3.write(row_index3, 3, re.sub("\r", " ", str(round(totalTaxOther[groupTax.id], 2))), decimal_style1)
            row_index3+= 1
        for i in range(4):
            worksheet3.col(i).width = 6000
        fp = BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        bytes_base64_encoded = base64.encodebytes(data)
        data_b64 =bytes_base64_encoded.decode('utf-8').replace('\n', '')
        attach_vals = {
            'name': 'Libro Compras/Ventas - %s.xls'%self.period,
            'datas':data_b64,
            'datas_fname': 'Libro Compras/Ventas - %s.xls'%self.period,
        }
        doc = self.env['ir.attachment'].create(attach_vals)
        res = {}
        res['type'] = 'ir.actions.act_url'
        res['target'] = 'new'
        res['url'] = "web/content/?model=ir.attachment&id="+str(doc.id)+"&filename_field=datas_fname&field=datas&download=true&filename="+str(doc.name)
        return res

    @api.multi
    def download_txt(self):
        res = {}
        op = self.operation == 'sale' and 'VENTAS' or 'COMPRAS'
        fname = '%s_%s_%s_Comprobantes.txt' %(self.company_id.cuit,self.period.replace('-','_'),op)
        txtFile = StringIO()
        i = 0
        for invoice in self.invoice_ids:
            i += 1
            line = ''
            partner = invoice.partner_id.commercial_partner_id
            if not partner.cuit:
                raise ValidationError('El partner %s no posee C.U.I.T.'%partner.name)
            if not partner.responsability_id:
                raise ValidationError('El partner %s no posee Tipo de Responsabilidad asignada'%partner.name)
            if not partner.documento_id:
                raise ValidationError('El partner %s no posee Tipo de Documento asignado'%partner.name)
            punto_venta = invoice.type in ['out_invoice','out_refund'] and invoice.punto_venta.name or invoice.punto_venta_proveedor
            if invoice.type not in ['out_invoice','out_refund'] and invoice.tipo_comprobante.is_import:
                punto_venta = '00000'
            fecha_factura = datetime.strftime(invoice.date_invoice, '%Y%m%d')
            if self.operation != 'sale':
                 fecha_factura = invoice.date and datetime.strftime(invoice.date, '%Y%m%d') or datetime.strftime(invoice.date_invoice, '%Y%m%d')
            line+= fecha_factura #fecha factura
            line+= invoice.tipo_comprobante.codigo #tipo comprobante
            line+= punto_venta.zfill(5) #punto de ventaa
            if not invoice.tipo_comprobante.is_import:
                if not invoice.num_comprobante:
                    raise ValidationError('Factura %s ID(%s) no presenta Numero de Comprobante'% (invoice.number, invoice.id))
                line+= invoice.num_comprobante and invoice.num_comprobante.zfill(20) or datetime.strftime(invoice.date_due, '%Y%m%d') #num comprobante
            else:
                line +='00000000000000000000'
            if invoice.type in ['in_invoice','in_refund'] and not invoice.tipo_comprobante.is_import:
                line += '                ' #Despacho Importacion
            elif invoice.type in ['in_invoice','in_refund'] and invoice.tipo_comprobante.is_import:
                if invoice.reference:
                    line += invoice.reference.zfill(16)
                elif invoice.num_comprobante:
                    line += invoice.num_comprobante.zfill(16)
                else:
                    raise UserError(u'Factura %s No posee un Numero de Despacho de Importacion, por favor colocar en la Referencia de Proveedor' % invoice.display_name)
            else:
                line += invoice.num_comprobante and invoice.num_comprobante.zfill(20) or '0'.zfill(20)  # Num comprobante hasta
            if not partner.documento_id:
                raise ValidationError('Debe seleccionar el tipo de documento de la Empresa con la factura %s'%invoice.number)
            line+= partner.documento_id.codigo #codigo doc vendedor/comprador
            line+= partner.cuit.strip().replace('-','').zfill(20) #num identificacion vendedor/comprador
            name = partner.name.encode("ascii", errors="ignore").decode()
            line+= len(name) >= 30 and name[0:30] or name.ljust(30) #Nombre Comprador/Vendedor
            line+= self.format_float(invoice.amount_total * invoice.rate) #Importe total
            line+= self.format_float(invoice.no_gravado * invoice.rate) #Importe total de conceptos que no integran el precio neto gravado
            if invoice.type in ['out_invoice','out_refund']:
                line+= '0'.zfill(15) #Percepción a no categorizados
            line+= self.format_float(invoice.amount_excempt * invoice.rate) #Importe exento
            if invoice.type in ['in_invoice','in_refund']:
                line+= '0'.zfill(15) #Importe de percepciones o pagos a cuenta del Impuesto al Valor Agregado
            line+= self.format_float(sum([x.amount * invoice.rate for x in invoice.tax_line_ids if(x.tax_id.is_iva is False and x.tax_id.tipo_tributo == '1')])) #Importe de percepciones o pagos a cuenta de otros impuestos nacionales
            line += self.format_float(sum([x.amount * invoice.rate for x in invoice.tax_line_ids if (x.tax_id.is_iva is False and x.tax_id.tipo_tributo == '2')]))  # Percepciones de Ingresos Brutos
            line+= self.format_float(sum([x.amount * invoice.rate for x in invoice.tax_line_ids if(x.tax_id.is_iva is False and x.tax_id.tipo_tributo == '3')])) #Importe de percepciones de Impuestos Municipales
            line+= self.format_float(sum([x.amount * invoice.rate for x in invoice.tax_line_ids if(x.tax_id.is_iva is False and x.tax_id.tipo_tributo == '4')])) #Importe de Impuestos Internos
            line += 'PES' #Siempre en PESOS se debe hacer la conversion
            #line+= invoice.currency_id.name == 'ARS' and 'PES' or invoice.currency_id.name #Moneda
            line+= '0001000000' #Tipo de Cambio
            tax_qty = len([x.id for x in invoice.tax_line_ids if(x.tax_id.is_iva is True and not x.tax_id.is_excempt)])
            if not tax_qty and not invoice.tipo_comprobante.is_exempt:
                if invoice.tipo_comprobante.desc not in ['B', 'C']:
                    tax_qty = 1
            elif not tax_qty and invoice.type in ['in_refund']:
                tax_qty = 1
            line+= str(tax_qty) #Cantidad de alicuotas
            if invoice.cod_operacion:
                line+= invoice.cod_operacion #Código de operación
            if invoice.type in ['in_invoice','in_refund']:
                line+= self.format_float(invoice.amount_iva * invoice.rate) #Crédito Fiscal Computable
            line+= self.format_float(sum([x.amount * invoice.rate for x in invoice.tax_line_ids if(x.tax_id.is_iva is False and x.tax_id.tipo_tributo == '99')])) #Otros Tributos
            if invoice.type in ['in_invoice','in_refund']:
                line+= '00000000000'
                line+= '                              '
                line+= '000000000000000' # IVA Comisión
            if invoice.type in ['out_invoice', 'out_refund'] and invoice.tipo_comprobante.desc != 'E' and not invoice.tipo_comprobante.comprobante_credito:
                line+= invoice.date_due < invoice.date_invoice and datetime.strftime(invoice.date_invoice,'%Y%m%d') or datetime.strftime(invoice.date_due,'%Y%m%d') #fecha vencimiento pago
            else:
                line += '00000000'
            line += '\r\n'
            txtFile.write(self.clean_accents(line))
        txtFile.seek(0)
        bytes_base64_encoded = base64.encodebytes(txtFile.read().encode('utf-8'))
        data = bytes_base64_encoded.decode('utf-8').replace('\n', '')
        txtFile.close()
        attach_vals = {'name': fname, 'datas': data, 'datas_fname': fname}
        doc_id = self.env['ir.attachment'].create(attach_vals)
        res['type'] = 'ir.actions.act_url'
        res['target'] = 'new'
        res['url'] = "web/content/?model=ir.attachment&id=" + str(
            doc_id.id) + "&filename_field=datas_fname&field=datas&download=true&filename=" + str(doc_id.name)
        return res

    @api.multi
    def download_txt_a(self):
        account_precision = self.env['decimal.precision'].precision_get('Account')
        res = {}
        tax_map = {'10.5': '0004', '21.0': '0005', '27.0': '0006','2.5': '0009', '5.0': '0008'}
        txtFile = StringIO()
        op = self.operation == 'sale' and 'VENTAS' or 'COMPRAS'
        fname = '%s_%s_%s_Alicuotas.txt' %(self.company_id.cuit,self.period.replace('-','_'),op)
        invoice_processed = []
        for invoice in self.invoice_ids:
            if not invoice.tipo_comprobante.is_import and not invoice.tipo_comprobante.is_exempt:
                if not invoice.tax_line_ids and invoice.tipo_comprobante.desc not in ['B', 'C']:
                    line = ''
                    partner = invoice.commercial_partner_id
                    if not partner.cuit:
                        raise ValidationError('El partner %s no posee C.U.I.T.' % partner.name)
                    if not partner.responsability_id:
                        raise ValidationError('El partner %s no posee Tipo de Responsabilidad asignada' % partner.name)
                    if not partner.documento_id:
                        raise ValidationError('El partner %s no posee Tipo de Documento asignado' % partner.name)
                    punto_venta = invoice.type in ['out_invoice',
                                                   'out_refund'] and invoice.punto_venta.name or invoice.punto_venta_proveedor
                    line += invoice.tipo_comprobante.codigo  # tipo comprobante
                    line += punto_venta.zfill(5)  # punto de venta
                    line += invoice.num_comprobante and invoice.num_comprobante.zfill(20) or '0'.zfill(
                        20)  # num comprobante
                    if invoice.type in ['in_invoice', 'in_refund']:
                        if not invoice.partner_id.commercial_partner_id.documento_id:
                            raise ValidationError(
                                'Debe seleccionar el tipo de documento del partner %s' % invoice.partner_id.commercial_partner_id.name)
                        line += partner.documento_id.codigo
                        line += partner.cuit.replace('-', '').zfill(20)  # num identificacion vendedor
                    line += self.format_float(0.0)  # Importe neto gravado
                    line += '0003'  # Alícuota de IVA
                    line += self.format_float(0.0)  # Impuesto Liquidado
                    line += '\r\n'
                    txtFile.write(self.clean_accents(line))
                else:
                    tax_plus = False
                    for taxLine in invoice.tax_line_ids.filtered(lambda t: t.tax_id.is_iva):
                        if not float_is_zero(taxLine.tax_id.amount, account_precision):
                            tax_plus = True
                    for taxLine in invoice.tax_line_ids:
                        if taxLine.tax_id.is_iva and not taxLine.tax_id.is_excempt:
                            invoice_processed += [invoice.id]
                            line = ''
                            partner = invoice.commercial_partner_id
                            if not partner.cuit:
                                raise ValidationError('El partner %s no posee C.U.I.T.'%partner.name)
                            if not partner.responsability_id:
                                raise ValidationError('El partner %s no posee Tipo de Responsabilidad asignada'%partner.name)
                            if not partner.documento_id:
                                raise ValidationError('El partner %s no posee Tipo de Documento asignado'%partner.name)
                            punto_venta = invoice.type in ['out_invoice','out_refund'] and invoice.punto_venta.name or invoice.punto_venta_proveedor
                            line+= invoice.tipo_comprobante.codigo #tipo comprobante
                            line+= punto_venta.zfill(5) #punto de venta
                            line+= invoice.num_comprobante and invoice.num_comprobante.zfill(20) or '0'.zfill(20) #num comprobante
                            if invoice.type in ['in_invoice','in_refund']:
                                if not invoice.partner_id.commercial_partner_id.documento_id:
                                    raise ValidationError('Debe seleccionar el tipo de documento del partner %s'%invoice.partner_id.commercial_partner_id.name)
                                line+= partner.documento_id.codigo
                                line+= partner.cuit.replace('-','').zfill(20) #num identificacion vendedor
                            line+= self.format_float(taxLine.base * invoice.rate) #Importe neto gravado
                            line+= tax_map.get(str(taxLine.tax_id.amount),False) and tax_map[str(taxLine.tax_id.amount)] or '0000'#Alícuota de IVA
                            line+= self.format_float(taxLine.amount * invoice.rate) #Impuesto Liquidado
                            line += '\r\n'
                            txtFile.write(self.clean_accents(line))
                        elif invoice.tipo_comprobante.desc not in ['B', 'C'] and invoice.id not in invoice_processed and not tax_plus:
                            invoice_processed += [invoice.id]
                            line = ''
                            partner = invoice.partner_id.commercial_partner_id
                            if not partner.cuit:
                                raise ValidationError('El partner %s no posee C.U.I.T.' % partner.name)
                            if not partner.responsability_id:
                                raise ValidationError(
                                    'El partner %s no posee Tipo de Responsabilidad asignada' % partner.name)
                            if not partner.documento_id:
                                raise ValidationError(
                                    'El partner %s no posee Tipo de Documento asignado' % partner.name)
                            punto_venta = invoice.type in ['out_invoice',
                                                           'out_refund'] and invoice.punto_venta.name or invoice.punto_venta_proveedor
                            line += invoice.tipo_comprobante.codigo  # tipo comprobante
                            line += punto_venta.zfill(5)  # punto de venta
                            line += invoice.num_comprobante and invoice.num_comprobante.zfill(20) or '0'.zfill(
                                20)  # num comprobante
                            if invoice.type in ['in_invoice', 'in_refund']:
                                if not invoice.partner_id.commercial_partner_id.documento_id:
                                    raise ValidationError(
                                        'Debe seleccionar el tipo de documento del partner %s' % invoice.partner_id.commercial_partner_id.name)
                                line += partner.documento_id.codigo
                                line += partner.cuit.replace('-', '').zfill(20)  # num identificacion vendedor
                            line += self.format_float(0.0)  # Importe neto gravado
                            line += '0003'  # Alícuota de IVA
                            line += self.format_float(0.0)  # Impuesto Liquidado
                            line += '\r\n'
                            txtFile.write(self.clean_accents(line))
        txtFile.seek(0)
        bytes_base64_encoded = base64.encodebytes(txtFile.read().encode('utf-8'))
        data = bytes_base64_encoded.decode('utf-8').replace('\n', '')
        txtFile.close()
        attach_vals = {'name': fname, 'datas': data, 'datas_fname': fname}
        doc_id = self.env['ir.attachment'].create(attach_vals)
        res['type'] = 'ir.actions.act_url'
        res['target'] = 'new'
        res['url'] = "web/content/?model=ir.attachment&id=" + str(
            doc_id.id) + "&filename_field=datas_fname&field=datas&download=true&filename=" + str(doc_id.name)
        return res

    @api.multi
    def download_txt_a_i(self):
        res = {}
        tax_map = {'10.5': '0004', '21.0': '0005', '27.0': '0006', '2.5': '0009', '5.0': '0008'}
        txtFile = StringIO()
        op = 'COMPRAS'
        fname = '%s_%s_%s_Alicuotas_Importacion.txt' % (self.company_id.cuit, self.period.replace('-', '_'), op)
        for invoice in self.invoice_ids:
            if invoice.tipo_comprobante.is_import:
                for taxLine in invoice.tax_line_ids:
                    if taxLine.tax_id.is_iva:
                        line = ''
                        # num comprobante
                        if invoice.type in ['in_invoice', 'in_refund'] and invoice.tipo_comprobante.is_import:
                            if invoice.reference:
                                line += invoice.reference.zfill(16)
                            elif invoice.num_comprobante:
                                line += invoice.num_comprobante.zfill(16)
                            else:
                                raise UserError(
                                    u'Factura %s No posee un Numero de Despacho de Importacion, por favor colocar en la Referencia de Proveedor' % invoice.display_name)
                        line += self.format_float(taxLine.base * invoice.rate)  # Importe neto gravado
                        line += tax_map.get(str(taxLine.tax_id.amount), False) and tax_map[
                            str(taxLine.tax_id.amount)] or '0000'  # Alícuota de IVA
                        line += self.format_float(taxLine.amount * invoice.rate)  # Impuesto Liquidado
                        line += '\r\n'
                        txtFile.write(self.clean_accents(line))
        txtFile.seek(0)
        bytes_base64_encoded = base64.encodebytes(txtFile.read().encode('utf-8'))
        data = bytes_base64_encoded.decode('utf-8').replace('\n', '')
        txtFile.close()
        attach_vals = {'name': fname, 'datas': data, 'datas_fname': fname}
        doc_id = self.env['ir.attachment'].create(attach_vals)
        res['type'] = 'ir.actions.act_url'
        res['target'] = 'new'
        res['url'] = "web/content/?model=ir.attachment&id=" + str(
            doc_id.id) + "&filename_field=datas_fname&field=datas&download=true&filename=" + str(doc_id.name)
        return res

    @api.model
    def get_grouped_taxes(self, responsability=False):
        res = {'iva': [], 'other': []}
        for invoice in self.invoice_ids:
            if responsability:
                group_iva = groupby(invoice.tax_line_ids.filtered(lambda r: r.tax_id.is_iva is True and r.invoice_id.partner_id.commercial_partner_id.responsability_id == responsability))
                group_other = groupby(invoice.tax_line_ids.filtered(lambda r: r.tax_id.is_iva is False and r.invoice_id.partner_id.commercial_partner_id.responsability_id == responsability))
            else:
                group_iva = groupby(invoice.tax_line_ids.filtered(lambda r: r.tax_id.is_iva is True))
                group_other = groupby(invoice.tax_line_ids.filtered(lambda r: r.tax_id.is_iva is False))
            for key, values in group_iva:
                if key.tax_id not in res['iva']:
                    res['iva'].append(key.tax_id)
            for key, values in group_other:
                if key.tax_id not in res['other']:
                    res['other'].append(key.tax_id)
        return res

    @api.model
    def get_total_taxes(self, tax_id, responsability=False):
        res = []
        for invoice in self.invoice_ids:
            signe = 1
            if invoice.type in ('in_refund', 'out_refund') and invoice.refund_type == 'credit':
                signe = -1
            if not responsability:
                res += [x.amount * x.invoice_id.rate * signe for x in invoice.tax_line_ids if(x.tax_id.id == tax_id.id)]
            else:
                res += [x.amount * x.invoice_id.rate * signe for x in invoice.tax_line_ids if (x.tax_id.id == tax_id.id and x.invoice_id.partner_id.commercial_partner_id.responsability_id == responsability)]
        return {tax_id.id: sum(res)}

    @api.model
    def get_total_tax_bases(self, tax_id, responsability=False):
        res = []
        for invoice in self.invoice_ids:
            signe = 1
            if invoice.type in ('in_refund', 'out_refund') and invoice.refund_type == 'credit':
                signe = -1
            if not responsability:
                if not float_is_zero(tax_id.amount, precision_digits=2):
                    res += [x.base * x.invoice_id.rate * signe for x in invoice.tax_line_ids if(x.tax_id.id == tax_id.id)]
                else:
                    res += [(invoice._get_no_excempt_book() + invoice._get_no_gravado_book()) * invoice.rate * signe]
            else:
                if not float_is_zero(tax_id.amount, precision_digits=2):
                    res += [x.base * x.invoice_id.rate * signe for x in invoice.tax_line_ids if(x.tax_id.id == tax_id.id and x.invoice_id.partner_id.commercial_partner_id.responsability_id == responsability)]
                else:
                    res += [invoice.partner_id.commercial_partner_id.responsability_id == responsability and (invoice._get_no_excempt_book() + invoice._get_no_gravado_book()) * invoice.rate * signe]
        return {tax_id.id : sum(res)}

    @api.model
    def tax_is_zero(self, tax):
        return float_is_zero(tax.amount, precision_digits=2)

    @api.model
    def grouped_tipo_responsable(self):
        responsability = []
        for invoice in self.invoice_ids:
            partner = self.get_parent(invoice.partner_id)
            responsability += [partner.responsability_id]
        return list(set(responsability))

    @api.model
    def taxes_by_responsability(self, responsability, tax_id):
        account_precision = self.env['decimal.precision'].precision_get('Account')
        res = {'invoice_tax': 0.0, 'debitnote_tax': 0.0, 'creditnote_tax': 0.0,
               'invoice_base': 0.0, 'debitnote_base': 0.0, 'creditnote_base': 0.0}
        for invoice in self.invoice_ids:
            signe = 1
            if invoice.type in ('in_refund', 'out_refund') and invoice.refund_type == 'credit':
                signe = -1
            res['invoice_tax'] += sum([x.amount * invoice.rate * signe for x in invoice.tax_line_ids if (x.tax_id.id == tax_id.id
                                                                                                         and invoice.partner_id.commercial_partner_id.responsability_id.id == responsability.id
                                                                                                         and invoice.type in ['out_invoice','in_invoice'])])
            res['debitnote_tax'] += sum([x.amount * invoice.rate * signe for x in invoice.tax_line_ids if (x.tax_id.id == tax_id.id
                                                                                                           and invoice.partner_id.commercial_partner_id.responsability_id.id == responsability.id
                                                                                                           and invoice.type in ['out_refund','in_refund']
                                                                                                           and invoice.refund_type == 'debit')])
            res['creditnote_tax'] += sum([x.amount * invoice.rate * signe for x in invoice.tax_line_ids if (x.tax_id.id == tax_id.id
                                                                                                            and invoice.partner_id.commercial_partner_id.responsability_id.id == responsability.id
                                                                                                            and invoice.type in ['out_refund','in_refund']
                                                                                                            and invoice.refund_type == 'credit')])
            if not float_is_zero(tax_id.amount, account_precision):
                res['invoice_base'] += sum([x.base * invoice.rate * signe for x in invoice.tax_line_ids if (x.tax_id.id == tax_id.id
                                                                                                            and invoice.partner_id.commercial_partner_id.responsability_id.id == responsability.id
                                                                                                            and invoice.type in ['out_invoice','in_invoice'])])
            else:
                res['invoice_base'] += sum([invoice.partner_id.commercial_partner_id.responsability_id.id == responsability.id and invoice.type in ['out_invoice','in_invoice'] and
                                            invoice.rate * signe * (invoice._get_no_excempt_book() + invoice._get_no_gravado_book())])
            if not float_is_zero(tax_id.amount, account_precision):
                res['debitnote_base'] += sum([x.base * invoice.rate * signe for x in invoice.tax_line_ids if (x.tax_id.id == tax_id.id
                                                                                                          and invoice.partner_id.commercial_partner_id.responsability_id.id == responsability.id
                                                                                                          and invoice.type in ['out_refund','in_refund']
                                                                                                          and invoice.refund_type == 'debit')])
            else:
                res['debitnote_base'] += sum([
                    invoice.partner_id.commercial_partner_id.responsability_id.id == responsability.id
                    and invoice.type in ['out_refund', 'in_refund']
                    and invoice.refund_type == 'debit' and
                                               invoice.rate * signe * (invoice._get_no_excempt_book() + invoice._get_no_gravado_book())])
            if not float_is_zero(tax_id.amount, account_precision):
                res['creditnote_base'] += sum([x.base * invoice.rate * signe for x in invoice.tax_line_ids if (x.tax_id.id == tax_id.id
                                                                                                           and invoice.partner_id.commercial_partner_id.responsability_id.id == responsability.id
                                                                                                           and invoice.type in ['out_refund','in_refund']
                                                                                                           and invoice.refund_type == 'credit')])
            else:
                res['creditnote_base'] += sum([
                    invoice.partner_id.commercial_partner_id.responsability_id.id == responsability.id
                    and invoice.type in ['out_refund', 'in_refund']
                    and invoice.refund_type == 'credit' and
                    invoice.rate * signe * (invoice._get_no_excempt_book() + invoice._get_no_gravado_book())])
        return res

    @api.constrains('is_locked', 'date_lock')
    def _check_date_look(self):
        date_current = fields.Date.today()
        for record in self:
            if record.is_locked and record.date_lock < date_current:
                raise ValidationError("Usted debe seleccionar una fecha de bloqueo mayor o igual a la fecha actual (%s)" % date_current)


class AccountBookInvoice(models.Model):
    _inherit = 'account.invoice'

    book_id = fields.Many2one('account.book', string="Libros")
    rate = fields.Float('Rate', compute='_get_rate')

    def _get_no_gravado_book(self):
        for inv in self:
            if inv.id == 5787:
                print('1')
            if inv.type in ['out_invoice', 'out_refund']:
                no_gravado = inv.no_gravado
            else:
                if self.type in ['in_invoice', 'in_refund'] and self.tipo_comprobante.desc in ['B', 'C']:
                    no_gravado = sum(line.price_subtotal for line in self.invoice_line_ids if
                                     (not line.invoice_line_tax_ids and not line.invoice_id.tipo_comprobante.is_exempt))
                else:
                    no_gravado = inv.no_gravado
            return no_gravado

    def _get_no_excempt_book(self):
        for inv in self:
            if inv.id == 5787:
                print ('1')
            if inv.type in ['out_invoice', 'out_refund']:
                amount_excempt = inv.amount_excempt
            else:
                if self.type in ['in_invoice', 'in_refund'] and self.tipo_comprobante.desc in ['B', 'C']:
                    amount_excempt = sum(
                        line.base for line in self.tax_line_ids if (line.tax_id.is_excempt is True))
                else:
                    amount_excempt = inv.amount_excempt
            return amount_excempt

    def _get_currency_rate_date(self):
        date = self.date or self.date_invoice
        if date:
            date = date + timedelta(days=1)
            date = date.strftime(DEFAULT_SERVER_DATE_FORMAT)
        return date

    @api.multi
    def _get_rate(self):
        for inv in self:
            rate = 1.0
            if inv.currency_id != inv.company_id.currency_id:
                rate = inv.amount_total_company_signed / inv.amount_total
            inv.rate = abs(rate)

    @api.constrains('state','date','date_invoice')
    def _check_date_look(self):
        date_current = fields.Date.today()
        account_book_obj = self.env['account.book']

        for record in self:
            if record.state != 'paid':
                operation = False
                if record.type in ['out_refund', 'out_invoice']:
                    operation = 'sale'
                    date = record.date_invoice
                elif record.type in ['in_refund', 'in_invoice']:
                    operation = 'purchase'
                    date = record.date

                if not (operation and date):
                    continue

                date_from = fields.Date.from_string(date).strftime('%Y-%m') + '-01'
                date_to = (fields.Date.from_string(date) + relativedelta(months=1)).strftime('%Y-%m') + '-01'

                account_book_id = account_book_obj.search([
                    ('operation', '=', operation),
                    ('date', '>=', date_from),
                    ('date', '<', date_to),
                    ('date_lock', '<=', date_current),
                    ('is_locked', '=', True)
                ], order='date asc', limit=1)

                if account_book_id:
                    d_operation = {
                        'sale': 'Venta',
                        'purchase': 'Compra'
                    }
                    raise ValidationError("La factura no puede ser procesada porque el libro de %s, del período %s, la esta bloqueando." %(d_operation[operation], account_book_id.period))



