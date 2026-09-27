# Os 20 min por revisao eram chute meu, e o ciclo inteiro depende deles: se a revisao
# leva 5 min e o app supoe 20, a barra diz que cabem 12 por dia quando cabem 48.
# A tela de revisao agora cronometra do abrir ao responder.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
RESUMO={'texto':'VISAO GERAL: texto do resumo.','geradoEm':'2026-08-01T10:00:00Z','origem':'web'}
SUBS=[{'id':'s%d'%i,'name':'A%d'%i,'priority':70,'studied':True,'studiedAt':'2026-01-01',
       'resumo':RESUMO} for i in range(1,13)]
seed=make_seed({'studyNickname':'Leo','kingdoms':[{'id':'k1','name':'Enf','icon':'🏥'}],
  'topics':{'k1':[{'id':'t1','name':'T','subtopics':SUBS}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        print('=== A) sem amostras suficientes, segue no palpite ===')
        r=await page.evaluate("""()=>{
          db.revOrcamentoMin=240; db.revDuracoes=[]; delete db.revCustoMin;
          const a=revEstado();
          db.revDuracoes=[300,300,300,300];        // so 4 revisoes de 5 min
          const b=revEstado();
          return {vazio:{custo:a.custo,medido:a.medido,porDia:a.porDia},
                  poucas:{custo:b.custo,medido:b.medido,amostras:b.amostras}};
        }""")
        print('   sem nenhuma: %d min (medido: %s) -> %d por dia'
              %(r['vazio']['custo'],r['vazio']['medido'],r['vazio']['porDia']))
        print('   com 4 amostras: %d min (medido: %s) — ainda nao vale'
              %(r['poucas']['custo'],r['poucas']['medido']))
        assert r['vazio']['custo']==20 and r['vazio']['medido'] is None
        assert r['poucas']['custo']==20 and r['poucas']['medido'] is None
        print('   OK\n')

        print('=== B) 5 revisoes de 5 min: o ciclo se ajusta sozinho ===')
        r2=await page.evaluate("""()=>{
          db.revDuracoes=[300,300,290,310,300];
          const e=revEstado();
          return {custo:e.custo,medido:e.medido,porDia:e.porDia,ciclo:e.ciclo,est:e.estudados};
        }""")
        print('   %d assuntos · %d min por revisao (medido) · %d por dia · ciclo %d dias'
              %(r2['est'],r2['custo'],r2['porDia'],r2['ciclo']))
        assert r2['medido']==5 and r2['custo']==5 and r2['porDia']==48
        print('   OK — antes o app diria 12 por dia\n')

        print('=== C) mediana, nao media: uma revisao interrompida nao desloca tudo ===')
        r3=await page.evaluate("""()=>{
          db.revDuracoes=[300,300,300,300,300,300,300,300,300,4200]; // 9x 5min + 1x 70min
          const med=revCustoMedido();
          const media=Math.round(db.revDuracoes.reduce((a,b)=>a+b,0)/db.revDuracoes.length/60);
          return {med,media};
        }""")
        print('   mediana %d min vs media %d min'%(r3['med'],r3['media']))
        assert r3['med']==5 and r3['media']>10
        print('   OK\n')

        print('=== D) a tela cronometra de verdade, do abrir ao responder ===')
        r4=await page.evaluate("""async()=>{
          db.revDuracoes=[];
          revAbrirTela('s1');
          await new Promise(r=>setTimeout(r,300));
          // simula 6 minutos passados desde a abertura
          revAbertoEm=Date.now()-6*60*1000;
          revTelaResponder('s1',4);
          await new Promise(r=>setTimeout(r,200));
          return {n:(db.revDuracoes||[]).length, seg:(db.revDuracoes||[])[0]};
        }""")
        print('   registrou %d amostra de %d segundos (~%d min)'%(r4['n'],r4['seg'],round(r4['seg']/60)))
        assert r4['n']==1 and 350<=r4['seg']<=370
        print('   OK\n')

        print('=== E) fechar sem responder, ou ficar 3 horas, nao contam ===')
        r5=await page.evaluate("""async()=>{
          db.revDuracoes=[];
          revAbrirTela('s2'); await new Promise(r=>setTimeout(r,150));
          revFecharTela();                       // fechou no X
          const aposFechar=(db.revDuracoes||[]).length;
          revAbrirTela('s3'); await new Promise(r=>setTimeout(r,150));
          revAbertoEm=Date.now()-3*60*60*1000;   // 3 horas
          revTelaResponder('s3',4); await new Promise(r=>setTimeout(r,150));
          const aposLongo=(db.revDuracoes||[]).length;
          revAbrirTela('s4'); await new Promise(r=>setTimeout(r,150));
          revAbertoEm=Date.now()-4*1000;         // 4 segundos
          revTelaResponder('s4',4); await new Promise(r=>setTimeout(r,150));
          return {aposFechar,aposLongo,aposCurto:(db.revDuracoes||[]).length};
        }""")
        print('   fechou no X: %d amostras · 3 horas: %d · 4 segundos: %d'
              %(r5['aposFechar'],r5['aposLongo'],r5['aposCurto']))
        assert r5['aposFechar']==0 and r5['aposLongo']==0 and r5['aposCurto']==0
        print('   OK\n')

        print('=== F) a janela movel guarda so as ultimas 30 ===')
        r6=await page.evaluate("""()=>{
          db.revDuracoes=[];
          for(let i=0;i<40;i++)revRegistrarDuracao(60*(i+1));
          return {n:db.revDuracoes.length,primeira:db.revDuracoes[0]/60};
        }""")
        print('   40 registradas -> guardou %d, comecando em %d min'%(r6['n'],r6['primeira']))
        assert r6['n']==30 and r6['primeira']==11
        print('   OK\n')

        print('=== G) a barra diz de onde vem o numero ===')
        r7=await page.evaluate("""()=>{
          db.revDuracoes=[]; filterRevs('fila',document.querySelector('#screen-revisions .chip'));
          const est=document.getElementById('revisions-list').textContent.replace(/\\s+/g,' ');
          db.revDuracoes=[300,300,300,300,300]; renderRevisions();
          const med=document.getElementById('revisions-list').textContent.replace(/\\s+/g,' ');
          return {est:est.indexOf('por revisão · estimado')>=0,
                  med:med.indexOf('por revisão · medido')>=0,
                  temCinco:med.indexOf('5min')>=0};
        }""")
        print('   sem medicao mostra "estimado": %s'%r7['est'])
        print('   com medicao mostra "medido" e o 5min: %s / %s'%(r7['med'],r7['temCinco']))
        assert r7['est'] and r7['med'] and r7['temCinco']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
