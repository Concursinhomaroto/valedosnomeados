# -*- coding: utf-8 -*-
# Fixture do plano por edital: dois editais sobre a conta de teste do cronograma (73 capitulos).
import sys
sys.path.insert(0,'tests/e2e'); sys.path.insert(0,'.')
from _cron_fixture import seed_cron

def sid(cap,i): return 's%s_%d'%(cap,i)
def ass(i,nome,sub=None,top=None):
    a={'id':i,'nome':nome}
    if sub: a['subId']=sub
    if top: a['topicId']=top
    return a

ENF='_loi52dk'; POR='_22dn7iw'; SUS='_scn56um'
E1={'id':'e1','nome':'Edital A','cargo':'Enfermeiro','banca':'FGV','orgao':'','icon':'📋','color':'#6c47ff','status':'inscrito','data':'2027-03-14',
  'disciplinas':[
    {'id':'D1','nome':'Enfermagem','questoes':30,'assuntos':[ass('a%d'%i,'Enf %d'%i,sid(ENF,i)) for i in range(1,7)]},
    {'id':'D2','nome':'Português','questoes':10,'assuntos':[ass('p%d'%i,'Port %d'%i,sid(POR,i)) for i in range(1,4)]+[ass('px','Assunto sem vinculo')]}]}
E2={'id':'e2','nome':'Edital B','cargo':'Enfermeiro','banca':'Outra','orgao':'','icon':'📋','color':'#6c47ff','status':'inscrito','data':'',
  'disciplinas':[
    {'id':'D3','nome':'Enfermagem','questoes':20,'assuntos':[ass('b%d'%i,'Enf %d'%i,sid(ENF,i)) for i in (1,2,7,8)]},
    {'id':'D4','nome':'SUS','questoes':0,'assuntos':[ass('s%d'%i,'SUS %d'%i,sid(SUS,i)) for i in range(1,5)]}]}

def seed_agenda(extra=None):
    d={'editais':[E1,E2]}
    d.update(extra or {})
    return seed_cron(d)

# liga o plano por edital direto no db (os testes do motor nao passam pela interface)
ATIVAR_JS="""(args)=>{window.todayStr=()=>args.hoje||'2026-11-04';
  db.cronograma={ativo:true,horaInicio:'06:00',inicio:args.inicio||'2026-11-05',complementar:false,rodizio:true,v:2,feitos:{},lidos:{},fases:[{desde:args.inicio||'2026-11-05',horas:args.horas||4}]};
  const pl={id:'p1',nome:'Teste',editalIds:args.eds,pct:args.pct||{},config:{inicio:args.inicio||'2026-11-05',horasDia:args.horas||4,horaInicio:'06:00',diasSemana:[1,2,3,4,5,6]},
    pesos:args.pesos||{},minPorAssunto:{},excluidos:args.excl||{},prioridade:{},reforco:{},bloqueios:[],indisp:[]};
  db.agendaPlanos={ativoId:'p1',planos:{p1:pl},versoes:[]};return true;}"""
