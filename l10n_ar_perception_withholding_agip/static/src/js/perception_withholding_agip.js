odoo.define('perception.withholding.agip', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.form_common');
var formats = require('web.formats');
var Model = require('web.Model');
var widget = require('web_editor.widget');

var FieldBinaryFile = core.form_widget_registry.get('binary');

var QWeb = core.qweb;
var _t = core._t;

FieldBinaryFile.include({
    init: function(field_manager, node) {
        var self = this;
        this._super(field_manager, node);
        this.binary_value = false;
        this.useFileAPI = !!window.FileReader;
        this.max_upload_size = 250 * 1024 * 1024; // 25Mo
        if (!this.useFileAPI) {
            this.fileupload_id = _.uniqueId('o_fileupload');
            $(window).on(this.fileupload_id, function() {
                var args = [].slice.call(arguments).slice(1);
                self.on_file_uploaded.apply(self, args);
            });
        }
    },
});

});



