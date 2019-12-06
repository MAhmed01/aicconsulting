import os
import tempfile
import base64
from datetime import datetime
from odoo.tools.misc import xlwt
import xml.dom.minidom as ET
from odoo import api, fields, models
from io import BytesIO


class WizardProductMatrix(models.TransientModel):
    _name = "invoice.generator.wiz"

    xml_file = fields.Binary(string='Upload XML')

    def action_generate_invoice(self):
        if self.xml_file:
            main_path = os.path.join(tempfile.gettempdir())
            os.chdir(main_path)
            scr_file_path = main_path + '/'+ 'invoice_generator' +'.xml'
            outfile = open(scr_file_path, 'wb')
            outfile.write(base64.decodestring(self.xml_file))
            outfile.close()
            doc = ET.parse(scr_file_path)
            child_vals = []
            order_vals = {}
            line_items = []
            partner_obj = self.env['res.partner']
            product_obj = self.env['product.product']
            for cont in doc.getElementsByTagName('BillToAddress'):
                for add in cont.getElementsByTagName('Contact'):
                   child_vals.append({
                                    'type': 'invoice',
                                    'name': add.getAttribute('firstName'),
                                    'phone': add.getAttribute('workPhone'),
                                    'mobile': add.getAttribute('mobile'),
                                    'email': add.getAttribute('email'),
                                    'street': add.getAttribute('AddressLine1') + ' ' +
                                             add.getAttribute('AddressLine2'),
                                    'steet2': add.getAttribute('AddressLine3') + ' ' +
                                             add.getAttribute('AddressLine4') + ' ' +
                                             add.getAttribute('AddressLine5'),
                                    'zip': add.getAttribute('PostalCode')
                                      })

            for cont in doc.getElementsByTagName('ShipToAddress'):
                for add in cont.getElementsByTagName('Contact'):
                    child_vals.append({
                        'type': 'delivery',
                        'name': add.getAttribute('firstName'),
                        'phone': add.getAttribute('workPhone'),
                        'mobile': add.getAttribute('mobile'),
                        'email': add.getAttribute('email'),
                        'street': add.getAttribute('AddressLine1') + ' ' +
                                  add.getAttribute('AddressLine2'),
                        'steet2': add.getAttribute('AddressLine3') + ' ' +
                                  add.getAttribute('AddressLine4') + ' ' +
                                  add.getAttribute('AddressLine5'),
                        'zip': add.getAttribute('PostalCode')
                    })
            

            if doc.getElementsByTagName('Header') and doc.getElementsByTagName('Header')[0].getElementsByTagName('TradingPartners') and \
                doc.getElementsByTagName('Header')[0].getElementsByTagName('TradingPartners')[0].getElementsByTagName('Supplier'):
                domain = []
                name = ''
                email = ''
                phone = ''
                fax = ''
                ref = ''
                if doc.getElementsByTagName('Header')[0].getElementsByTagName('TradingPartners')[0].getElementsByTagName('Supplier') and \
                    doc.getElementsByTagName('Header')[0].getElementsByTagName('TradingPartners')[0].getElementsByTagName('Supplier')[0].getElementsByTagName('Contact'):
                    email = doc.getElementsByTagName('Header')[0].getElementsByTagName('TradingPartners')[0].getElementsByTagName('Supplier')[0].getElementsByTagName('Contact')[0].getAttribute('email').strip() or ''
                    phone  = doc.getElementsByTagName('Header')[0].getElementsByTagName('TradingPartners')[0].getElementsByTagName('Supplier')[0].getElementsByTagName('Contact')[0].getAttribute('workPhone').strip() or ''
                    fax = doc.getElementsByTagName('Header')[0].getElementsByTagName('TradingPartners')[0].getElementsByTagName('Supplier')[0].getElementsByTagName('Contact')[0].getAttribute('fax').strip() or ''
                    if email:
                        domain.append(('email', '=', email))
                if doc.getElementsByTagName('Header')[0].getElementsByTagName('TradingPartners')[0].getElementsByTagName('Supplier')[0].getElementsByTagName('ExtendedProperties') and \
                    doc.getElementsByTagName('Header')[0].getElementsByTagName('TradingPartners')[0].getElementsByTagName('Supplier')[0].getElementsByTagName('ExtendedProperties')[0].getAttribute('supplierCode'):
                    ref = doc.getElementsByTagName('Header')[0].getElementsByTagName('TradingPartners')[0].getElementsByTagName('Supplier')[0].getElementsByTagName('ExtendedProperties')[0].getAttribute('supplierCode').strip()
                    domain.append(('ref', '=', ref))
                if doc.getElementsByTagName('Header')[0].getElementsByTagName('TradingPartners')[0].getElementsByTagName('Supplier')[0].getAttribute('name'):
                    name = doc.getElementsByTagName('Header')[0].getElementsByTagName('TradingPartners')[0].getElementsByTagName('Supplier')[0].getAttribute('name').strip()
                    if not domain:
                        domain.append(('name', '=', name))
                partner_rec = partner_obj.search(domain)
                if partner_rec:
                    order_vals.update({'partner_id': partner_rec.id})
                else:
                    partner = partner_obj.create({
                        'name': name,
                        'phone': phone,
                        'mobile': phone,
                        'email': email,
                        'fax': fax,
                        'ref': ref,
                        'supplier': True,
                        'child_ids':[(0,0,child) for child in child_vals]
                    })
                    order_vals.update({'partner_id':partner.id})


            for header in doc.getElementsByTagName('Header'):
                order_vals.update({'name': header.getAttribute('purchaseOrderName'),
                                   'date_order': header.getAttribute('purchaseOrderDate'),
                                   })

            for items in doc.getElementsByTagName('LineItems'):
                for item in items.getElementsByTagName('Item'):
                    product_rec = product_obj.search([('default_code','=', item.getAttribute('buyerPartNumber'))])
                    if product_rec:
                        product_id = product_rec
                    else:
                        product_id = product_obj.create({'name':item.getAttribute('shortDescription'),
                                                         'type':'product','default_code': item.getAttribute('buyerPartNumber')})
                    line_items.append({
                        'product_id':product_id.id,
                        'name':product_id.name,
                        'product_uom':self.env.ref('uom.product_uom_unit').id,
                        'product_qty':item.getAttribute('quantity'),
                        'price_unit':item.getAttribute('extendedAmountIncTax'),
                        'date_planned':[header.getAttribute('purchaseOrderDate') for header in doc.getElementsByTagName('Header')],
                        'qty_received':item.getAttribute('quantity'),
                        'qty_invoiced': 0.0,
                    })
            order_vals.update({'order_line':[(0,0,line) for line in line_items]})
            order = self.env['purchase.order'].create(order_vals)
            order.button_confirm()
            invoice = self.env['account.invoice'].create({'type':'in_invoice',
                                                          'purchase_id':order.id,
                                                          'partner_id':order.partner_id.id,

            })
            new_lines = self.env['account.invoice.line']
            for line in order.order_line:
                data = self.env['account.invoice']._prepare_invoice_line_from_po_line(line)
                new_line = new_lines.new(data)
                new_lines += new_line
            invoice.invoice_line_ids += new_lines
        return True


