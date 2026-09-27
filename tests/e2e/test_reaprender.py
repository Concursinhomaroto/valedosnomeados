import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
FC={}
for i in range(1,9):
    FC['c%d'%i]={'id':'c%d'%i,'mbId':'t1','pergunta':'Pergunta %d'%i,'resposta':'R%d'%i,'tags':'',
                 'dificuldade':2,'acertos':0,'erros':0,'lastConf':0,
                 'criacao':'2026-09-01T10:00:00Z','ultimaRevisao':None}
seed=make_seed({'studyNickname':'Leo','plan':'full','onboardingCompleted':True,'flashcards':FC,
  'kingdoms':[{'id':'k1','name':'Enf','icon':'💉'}],
  'topics':{'k1':[{'id':'t1','name':'Chefao','subtopics':[]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate("()=>{showScreen('flashcards');fcOverviewClick('new');}")
        await page.wait_for_timeout(500)
        est=lambda: page.evaluate("""()=>({idx:fcStudyIdx,fila:fcStudyCards.map(c=>c.id),
            reap:[...fcReaprender.keys()],fim:fcSessaoFim})""")
        print('--- inicio'); print('   ',await est())

        alvo=(await est())['fila'][0]
        await page.evaluate("(id)=>fcStudyConf(id,1)",alvo)   # ERRA o primeiro
        await page.wait_for_timeout(300)
        e=await est()
        print('\n--- errou %s ("nao lembrei")'%alvo)
        print('    fila agora: %s'%e['fila'])
        print('    %s foi recolocado? %s (posicoes: %s)'%(alvo,e['fila'].count(alvo)>1,
              [i for i,x in enumerate(e['fila']) if x==alvo]))
        print('    na fila de reaprendizado: %s'%e['reap'])

        # acerta todos os outros ate acabar
        for _ in range(40):
            e=await est()
            if e['fim']: break
            cur=e['fila'][e['idx']] if e['idx']<len(e['fila']) else None
            if cur is None: break
            await page.evaluate("(id)=>fcStudyConf(id,3)",cur)
            await page.wait_for_timeout(120)
        e=await est()
        print('\n--- respondeu tudo')
        print('    sessao terminou: %s  (nao pode dar a volta no baralho)'%e['fim'])
        print('    reaprendizado pendente: %s  (tem que estar vazio)'%e['reap'])
        tela=await page.evaluate("""()=>{const el=document.querySelector('.fc-fim');
            return el?{tit:el.querySelector('.fc-fim-tit').textContent,
                       sub:el.querySelector('.fc-fim-sub').textContent.replace(/\\s+/g,' '),
                       botoes:[...el.querySelectorAll('button')].map(b=>b.textContent.replace(/\\s+/g,' ').trim())}:null;}""")
        print('\n--- tela de fim de fila')
        if tela:
            print('    %s'%tela['tit']); print('    %s'%tela['sub'])
            for x in tela['botoes']: print('    [%s]'%x)
        else: print('    NAO RENDERIZOU')

        # o card errado ficou agendado pra 1 dia tambem (nao so na sessao)
        d=await page.evaluate("(id)=>({fsrs:db.flashcards[id].fsrs,prox:fcNextInterval(db.flashcards[id])})",alvo)
        print('\n--- o card errado tambem tem data real: %s'%json.dumps(d))
        print('erros: %s'%[e for e in errs if 'selectedPixTier' not in e])
        await b.close()
asyncio.run(main())
