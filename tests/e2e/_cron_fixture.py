# -*- coding: utf-8 -*-
# Conta de teste com os 73 capitulos do cronograma (ids e numero de assuntos do prompt).
import json, os, sys
sys.path.insert(0,'.')
from test_sala import make_seed

AQUI=os.path.dirname(os.path.abspath(__file__))
DADOS=json.load(open(os.path.join(AQUI,'..','..','docs','cronograma','ebserh-2026.json'),encoding='utf-8'))

def seed_cron(extra=None):
    reinos={'esp':{'id':'kE','name':'Enfermagem','icon':'💉','color':'#22d3ee'},
            'bas':{'id':'kB','name':'Básicos','icon':'📚','color':'#a78bfa'},
            'comp':{'id':'kC','name':'Complementar','icon':'🧩','color':'#fb923c'}}
    topics={r['id']:[] for r in reinos.values()}
    for c in DADOS['cap']:
        k=reinos[c['cat']]['id']
        topics[k].append({'id':c['id'],'name':c['nome'],'icon':'⚔️','subtopics':[
            {'id':'s%s_%d'%(c['id'],i),'name':'%s — assunto %d'%(c['nome'],i),'priority':70,'studied':False}
            for i in range(1,c['n']+1)]})
    d={'studyNickname':'Leo','kingdoms':list(reinos.values()),'topics':topics}
    d.update(extra or {})
    return make_seed(d)
