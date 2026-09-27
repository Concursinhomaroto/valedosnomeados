import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
FC={
 'novo':{'id':'novo','mbId':'t1','pergunta':'Card novo','resposta':'R','tags':'','dificuldade':2,
         'acertos':0,'erros':0,'lastConf':0,'criacao':'2026-09-01T10:00:00Z','ultimaRevisao':None},
 'maduro':{'id':'maduro','mbId':'t1','pergunta':'Card maduro','resposta':'R','tags':'','dificuldade':2,
         'acertos':3,'erros':0,'lastConf':4,'criacao':'2026-01-01T10:00:00Z',
         'ultimaRevisao':'2026-08-22T10:00:00Z','sm2':{'ef':2.5,'reps':3,'interval':21}},
}
seed=make_seed({'studyNickname':'Leo','plan':'full','onboardingCompleted':True,'flashcards':FC,
  'kingdoms':[{'id':'k1','name':'Enf','icon':'💉'}],
  'topics':{'k1':[{'id':'t1','name':'Chefao','subtopics':[]}]}})
async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        import json as _j
        for cid,rot in [('novo','CARD NOVO'),('maduro','CARD MADURO')]:
            await page.evaluate("(d)=>{db.flashcards=JSON.parse(d);}", _j.dumps(FC))
            await page.evaluate("""(id)=>{showScreen('flashcards');
                // deixa SO o card do caso no banco, senao a fila e remontada com os dois
                Object.keys(db.flashcards).forEach(k=>{if(k!==id)delete db.flashcards[k];});
                fcSelectedMb={id:'__ALL__',name:'x',icon:'x',kIcon:'',kingdom:'x'};
                fcStudyFilter='all';fcMode='study';fcShuffleSession();fcReaprenderLimpar();
                fcStudyCards=[db.flashcards[id]];fcStudyIdx=0;fcStudyFlipped=true;
                renderFCMain();}""",cid)
            await page.wait_for_timeout(350)
            r=await page.evaluate("""()=>[...document.querySelectorAll('.fc-conf-btn')]
                .map(b=>b.textContent.replace(/\\s+/g,' ').trim())""")
            print('--- %s'%rot)
            for x in r: print('    %s'%x)
            print()
        print('erros: %s'%[e for e in errs if 'selectedPixTier' not in e])
        await b.close()
asyncio.run(main())
