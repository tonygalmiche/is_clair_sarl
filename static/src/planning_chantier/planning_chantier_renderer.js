/** @odoo-module **/
import AbstractRendererOwl from 'web.AbstractRendererOwl';
import core  from 'web.core';
import QWeb from 'web.QWeb';
import session from 'web.session';
import utils from 'web.utils';

const _t = core._t;
const { useState } = owl.hooks;
var rpc = require('web.rpc');


class PlanningChantierRenderer extends AbstractRendererOwl {
    constructor(parent, props) {
        super(...arguments);
        this.qweb = new QWeb(this.env.isDebug(), {_s: session.origin});
        this.qweb.add_template(utils.json_node_to_xml(props.templates));
 
        //useState permet de faire un lien entre la vue XML et l'Object Javascript
        //Chaque modification de l'objet this.state entraine une modification de l'interface utilisateur
        this.state = useState({
            decale_planning: 0,
            nb_semaines:16,
            dict:{},
        });
    }

    mounted() {
        this.GetChantiers();
    }


    // Click pour colorier une ligne
    TrMouseLeave(ev) {
        const click=ev.target.attributes.click.value;
        if (click!="1"){
            const memstyle = ev.target.attributes.memstyle.value;
            ev.target.style=memstyle;
        }
    }
    TrMouseEnter(ev) {
        const click=ev.target.attributes.click.value;
        if (click!="1"){
            ev.target.style="background-color:#FFFF00;opacity: 0.5;";
        }
    }
    TrClick(ev) {
        var click=ev.target.parentElement.attributes.click;
        if (click!==undefined){
            click.value=-click.value
            if (click.value==1){
                ev.target.parentElement.style="background-color:rgb(204, 255, 204);opacity: 0.5;";
            } else {
                const memstyle = ev.target.parentElement.attributes.memstyle.value;
                ev.target.parentElement.style=memstyle;
            }
            ev.target.parentElement.attributes.click.value=click.value;
        }
    }



    //Alonger la durée du chantier par glissé/déposé
    tdMouseDown(ev) {
        //On mémorise le chantier, le jour et la couleur lors du down de la souris
        var chantierid=ev.target.parentElement.attributes.chantierid;
        var jour=ev.target.attributes.jour;
        var color=ev.target.attributes.color;
        if (chantierid!==undefined && jour!==undefined && color!==undefined){
            chantierid = parseInt(chantierid.value);
            jour       = parseInt(jour.value);
            color      = color.value;
            if (this.state.dict[chantierid]!==undefined) {
                if (this.state.dict[chantierid]["jours"]!==undefined) {
                    if (this.state.dict[chantierid]["jours"][jour]!==undefined) {
                        const cursor = this.state.dict[chantierid]["jours"][jour].cursor;
                        if (cursor=="col-resize" || cursor=="move") {
                            this.state.action=cursor;
                            console.log("tdMouseDown", ev.target.parentElement, chantierid);
                            this.state.chantierid=chantierid;
                            this.state.jour=jour;
                            this.state.color=color;
                        }
                    }
                }
            }
        }
    }
    tdMouseMove(ev) {
        if (this.state.action=="col-resize"){
            if (this.state.chantierid>0){
                const jour=ev.target.attributes.jour;
                if (jour!==undefined){
                    //Si le jour est supérieur au jour mémorisé, il faut allonger la durée
                    if(parseInt(jour.value)>parseInt(this.state.jour)){
                        for (let i = parseInt(this.state.jour); i <= parseInt(jour.value); i++) {
                            this.state.dict[this.state.chantierid]["jours"][i].color=this.state.color;
                            var cursor="move";
                            if (i==jour.value){
                                cursor="col-resize";
                            }
                            this.state.dict[this.state.chantierid]["jours"][i].cursor=cursor;
                            this.state.dict[this.state.chantierid].fin = parseInt(jour.value)+1;
                            const duree = this.state.dict[this.state.chantierid].fin - this.state.dict[this.state.chantierid].debut + 1;
                            this.state.dict[this.state.chantierid].duree = duree
                            this.state.jour = jour.value;
                        }
                    }
                    //Si le jour est inférieur au jour mémorisé, il faut réduire la durée
                    if(parseInt(jour.value)<parseInt(this.state.jour)){
                        this.state.dict[this.state.chantierid]["jours"][parseInt(jour.value)].cursor="col-resize";
                        for (let i = (parseInt(this.state.jour)+1); i > parseInt(jour.value); i--) {
                            this.state.dict[this.state.chantierid]["jours"][i].color="none";
                            this.state.dict[this.state.chantierid]["jours"][i].cursor="default";
                            this.state.dict[this.state.chantierid].fin = parseInt(jour.value)+1;
                            const duree = this.state.dict[this.state.chantierid].fin - this.state.dict[this.state.chantierid].debut + 1;
                            this.state.dict[this.state.chantierid].duree = duree
                            this.state.jour = jour.value;
                        }
                    }
                }
            }
        }
    }
    tdMouseUp(ev) {
        if (this.state.action=="col-resize"){
            console.log('TrMouseUp',ev);
            if (this.state.chantierid>0){
                const chantier = this.state.dict[this.state.chantierid];
                const duree = chantier.duree;
                if (duree>1) {
                    this.writeChantier(this.state.chantierid,duree);
                }
                console.log("fin, duree =",this.state.dict[this.state.chantierid].fin,duree);
            }
            this.state.chantierid=0;
            this.state.jour=0;
            this.state.color="";
            this.state.action="";
        }
    }
    tbodyMouseLeave(ev) {
        this.state.chantierid=0;
        this.state.jour=0;
        this.state.color="";
        this.state.action="";
    }



