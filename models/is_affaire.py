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

    name               = fields.Char("N° d'Affaire", required=True, index=True, help="Sous la forme AA-XXXX")
    nom                = fields.Char("Nom de l'affaire")
    date_creation      = fields.Date("Date de création", default=lambda *a: fields.Date.today())
    client_id          = fields.Many2one('res.partner' , 'Client')
    chantier_id        = fields.Many2one('res.partner' , 'Adresse du chantier')
    nature_travaux_ids = fields.Many2many('is.nature.travaux', 'is_affaire_nature_travaux_rel', 'affaire_id', 'nature_id'     , string="Nature des travaux")
    type_travaux_ids   = fields.Many2many('is.type.travaux'  , 'is_affaire_type_travaux_rel'  , 'affaire_id', 'type_id'       , string="Type des travaux")
    specificite_ids    = fields.Many2many('is.specificite'   , 'is_affaire_specificite_rel'   , 'affaire_id', 'specificite_id', string="Spécificités")
    commentaire        = fields.Text("Commentaire")




    def name_get(self):
        result = []
        for obj in self:
            name="[%s] %s - %s %s %s %s"%(obj.name,obj.nom or '', obj.chantier_id.street or '', obj.chantier_id.street2 or '', obj.chantier_id.zip or '', obj.chantier_id.city or '')
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


            ids = list(self._search(filtre + args, limit=limit))

        search_domain = [('name', operator, name)]
        if ids:
            search_domain.append(('id', 'not in', ids))
        ids += list(self._search(search_domain + args, limit=limit))

        return ids

