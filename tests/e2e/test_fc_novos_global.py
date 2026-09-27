import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
# 3 chefoes em 2 reinos. Novos espalhados; o chefao "Cardio" tem MAIS novos (era o
# unico que aparecia antes). Tambem ha vencidos e cards em dia, que nao podem entrar.
FC={}
def card(i,mb,tipo):
    c={'id':'c%d'%i,'mbId':mb,'pergunta':'P%d (%s)'%(i,mb),'resposta':'R%d'%i,
       'tags':'','dificuldade':2,'acertos':0,'erros':0,'lastConf':0,
       'criacao':'2026-01-01T10:00:00Z','ultimaRevisao':None}
    if tipo=='due':
        c.update({'acertos':1,'ultimaRevisao':'2026-01-02T10:00:00Z','sm2':{'ef':2.5,'reps':1,'interval':1}})
    elif tipo=='ok':
        c.update({'acertos':3,'ultimaRevisao':'2026-09-11T10:00:00Z','sm2':{'ef':2.6,'reps':3,'interval':60}})
    return c
i=0
for mb,novos,dues,oks in [('t1',3,2,1),('t2',2,1,1),('t3',6,4,2)]:
    for _ in range(novos): i+=1; FC['c%d'%i]=card(i,mb,'new')
    for _ in range(dues):  i+=1; FC['c%d'%i]=card(i,mb,'due')
    for _ in range(oks):   i+=1; FC['c%d'%i]=card(i,mb,'ok')
seed=make_seed({'studyNickname':'Leo','plan':'full','onboardingCompleted':True,'flashcards':FC,
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'},{'id':'k2','name':'Legislação','icon':'⚖️'}],
  'topics':{'k1':[{'id':'t1','name':'Saúde Mental','subtopics':[]},
                  {'id':'t3','name':'Cardio','subtopics':[]}],
            'k2':[{'id':'t2','name':'SUS','subtopics':[]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate("()=>{showScreen('flashcards');fcSelectedMb=null;fcInit();renderFCMbList();renderFCMain();}")
        await page.wait_for_timeout(400)

        async def estudar(js):
            await page.evaluate(js)
            await page.wait_for_timeout(400)
            return await page.evaluate("""()=>({
                titulo:(document.querySelector('.fc-title')||{}).textContent||'',
                fila:(fcStudyCards||[]).map(c=>c.id),
                materias:[...new Set((fcStudyCards||[]).map(c=>c.mbId))],
                status:[...new Set((fcStudyCards||[]).map(c=>fcStatus(c)))],
                filtro:fcStudyFilter, rev:fcRevFilter})""")

        r=await estudar("()=>fcOverviewClick('new')")
        print('--- clicou em "Novos" no resumo geral')
        print('    título        : %s'%r['titulo'].strip())
        print('    matérias na fila: %s  (tem que ser as 3)'%sorted(r['materias']))
        print('    status na fila  : %s  (tem que ser só new)'%r['status'])
        print('    total de cards  : %d  (11 novos no total)'%len(r['fila']))
        print('    ordem           : %s'%r['fila'])
        blocado = all(r['fila'][j].startswith('c') for j in range(0,0))
        # checa se NAO esta agrupado por materia
        mats=[c for c in r['fila']]
        print()

        # a fila muda de ordem a cada sessao?
        r2=await estudar("()=>{fcVoltar();return fcOverviewClick('new');}")
        print('--- nova sessão: ordem sorteada de novo?  %s'%('SIM' if r2['fila']!=r['fila'] else 'não (mesma ordem)'))
        print('    ordem 2         : %s'%r2['fila'])

        # com filtro de revisao ligado antes, nao pode vir vazio
        r3=await estudar("()=>{fcVoltar();fcRevFilter='due';return fcOverviewClick('new');}")
        print('\n--- com filtro "vencidos" ligado antes: %d cards (não pode ser 0) | rev=%s'%(len(r3['fila']),r3['rev']))

        # o botao explicito existe
        await page.evaluate("()=>{fcVoltar();renderFCMain();}")
        await page.wait_for_timeout(300)
        btn=await page.evaluate("""()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent.includes('Só os novos'));
            return b?{txt:b.textContent.trim(),desativado:b.disabled}:null;}""")
        print('\n--- botão no resumo geral: %s'%btn)
        print('erros: %s'%[e for e in errs if 'selectedPixTier' not in e])
        await b.close()
asyncio.run(main())
