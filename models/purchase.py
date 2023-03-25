# -*- coding: utf-8 -*-
from itertools import product
from pdb import line_prefix
from odoo import models,fields,api
from odoo.tools.misc import formatLang, get_lang


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
    is_delai               = fields.Char("Délai prévisionnel", store=True, readonly=True, compute='_compute_is_delai', help="Délai prévisionnel de l'affaire")
    is_date_livraison      = fields.Date('Date de livraison')
    is_lieu_livraison      = fields.Selection([
        ('notre_adresse', 'A notre adresse'),
        ('chantier'     , 'Livraison sur chantier référence'),
        ('enlevement'   , 'Enlèvement'),
    ], 'Lieu de livraison')
    is_condition_tarifaire = fields.Text('Conditions tarifaire', related='partner_id.is_condition_tarifaire')
    is_repere_ids          = fields.One2many('is.purchase.order.repere', 'order_id', 'Repère de plan')
    is_mois_ids            = fields.One2many('is.purchase.order.mois'  , 'order_id', 'Mois de réalisation des tâches')
    is_sale_order_id       = fields.Many2one('sale.order', 'Commande client associée')


    @api.onchange('is_affaire_id')
    def onchange_is_affaire_id(self):
        for obj in self:
            if obj.is_affaire_id.contact_chantier_id:
                obj.is_contact_chantier_id = obj.is_affaire_id.contact_chantier_id.id


    @api.depends('is_delai_mois_id','is_delai_annee')
    def _compute_is_delai(self):
        for obj in self:
            t=[(obj.is_delai_mois_id.name or ''), (obj.is_delai_annee or '')]
            x = " ".join(t)
            obj.is_delai=x


    def write(self, vals):
        res = super(purchase_order, self).write(vals)
        self.update_reperes()
        return res


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



    # def _default_is_sequence_facturation(self):
    #     return 1234


    # @api.depends('is_preparation_id')
    # def _compute_is_sequence_facturation(self):
    #     for obj in self:
    #         obj.is_sequence_facturation = obj.is_preparation_id.id
    #         print("_compute_is_sequence_facturation", obj,obj.is_preparation_id.id)




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
