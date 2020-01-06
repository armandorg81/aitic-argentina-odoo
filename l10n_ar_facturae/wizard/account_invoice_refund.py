# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError


class AccountInvoiceRefundFacturae(models.TransientModel):
    _inherit = "account.invoice.refund"

    @api.model
    def default_get(self, fields):
        res = super(AccountInvoiceRefundFacturae, self).default_get(fields)
        if 'journal_id' not in res:
            ctx = self._context
            if 'active_id' in ctx:
                inv = self.env['account.invoice'].browse(ctx['active_id'])
                refund_comp = self.env['tipo.comprobante'].search([
                                ('referencia_id','=',inv.tipo_comprobante.id),
                                ('type','=','credit_note')
                            ])
                type_clause = inv.type in ['out_invoice','out_refund'] and ('type','=','sale') or ('type','=','purchase')
                journal = self.env['account.journal'].search([
                    ('comprobante_id','=',refund_comp.id),
                    ('company_id','=',self.env.user.company_id.id),
                    type_clause
                ])
                res['journal_id'] = journal and journal[0].id or False
        return res

    @api.multi
    def compute_refund(self, mode='refund'):
        inv_obj = self.env['account.invoice']
        inv_tax_obj = self.env['account.invoice.tax']
        inv_line_obj = self.env['account.invoice.line']
        context = dict(self._context or {})
        xml_id = False

        for form in self:
            created_inv = []
            date = False
            description = False
            TYPES = {
                'out_invoice': _('Invoice'),
                'in_invoice': _('Vendor Bill'),
                'out_refund': _('Credit Note'),
                'in_refund': _('Vendor Credit note'),
            }
            for inv in inv_obj.browse(context.get('active_ids')):
                if inv.state in ['draft', 'proforma2', 'cancel']:
                    raise UserError(_('Cannot refund draft/proforma/cancelled invoice.'))
                if inv.reconciled and mode in ('cancel', 'modify'):
                    raise UserError(_('Cannot refund invoice which is already reconciled, invoice should be unreconciled first. You can only refund this invoice.'))

                date = form.date or False
                description = form.description or inv.name
                journal_id = form.journal_id or inv.journal_id
                refund = self._get_refund(inv, form, date, description, journal_id)

                if journal_id and journal_id.comprobante_id:
                    refund_comp = journal_id.comprobante_id
                else:
                    refund_comp = self.env['tipo.comprobante'].search([
                                ('referencia_id','=',inv.tipo_comprobante.id),
                                ('type','=','credit_note')
                            ])
                if inv.type == 'out_refund':
                    refund.update({'type': 'out_refund'})
                elif inv.type == 'in_refund':
                    refund.update({'type': 'in_refund'})


                refund.update({
                    'refund_type': 'credit',
                    'name': TYPES[inv.type],
                    'punto_venta': inv.punto_venta,
                    'tipo_comprobante':  refund_comp and refund_comp.id or False
                })

                created_inv.append(refund.id)

                if mode in ('cancel', 'modify'):
                    movelines = inv.move_id.line_ids
                    to_reconcile_ids = {}
                    to_reconcile_lines = self.env['account.move.line']
                    for line in movelines:
                        if line.account_id.id == inv.account_id.id:
                            to_reconcile_lines += line
                            to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
                        if line.reconciled:
                            line.remove_move_reconcile()
                    # refund.action_invoice_open()
                    for tmpline in refund.move_id.line_ids:
                        if tmpline.account_id.id == inv.account_id.id:
                            to_reconcile_lines += tmpline
                            to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()
                    if mode == 'modify':
                        invoice = inv.read(
                                    ['name', 'type', 'number', 'reference',
                                    'comment', 'date_due', 'partner_id',
                                    'payment_term_id', 'account_id', 'team_id',
                                    'currency_id', 'invoice_line_ids', 'tax_line_ids',
                                    'journal_id', 'date'])
                        invoice = invoice[0]
                        del invoice['id']
                        invoice_lines = inv_line_obj.browse(invoice['invoice_line_ids'])
                        invoice_lines = self._get_refund_cleanup(inv, invoice_lines)
                        tax_lines = inv_tax_obj.browse(invoice['tax_line_ids'])
                        tax_lines = inv_obj._refund_cleanup_lines(tax_lines)
                        invoice.update({
                            'type': inv.type,
                            'date_invoice': form.date_invoice,
                            'state': 'draft',
                            'number': False,
                            'invoice_line_ids': invoice_lines,
                            'tax_line_ids': tax_lines,
                            'date': date,
                            'origin': inv.origin,
                            'fiscal_position_id': inv.fiscal_position_id.id,
                            'journal_id': journal_id.id,
                            'punto_venta': inv.punto_venta.id,
                            'tipo_comprobante': inv.tipo_comprobante.id,
                            'move_id': False,
                            'name': TYPES[inv.type],
                        })
                        for field in ('partner_id', 'account_id', 'currency_id',
                                         'payment_term_id', 'team_id'):
                                invoice[field] = invoice[field] and invoice[field][0]
                        inv_refund = inv_obj.create(invoice)
                        if inv_refund.payment_term_id.id:
                            inv_refund._onchange_payment_term_date_invoice()
                        created_inv.append(inv_refund.id)
                xml_id = (inv.type in ['out_refund', 'out_invoice']) and 'action_invoice_tree1' or \
                         (inv.type in ['in_refund', 'in_invoice']) and 'action_invoice_tree2'
                # Put the reason in the chatter
                subject = _("Invoice refund")
                body = description
                refund.message_post(body=body, subject=subject)
        if xml_id:
            result = self.env.ref('account.%s' % (xml_id)).read()[0]
            if result.get('domain', False):
                invoice_domain = safe_eval(result['domain'])
                invoice_domain.append(('id', 'in', created_inv))
                result['domain'] = invoice_domain
            return result
        return True
