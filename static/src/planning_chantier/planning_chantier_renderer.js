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
            //dict:{},
            //activity_types:[]
        });
    }

    mounted() {
        //console.log("PlanningChantierRenderer : mounted",this);
        this.GetChantiers();
    }
    // willStart() {
    //     console.log("PlanningChantierRenderer : willStart",this);
    // }
    // willRender() {
    //     console.log("PlanningChantierRenderer : willRender",this);
    // }
    // rendered() {
    //     console.log("PlanningChantierRenderer : rendered",this);
    // }
    //  willUpdateProps() {
    //     console.log("PlanningChantierRenderer : willUpdateProps",this);
    // }
    // willPatch() {
    //     console.log("PlanningChantierRenderer : willPatch",this);
    // }
    // patched() {
    //     console.log("PlanningChantierRenderer : patched",this);
    // }
    // willUnmount() {
    //     console.log("PlanningChantierRenderer : willUnmount",this);
    // }
    // willDestroy() {
    //     console.log("PlanningChantierRenderer : willDestroy",this);
    // }
    // onError() {
    //     console.log("PlanningChantierRenderer : onError",this);
    // }


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
        var chantierid=ev.target.parentElement.attributes.chantierid;

        console.log("tdMouseDown", ev.target.parentElement, chantierid);

        if (chantierid!==undefined){
            this.state.chantierid=chantierid.value;
        }
        var jour=ev.target.attributes.jour;
        if (jour!==undefined){
            this.state.jour=jour.value;
        }
        var color=ev.target.attributes.color;
        if (color!==undefined){
            this.state.color=color.value;
        }

        // if (jour!==undefined && chantierid!==undefined){
        //     this.state.dict[chantierid.value]["jours"][jour.value].cursor="default";
        // }





        console.log('TrMouseDown : parentElement=',ev.target.parentElement);
    }
    tdMouseMove(ev) {
        if (this.state.chantierid>0){
            const jour=ev.target.attributes.jour;
            if (jour!==undefined){
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
            }
        }
    }
    tdMouseUp(ev) {
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



    }

    tbodyMouseLeave(ev) {
        this.state.chantierid=0;
        this.state.jour=0;
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



    // Recherche des chantiers
    OKButtonClick(ev) {
        console.log("OKButtonClick",this)
        this.GetChantiers();
    }
    async GetChantiers(s){
        var self=this;
        rpc.query({
            model: 'is.chantier',
            method: 'get_chantiers',
            kwargs: {
                domain: this.props.domain,
            }
        }).then(function (result) {
            self.state.dict = result.dict;
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



        // rpc.query({
        //     model: 'is.chantier',
        //     method: 'get_vue_owl_99',
        //     kwargs: {
        //         domain: [],
        //     }
        // }).then(function (result) {
        //     console.log("testRpcMethod : result=",result);
        //     self.state.partners = result.partners;
        // });
    }



    // TestButtonClick(ev) {
    //     console.log("TestButtonClick",ev)
    //     this.testRpcWrite();
    //     this.testRpcRead();
    //     this.testRpcMethod();
    // }

    // async testRpcWrite(s){
    //     var vals={
    //         "name": "3IA Auxerre 2222",
    //     }
    //     var prom = rpc.query({
    //         model: 'res.partner',
    //         method: 'write',
    //         args: [[108], vals],
    //     });
    //     console.log("testRpcWrite")
    // }

    // async testRpcRead(s){
    //     rpc.query({
    //         model: 'product.product',
    //         method: 'search_read',
    //         args: [[], ['id','name']],
    //         kwargs: {
    //             limit: 10,
    //         }
    //     }).then(function (products) {
    //         console.log(products);
    //     });
    //     console.log("testRpcRead")
    // }

    // async testRpcMethod(s){
    //     console.log("testRpcMethod : this=",this)

    //     var self=this;
    //     rpc.query({
    //         model: 'res.partner',
    //         method: 'get_vue_owl_99',
    //         kwargs: {
    //             domain: [],
    //         }
    //     }).then(function (result) {
    //         console.log("testRpcMethod : result=",result);
    //         self.state.partners = result.partners;
    //     });
    // }



}

PlanningChantierRenderer.components = {};
PlanningChantierRenderer.template = 'is_clair_sarl.PlanningChantierTemplate';
export default PlanningChantierRenderer;
