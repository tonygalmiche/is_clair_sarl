# -*- coding: utf-8 -*-
from odoo import api, fields, models
from random import randint


class IsNatureTravaux(models.Model):
    _name='is.equipe'
    _description = "Equipe"
    _order='name'

    def _get_default_color(self):
        return randint(1, 11)

    name  = fields.Char('Equipe', required=True, index=True)
    color = fields.Integer('Couleur', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Cette équipe exite déjà !"),
    ]


class IsChantier(models.Model):
    _name='is.chantier'
    _description = "Chantiers"
    _order='name'

    name              = fields.Char('N°', index=True, readonly=True)
    affaire_id        = fields.Many2one('is.affaire', 'Affaire', required=False)
    equipe_id         = fields.Many2one('is.equipe', 'Equipe', required=False)
    equipe_color      = fields.Integer('Couleur', help='Couleur Equipe', related="equipe_id.color")
    nature_travaux_id = fields.Many2one('is.nature.travaux', string="Nature des travaux", required=False)
    date_debut        = fields.Date('Date début', required=False)
    date_fin          = fields.Date('Date fin', required=False)
    commentaire       = fields.Char('Commentaire')


    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('is.chantier')
        res = super(IsChantier, self).create(vals)
        return res


    @api.model
    def get_chantiers(self,domain):#, res_model, ):
        res=[]
        chantiers=self.env['is.chantier'].search(domain, order="name", limit=10)
        for chantier in chantiers:
            vals={
                "id"      : chantier.id,
                "name"    : chantier.name,
                "chantier": chantier,
            }
            res.append(vals)
        #print('get_chantiers=',res)
        return {"chantiers":res}
        #return "toto et tutu"