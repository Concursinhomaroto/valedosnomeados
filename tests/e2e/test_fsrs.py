import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
FC={
 'novo':{'id':'novo','mbId':'t1','pergunta':'Card novo','resposta':'R','tags':'','dificuldade':2,
         'acertos':0,'erros':0,'lastConf':0,'criacao':'2026-09-01T10:00:00Z','ultimaRevisao':None},
 'maduro':{'id':'maduro','mbId':'t1','pergunta':'Card maduro','resposta':'R','tags':'','dificuldade':2,
         'acertos':3,'erros':0,'lastConf':4,'criacao':'2026-01-01T10:00:00Z',
         'ultimaRevisao':'2026-08-22T10:00:00Z','sm2':{'ef':2.5,'reps':3,'interval':21}},
 'errado':{'id':'errado','mbId':'t1','pergunta':'Card que erro muito','resposta':'R','tags':'','dificuldade':2,
         'acertos':2,'erros':6,'lastConf':1,'criacao':'2026-01-01T10:00:00Z',
         'ultimaRevisao':'2026-09-05T10:00:00Z','sm2':{'ef':1.3,'reps':1,'interval':4}},
}
seed=make_seed({'studyNickname':'Leo','plan':'full','onboardingCompleted':True,'flashcards':FC,
  'kingdoms':[{'id':'k1','name':'Enf','icon':'💉'}],
  'topics':{'k1':[{'id':'t1','name':'Chefao','subtopics':[]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        print('--- migracao: estado inicial derivado do que ja existia')
        r=await page.evaluate("""()=>Object.values(db.flashcards).map(c=>({
            id:c.id, e:fsrsEstado(c), intervalo:fcNextInterval(c)}))""")
        for x in r: print('    %-8s %-34s intervalo atual: %s d'%(x['id'],json.dumps(x['e']),x['intervalo']))

        print('\n--- previa dos 4 botoes (o que aparece embaixo de cada um)')
        for cid in ('novo','maduro','errado'):
            pv=await page.evaluate("(id)=>[1,2,3,4].map(g=>fsrsPrevia(db.flashcards[id],g))",cid)
            print('    %-8s nao lembrei=%-4s dificil=%-4s lembrei=%-4s facil=%s'%(cid,*['%dd'%x for x in pv]))
        print('    (no SM-2, "novo" dava 1d nos quatro e "maduro" dava 52d em tres)')

        print('\n--- previa NAO pode gravar nada no card')
        antes=await page.evaluate("()=>JSON.stringify(db.flashcards.maduro)")
        await page.evaluate("()=>[1,2,3,4].forEach(g=>fsrsPrevia(db.flashcards.maduro,g))")
        depois=await page.evaluate("()=>JSON.stringify(db.flashcards.maduro)")
        print('    card intacto: %s'%(antes==depois))

        print('\n--- respondendo de verdade')
        for cid,conf,rot in [('novo',4,'novo + Facil (w[3]=5)'),('maduro',3,'maduro + Lembrei'),
                             ('errado',1,'que erro muito + Nao lembrei')]:
            r=await page.evaluate("""(a)=>{const c=db.flashcards[a.id];
                const d=fsrsAplicar(c,a.g);
                return {dias:d,S:c.fsrs.S,D:c.fsrs.D,sm2Intacto:JSON.stringify(c.sm2||null)};}""",{'id':cid,'g':conf})
            print('    %-32s -> %3d dias  S=%-7s D=%-5s  sm2 preservado: %s'%(
                  rot,r['dias'],r['S'],r['D'],r['sm2Intacto']))

        print('\n--- erro NAO zera: S cai mas nao vira 1')
        r=await page.evaluate("""()=>{const c={acertos:5,erros:0,sm2:{interval:60},
            ultimaRevisao:new Date(Date.now()-60*864e5).toISOString()};
            const antes=fsrsEstado(c).S; const d=fsrsAplicar(c,1);
            return {antes,depois:c.fsrs.S,dias:d};}""")
        print('    S ia de %s -> %s  (volta em %d dias, nao em 1)'%(r['antes'],r['depois'],r['dias']))

        print('\n--- efeito do espacamento: revisar atrasado rende MAIS')
        r=await page.evaluate("""()=>[0,10,30].map(atraso=>{
            const c={acertos:3,erros:0,sm2:{interval:21},
              ultimaRevisao:new Date(Date.now()-(21+atraso)*864e5).toISOString()};
            return {atraso,dias:fsrsAplicar(c,3)};})""")
        for x in r: print('    %2d dias de atraso -> proximo intervalo %d dias'%(x['atraso'],x['dias']))

        print('\n--- revisoes de MINIBOSS nao podem ter mudado (outro fluxo)')
        r=await page.evaluate("()=>sm2Next({ef:2.5,reps:3,interval:21},4)")
        print('    sm2Next({21d,reps3}, q=4) = %s'%json.dumps(r))
        print('\nerros: %s'%[e for e in errs if 'selectedPixTier' not in e])
        await b.close()
asyncio.run(main())
