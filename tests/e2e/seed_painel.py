import datetime, sys
from test_sala import make_seed

def seed():
    hoje=datetime.date.today(); ontem=hoje-datetime.timedelta(days=1)
    K='k1'
    nomes=['Cuidados com drenos e sondas','Vacina Vírus Sincicial Respiratório (VSR)',
           'Sarampo, caxumba e rubéola (tríplice viral)','Hepatite A','Verbo','Preposição',
           'Conjunção','Adjetivos']
    # prioridades reais do app (30 comum, 70 raro, 100 lendario) e simStats em
    # alguns, pra os cartoes de simulado e de raridade renderizarem de verdade
    prios=[100,70,30,100,70,30,100,70]
    subs=[]
    for i,n in enumerate(nomes):
        sub={'id':f's{i}','name':n,'priority':prios[i],'studied':True,
             'studiedAt':str(ontem),'lastStudiedAt':str(ontem)}
        if i<4:
            sub['simStats']={'questoesTotal':20+i*5,'acertosTotal':int((20+i*5)*(0.4+0.15*i))}
        subs.append(sub)
    return make_seed({'studyNickname':'R','studyCharacter':'ash',
        'kingdoms':[{'id':K,'name':'Português','icon':'📘','color':'#7c3aed'},
                    {'id':'k2','name':'Enfermagem','icon':'💉','color':'#ef4444'}],
        'topics':{K:[{'id':'t1','name':'Morfologia','icon':'📖','priority':1,'subtopics':subs}],
                  'k2':[{'id':'t2','name':'Vacinação','icon':'💉','priority':1,'subtopics':[
                      {'id':'s9','name':'Hepatite A','priority':90,'studied':True,
                       'studiedAt':str(ontem),'lastStudiedAt':str(ontem)}]}]},
        'revisions':{f's{i}':[{'date':str(hoje-datetime.timedelta(days=70+i)),'completed':False}] for i in range(6)},
        'times':{f's{i}':3600 for i in range(8)},
        'sessions':{str(hoje-datetime.timedelta(days=d)):3600*(d%3+1) for d in range(7)},
        'subTotalSeconds':{f's{i}':3600 for i in range(8)},
        'simSessionsCount':6,
        # 22 revisoes de flashcard em dois dias, como no painel real do usuario
        'fcReviewLog':[{'date':str(hoje-datetime.timedelta(days=d)),'ok':(j%9)!=0}
                       for d in (1,2) for j in range(11)]})
