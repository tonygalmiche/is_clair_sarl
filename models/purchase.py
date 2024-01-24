# -*- coding: utf-8 -*-
from itertools import product
from pdb import line_prefix
from odoo import models,fields,api
from odoo.tools.misc import formatLang, get_lang
import base64
from subprocess import PIPE, Popen
import re
from thefuzz import fuzz 
from collections import OrderedDict
import operator

def str2float(x):
    try:
        resultat = float(x)
    except:
        return 0
    return resultat


def str2eval(x):
    try:
        resultat = str2float(eval(x))
    except:
        return 0
    return resultat


class purchase_order(models.Model):
    _inherit = "purchase.order"

    is_affaire_id          = fields.Many2one('is.affaire', 'Affaire')
    is_contact_chantier_id = fields.Many2one('res.users' , 'Contact chantier')
    is_date                = fields.Date('Date')
    is_delai_mois_id       = fields.Many2one('is.mois.trimestre', 'Délai (Mois / Trimestre)')
    is_delai_annee         = fields.Char('Délai (Année)')
    #is_delai               = fields.Char("Délai prévisionnel", store=True, readonly=True, compute='_compute_is_delai', help="Délai prévisionnel de l'affaire")
    is_delai               = fields.Char("Délai prévisionnel", help="Délai prévisionnel de l'affaire")
    is_date_livraison      = fields.Date('Date de livraison')
    is_lieu_livraison      = fields.Selection([
        ('notre_adresse'      , 'A notre adresse'),
        ('chantier'           , 'Livraison sur chantier référence'),
        ('enlevement'         , 'Enlèvement'),
        ('livraison_sur_ordre', 'Livraison sur ordre'),
    ], 'Lieu de livraison')
    is_condition_tarifaire = fields.Text('Conditions tarifaire', related='partner_id.is_condition_tarifaire')
    is_repere_ids          = fields.One2many('is.purchase.order.repere', 'order_id', 'Repère de plan')
    is_mois_ids            = fields.One2many('is.purchase.order.mois'  , 'order_id', 'Mois de réalisation des tâches')
    is_sale_order_id       = fields.Many2one('sale.order', 'Commande client associée')
    is_modele_commande_id  = fields.Many2one(related='partner_id.is_modele_commande_id')

    is_import_pdf_ids      = fields.Many2many('ir.attachment' , 'purchase_order_is_import_pdf_ids_rel', 'order_id', 'attachment_id', 'PDF à importer')
    is_import_pdf_resultat = fields.Text("Résultat de l'importation", readonly=1)
    is_eco_contribution    = fields.Float("Montant Eco-contribution", digits=(14,2), help='Si ce montant est renseigné, cela ajoutera automatiquement une ligne sur la commande')


    @api.onchange('is_affaire_id')
    def onchange_is_affaire_id(self):
        for obj in self:
            if obj.is_affaire_id.contact_chantier_id:
                obj.is_contact_chantier_id = obj.is_affaire_id.contact_chantier_id.id


    # @api.depends('is_delai_mois_id','is_delai_annee')
    # def _compute_is_delai(self):
    #     for obj in self:
    #         t=[(obj.is_delai_mois_id.name or ''), (obj.is_delai_annee or '')]
    #         x = " ".join(t)
    #         obj.is_delai=x


    def write(self, vals):
        res = super(purchase_order, self).write(vals)
        self.update_reperes()
        self.ajout_eco_contribution()
        return res


    def ajout_eco_contribution(self):
        for obj in self:
            if obj.is_eco_contribution>0:
                products = self.env['product.product'].search([('default_code','=','ECOCON')])
                for product in products:
                    sequence = 0
                    order_line=False
                    for line in obj.order_line:
                        print(line, line.sequence)
                        if line.sequence>sequence:
                            sequence=line.sequence
                        if line.product_id == product:
                            order_line = line
                    sequence+=10
                    if not order_line:
                        vals={
                            'order_id': obj.id,
                            'product_id': product.id,
                            'name': product.name_get()[0][1],
                            'product_qty': 1,
                            'price_unit':obj.is_eco_contribution,
                            'sequence': sequence,
                        }
                        res=self.env['purchase.order.line'].create(vals)
                    else:
                        order_line.sequence=sequence
                        order_line.price_unit = obj.is_eco_contribution
                

    def update_reperes(self):
        cr,uid,context,su = self.env.args
        for obj in self:
            #** Ajout des lignes des reperes **********************************
            ids=[]
            for r in obj.is_repere_ids:
                ids.append(r)
            for line in obj.order_line:
                ids2=[]
                for r2 in line.is_repere_ids:
                    ids2.append(r2.repere_id)
                    r2.sequence=r2.repere_id.sequence
                for r in ids:
                    if r not in ids2:
                        vals={
                            "line_id"  : line.id,
                            "repere_id": r.id,
                            "sequence" : r.sequence,
                        }
                        res = self.env['is.purchase.order.line.repere'].create(vals)


            #** Ajout des lignes des mois *************************************
            ids=[]
            for r in obj.is_mois_ids:
                ids.append(r)
            for line in obj.order_line:
                ids2=[]
                for r2 in line.is_mois_ids:
                    ids2.append(r2.mois_id)
                for r in ids:
                    if r not in ids2:
                        vals={
                            "line_id": line.id,
                            "mois_id": r.id,
                        }
                        res = self.env['is.purchase.order.line.mois'].create(vals)


            #** Calcul des totaux des reperes *********************************
            for r in obj.is_repere_ids:
                SQL="""
                    SELECT montant
                    FROM is_purchase_order_line_repere
                    WHERE repere_id=%s
                """
                cr.execute(SQL,[r.id])
                for row in cr.fetchall():
                    r.montant = row[0]


            #** Calcul des totaux des mois ************************************
            for r in obj.is_mois_ids:
                SQL="""
                    SELECT montant
                    FROM is_purchase_order_line_mois
                    WHERE mois_id=%s
                """
                cr.execute(SQL,[r.id])
                for row in cr.fetchall():
                    r.montant = row[0]


    def importer_tache_action(self):
        cr,uid,context,su = self.env.args
        for obj in self:
            obj.order_line.unlink()
            SQL="""
                SELECT pp.id, pt.name, isf.name
                FROM product_product pp join product_template pt on pp.product_tmpl_id=pt.id
                                        join is_famille       if on pt.is_famille_id=if.id
                                        left join is_sous_famille isf on pt.is_sous_famille_id=isf.id
                WHERE if.name='Tâche' and pt.active='t'
                ORDER BY if.name,isf.name,pt.is_ordre_tri,pt.name
            """
            cr.execute(SQL)
            sequence=1
            mem=""
            for row in cr.fetchall():
                if row[2]!=mem:
                    mem=row[2]
                    vals={
                        "order_id"    : obj.id,
                        "sequence"    : sequence,
                        "name"        : mem,
                        "product_qty" : 0,
                        "display_type": "line_section",
                    }
                    res = self.env['purchase.order.line'].create(vals)
                vals={
                    "order_id"       : obj.id,
                    "product_id"     : row[0],
                    "sequence"       : sequence,
                    "name"           : row[1],
                    "product_uom_qty": 1,
                }
                res = self.env['purchase.order.line'].create(vals)
                sequence+=1


    def view_order_action(self):
        for obj in self:
            return {
                "name": "Commande %s"%(obj.name),
                "view_mode": "form",
                "res_model": "purchase.order",
                "res_id"   : obj.id,
                "type": "ir.actions.act_window",
            }


    def initialiser_depuis_modele_commande(self):
        for obj in self:
            sequence=10
            for line in obj.is_modele_commande_id.ligne_ids:
                vals={
                    'order_id'    : obj.id,
                    'sequence'    : sequence,
                    'product_id'  : line.product_id.id,
                    'name'        : line.description or line.product_id.name_get()[0][1],
                    'product_qty' : 0,
                }
                self.env['purchase.order.line'].create(vals)
                sequence+=10








    def import_pdf_action(self):
        for obj in self:
            for attachment in obj.is_import_pdf_ids:
                pdf=base64.b64decode(attachment.datas)
                name = 'purchase_order-%s'%obj.id
                path = "/tmp/%s.pdf"%name
                f = open(path,'wb')
                f.write(pdf)
                f.close()
                cde = "cd /tmp && pdftotext -layout %s.pdf"%name
                p = Popen(cde, shell=True, stdout=PIPE, stderr=PIPE)
                stdout, stderr = p.communicate()
                path = "/tmp/%s.txt"%name
                r = open(path,'rb').read().decode('utf-8')
                lines = r.split('\n')
                order_lines=[]
                dict={}
                # chantier=False
                # ligne_chantier = 0
                # lignes_chantier=[]
                # montants = []

                #** Recherche si c'est bien un PDF de LOXAM *******************
                test=False
                for line in lines:
                    x = re.findall("LOXAM", line) 
                    if x:
                        test = True
                        break
                if test==False:
                    obj.is_import_pdf_resultat = "Ce PDF n'est pas de LOXAM => Importation impossible"
                #**************************************************************

                #** Recherche de l'adresse du chantier ************************
                chantier=[]
                if test:
                    lig=0
                    for line in lines:
                        x = re.findall("Adresse de chantier", line) 
                        if x:
                            lig=1
                        if lig>1 and lig<=6:
                            v = line[0:160].strip()
                            chantier.append(v)
                        if lig>=6:
                            break
                        if lig:
                            lig+=1
                if chantier:
                    dict["Chantier"] = ' '.join(chantier)
                #**************************************************************

                #** Code postal du chantier ***********************************
                chantier_zip=False
                if chantier:
                    adresse = dict["Chantier"]
                    x = re.findall("[0-9]{5}", adresse)
                    if x:
                        chantier_zip = x[0]
                #**************************************************************

                #** N°BDC (Code Affaire) ***************************************
                affaire=False
                if test:
                    for line in lines:
                        x = re.findall("N°BDC", line) 
                        if x:
                            v = line.strip()[0:30].strip()
                            v = v.split(' : ')
                            if len(v)==2:
                                bdc = v[1].strip()
                                x = re.findall("[0-9]{2}\.[0-9]{4}", bdc)
                                if x:
                                    bdc=x[0]

                                    affaires = self.env['is.affaire'].search([('name','=',bdc)])
                                    if affaires:
                                        affaire=affaires[0]
                                dict["N°BDC"] = bdc
                            break
                #**************************************************************

                #** Recherche de l'affaire ************************************
                if test and not affaire:
                    chantier = dict["Chantier"].upper()
                    filtre=[]
                    if chantier_zip:
                        filtre=[('zip','=',chantier_zip)]
                    affaires = self.env['is.affaire'].search(filtre,order="adresse_chantier")
                    affaire_dict={}
                    for line in affaires:
                        adresse = line.adresse_chantier.replace('\n',' ').strip().upper()
                        if adresse!='':
                            ratio = fuzz.ratio(chantier, adresse)
                            affaire_dict[ratio] = (line, line.name)
                            #print(ratio,chantier, adresse)
                    key_sorted = sorted(affaire_dict, reverse=True)
                    for key in key_sorted:
                        affaire = affaire_dict[key][0]
                        break
                #**************************************************************

                #** Affaire ***************************************************
                if affaire:
                    obj.is_affaire_id = affaire.id
                #**************************************************************

                #** Recherche Acheteur ****************************************
                if test:
                    for line in lines:
                        x = re.findall("Acheteur", line) 
                        if x:
                            v = line.strip()[0:30].strip()
                            v = v.split(' : ')
                            if len(v)==2:
                                dict["Acheteur"] = v[1]
                            break
                #**************************************************************

 
                #** Lignes avec des Quantités ou des montants *****************
                if test:
                    debut=fin=False
                    debut_libelle = fin_libelle = False
                    libelles = []
                    qte = 0
                    montant_total = 0
                    res=[]
                    new=False
                    for line in lines:
                        if debut and not fin:
                            #** Quantité **************************************
                            qte = 0
                            libelle = False
                            montant = 0
                            tab = line.strip().split(' ')
                            if len(tab)>1:
                                try:
                                    qte=float(tab[0].strip())
                                except:
                                    qte=0
                            
                            #** Montant ***************************************
                            x = re.findall("[0-9]*\.[0-9]{2}$", line.strip())
                            if x:
                                x2 = " ".join(line.split()) # Supprimer les espaces en double
                                list = x2.split()
                                if len(list)>1:
                                    try:
                                        montant=float(x[0].strip())
                                    except:
                                        montant=0

                            #** Libellé sans Qté et sans Montant **************
                            l = False
                            if not qte and not montant:
                                x = " ".join(line.split()) # Supprimer les espaces en double
                                list = x.split()
                                l = ' '.join(list)

                            #** Libellé avec Qté et Montant *******************
                            if qte and montant:
                                x = " ".join(line.split()) # Supprimer les espaces en double
                                list = x.split()
                                list.pop(0) # Supprime le premier element (la quantité)
                                list.pop()  # Supprime le dernier element (le montant)
                                l = ' '.join(list)

                            #** Libellé avec Qté et sans Montant **************
                            if qte and not montant:
                                x = " ".join(line.split()) # Supprimer les espaces en double
                                list = x.split()
                                list.pop(0) # Supprime le premier element (la quantité)
                                l = ' '.join(list)

                            #** Autres libellés *******************************
                            x = re.findall("Total période", line)
                            if montant and x:
                                l=x[0].strip()
                            x = re.findall("Contribution verte", line)
                            if montant and x:
                                l=x[0].strip()
                                qte = qte or 1
                            x = re.findall("Forfait transport Aller", line)
                            if montant and x:
                                l=x[0].strip()
                                qte = qte or 1
                            x = re.findall("Forfait transport Retour", line)
                            if montant and x:
                                l=x[0].strip()
                                qte = qte or 1

                            #** Elimination des intitulés indésirables ********
                            indesirable=False
                            if l:
                                l=l.strip()
                                if l=='' or l=='Total période':
                                    indesirable=True
                                x = re.findall("Ventes Prix Unitaire", l)
                                if x:
                                    indesirable=True
                                x = re.findall("Étude BVA - Viséo CI", l)
                                if x:
                                    indesirable=True
                            if l and not indesirable:
                                libelles.append(l.strip())

                            #** Test si nouvelle ligne ************************
                            new = False
                            if qte and montant:
                                new=True
                            if l=="Total période":
                                new=True
                            if new:
                                libelle = '\n'.join(libelles)
                                libelles=[]
                                montant_total+=montant
                                order_lines.append([qte, libelle, montant])

                        x = re.findall("Qté.*Libellé.*Montant", line)
                        if x:
                            debut = True
                        x = re.findall("Total HT", line)
                        if x:
                            fin=True
                            x = re.findall("[0-9]*\.[0-9]{2}$", line.strip())
                            if x:
                                try:
                                    ht=float(x[0].strip())
                                except:
                                    ht=0
                                dict["Total HT"] = ht
                dict["Total calculé"] = montant_total

                #** Résultat du traitement ************************************
                if test:
                    for key in dict:
                        x = "%s : %s"%(key.ljust(15), dict[key])
                        res.append(x)
                    obj.is_import_pdf_resultat = '\n'.join(res)
                #**************************************************************

                #** Ajout des lignes de la commande ***************************
                if test:
                    obj.order_line.unlink()
                    sequence = 0
                    for line in order_lines:
                        libelle = line[1]
                        sequence+=10
                        product = obj.get_loxam_product(libelle)
                        if product:
                            vals={
                                "order_id"       : obj.id,
                                "product_id"     : product.id,
                                "sequence"       : sequence,
                                "name"           : line[1],
                                "product_qty"    : 1,
                                "price_unit"     : line[2],
                                "product_uom"    : product.uom_id.id,
                            }
                            order_line = self.env['purchase.order.line'].create(vals)
                    #**********************************************************


    def get_loxam_product(self, libelle):
        for obj in self:
            dict={
                'Gaz'	                            : 'GAZ',
                'CHARIOT TELESC'                    : 'CHARIOT',
                'PLATEFORME'                        : 'PLATEFORME',
                'NACELLE'                           : 'NACELLE',
                'BENNE DE REPRISE POUR CHARIOT'     : 'GODET',
                'Constu modulaire R/R'              :  'BUNGALOW',
                'Forfait transport'                 : 'TCHANTIER',
                #'Forfait transport Aller'           : 'TCHANTIER',
                #'Forfait transport Retour'          : 'TCHANTIER',
                'MAJORATION TRANSPORT ALLER ZONE A' : 'TCHANTIER',
                'MAJORATION TRANSPORT RETOUR ZONE A': 'TCHANTIER',
                'Kilometres supplémentaires'        : 'TCHANTIER',
                'CONTRIBUTION VERTE'                : 'ECOCON',
                'Carburant gazole non routier'      : 'GAZOLE',
                'Prestation forfait recharge elec'  : 'RECHAELEC',
                'Garantie dommages'                 : 'ASSURANCE',
                'Remise'                            : 'REMISE',
            }


            product = False
            for key in dict:
                if re.search(key, libelle, re.IGNORECASE):
                    filtre=[
                        ("default_code"  ,"=", dict[key]),  
                    ]
                    products = self.env['product.product'].search(filtre)
                    if len(products):
                        product = products[0]
            if not product:
                filtre=[
                    ("name"  ,"=", 'divers'),  
                ]
                products = self.env['product.product'].search(filtre)
                if len(products):
                    product = products[0]
            return product


    # def import_pdf_action(self):
    #     for obj in self:
    #         for attachment in obj.is_import_pdf_ids:
    #             pdf=base64.b64decode(attachment.datas)
    #             name = 'purchase_order-%s'%obj.id
    #             path = "/tmp/%s.pdf"%name
    #             f = open(path,'wb')
    #             f.write(pdf)
    #             f.close()
    #             cde = "cd /tmp && pdftotext -layout %s.pdf"%name
    #             p = Popen(cde, shell=True, stdout=PIPE, stderr=PIPE)
    #             stdout, stderr = p.communicate()
    #             path = "/tmp/%s.txt"%name
    #             r = open(path,'rb').read().decode('utf-8')
    #             lines = r.split('\n')
    #             res=[]
    #             dict={}
    #             chantier=False
    #             ligne_chantier = 0
    #             lignes_chantier=[]

    #             montants = []

    #             #** Recherche si c'est bien un PDF de LOXAM *******************
    #             test=False
    #             for line in lines:
    #                 x = re.findall("LOXAM", line) 
    #                 if x:
    #                     test = True
    #                     break
    #             if test==False:
    #                 obj.is_import_pdf_resultat = "Ce PDF n'est pas de LOXAM => Importation impossible"
    #             if test:
    #                 #** Initialisation du fournisseur *************************
    #                 partners = self.env['res.partner'].search([("name"  ,"ilike", 'LOXAM')])
    #                 for partner in partners:
    #                     obj.partner_id = partner.id
    #                     break
    #                 #**********************************************************

    #                 fin_lignes = False
    #                 agence = False
    #                 for line in lines:
    #                     if len(line):

    #                         #** Agence ****************************************
    #                         x = re.findall("LOXAM ACCESS", line)
    #                         if x:
    #                             agence = line.strip()
    #                             dict["Agence"] = agence

    #                         #** Recherche NACELLE *****************************
    #                         x = re.findall("(.*)(NACELLE.*)([0-9]*\.[0-9]*$)", line)
    #                         if x:
    #                             if len(x[0])>1:
    #                                 nacelle = x[0][1][0:40].strip()
    #                                 #dict["NACELLE"] = nacelle

    #                         #** Recherche des montants ************************
    #                         if line[0:23]!='                 Dégr. ':
    #                             if fin_lignes==False:
    #                                 #** Recherche des montants en fin de ligne avec 1 décimale
    #                                 # if agence=="LOXAM ACCESS CHALON":
    #                                 #     x = re.findall("[0-9]*\.[0-9]{1}$", line.strip())
    #                                 # else:
    #                                 #     x = re.findall("[0-9]*\.[0-9]{2}$", line.strip())
    #                                 x = re.findall("[0-9]*\.[0-9]{1}$", line.strip())
    #                                 v = 0
    #                                 if x:
    #                                     for l in x:
    #                                         try:
    #                                             v=float(l.strip())
    #                                         except:
    #                                             v=0
    #                                 if v:
    #                                     description = line[0:50].strip()
    #                                     if len(description)==0:
    #                                         description = nacelle
    #                                     #montants.append("%s : %s (%s)"%(description,l.strip(),v))
    #                                     montants.append([description,l.strip(),v])
    #                        #**************************************************

    #                         if line[0:14]=='Date sortie : ':
    #                             dict["Date sortie"] = line[14:22]
    #                         if line[0:15]=='Retour prévu : ':
    #                             dict["Retour prévu"] = line[15:23]
    #                         if line[0:11]=='  Acheteur:':
    #                             dict["Acheteur"] = line[11:].strip().replace(" ","").replace(":","")

    #                         if  line[0:11]=='  Chantier:' and chantier==False:
    #                             chantier = True
    #                             ligne_chantier = 0

    #                         if ligne_chantier>=1 and ligne_chantier<=2:
    #                             x = " ".join(line.split()) # Supprimer les espaces en double
    #                             lignes_chantier.append(x)
    #                         if chantier:
    #                             ligne_chantier+=1

    #                         #** Fin des lignes avec un montant ****************
    #                         x = re.findall("Nom et signature", line)
    #                         if x:
    #                             fin_lignes = True

    #                         #** Recherche du montant total ********************
    #                         x = re.findall("Sous-Tot.HT:", line)
    #                         if not x:
    #                             x = re.findall("Total HT", line)
    #                         if x:
    #                             x = re.findall("[0-9]*\.[0-9]{1}$", line) 
    #                             if x:
    #                                 for l in x:
    #                                     dict["Sous-Tot.HT"] = l
    #                                     try:
    #                                         montant_total=float(l.strip())
    #                                     except:
    #                                         montant_total=0
    #                                     break
    #                 #** Recherche de l'affaire ********************************
    #                 chantier = ', '.join(lignes_chantier)
    #                 dict["Chantier"] = chantier
    #                 affaires = self.env['is.affaire'].search([])
    #                 affaire_dict={}
    #                 for affaire in affaires:
    #                     name = '%s %s %s'%(affaire.name, affaire.nom, affaire.chantier_adresse)
    #                     ratio = fuzz.ratio(chantier, name)
    #                     affaire_dict[ratio] = (affaire, affaire.name)
    #                 key_sorted = sorted(affaire_dict, reverse=True)
    #                 for key in key_sorted:
    #                     affaire = affaire_dict[key][0]
    #                     obj.is_affaire_id = affaire.id
    #                     break
    #                 #**********************************************************

    #                 for key in dict:
    #                     x = "%s : %s"%(key.ljust(15), dict[key])
    #                     res.append(x)

    #                 if montants:
    #                     res.append("Montants trouvés avec 1 décimale en fin de ligne : ")
    #                     for m in montants:
    #                         x = "%s : %s (%s)"%(m[0], m[1], m[2])
    #                         res.append("- %s"%x)

    #                 res.append('\n' + '-'*160)
    #                 for line in lines:
    #                     if len(line):
    #                         res.append(line)
    #                 obj.is_import_pdf_resultat = '\n'.join(res)


    #                 if montants:
    #                     obj.order_line.unlink()

    #                     #** Ajout d'une note sur la premiere ligne ****************
    #                     note = []
    #                     for key in dict:
    #                         note.append("%s : %s"%(key, dict[key]))
    #                     note = "\n".join(note)
    #                     sequence = 10
    #                     vals={
    #                         "order_id"       : obj.id,
    #                         "sequence"       : 10,
    #                         "name"           : note,
    #                         "product_qty"    : 0,
    #                         "display_type"   : "line_note",
    #                     }
    #                     order_line = self.env['purchase.order.line'].create(vals)
    #                     #**********************************************************

    #                     #** Ajout des lignes de la commande ***********************
    #                     for m in montants:
    #                         sequence+=10

    #                         filtre=[
    #                             ("name"  ,"=", 'divers'),  
    #                         ]
    #                         if re.search('nacelle', m[0], re.IGNORECASE):
    #                             filtre=[
    #                                 ("name"  ,"=", 'Nacelle'), 
    #                             ]
    #                         if re.search('transport', m[0], re.IGNORECASE):
    #                             filtre=[
    #                                 ("default_code"  ,"=", 'TCHANTIER'),  
    #                             ]
    #                         products = self.env['product.product'].search(filtre)
    #                         product = False
    #                         for p in products:
    #                             product = p
    #                             break 
    #                         if p:
    #                             vals={
    #                                 "order_id"       : obj.id,
    #                                 "product_id"     : product.id,
    #                                 "sequence"       : sequence,
    #                                 "name"           : m[0],
    #                                 "product_qty"    : 1,
    #                                 "price_unit"     : m[2],
    #                                 "product_uom"    : product.uom_id.id,
    #                             }
    #                             order_line = self.env['purchase.order.line'].create(vals)
    #                     #**********************************************************





