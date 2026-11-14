# -*- coding: utf-8 -*-
# Estatisticas que nao se perdem: diario por dia (registro + aparelho), juntar pelo maior (so sobe),
# reconstruir questoes/dia a partir das questoes, e aviso ao fechar com envio pendente.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors
from test_treino_filtros import seed, ACERVO

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)

        print('=== A) diario: saveDB grava o retrato do dia no registro e, no flush, no aparelho ===')
        r=await page.evaluate("""()=>{db.xp=777;db.lifetimeSeconds=5000;db.questoesPorDia={};db.questoesPorDia[todayStr()]={n:12,c:9,x:3};
          saveDB();saveFlush();const h=todayStr();const loc=statLogLerLocal();
          return {reg:db.statLog[h],loc:loc[h]};}""")
        print('   ',r)
        assert r['reg']['xp']==777 and r['reg']['n']==12 and r['loc']['xp']==777 and r['loc']['life']==5000
        print('   OK\n')

        print('=== B) juntar pelo maior: so sobe, nao apaga nada ===')
        r=await page.evaluate("""()=>{
          const hoje=todayStr(),ontem=addDays(hoje,-1);
          db.xp=100;db.lifetimeSeconds=1000;db.questoesPorDia={};db.questoesPorDia[ontem]={n:5,c:3,x:2};db.sessions={};db.sessions[ontem]=60;
          db.flashcards={a:{x:1}};
          const bkp={xp:900,lifetimeSeconds:20000,questoesPorDia:{[ontem]:{n:90,c:60,x:30},[addDays(hoje,-2)]:{n:40,c:20,x:20}},sessions:{[ontem]:3600},kingdomSeconds:{k1:500}};
          const mud=estatJuntar(bkp);
          const mud2=estatJuntar({xp:5,lifetimeSeconds:1,questoesPorDia:{[ontem]:{n:1,c:1,x:0}}});
          return {mud,mud2,xp:db.xp,life:db.lifetimeSeconds,ontem:db.questoesPorDia[ontem],anteontem:db.questoesPorDia[addDays(hoje,-2)],ses:db.sessions[ontem],ks:db.kingdomSeconds,fc:db.flashcards};}""")
        print('   ',r)
        assert r['xp']==900 and r['life']==20000 and r['ontem']['n']==90 and r['anteontem']['n']==40 and r['ses']==3600 and r['ks']=={'k1':500}
        assert r['mud']>=5 and r['mud2']==0 and r['fc']=={'a':{'x':1}}
        print('   OK\n')

        print('=== C) diario do aparelho recupera numeros que o registro perdeu ===')
        r=await page.evaluate("""()=>{
          const hoje=todayStr(),ontem=addDays(hoje,-1);
          localStorage.setItem(statLogChave(),JSON.stringify({[ontem]:{xp:5000,life:90000,seg:7200,n:100,c:70,x:30,ts:1}}));
          db.xp=10;db.lifetimeSeconds=10;db.sessions={};db.questoesPorDia={};
          const mud=estatJuntarDiario(statLogLerLocal());
          return {mud,xp:db.xp,life:db.lifetimeSeconds,seg:db.sessions[ontem],q:db.questoesPorDia[ontem]};}""")
        print('   ',r)
        assert r['xp']==5000 and r['life']==90000 and r['seg']==7200 and r['q']['n']==100
        print('   OK\n')

        print('=== D) reconstruir questoes/dia a partir do acervo ===')
        r=await page.evaluate("""async()=>{
          const hoje=todayStr(),ontem=addDays(hoje,-1);
          db.acervo.slice(0,6).forEach((q,i)=>{q.contadaEm=ontem;q.contadaResultado=i<4?'C':'E';});
          db.questoesPorDia={};
          const mud=await estatReconstruirDoAcervo();
          return {mud,d:db.questoesPorDia[ontem]};}""")
        print('   ',r)
        assert r['d']=={'n':6,'c':4,'x':2}
        print('   OK\n')

        print('=== E) modal de recuperar abre e mostra as fontes; botao Juntar funciona ===')
        r=await page.evaluate("""async()=>{await abrirRecuperarEstatisticas();
          const t=document.querySelector('.modal, #modal, [class*=modal]');
          const txt=document.body.innerText;
          return {titulo:txt.includes('Recuperar minhas estatísticas'),agora:txt.includes('Agora, na conta'),btn:txt.includes('Juntar pelo maior')};}""")
        print('   ',r); assert r['titulo'] and r['agora'] and r['btn']
        print('   OK\n')

        print('=== F) aviso ao fechar: envio pendente chama flush ===')
        r=await page.evaluate("""()=>{db.xp=(db.xp||0)+1;saveDB();const antes=savePendente;
          const ev=new Event('beforeunload',{cancelable:true});window.dispatchEvent(ev);return {antes,depois:savePendente,bloqueou:ev.defaultPrevented};}""")
        print('   ',r); assert r['antes'] is True and r['depois'] is False and r['bloqueou'] is True
        print('   OK\n')

        e=real_errors(errs); print('erros:',e); assert not e
        await b.close()
        print('TUDO OK')
asyncio.run(main())
