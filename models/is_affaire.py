# -*- coding: utf-8 -*-
from odoo import api, fields, models
from random import randint
import re


class IsNatureTravaux(models.Model):
    _name='is.nature.travaux'
    _description = "Nature des travaux"
    _order='name'

    def _get_default_color(self):
        return randint(1, 11)

    name  = fields.Char('Nature des travaux', required=True, index=True)
    color = fields.Integer('Couleur', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class IsTypeTravaux(models.Model):
    _name='is.type.travaux'
    _description = "Type des travaux"
    _order='name'

    def _get_default_color(self):
        return randint(1, 11)

    name  = fields.Char('Type des travaux', required=True, index=True)
    color = fields.Integer('Couleur', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class IsSpecificite(models.Model):
    _name='is.specificite'
    _description = "Spécificité"
    _order='name'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Spécificité', required=True, index=True)
    color = fields.Integer('Couleur', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class IsAffaireAnalyse(models.Model):
    _name='is.affaire.analyse'
    _description = "Analyse de commandes par affaire"

    affaire_id       = fields.Many2one('is.affaire', 'Affaire', required=True, ondelete='cascade')
    fournisseur_id   = fields.Many2one('res.partner' , 'Fournisseur')
    famille_id       = fields.Many2one('is.famille', 'Famille')
    intitule         = fields.Char('Intitulé')
    budget           = fields.Float("Budget"          , digits=(14,2))
    montant_cde      = fields.Float("Montant Commandé", digits=(14,2))
    montant_fac      = fields.Float("Montant Facturé" , digits=(14,2))
    ecart            = fields.Float("Ecart Cde/Fac"   , digits=(14,2))
    ecart_pourcent   = fields.Float("% Ecart"         , digits=(14,2))
    ecart_budget_cde = fields.Float("Ecart Budget/Cde", digits=(14,2))
    ecart_budget_fac = fields.Float("Ecart Budget/Fac", digits=(14,2))


class IsAffaireBudgetFamille(models.Model):
    _name='is.affaire.budget.famille'
    _description = "Budget affaire par famille"

    affaire_id = fields.Many2one('is.affaire', 'Affaire', required=True, ondelete='cascade')
    famille_id = fields.Many2one('is.famille', 'Famille', required=True)
    budget     = fields.Float("Budget", digits=(14,2))


class IsAffaireSalaire(models.Model):
    _name='is.affaire.salaire'
    _description = "Salaires des affaires"

    affaire_id     = fields.Many2one('is.affaire', 'Affaire', required=True, ondelete='cascade')
    importation_id = fields.Many2one('is.import.salaire', 'Importation')
    date           = fields.Date("Date", required=True)
    montant        = fields.Float("Montant", digits=(14,2))


    def view_affaire_action(self):
        for obj in self:
            return {
                "name": "Affaire %s"%(obj.importation_id.name),
                "view_mode": "form",
                "res_model": "is.affaire",
                "res_id"   : obj.affaire_id.id,
                "type": "ir.actions.act_window",
            }



class IsAffaireRemise(models.Model):
    _name='is.affaire.remise'
    _description = "IsAffaireRemise"

    affaire_id = fields.Many2one('is.affaire', 'Affaire', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Remise facturation', required=True, domain=[('is_famille_id.name','=','Facturation')])
    remise     = fields.Float("Remise (%)", digits=(14,2), required=True)


class IsAffaire(models.Model):
    _name='is.affaire'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Affaire"
    _order='name desc'

    name                = fields.Char("N° d'Affaire", index=True, help="Sous la forme AA-XXXX")
    nom                 = fields.Char("Nom de l'affaire")
    date_creation       = fields.Date("Date de création", default=lambda *a: fields.Date.today())
    client_id           = fields.Many2one('res.partner' , 'Client')
    # chantier_id         = fields.Many2one('res.partner' , 'Adresse du chantier')
    # chantier_adresse    = fields.Text('Adresse complète du chantier', related='chantier_id.is_adresse')
    street              = fields.Char("Rue")
    street2             = fields.Char("Rue 2")
    zip                 = fields.Char("CP")
    city                = fields.Char("Ville")
    adresse_chantier    = fields.Text('Adresse du chantier', store=True, readonly=True, compute='_compute_adresse_chantier')
    nature_travaux_ids  = fields.Many2many('is.nature.travaux', 'is_affaire_nature_travaux_rel', 'affaire_id', 'nature_id'     , string="Nature des travaux")
    type_travaux_ids    = fields.Many2many('is.type.travaux'  , 'is_affaire_type_travaux_rel'  , 'affaire_id', 'type_id'       , string="Type des travaux")
    specificite_ids     = fields.Many2many('is.specificite'   , 'is_affaire_specificite_rel'   , 'affaire_id', 'specificite_id', string="Spécificités")
    commentaire         = fields.Text("Commentaire")
    achat_facture       = fields.Float("Achats facturés" , digits=(14,2), store=False, readonly=True, compute='_compute_achat_facture')
    vente_facture       = fields.Float("Ventes facturées", digits=(14,2), store=False, readonly=True, compute='_compute_vente_facture')
    contact_chantier_id = fields.Many2one('res.users' , 'Contact chantier')
    analyse_ids         = fields.One2many('is.affaire.analyse'       , 'affaire_id', 'Analyse de commandes')
    budget_famille_ids  = fields.One2many('is.affaire.budget.famille', 'affaire_id', 'Budget par famille')
    active              = fields.Boolean("Active", default=True)
    compte_prorata      = fields.Float("Compte prorata (%)", digits=(14,2))
    retenue_garantie    = fields.Float("Retenue de garantie (%)", digits=(14,2))
    salaire_ids         = fields.One2many('is.affaire.salaire', 'affaire_id', 'Salaires')
    montant_salaire     = fields.Float("Montant salaire", digits=(14,2), store=True, readonly=True, compute='_compute_montant_salaire')

    remise_ids         = fields.One2many('is.affaire.remise', 'affaire_id', 'Remises')






    @api.depends('street','street2','city','zip')
    def _compute_adresse_chantier(self):
        for obj in self:
            adresse = '%s\n%s'%((obj.street or ''), (obj.street2 or ''))
            if obj.zip or obj.city:
                adresse += '\n%s - %s'%((obj.zip or ''), (obj.city or ''))
            adresse = re.sub('\\n+','\n',adresse) # Supprimer les \n en double
            obj.adresse_chantier = adresse


    @api.depends('salaire_ids','salaire_ids.montant')
    def _compute_montant_salaire(self):
        for obj in self:
            montant = 0
            for line in obj.salaire_ids:
                montant+=line.montant
            obj.montant_salaire = montant


    @api.depends('name')
    def _compute_achat_facture(self):
        cr,uid,context,su = self.env.args
        for obj in self:
            val=0
            if isinstance(obj.id, int):
                SQL="""
                    SELECT sum(aml.price_subtotal)
                    FROM account_move_line aml join account_move am on aml.move_id=am.id
                    WHERE aml.is_affaire_id=%s and aml.exclude_from_invoice_tab='f' and aml.journal_id=2 and am.state='posted'
                """
                cr.execute(SQL,[obj.id])
                for row in cr.fetchall():
                    val = row[0]
            obj.achat_facture = val


    @api.depends('name')
    def _compute_vente_facture(self):
        cr,uid,context,su = self.env.args
        for obj in self:
            val=0
            if isinstance(obj.id, int):
                SQL="""
                    SELECT sum(aml.price_subtotal)
                    FROM account_move_line aml join account_move am on aml.move_id=am.id
                    WHERE aml.is_affaire_id=%s and aml.exclude_from_invoice_tab='f' and aml.journal_id=1 and am.state='posted'
                """
                cr.execute(SQL,[obj.id])
                for row in cr.fetchall():
                    val = row[0]
            obj.vente_facture = val



    def ajout_famille_action(self):
        for obj in self:
            familles = self.env['is.famille'].search([])
            for famille in familles:
                vals={
                    "affaire_id": obj.id,
                    "famille_id": famille.id,
                }
                res = self.env['is.affaire.budget.famille'].create(vals)


    def ajout_salaire(self):
        for obj in self:
            vals={
                "affaire_id"    : obj.id,
                "intitule"      : "0-SALAIRES",
                "montant_cde"   : obj.montant_salaire,
                "montant_fac"   : obj.montant_salaire,
                "ecart"         : 0,
                "ecart_pourcent": 0,
            }
            res = self.env['is.affaire.analyse'].sudo().create(vals)




    def analyse_par_fournisseur_action(self):
        cr,uid,context,su = self.env.args
        for obj in self:
            obj.analyse_ids.sudo().unlink()
            SQL="""
                SELECT coalesce(rp.parent_id,po.partner_id),sum(amount_untaxed)
                FROM purchase_order po join res_partner rp on po.partner_id=rp.id
                WHERE is_affaire_id=%s and state='purchase'
                GROUP BY coalesce(rp.parent_id,po.partner_id)
            """
            cr.execute(SQL,[obj.id])
            for row in cr.fetchall():
                partner_id = row[0]
                partner = self.env['res.partner'].browse(partner_id)
                montant_cde = row[1] or 0
                SQL="""
                    SELECT sum(aml.price_subtotal)
                    FROM account_move_line aml join account_move am on aml.move_id=am.id
                                               join res_partner rp on am.partner_id=rp.id
                    WHERE 
                        aml.is_affaire_id=%s and 
                        aml.exclude_from_invoice_tab='f' and 
                        aml.journal_id=2 and 
                        (am.partner_id=%s or rp.parent_id=%s) and
                        am.state='posted'
                """
                cr.execute(SQL,[obj.id, row[0], row[0]])
                montant_fac=ecart=ecart_pourcent=0
                for row2 in cr.fetchall():
                    montant_fac = row2[0] or 0
                ecart=montant_cde-montant_fac
                if montant_fac>0:
                    ecart_pourcent = 100*ecart/montant_fac
                vals={
                    "affaire_id"    : obj.id,
                    "intitule"      : partner.name,
                    "fournisseur_id": partner_id,
                    "montant_cde"   : montant_cde,
                    "montant_fac"   : montant_fac,
                    "ecart"         : ecart,
                    "ecart_pourcent": ecart_pourcent,
                }
                res = self.env['is.affaire.analyse'].sudo().create(vals)
            obj.ajout_salaire()
            return obj.is_affaire_analyse_action("Analyse par fournisseur")


    def analyse_par_famille_action(self):
        cr,uid,context,su = self.env.args
        for obj in self:
            obj.analyse_ids.sudo().unlink()
            lines = self.env['is.famille'].search([])
            familles=[]
            for line in lines:
                familles.append(line)
            familles.append(None)
            for famille in familles:
                intitule=""
                famille_id = None
                #** Budget ****************************************************
                budget=0
                if famille:
                    famille_id = famille.id
                    intitule   = famille.name
                    filtre=[('affaire_id', '=', obj.id),('famille_id', '=', famille_id)]
                    lines = self.env['is.affaire.budget.famille'].search(filtre)
                    budget=0
                    for line in lines:
                        budget=line.budget
                #**************************************************************

                #** Montant Cde ***********************************************
                montant_cde=0
                SQL="""
                    SELECT pt.is_famille_id,sum(pol.price_subtotal)
                    FROM purchase_order po join purchase_order_line pol on po.id=pol.order_id
                                        join product_product pp on pol.product_id=pp.id
                                        join product_template pt on pp.product_tmpl_id=pt.id
                    WHERE po.is_affaire_id=%s and  po.state='purchase'
                """%obj.id
                if famille_id:
                    SQL+=" and pt.is_famille_id=%s "%famille_id
                else:
                    SQL+=" and pt.is_famille_id is null " 
                SQL+="GROUP BY pt.is_famille_id"
                cr.execute(SQL)
                #cr.execute(SQL,[obj.id, famille_id])
                for row in cr.fetchall():
                    montant_cde = row[1] or 0
                ecart_budget_cde = budget-montant_cde
                #**************************************************************

                #** Montant Fac ***********************************************
                SQL="""
                    SELECT sum(aml.price_subtotal)
                    FROM account_move_line aml join account_move am on aml.move_id=am.id
                                               join product_product pp on aml.product_id=pp.id
                                               join product_template pt on pp.product_tmpl_id=pt.id
                    WHERE 
                        aml.is_affaire_id=%s and 
                        aml.exclude_from_invoice_tab='f' and 
                        aml.journal_id=2 and 
                        am.state='posted'
                """%obj.id
                if famille_id:
                    SQL+=" and pt.is_famille_id=%s "%famille_id
                else:
                    SQL+=" and pt.is_famille_id is null " 
                cr.execute(SQL)
                montant_fac=ecart=ecart_pourcent=0
                for row2 in cr.fetchall():
                    montant_fac = row2[0] or 0
                ecart=montant_cde-montant_fac
                if montant_fac>0:
                    ecart_pourcent = 100*ecart/montant_fac
                ecart_budget_fac = budget-montant_fac
                #**************************************************************

                if budget!=0 or montant_cde!=0 or montant_fac!=0:
                    vals={
                        "affaire_id": obj.id,
                        "intitule": intitule,
                        "famille_id": famille_id,
                        "budget"    : budget,
                        "montant_cde"     : montant_cde,
                        "montant_fac"   : montant_fac,
                        "ecart"         : ecart,
                        "ecart_pourcent": ecart_pourcent,
                        "ecart_budget_cde": ecart_budget_cde,
                        "ecart_budget_fac": ecart_budget_fac,
                    }
                    res = self.env['is.affaire.analyse'].sudo().create(vals)
            obj.ajout_salaire()
            return obj.is_affaire_analyse_action("Analyse par famille")


    def import_budget_famille_action(self):
        cr,uid,context,su = self.env.args
        for obj in self:
            # filtre=[('is_affaire_id', '=', obj.id)]
            # orders = self.env['sale.order'].search(filtre)
            # for order in orders:
            for line in obj.budget_famille_ids:
                SQL="""
                    SELECT sum(sol.product_uom_qty*sol.is_prix_achat)
                    FROM sale_order so join sale_order_line sol on so.id=sol.order_id
                                    join product_product pp on sol.product_id=pp.id
                                    join product_template pt on pp.product_tmpl_id=pt.id
                    WHERE 
                        so.is_affaire_id=%s and 
                        pt.is_famille_id=%s 
                """
                cr.execute(SQL,[obj.id, line.famille_id.id])
                budget=0
                for row in cr.fetchall():
                    budget = row[0] or 0
                line.budget=budget




    def is_affaire_analyse_action(self,name):
        for obj in self:
            return {
                "name": name,
                "view_mode": "tree,form,pivot,graph",
                "res_model": "is.affaire.analyse",
                "res_id"   : obj.id,
                "type": "ir.actions.act_window",
                "domain": [
                    ("affaire_id","=",obj.id),
                ],
            }


    def liste_achat_facture_action(self):
        for obj in self:
            tree_id = self.env.ref('is_clair_sarl.is_account_move_line_tree_view').id
            form_id = self.env.ref('is_clair_sarl.is_account_move_line_form_view').id
            return {
                "name": "Lignes de factures ",
                "view_mode": "tree,form",
                "res_model": "account.move.line",
                "domain": [
                    ("is_affaire_id","=",obj.id),
                    ("exclude_from_invoice_tab","=",False),
                    ("journal_id","=",2),
                    ("move_id.state","=","posted"),
                ],
                "type": "ir.actions.act_window",
                "views"    : [[tree_id, "tree"],[form_id, "form"]],
            }


    def liste_vente_facture_action(self):
        for obj in self:
            tree_id = self.env.ref('is_clair_sarl.is_account_move_line_tree_view').id
            form_id = self.env.ref('is_clair_sarl.is_account_move_line_form_view').id
            return {
                "name": "Lignes de factures ",
                "view_mode": "tree,form",
                "res_model": "account.move.line",
                "domain": [
                    ("is_affaire_id","=",obj.id),
                    ("exclude_from_invoice_tab","=",False),
                    ("journal_id","=",1),
                ],
                "type": "ir.actions.act_window",
                "views"    : [[tree_id, "tree"],[form_id, "form"]],
            }


    def name_get(self):
        result = []
        for obj in self:

            name=""
            if obj.name and obj.nom:
                name = "[%s] %s"%(obj.name,obj.nom)
            if obj.name and not obj.nom:
                name = "%s"%(obj.name)
            if obj.nom and not obj.name:
                name = "%s"%(obj.nom)
            #if obj.chantier_id:
            #    name+=" - %s %s %s %s"%(obj.chantier_id.street or '', obj.chantier_id.street2 or '', obj.chantier_id.zip or '', obj.chantier_id.city or '')
            
            name+=" - %s %s %s %s"%(obj.street or '', obj.street2 or '', obj.zip or '', obj.city or '')


            
            result.append((obj.id, name))



        return result


    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if args is None:
            args = []

        ids = []
        if len(name) >= 1:
            # filtre=[
            #     '|','|','|','|','|','|',
            #     ('name', 'ilike', name),
            #     ('nom', 'ilike', name),
            #     ('chantier_id.name', 'ilike', name),
            #     ('chantier_id.street', 'ilike', name),
            #     ('chantier_id.street2', 'ilike', name),
            #     ('chantier_id.zip', 'ilike', name),
            #     ('chantier_id.city', 'ilike', name),
            # ]

            filtre=[
                '|','|','|','|','|',
                ('name'   , 'ilike', name),
                ('nom'    , 'ilike', name),
                ('street' , 'ilike', name),
                ('street2', 'ilike', name),
                ('zip'    , 'ilike', name),
                ('city'   , 'ilike', name),
            ]



            if name=="[":
                filtre=[('name', '!=', False)]
            if name=="#":
                filtre=[('name', '=', False)]
            ids = list(self._search(filtre + args, limit=limit))

        search_domain = [('name', operator, name)]
        if ids:
            search_domain.append(('id', 'not in', ids))
        ids += list(self._search(search_domain + args, limit=limit))
        return ids


class IsImportSalaire(models.Model):
    _name='is.import.salaire'
    _description = "Importation des salaires dans les affaires"
    _order='name desc'

    name        = fields.Date('Date', required=True, index=True)
    importation = fields.Text('Données à importer', help="Faire un copier / coller d'Excel dans ce champ")
    total       = fields.Float('Total importé', readonly=1)
    resultat    = fields.Text('Résultat importation', readonly=1)
    salaire_ids = fields.One2many('is.affaire.salaire', 'importation_id', 'Salaires')


    def importation_salaire_action(self):
        for obj in self:
            lines = obj.importation.split('\n')
            total = 0
            resultat = []
            obj.salaire_ids.unlink()
            for line in lines:
                test=False
                t = line.split('\t')
                if len(t)==2:
                    t2 = t[0].split(' ')
                    if len(t2)>=2:
                        #name    = t[0][0:7].strip()
                        name    = t2[0]
                        montant = t[1]
                        affaires=self.env['is.affaire'].search([('name', '=',name),('name', '!=','')])
                        affaire = False
                        for a in affaires:
                            affaire = a
                            break
                        if affaire:
                            try:
                                montant=float(t[1].replace(',','.'))
                            except:
                                montant=0
                            total+=montant
                            vals={
                                'affaire_id'    : affaire.id,
                                'importation_id': obj.id,
                                'date'          : obj.name,
                                'montant'       : montant,
                            }
                            res = self.env['is.affaire.salaire'].create(vals)
                            test=True
                if test==False and line.strip()!='':
                    resultat.append("Affaire non trouvée => %s"%line)
            if len(resultat)==0:
                resultat = False
            else:
                resultat = "\n".join(resultat)
            obj.resultat = resultat
            obj.total = total


