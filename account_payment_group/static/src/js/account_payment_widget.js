odoo.define('account_payment_group', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.view_dialogs');
var field_registry = require('web.field_registry');
var AbstractField = require('web.AbstractField');
var field_utils = require('web.field_utils');

var QWeb = core.qweb;

var _t = core._t;
var Payment = field_registry.get('payment');

var FormViewDialog = form_common.FormViewDialog;

Payment.include({

    _render: function() {
        var self = this;
        var info = JSON.parse(this.value);
        if (!info) {
            this.$el.html('');
            return;
        }
        _.each(info.content, function (k, v){
            k.index = v;
            k.amount = field_utils.format.float(k.amount, {digits: k.digits});
            if (k.date){
                k.date = field_utils.format.date(field_utils.parse.date(k.date, {}, {isUTC: true}));
            }
        });
        this.$el.html(QWeb.render('ShowPaymentInfo', {
            lines: info.content,
            outstanding: info.outstanding,
            title: info.title,
            different_company: info.different_company
        }));
        _.each(this.$('.js_payment_info'), function (k, v){
            var content = info.content[v];
            var options = {
                content: function () {
                    var $content = $(QWeb.render('PaymentPopOver', {
                        name: content.name,
                        journal_name: content.journal_name,
                        date: content.date,
                        amount: content.amount,
                        currency: content.currency,
                        position: content.position,
                        payment_id: content.payment_id,
                        move_id: content.move_id,
                        ref: content.ref,
                        account_payment_id: content.account_payment_id,
                        invoice_id: content.invoice_id,
                    }));
                    $content.filter('.js_unreconcile_payment').on('click', self._onRemoveMoveReconcile.bind(self));
                    $content.filter('.js_open_payment').on('click', self._onOpenPayment.bind(self));
                    $content.filter('.js_account_payment_group').on('click', self._onOpenPaymentGroup.bind(self));
                    return $content;
                },
                html: true,
                placement: 'left',
                title: 'Información del pago',
                trigger: 'focus',
                delay: { "show": 0, "hide": 100 },
            };
            $(k).popover(options);
        });
    },

    _onOpenPaymentGroup: function (event) {
        var invoiceId = parseInt($(event.target).attr('invoice-id'));
        var paymentId = parseInt($(event.target).attr('payment-id'));
        var moveId = parseInt($(event.target).attr('move-id'));
        var res_model;
        var id;
        if (invoiceId !== undefined && !isNaN(invoiceId)){
            res_model = "account.invoice";
            id = invoiceId;
        } else if (paymentId !== undefined && !isNaN(paymentId)){
            res_model = "account.payment.group";
            id = paymentId;
        } else if (moveId !== undefined && !isNaN(moveId)){
            res_model = "account.move";
            id = moveId;
        }
        //Open form view of account.move with id = move_id
        if (res_model && id) {
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: res_model,
                res_id: id,
                views: [[false, 'form']],
                target: 'current'
            });
        }
    },

    _onOutstandingCreditAssign: function (event) {
        var self = this;
        var id = $(event.target).data('id') || false;
        var payment = $(event.target).data('payment') || 0;
        this._rpc({
                model: 'account.invoice',
                method: 'assign_outstanding_credit',
                args: [JSON.parse(this.value).invoice_id, id, payment],
            }).then(function () {
                self.trigger_up('reload');
            });
    },

    _onRemoveMoveReconcile: function (event) {
        var self = this;
        var paymentId = parseInt($(event.target).attr('payment-id'));
        var paymentAccountId = parseInt($(event.target).attr('account-payment-id'));
        if (paymentId !== undefined && !isNaN(paymentId)){
            this._rpc({
                model: 'account.invoice',
                method: 'remove_move_reconcile',
                args: [this.res_id, {'payment_id': paymentId, 'group_payment_id': paymentAccountId}]
            }).then(function () {
                self.trigger_up('reload');
            });
        }
    },

});

FormViewDialog.include({
    init: function (parent, options) {
        var self = this;
        options = options || {};

        this.res_id = options.res_id || null;
        this.on_saved = options.on_saved || (function () {});
        this.on_remove = options.on_remove || (function () {});
        this.context = options.context;
        this.model = options.model;
        this.parentID = options.parentID;
        this.recordID = options.recordID;
        this.shouldSaveLocally = options.shouldSaveLocally;
        this.readonly = options.readonly;
        this.deletable = options.deletable;
        this.disable_multiple_selection = options.disable_multiple_selection;

        var multi_select = !_.isNumber(options.res_id) && !options.disable_multiple_selection;
        var readonly = _.isNumber(options.res_id) && options.readonly;

        if (!options.buttons) {
            options.buttons = [{
                text: (readonly ? _t("Close") : _t("Discard")),
                classes: "btn-secondary o_form_button_cancel",
                close: true,
                click: function () {
                    if (!readonly) {
                        self.form_view.model.discardChanges(self.form_view.handle, {
                            rollback: self.shouldSaveLocally,
                        });
                    }
                },
            }];

            if (!readonly) {
                options.buttons.unshift({
                    text: (multi_select ? _t("Save & Close") : _t("Save")),
                    classes: "btn-primary",
                    click: function () {
                        this._save().then(self.close.bind(self));
                    }
                });
                if (multi_select && !(options.res_model == "account.payment" && options.context.payment_group)) {
                    options.buttons.splice(1, 0, {
                        text: _t("Save & New"),
                        classes: "btn-primary",
                        click: function () {
//                            if (this.form_view.modelName == "account.payment"){
//                                var amount_div = this.$el.find('div[name="amount"]');
//                                if (amount_div.length>0 && amount_div[0].children.length>1) {
//                                    var input = amount_div[0].children[0].value
//                                    self.context.default_amount = this.context.default_amount - input
//                                }
//                            }
                            this._save().then(self.form_view.createRecord.bind(self.form_view, self.parentID));
                        },
                    });
                }

                var multi = options.disable_multiple_selection;
                if (!multi && this.deletable) {
                    options.buttons.push({
                        text: _t("Remove"),
                        classes: 'btn-secondary o_btn_remove',
                        click: this._remove.bind(this),
                    });
                }
            }
        }
        this._super(parent, options);
    },
});

});






