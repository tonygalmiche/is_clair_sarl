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
        chantiers=self.env['is.chantier'].search(domain, order="name") #, limit=10)
        trcolor=""
        dict={}
        for chantier in chantiers:
            if trcolor=="#ffffff":
                trcolor="#f2f3f4"
            else:
                trcolor="#ffffff"
            trstyle="background-color:%s"%(trcolor)

            jours={}
            for i in range(1, 2*31):
                jour={
                    "key": i,
                    "style": "cursor:default;background-color:white",
                }
                if i>10 and i<20:
                    jour["style"] = "cursor:move;background-color:Chartreuse"
                if i==10 or i==20:
                    jour["style"] = "cursor:col-resize;background-color:Chartreuse"
                jours[i]=jour
            vals={
                "id"      : chantier.id,
                "name"    : chantier.name,
                "trstyle" : trstyle,
                "jours"   : jours,
            }
            res.append(vals)
            dict[chantier.id]=vals
        #print('get_chantiers=',res)
        return {
            #"chantiers":res,
            "dict"     : dict,
        }
    


    # @api.model
    # def get_vue_owl_99(self,domain):

    #     print('get_vue_owl_99 : domain=',domain)

    #     res=[]
    #     partners=self.env['res.partner'].search(domain, order="name", limit=100)
    #     trcolor=""
    #     for partner in partners:

    #         if trcolor=="#ffffff":
    #             trcolor="#f2f3f4"
    #         else:
    #             trcolor="#ffffff"
    #         trstyle="background-color:%s"%(trcolor)

    #         vals={
    #             "id"      : partner.id,
    #             "name"    : partner.name,
    #             "trstyle" : trstyle,
    #         }
    #         res.append(vals)
    #     print('get_vue_owl_99 : res=',res)
    #     return {"partners":res}


