# -*- coding: utf-8 -*-
#from itertools import product
from odoo import api, fields, models, _
import codecs
import unicodedata
import base64
import openpyxl


def xls2float(val):
    try:
        res = float(val or 0)
    except ValueError:
        res = 0
    return res


class IsImportClair(models.Model):
    _name = 'is.import.clair'
    _description = "Importation de fichiers Excel pour Clair SARL"


    name     = fields.Char("Description", required=True)
    file_ids = fields.Many2many('ir.attachment', 'is_import_clair_attachment_rel', 'doc_id', 'file_id', 'Fichiers')


    # def create_pricelist(self, wb, worksheet_name, pricelist_name):
    #     for obj in self: 
    #         pricelists = self.env['product.pricelist'].search([("name","=",pricelist_name)])
    #         vals={
    #             "name": pricelist_name,
    #         }
    #         if len(pricelists)==0:
    #             pricelist=self.env['product.pricelist'].create(vals)
    #         else:
    #             pricelist = pricelists[0]
    #             pricelist.write(vals)
    #         pricelist.item_ids.unlink()
    #         ws = wb[worksheet_name]
    #         cells = list(ws)
    #         lig=ct=0
    #         for row in ws.rows:
    #             code        = cells[lig][1].value
    #             prix        = xls2float(cells[lig][8].value)
    #             if code and prix:
    #                 products = self.env['product.template'].search([("default_code","=",code)])
    #                 for product in products:
    #                     vals={
    #                         "pricelist_id"   : pricelist.id,
    #                         "applied_on"     : "1_product",
    #                         "product_tmpl_id": product.id,
    #                         "fixed_price"    : prix,
    #                     }
    #                     items=self.env['product.pricelist.item'].create(vals)
    #                     print(ct, lig, code, prix, items)
    #                     ct+=1
    #             lig+=1


    def importation_excel_action(self):
        for obj in self:
            for attachment in obj.file_ids:
                xlsxfile=base64.b64decode(attachment.datas)

                path = '/tmp/is_import_clair-'+str(obj.id)+'.xlsx'
                f = open(path,'wb')
                f.write(xlsxfile)
                f.close()

                #** Test si fichier est bien du xlsx **************************
                try:
                    wb    = openpyxl.load_workbook(filename = path, data_only=True)
                    #print(wb.sheetnames)
                except:
                    raise Warning("Le fichier "+attachment.name+u" n'est pas un fichier xlsx")
                #**************************************************************


            ws = wb.active # ws = wb['base 2022']
            cells = list(ws)


            #** Cr??ation des fournisseurs *************************************
            lig=0
            fournisseurs=[]
            for row in ws.rows:
                if lig>0:
                    fournisseur = cells[lig][0].value
                    if fournisseur:
                        if fournisseur not in fournisseurs:
                            fournisseurs.append(fournisseur)
                lig+=1
            for fournisseur in fournisseurs:
                partner_id = False
                partners = self.env['res.partner'].search([("name","=",fournisseur)])
                for partner in partners:
                    partner_id = partner.id
                if partner_id==False:
                    vals={
                        "name"         : fournisseur,
                        "company_type" : "company",
                        "supplier_rank": 1,
                    }
                    partner=self.env['res.partner'].create(vals)
                    partner_id = partner.id
                print(fournisseur, partner_id)
            #******************************************************************



            #** Cr??ation des Sous-familles ************************************
            lig=0
            sous_familles=[]
            for row in ws.rows:
                if lig>0:
                    sous_famille = cells[lig][2].value
                    if sous_famille:
                        if sous_famille not in sous_familles:
                            sous_familles.append(sous_famille)
                lig+=1
            for sous_famille in sous_familles:
                sous_famille_id = False
                lines = self.env['is.sous.famille'].search([("name","=",sous_famille)])
                for line in lines:
                    sous_famille_id = line.id
                if sous_famille_id==False:
                    vals={
                        "name": sous_famille,
                    }
                    res=self.env['is.sous.famille'].create(vals)
                    sous_famille_id = res.id
                print(sous_famille, sous_famille_id)
            #******************************************************************



            #** Cr??ation des familles *****************************************
            lig=0
            familles={}
            for row in ws.rows:
                if lig>0:
                    famille      = cells[lig][1].value
                    sous_famille = cells[lig][2].value

                    if famille:
                        if famille not in familles:
                            familles[famille]=[]

                    if sous_famille:
                        lines = self.env['is.sous.famille'].search([("name","=",sous_famille)])
                        for line in lines:
                            if line.id not in familles[famille]:
                                familles[famille].append(line.id)
                lig+=1
            for famille in familles:
                print(famille)
                famille_id = False
                lines = self.env['is.famille'].search([("name","=",famille)])
                for line in lines:
                    famille_id = line.id
                if famille_id==False:
                    vals={
                        "name": famille,
                        "sous_famille_ids": [(6, 0, familles[famille])],
                        "is_longueur": True,
                        "is_largeur_utile": True,
                        "is_surface_panneau": True,
                        "is_surface_palette": True,
                        "is_poids": True,
                        "is_poids_rouleau": True,
                        "is_ondes": True,
                        "is_resistance_thermique": True,
                        "is_lambda": True,
                    }
                    famille=self.env['is.famille'].create(vals)
            #******************************************************************

            unites={
                "U" : "uom.product_uom_unit",	  # Unit??
                "BD": "uom.product_uom_unit",	  # Unit??
                "M??": "uom.uom_square_meter",     #	m??
                "ML": "uom.product_uom_meter",    # Longueur/distance
            }

            #** Cr??ation des articles *****************************************
            lig=0
            fournisseurs=[]
            for row in ws.rows:
                if lig>0:
                    fournisseur     = cells[lig][0].value
                    famille         = cells[lig][1].value
                    sous_famille    = cells[lig][2].value
                    code            = cells[lig][3].value
                    designation     = cells[lig][4].value
                    unite           = cells[lig][5].value
                    largeur_utile   = cells[lig][6].value
                    ondes           = cells[lig][7].value
                    poids           = cells[lig][8].value
                    r               = cells[lig][9].value
                    is_lambda       = cells[lig][10].value
                    surface_palette = cells[lig][11].value
                    surface_panneau = cells[lig][12].value
                    annotation      = cells[lig][13].value
                    prix            = cells[lig][14].value


                    if fournisseur and designation:
                        if not code:
                            code="XX-"+str(lig)
                        code=str(code).upper()

                        filtre=[("default_code","=",code)]
                        products = self.env['product.template'].search(filtre)

                        famille_id=False
                        lines = self.env['is.famille'].search([("name","=",famille)])
                        for line in lines:
                            famille_id = line.id

                        sous_famille_id=False
                        lines = self.env['is.sous.famille'].search([("name","=",sous_famille)])
                        for line in lines:
                            sous_famille_id = line.id

                        uom_id = self.env.ref("uom.product_uom_unit").id
                        if unite:
                            unite=unite.upper()
                            if unite in unites:
                                uom_id = self.env.ref(unites[unite]).id

                        vals={
                            "name"              : designation,
                            "default_code"      : code,
                            "is_famille_id"     : famille_id,
                            "is_sous_famille_id": sous_famille_id,
                            "uom_id"            : uom_id,
                            "uom_po_id"         : uom_id,
                            "is_largeur_utile"  : largeur_utile or 0,
                            "is_ondes"          : ondes or 0,
                            "is_poids"          : poids or 0,
                            "is_resistance_thermique": r or 0,
                            "is_lambda"         : is_lambda or 0,
                            "is_surface_palette": surface_palette or 0,
                            "is_surface_panneau": surface_panneau or 0,
                            "description"       : annotation,
                            "list_price"        : 0,
                        }



                        if len(products)==0:
                            product=self.env['product.template'].create(vals)
                        else:
                            product = products[0]
                            product.write(vals)

                        #** Cr??ation ligne tarif fournisseur ******************
                        partner_id=False
                        lines = self.env['res.partner'].search([("name","=",fournisseur)])
                        for line in lines:
                            partner_id = line.id
                        if partner_id:
                            vals={
                                "product_tmpl_id": product.id,
                                "name"           : partner_id,
                                "min_qty"        : 1,
                                "price"          : prix,
                            }
                            filtre=[("product_tmpl_id","=",product.id)]
                            supplierinfos = self.env['product.supplierinfo'].search(filtre)
                            if len(supplierinfos)==0:
                                supplierinfo=self.env['product.supplierinfo'].create(vals)
                            else:
                                supplierinfo = supplierinfos[0]
                                supplierinfo.write(vals)
                        print(lig,product, fournisseur,code,designation)
                lig+=1














            #uom_id   = self.env['ir.model.data'].xmlid_to_res_id('uom.product_uom_kgm') # Kg


            #     #** Recherche du fournisseur ******************************
            #     partner_id = False # Fournisseur = My Company
            #     if fournisseur:
            #         partners = self.env['res.partner'].search([("name","ilike",fournisseur)])
            #         for partner in partners:
            #             partner_id = partner.id
            #         if partner_id==False:
            #             vals={
            #                 "name"           : fournisseur,
            #                 "is_code_interne": "CREATION",
            #             }
            #             partner=self.env['res.partner'].create(vals)
            #             print("CREATION ",partner)
            #             partner_id = partner.id
            #     #**********************************************************


            #     if code and designation and prix and partner_id:
            #         filtre=[("default_code","=",code)]
            #         products = self.env['product.template'].search(filtre)
            #         vals={
            #             "name"                  : designation,
            #             "default_code"          : code,
            #             "list_price"            : 0,
            #             "is_nb_pieces_par_colis": colisage,
            #             "is_poids_net_colis"    : poids,
            #             "taxes_id"              : [(6, 0, [taxe_vente_id])],
            #             "supplier_taxes_id"     : [(6, 0, [taxe_achat_id])],
            #             "type"                  : "product",
            #         }
            #         if kg_piece=="K":
            #             vals["uom_id"]    = uom_id
            #             vals["uom_po_id"] = uom_id
                    
            #         if len(products)==0:
            #             product=self.env['product.template'].create(vals)
            #         else:
            #             product = products[0]
            #             product.write(vals)

            #         print(ct,product,code,kg_piece,prix,designation)

            #         #** Cr??ation ligne tarif fournisseur ******************
            #         vals={
            #             "product_tmpl_id": product.id,
            #             "name"           : partner_id,
            #             "min_qty"        : 1,
            #             "prix_brut"      : prix,
            #             "date_start"     : "2022-01-01",
            #             "date_end"       : "2032-01-01",
            #         }
            #         filtre=[("product_tmpl_id","=",product.id)]
            #         supplierinfos = self.env['product.supplierinfo'].search(filtre)
            #         if len(supplierinfos)==0:
            #             supplierinfo=self.env['product.supplierinfo'].create(vals)
            #             #print("Create supplierinfo", supplierinfo )
            #         else:
            #             supplierinfo = supplierinfos[0]
            #             supplierinfo.write(vals)
            #             #print("Write supplierinfo", supplierinfo )
            #         ct+=1
            #     lig+=1

            #     # if ct>100:
            #     #    break


            # self.create_pricelist(wb, "HT 2022"    , "TARIF HORS TRANSPORT")
            # self.create_pricelist(wb, "FRANCO 2022", "FRANCO DE PORT")