class account_invoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def generate_excel(self):
        filename = 'Sale Invoice Export.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        worksheet = workbook.add_sheet('Sale Invoice Header')
        worksheet1 = workbook.add_sheet('Sale Invoice Detail')
        worksheet2 = workbook.add_sheet('Payment Term')
        style = xlwt.easyxf('font:height 200, bold True, name Arial;align: horiz center;')
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'

        worksheet.col(0).width = 4000
        worksheet.col(1).width = 4000
        worksheet.col(2).width = 4000
        worksheet.col(3).width = 4000
        worksheet.col(4).width = 4000
        worksheet.col(5).width = 4000
        worksheet.col(6).width = 4000
        worksheet.col(7).width = 3000
        worksheet.col(8).width = 3000
        worksheet.col(9).width = 3000

        worksheet1.col(0).width = 4000
        worksheet1.col(1).width = 6000
        worksheet1.col(2).width = 4000
        worksheet1.col(3).width = 4000
        worksheet1.col(4).width = 4000
        worksheet1.col(5).width = 4000
        worksheet1.col(6).width = 4000
        worksheet1.col(7).width = 3000
        worksheet1.col(8).width = 3000
        worksheet1.col(9).width = 3000

        worksheet2.col(0).width = 4000
        worksheet2.col(1).width = 6000
        worksheet2.col(2).width = 4000
        worksheet2.col(3).width = 4000
        worksheet2.col(4).width = 8000

        worksheet.write(0, 0, "Customer", style)
        worksheet.write(0, 1, "Invoice date", style)
        worksheet.write(0, 2, "Invoice Number", style)
        worksheet.write(0, 3, "Site/Company", style)
        worksheet.write(0, 4, "Sales Person", style)
        worksheet.write(0, 5, "Due date", style)
        worksheet.write(0, 6, "Source Document", style)
        worksheet.write(0, 7, "Tax Ex Amt", style)
        worksheet.write(0, 8, "Tax", style)
        worksheet.write(0, 9, "Total", style)

        row0 = 1
        column0 = 0
        worksheet.write(row0, column0, self.partner_id.name)
        worksheet.write(row0, column0 + 1, self.date_invoice, date_format)
        worksheet.write(row0, column0 + 2, self.number)
        worksheet.write(row0, column0 + 3, self.company_id.name)
        worksheet.write(row0, column0 + 4, self.user_id.name)
        worksheet.write(row0, column0 + 5, self.date_due, date_format)
        worksheet.write(row0, column0 + 6, self.origin)
        worksheet.write(row0, column0 + 7, self.amount_total)
        worksheet.write(row0, column0 + 8, self.amount_tax)
        worksheet.write(row0, column0 + 9, self.amount_total)

        worksheet1.write(0, 0, 'Customer:', style)
        worksheet1.write(0, 1, 'Invoice Date:', style)
        worksheet1.write(0, 2, 'Site/Compnay:', style)
        worksheet1.write(0, 3, 'Invoice Number:', style)
        worksheet1.write(0, 4, "Product", style)
        worksheet1.write(0, 5, "Product description", style)
        worksheet1.write(0, 6, "Account", style)
        worksheet1.write(0, 7, "Qty", style)
        worksheet1.write(0, 8, "Tax Ex Amt", style)
        worksheet1.write(0, 9, "Tax", style)
        worksheet1.write(0, 10, "Total", style)
        row1 = 1
        column1 = 0
        for invoice in self.invoice_line_ids:
            worksheet1.write(row1, column1, self.partner_id.name)
            worksheet1.write(row1, column1 + 1, self.date_invoice, date_format)
            worksheet1.write(row1, column1 + 2, self.company_id.name)
            worksheet1.write(row1, column1 + 3, self.number)
            if invoice.product_id:
                worksheet1.write(row1, column1 + 4, invoice.product_id.name)
            if invoice.name:
                worksheet1.write(row1, column1 + 5, invoice.name)
            if invoice.account_id:
                worksheet1.write(row1, column1 + 6, invoice.account_id.name)
            if invoice.quantity:
                worksheet1.write(row1, column1 + 7, invoice.quantity)
            if invoice.price_subtotal:
                worksheet1.write(row1, column1 + 8, invoice.price_subtotal)
            if invoice.price_total:
                worksheet1.write(row1, column1 + 9, invoice.price_total - invoice.price_subtotal)
            if invoice.price_total:
                worksheet1.write(row1, column1 + 10, invoice.price_total)
            row1 += 1


        worksheet2.write(0, 0, "Customer", style)
        worksheet2.write(0, 1, "Invoice date", style)
        worksheet2.write(0, 2, "Invoice Number", style)
        worksheet2.write(0, 3, "Due date", style)
        worksheet2.write(0, 4, "Payment Terms", style)

        row2 = 1
        column2 = 0
        worksheet2.write(row2, column2, self.partner_id.name)
        worksheet2.write(row2, column2 + 1, self.date_invoice, date_format)
        worksheet2.write(row2, column2 + 2, self.number)
        worksheet2.write(row2, column2 + 3, self.date_due, date_format)
        worksheet2.write(row2, column2 + 4, self.payment_term_id.name)

        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['sale.invoice.excel.report.wiz'].create(
            {'report_excel_file': base64.encodestring(fp.getvalue()), 'report_file_name': filename})
        fp.close()
        return {
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'sale.invoice.excel.report.wiz',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self._context,
            'target': 'new',
        }
