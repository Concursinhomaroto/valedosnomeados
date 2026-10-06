# -*- coding: utf-8 -*-
# Relógio da revisão: abrir a tela de revisão começa a contar sozinho; responder, fechar
# (pelo X ou por outro caminho) lança o tempo no estudo do dia, no assunto e no reino. Com
# o cronômetro flutuante ligado, o relógio fica parado (não soma em dobro).
import asyncio, sys, datetime
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

hoje=(datetime.datetime.utcnow()-datetime.timedelta(hours=3)).date()
def d(n): return (hoje+datetime.timedelta(days=n)).isoformat()

def seed():
    subs=[{'id':'s0','name':'Pré-Natal de Alto Risco','priority':70,'studied':True,'studiedAt':d(-60)},
          {'id':'s1','name':'Puerpério','priority':70,'studied':True,'studiedAt':d(-60)}]
    return make_seed({'studyNickname':'Leo','kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Saúde da Mulher','icon':'⚔️','subtopics':subs}]},
      'revisions':{'s0':[{'date':d(-5),'completed':False}],'s1':[{'date':d(-3),'completed':False}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{db.sessions={};db.subTotalSeconds={};db.kingdomSeconds={};db.freeSessions=[];return true;}")

        print('=== A) abrir a revisão: o relógio aparece e corre sozinho ===')
        await page.evaluate("()=>revAbrirTela('s0')")
        t0=await page.evaluate("()=>document.getElementById('rev-relogio').textContent")
        await page.wait_for_timeout(3200)
        t1=await page.evaluate("()=>document.getElementById('rev-relogio').textContent")
        print('   %s -> %s'%(t0,t1))
        assert t0.startswith('⏱ 00:00:0') and t1>='⏱ 00:00:03'
        print('   OK\n')

        print('=== B) "Revisei": o tempo entra no dia, no assunto, no reino e no histórico ===')
        r=await page.evaluate("""()=>{revTelaResponder('s0',4);
          const fs=(db.freeSessions||[]).filter(x=>x.tipo==='revisao');
          return {dia:db.sessions[todayStr()]||0,sub:(db.subTotalSeconds||{}).s0||0,reino:(db.kingdomSeconds||{}).k1||0,
            fs:fs.length,seg:fs[0]&&fs[0].segundos,ticando:!!revTempoIntervalo};}""")
        print('   %s'%r)
        assert r['dia']>=3 and r['sub']==r['dia'] and r['reino']==r['dia'] and r['fs']==1 and r['seg']==r['dia'] and not r['ticando']
        print('   OK\n')

        print('=== C) fechar pelo X (sem responder) também lança o tempo ===')
        antes=await page.evaluate("()=>{revAbrirTela('s1');return db.sessions[todayStr()]||0;}")
        await page.wait_for_timeout(2200)
        await page.evaluate("()=>closeModal()")
        await page.wait_for_timeout(1300)
        r=await page.evaluate("()=>({dia:db.sessions[todayStr()]||0,sub:(db.subTotalSeconds||{}).s1||0,ticando:!!revTempoIntervalo})")
        print('   antes %s · %s'%(antes,r))
        assert r['dia']-antes>=2 and r['sub']>=2 and not r['ticando']
        print('   OK\n')

        print('=== D) cronômetro flutuante ligado: o relógio da revisão fica parado ===')
        r=await page.evaluate("()=>{ftRunning=true;ftStartedAt=Date.now();revAbrirTela('s1');return db.sessions[todayStr()]||0;}")
        await page.wait_for_timeout(2500)
        r2=await page.evaluate("""()=>{const t=document.getElementById('rev-relogio');const out={txt:t.textContent,pausa:t.classList.contains('rev-relogio-pausa')};
          revFecharTela();ftRunning=false;ftStartedAt=null;out.dia=db.sessions[todayStr()]||0;return out;}""")
        print('   antes %s · %s'%(r,r2))
        assert r2['pausa'] and r2['txt']=='⏱ contando no cronômetro' and r2['dia']==r
        print('   OK\n')

        print('=== E) revisando a partir do Painel, a "Meta diária" atualiza na hora ===')
        r=await page.evaluate("""()=>{db.dailyGoalMinutes=60;db.sessions[todayStr()]=29*60+27;showScreen('dashboard');
          return document.getElementById('goal-lbl').textContent;}""")
        await page.evaluate("()=>revAbrirTela('s1')")
        await page.wait_for_timeout(3400)
        r2=await page.evaluate("()=>{revTelaResponder('s1',4);return true;}")
        await page.wait_for_timeout(400)
        r3=await page.evaluate("()=>({lbl:document.getElementById('goal-lbl').textContent,ativa:document.getElementById('screen-dashboard').classList.contains('active')})")
        print('   antes %r · depois %s'%(r,r3))
        assert r.startswith('29 / 60'), 'antes da revisão: 29 min'
        assert r3['ativa'] and r3['lbl'].startswith('30 / 60') and int(r3['lbl'].split(' ')[0])>=30
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