class IsPurchaseOrderMois(models.Model):
    _name='is.purchase.order.mois'
    _description = "Mois pour le suivi des taches"
    _order='mois'
    _rec_name = 'mois'

    order_id = fields.Many2one('purchase.order', 'Commande', required=True, ondelete='cascade')
    mois     = fields.Date("Mois", required=True)
    montant  = fields.Float("Montant", digits=(14,2), readonly=True)


class IsPurchaseOrderRepere(models.Model):
    _name='is.purchase.order.repere'
    _description = "Repère de plan des commandes"
    _order='repere'
    _rec_name = 'repere'

    order_id = fields.Many2one('purchase.order', 'Commande', required=True, ondelete='cascade')
    sequence = fields.Integer("Sequence")
    repere   = fields.Char("Repère de plan", required=True)
    montant  = fields.Float("Montant", digits=(14,2), readonly=True)


class IsPurchaseOrderLineRepere(models.Model):
    _name='is.purchase.order.line.repere'
    _description = "Repère de plan des lignes de commandes"
    _order='sequence,id'
    _rec_name = 'repere_id'

    line_id   = fields.Many2one('purchase.order.line', 'Ligne de commande', required=True, ondelete='cascade')
    repere_id = fields.Many2one('is.purchase.order.repere', 'Repère de plan', required=True)
    sequence  = fields.Integer("Sequence")
    formule   = fields.Char("Formule")
    quantite  = fields.Float("Quantité", digits=(14,2), store=True, readonly=True, compute='_compute_quantite')
    montant   = fields.Float("Montant" , digits=(14,2), store=True, readonly=True, compute='_compute_quantite')

    @api.depends('formule')
    def _compute_quantite(self):
        for obj in self:
            v=str2eval(obj.formule)
            obj.quantite = v
            obj.montant  = v * obj.line_id.price_unit


