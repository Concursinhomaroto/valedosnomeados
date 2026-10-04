# -*- coding: utf-8 -*-
# Relógio do treino: abriu as questões, o tempo começa a contar (igual ao simulado). Só
# corre com o Treinar na tela e a aba visível; a cada resposta o tempo entra no estudo do
# dia, no assunto da questão; no fim, a sessão vai pro histórico de tempo como "Treino".
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed():
    subs=[{'id':'s0','name':'Assunto 0','priority':70,'studied':True,'studiedAt':'2026-01-01'}]
    return make_seed({'studyNickname':'Leo','kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Urgência','icon':'⚔️','subtopics':subs}]}})

ACERVO="""()=>{db.acervo=[];for(let j=0;j<4;j++){const q={questao:'Q'+j+': julgue o item.',correta:'C',formato:'certoerrado',
  alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],explicacao:'.',subId:'s0',subName:'Assunto 0',
  topicName:'Urgência',kingdomId:'k1',kingdomName:'Enfermagem',kingdomIcon:'💉'};
  db.acervo.push({...q,_chaveForte:acervoChave2(q),...acervoCamposNovos('ia')});}return db.acervo.length;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)
        await page.evaluate("()=>{db.sessions={};db.subTotalSeconds={};db.kingdomSeconds={};db.freeSessions=[];showScreen('simgeral');"
                            "treinoIniciar(db.acervo.slice(),{titulo:'Relógio'});renderSimGeralScreen();return true;}")

        print('=== A) abriu as questões: o relógio aparece e corre ===')
        t0=await page.evaluate("()=>document.getElementById('treino-relogio').textContent")
        await page.wait_for_timeout(3200)
        t1=await page.evaluate("()=>document.getElementById('treino-relogio').textContent")
        print('   %s -> %s'%(t0,t1))
        assert t0.startswith('⏱ 00:00:0') and t1>=('⏱ 00:00:03') and t1!=t0
        print('   OK\n')

        print('=== B) responder lança o tempo no dia, no assunto e no reino ===')
        r=await page.evaluate("""()=>{treinoSelecionar('C');treinoConfirmarResposta();
          return {dia:db.sessions[todayStr()]||0,sub:(db.subTotalSeconds||{}).s0||0,reino:(db.kingdomSeconds||{}).k1||0};}""")
        print('   %s'%r)
        assert r['dia']>=3 and r['sub']==r['dia'] and r['reino']==r['dia']
        print('   OK\n')

        print('=== C) fora da tela do Treinar o relógio para ===')
        a=await page.evaluate("()=>{showScreen('dashboard');return Math.floor(treinoSessao.seg);}")
        await page.wait_for_timeout(2500)
        bb=await page.evaluate("()=>{const v=Math.floor(treinoSessao.seg);showScreen('simgeral');renderSimGeralScreen();return v;}")
        print('   antes %ss · depois de 2,5s fora %ss'%(a,bb))
        assert bb-a<=1
        print('   OK\n')

        print('=== D) encerrar: o resto entra, sessão "Treino" no histórico, tempo no resumo ===')
        await page.wait_for_timeout(1500)
        r=await page.evaluate("""()=>{treinoEncerrar();
          const fs=(db.freeSessions||[]).filter(x=>x.tipo==='treino');
          return {fs:fs.length,seg:fs[0]&&fs[0].segundos,dia:db.sessions[todayStr()],
            resumo:(document.querySelector('.treino-resumo-tempo')||{}).textContent||'',
            ticando:!!treinoTempoIntervalo};}""")
        print('   %s'%r)
        assert r['fs']==1 and r['seg']==r['dia'] and r['seg']>=4 and 'de treino' in r['resumo'] and not r['ticando']
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