    // Actions
    MasquerChantierClick(ev){
        const id=ev.target.attributes.id.value;
        delete this.state.dict[id];
    }
    VoirChantierClick(ev) {
        const id=ev.target.attributes.id.value;
        this.env.bus.trigger('do-action', {
            action: {
                name:'Chantier',
                type: 'ir.actions.act_window',
                res_id: parseInt(id),
                res_model: 'is.chantier',
                views: [[false, 'form']],
            },
        });
    }
    ModifierChantierClick(ev) {
        const id=ev.target.attributes.id.value;
        this.env.bus.trigger('do-action', {
            action: {
                name:'Chantier',
                type: 'ir.actions.act_window',
                target: 'new',
                res_id: parseInt(id),
                res_model: 'is.chantier',
                views: [[false, 'form']],
            },
        });
    }


    onChangeNbSemaines(ev){
        this.state.nb_semaines = ev.target.value;
        this.GetChantiers(this.state.decale_planning, this.state.nb_semaines);
    }


    PrecedentClick(ev) {
        this.state.decale_planning = this.state.decale_planning-7;
        this.GetChantiers(this.state.decale_planning, this.state.nb_semaines);
    }
    SuivantClick(ev) {
        this.state.decale_planning = this.state.decale_planning+7;
        this.GetChantiers(this.state.decale_planning);
    }
    OKButtonClick(ev) {
        this.state.decale_planning = 0;
        this.GetChantiers(this.state.decale_planning, this.state.nb_semaines);
    }
    async GetChantiers(s){
        var self=this;
        rpc.query({
            model: 'is.chantier',
            method: 'get_chantiers',
            kwargs: {
                domain         : this.props.domain,
                decale_planning: this.state.decale_planning,
                nb_semaines    : this.state.nb_semaines,
            }
        }).then(function (result) {
            self.state.dict     = result.dict;
            self.state.mois     = result.mois;
            self.state.semaines = result.semaines;
            self.state.nb_semaines = result.nb_semaines;
            console.log("GetChantiers : this=",self)
        });
    }


    async writeChantier(chantierid,duree){
        console.log("writeChantier : chantierid,duree=",chantierid,duree)
        var self=this;
        var vals={
            "duree": parseInt(duree),
        }
        var prom = rpc.query({
            model: 'is.chantier',
            method: 'write',
            args: [[parseInt(chantierid)], vals],
        });
    }
}

PlanningChantierRenderer.components = {};
PlanningChantierRenderer.template = 'is_clair_sarl.PlanningChantierTemplate';
export default PlanningChantierRenderer;