class IsPurchaseOrderLineMois(models.Model):
    _name='is.purchase.order.line.mois'
    _description = "Mois des lignes de commandes"
    _order='mois_id'
    _rec_name = 'mois_id'

    line_id   = fields.Many2one('purchase.order.line', 'Ligne de commande', required=True, ondelete='cascade')
    mois_id   = fields.Many2one('is.purchase.order.mois', 'Mois', required=True)
    formule   = fields.Char("Formule")
    quantite  = fields.Float("Quantité", digits=(14,2), store=True, readonly=True, compute='_compute_quantite')
    montant   = fields.Float("Montant" , digits=(14,2), store=True, readonly=True, compute='_compute_quantite')

    @api.depends('formule')
    def _compute_quantite(self):
        for obj in self:
            v=str2eval(obj.formule)
            obj.quantite = v
            obj.montant  = v * obj.line_id.price_unit


class purchase_order_line(models.Model):
    _inherit = "purchase.order.line"


    is_famille_id      = fields.Many2one('is.famille', 'Famille'          , related='product_id.is_famille_id')
    is_sous_famille_id = fields.Many2one('is.sous.famille', 'Sous-famille', related='product_id.is_sous_famille_id')
    is_affaire_id      = fields.Many2one(related='order_id.is_affaire_id')
    is_finition_id     = fields.Many2one('is.finition'  , 'Finition')
    is_traitement_id   = fields.Many2one('is.traitement', 'Traitement')
    is_largeur         = fields.Float('Largeur')
    is_hauteur         = fields.Float('Hauteur')
    is_colis_ids       = fields.One2many('is.purchase.order.line.colis', 'line_id', 'Colis')
    is_liste_colis_action_vsb = fields.Boolean("Liste colis vsb", store=False, readonly=True, compute='_compute_is_liste_colis_action_vsb')
    is_colisage               = fields.Text("Colisage", store=False, readonly=True, compute='_compute_is_colisage')
    is_repere_ids             = fields.One2many('is.purchase.order.line.repere', 'line_id', 'Repère de plan')
    is_mois_ids               = fields.One2many('is.purchase.order.line.mois'  , 'line_id', 'Mois')
    is_preparation_id         = fields.Many2one('is.preparation.facture', 'Préparation facture')
    is_qt_a_facturer          = fields.Float('Qt à facturer', digits='Product Unit of Measure')
    is_montant_a_facturer     = fields.Float("Montant à facturer")

    is_date_livraison = fields.Date(related='order_id.is_date_livraison')
    is_sequence_facturation = fields.Integer("Ordre") #, store=True, readonly=True, compute='_compute_is_sequence_facturation') #, default=lambda self: self._default_is_sequence_facturation())


    @api.depends('is_colis_ids')
    def _compute_is_colisage(self):
        for obj in self:
            html=False
            if obj.is_colis_ids:
                html=""
                html+="<table style='width:100%' class='colisage'>"
                html+="<thead><tr><th>Colis</th><th>Nb</th><th>Long.</th><th>Note</th><th>Surface</th></tr></thead>"
                html+="<tbody>"
                for colis in obj.is_colis_ids:
                    nb=len(colis.line_ids)
                    ct=surface_total=0
                    for line in colis.line_ids:
                        surface_total+=line.surface
                        if ct==0:
                            html+="<tr><td style='white-space: normal;' rowspan='"+str(nb)+"'>"+colis.name+"</td>"
                        else:
                            html+="<tr>"
                        html+="<td style='text-align:right'>"+str(line.nb)+"</td>"
                        html+="<td style='text-align:right'>"+str(line.longueur)+"</td>"
                        html+="<td style='text-align:left'>"+(line.note or '')+"</td>"
                        html+="<td style='text-align:right'>"+str(line.surface)+"</td></tr>"
                        ct+=1
                    html+="<tr>"
                    html+="<td style='text-align:right;border-bottom: 1px solid black;' colspan='4'><b>Total:</b></td>"
                    html+="<td style='text-align:right;border-bottom: 1px solid black;'><b>%.2f</b></td>"%(surface_total)
                    html+="</tr>"
                html+="<div style='white-space: nowrap;'>                                                                </div>"
                html+="</tbody>"
                html+="</table>"
            obj.is_colisage=html


    @api.depends('product_id')
    def _compute_is_liste_colis_action_vsb(self):
        for obj in self:
            vsb=False
            if obj.product_id.is_famille_id.colisage:
                vsb=True
            obj.is_liste_colis_action_vsb=vsb


    # @api.onchange('is_largeur','is_hauteur')
    # def onchange_calculateur(self):
    #     for obj in self:
    #         if  obj.is_largeur and obj.is_hauteur:
    #             obj.product_qty = obj.is_largeur*obj.is_hauteur


    @api.onchange('is_repere_ids')
    def onchange_repere_ids(self):
        for obj in self:
            if  obj.is_repere_ids:
                    quantite=0
                    for r in obj.is_repere_ids:
                        quantite+=r.quantite
                    obj.product_qty=quantite




    @api.onchange('product_id','is_finition_id','is_traitement_id')
    def _product_id_change(self):
        if not self.product_id:
            return
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=self.partner_id.id,
            company_id=self.company_id.id,
        )
        name = "%s %s %s"%(self.product_id.name, (self.is_finition_id.name or ''), (self.is_traitement_id.name or ''))
        self.name = name
        self._compute_tax_id()


    def liste_colis_action(self):
        for obj in self:
            ctx={
                'default_line_id': obj.id,
            }
            return {
                "name": "Colis "+obj.name,
                "view_mode": "tree,form",
                "res_model": "is.purchase.order.line.colis",
                "domain": [
                    ("line_id","=",obj.id),
                ],
                "type": "ir.actions.act_window",
                "context": ctx,
            }


    def liste_lignes_colis_action(self):
        for obj in self:
            filtre=[
                ("line_id"  ,"=", obj.id),
            ]
            colis = self.env['is.purchase.order.line.colis'].search(filtre)
            ids=[]
            for c in colis:
                for line in c.line_ids:
                    ids.append(line.id)
            ctx={
                'group_by': 'colis_id',
            }
            return {
                "name": "Ligne "+str(obj.id),
                "view_mode": "kanban,tree,form",
                "res_model": "is.purchase.order.line.colis.line",
                "domain": [
                    ("id","in",ids),
                ],
                "type": "ir.actions.act_window",
                "context": ctx,
            }


    def _prepare_account_move_line(self, move=False):
        res = super(purchase_order_line, self)._prepare_account_move_line(move)
        res.update({
            'is_affaire_id': self.order_id.is_affaire_id.id,
        })
        return res





