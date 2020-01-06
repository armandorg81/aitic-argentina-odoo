# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError


class AccountInvoiceDebitFacturae(models.TransientModel):
    _inherit = "account.invoice.debit"

    @api.model
    def default_get(self, fields):
        res = super(AccountInvoiceDebitFacturae, self).default_get(fields)
        if 'journal_id' not in res:
            ctx = self._context
            if 'active_id' in ctx:
                inv = self.env['account.invoice'].browse(ctx['active_id'])
                refund_comp = self.env['tipo.comprobante'].search([
                                ('referencia_id','=',inv.tipo_comprobante.id),
                                ('type','=','debit_note')
                            ])
                type = ctx['type'] and ctx['type'] or inv.type
                type_clause = type in ['out_invoice','out_refund'] and ('type','=','sale') or ('type','=','purchase')
                journal = self.env['account.journal'].search([
                    ('comprobante_id','=',refund_comp.id),
                    ('company_id','=',self.env.user.company_id.id),
                    type_clause
                ])
                res['journal_id'] = journal and journal[0].id or False
        return res

    @api.multi
    def compute_debit(self, mode='debit'):
        inv_obj = self.env['account.invoice']
        inv_tax_obj = self.env['account.invoice.tax']
        inv_line_obj = self.env['account.invoice.line']
        context = dict(self._context or {})
        xml_id = False

        for form in self:
            created_inv = []
            date = False
            description = False
            for inv in inv_obj.browse(context.get('active_ids')):
                if inv.state in ['draft', 'proforma2', 'cancel']:
                    raise UserError(_('Cannot refund draft/proforma/cancelled invoice.'))
                if inv.reconciled and mode in ('cancel', 'modify'):
                    raise UserError(_('Cannot refund invoice which is already reconciled, invoice should be unreconciled first. You can only refund this invoice.'))

                date = form.date or False
                description = form.description or inv.name
                journal_id = form.journal_id or inv.journal_id

                invoice = inv.copy()
                refund_comp = self.env['tipo.comprobante'].search([
                                ('referencia_id','=',inv.tipo_comprobante.id),
                                ('type','=','debit_note')
                            ])

                invoice.update({
                    'type': inv.type == 'in_invoice' and 'in_refund' or inv.type == 'out_invoice' and 'out_refund' or inv.type,
                    'refund_type': 'debit',
                    'name': description,
                    'date_invoice': form.date_invoice,
                    'date': date,
                    'journal_id': journal_id.id,
                    'punto_venta': inv.punto_venta,
                    'tipo_comprobante':  refund_comp and refund_comp.id or False
                })

                created_inv.append(invoice.id)

                xml_id = (inv.type in ['out_refund', 'out_invoice']) and 'action_invoice_tree1' or \
                         (inv.type in ['in_refund', 'in_invoice']) and 'action_invoice_tree2'
                # Put the reason in the chatter
                subject = _("Debit Note")
                body = description
                invoice.message_post(body=body, subject=subject)
        if xml_id:
            result = self.env.ref('account.%s' % (xml_id)).read()[0]
            if result.get('domain', False):
                invoice_domain = safe_eval(result['domain'])
                invoice_domain.append(('id', 'in', created_inv))
                result['domain'] = invoice_domain
            return result
        return True
