# -*- coding: utf-8 -*-
from odoo import api, fields, models
from random import randint


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


class IsAffaire(models.Model):
    _name='is.affaire'
    _description = "Affaire"
    _order='name desc'

    name                = fields.Char("N° d'Affaire", index=True, help="Sous la forme AA-XXXX")
    nom                 = fields.Char("Nom de l'affaire")
    date_creation       = fields.Date("Date de création", default=lambda *a: fields.Date.today())
    client_id           = fields.Many2one('res.partner' , 'Client')
    chantier_id         = fields.Many2one('res.partner' , 'Adresse du chantier')
    nature_travaux_ids  = fields.Many2many('is.nature.travaux', 'is_affaire_nature_travaux_rel', 'affaire_id', 'nature_id'     , string="Nature des travaux")
    type_travaux_ids    = fields.Many2many('is.type.travaux'  , 'is_affaire_type_travaux_rel'  , 'affaire_id', 'type_id'       , string="Type des travaux")
    specificite_ids     = fields.Many2many('is.specificite'   , 'is_affaire_specificite_rel'   , 'affaire_id', 'specificite_id', string="Spécificités")
    commentaire         = fields.Text("Commentaire")
    achat_facture       = fields.Float("Achats facturés" , digits=(14,2), store=False, readonly=True, compute='_compute_achat_facture')
    vente_facture       = fields.Float("Ventes facturées", digits=(14,2), store=False, readonly=True, compute='_compute_vente_facture')
    contact_chantier_id = fields.Many2one('res.users' , 'Contact chantier')


    @api.depends('name')
    def _compute_achat_facture(self):
        cr,uid,context,su = self.env.args
        for obj in self:
            val=0
            if isinstance(obj.id, int):
                SQL="""
                    SELECT sum(price_subtotal)
                    FROM account_move_line
                    WHERE is_affaire_id=%s and exclude_from_invoice_tab='f' and journal_id=2
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
                    SELECT sum(price_subtotal)
                    FROM account_move_line
                    WHERE is_affaire_id=%s and exclude_from_invoice_tab='f' and journal_id=1
                """
                cr.execute(SQL,[obj.id])
                for row in cr.fetchall():
                    val = row[0]
            obj.vente_facture = val


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
            if obj.chantier_id:
                name+=" - %s %s %s %s"%(obj.chantier_id.street or '', obj.chantier_id.street2 or '', obj.chantier_id.zip or '', obj.chantier_id.city or '')
            result.append((obj.id, name))
        return result


    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if args is None:
            args = []

        ids = []
        if len(name) >= 1:
            filtre=[
                '|','|','|','|','|','|',
                ('name', 'ilike', name),
                ('nom', 'ilike', name),
                ('chantier_id.name', 'ilike', name),
                ('chantier_id.street', 'ilike', name),
                ('chantier_id.street2', 'ilike', name),
                ('chantier_id.zip', 'ilike', name),
                ('chantier_id.city', 'ilike', name),
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