class IsMoisTrimestre(models.Model):
    _name='is.mois.trimestre'
    _description = "IsMoisTrimestre"
    _order='name'

    name = fields.Char('Mois / Trimestre', required=True, index=True)


class IsFinition(models.Model):
    _name='is.finition'
    _description = "Finition"
    _order='name'

    name = fields.Char('Finition', required=True, index=True)


class IsTraitement(models.Model):
    _name='is.traitement'
    _description = "Traitement"
    _order='name'

    name = fields.Char('Traitement', required=True, index=True)


class IsPurchaseOrderLineColis(models.Model):
    _name='is.purchase.order.line.colis'
    _description = "Colis des lignes de commandes fournisseurs"
    _order='name'

    line_id          = fields.Many2one('purchase.order.line', 'Ligne de commande', required=True, ondelete='cascade')
    product_id       = fields.Many2one('product.product', 'Article', related='line_id.product_id')
    largeur_utile    = fields.Integer("Largeur utile (mm)", related='product_id.is_largeur_utile')
    poids            = fields.Float("Poids (Kg/㎡)"        , related='product_id.is_poids')
    poids_colis      = fields.Float("Poids colis", digits=(14,2), store=True, readonly=True, compute='_compute_poids_colis')
    forfait_coupe_id = fields.Many2one('product.product', 'Longueur mini forfait coupe', related='product_id.is_forfait_coupe_id')
    name             = fields.Char('Colis', required=True, index=True)
    surface          = fields.Float("Surface (㎡)", digits=(14,2), store=True, readonly=True, compute='_compute_surface')
    forfait_coupe    = fields.Integer("Forfait coupe"            , store=True, readonly=True, compute='_compute_surface')
    line_ids         = fields.One2many('is.purchase.order.line.colis.line', 'colis_id', 'Lignes')

    @api.depends('line_ids')
    def _compute_poids_colis(self):
        for obj in self:
            poids=0
            for line in obj.line_ids:
                poids+=line.poids
            obj.poids_colis=poids


    @api.depends('line_ids')
    def _compute_surface(self):
        for obj in self:
            surface=0
            forfait_coupe=0
            for line in obj.line_ids:
                surface+=line.surface
                forfait_coupe+=line.forfait_coupe
            obj.surface       = surface
            obj.forfait_coupe = forfait_coupe
            qty=0
            for line in obj.line_id.is_colis_ids:
                qty+=line.surface
            if qty>0:
                obj.line_id.product_qty=qty
            #** Ajout des forfait coupe ***************************************
            if obj.line_id.order_id and obj.forfait_coupe_id:
                forfait_coupe=0
                for order in obj.line_id.order_id:
                    for line in order.order_line:
                        for colis in line.is_colis_ids:
                            if obj.forfait_coupe_id==colis.forfait_coupe_id:
                                forfait_coupe+=colis.forfait_coupe 
                filtre=[
                    ("order_id"  ,"=", obj.line_id.order_id.id),
                    ("product_id","=", obj.forfait_coupe_id.id),
                ]
                lines = self.env['purchase.order.line'].search(filtre)
                vals={
                    "order_id"   : obj.line_id.order_id.id,
                    "product_id" : obj.forfait_coupe_id.id,
                    "name"       : obj.forfait_coupe_id.name,
                    "product_qty": forfait_coupe,
                    "price_unit" : obj.forfait_coupe_id.standard_price,
                    "sequence"   : 900,
                }
                filtre=[
                    ("order_id"  ,"=", obj.line_id.order_id.id),
                    ("product_id","=", obj.forfait_coupe_id.id),
                ]
                lines = self.env['purchase.order.line'].search(filtre)
                if len(lines)>0:
                    lines[0].write(vals)
                else:
                    res=self.env['purchase.order.line'].create(vals)
            #******************************************************************


class IsPurchaseOrderLineColisLine(models.Model):
    _name='is.purchase.order.line.colis.line'
    _description = "Lignes des colis des lignes de commandes fournisseurs"
    _order='colis_id,id'

    colis_id      = fields.Many2one('is.purchase.order.line.colis', 'Colis', required=True, ondelete='cascade')
    poids_colis   = fields.Float("Poids colis", related='colis_id.poids_colis')
    order_line_id = fields.Many2one('purchase.order.line', related='colis_id.line_id')
    colis_ids     = fields.Many2many('is.purchase.order.line.colis', 'is_purchase_order_line_colis_ids', 'line_id', 'colis_id', store=False, readonly=True, compute='_compute_colis_ids', string="Colis de la ligne")
    nb            = fields.Integer('Nb'      , required=True)
    longueur      = fields.Integer("Longueur", required=True)
    note          = fields.Char("Note")
    surface       = fields.Float("Surface (㎡)", digits=(14,2) , store=True, readonly=True, compute='_compute_surface_poids')
    poids         = fields.Float("Poids"       , digits=(14,2) , store=True, readonly=True, compute='_compute_surface_poids')
    forfait_coupe = fields.Integer("Forfait coupe"             , store=True, readonly=True, compute='_compute_surface_poids')


    @api.depends('nb','longueur')
    def _compute_surface_poids(self):
        for obj in self:
            surface = obj.nb*obj.longueur*obj.colis_id.largeur_utile/1000000
            obj.surface       = surface
            obj.poids         = surface*obj.colis_id.poids
            forfait_coupe = 0
            if obj.longueur<obj.colis_id.forfait_coupe_id.is_lg_mini_forfait:
                forfait_coupe = obj.nb
            obj.forfait_coupe = forfait_coupe


    @api.depends('colis_id')
    def _compute_colis_ids(self):
        for obj in self:
            filtre=[
                ("line_id"  ,"=", obj.order_line_id.id),
            ]
            colis = self.env['is.purchase.order.line.colis'].search(filtre)
            ids=[]
            for c in colis:
                ids.append(c.id)
            obj.colis_ids= [(6, 0, ids)]
