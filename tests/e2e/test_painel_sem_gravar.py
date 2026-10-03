# -*- coding: utf-8 -*-
# Redesign, regra 6 do pedido: abrir o Painel nao pode gravar nada no banco. Antes,
# renderDashboard dava XP da meta, marco de sequencia e recordes — e chamava saveDB —
# a cada visita. Isso foi movido pra marcosDoDiaVerificar(), chamada so quando entra
# tempo de estudo (logStudySeconds) ou quando a meta e trocada (saveDailyGoal).
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

CONTA="""()=>{window.__saves=0;const orig=window.saveDB;
  window.saveDB=function(){window.__saves++;return orig.apply(this,arguments);};return true;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,make_seed({'xp':100,'dailyGoalMinutes':30}))
        await page.evaluate(CONTA)

        print('=== A) abrir o Painel varias vezes com a meta ja batida: zero gravacao ===')
        r=await page.evaluate("""()=>{
          db.sessions={};db.sessions[todayStr()]=40*60;db.goalHitDays=[];
          const xpAntes=db.xp;window.__saves=0;
          for(let i=0;i<5;i++){showScreen('map');showScreen('dashboard');}
          return {saves:window.__saves,xpAntes,xpDepois:db.xp,metaGravada:(db.goalHitDays||[]).length};}""")
        print('   %s'%r)
        assert r['saves']==0, 'visualizar o Painel nao pode chamar saveDB'
        assert r['xpDepois']==r['xpAntes'] and r['metaGravada']==0
        print('   OK\n')

        print('=== B) entrar tempo de estudo que bate a meta da o XP de sempre ===')
        r=await page.evaluate("""async()=>{
          db.sessions={};db.goalHitDays=[];const xpAntes=db.xp;
          logStudySeconds(31*60);
          await new Promise(r=>setTimeout(r,20));
          return {ganhou:db.xp-xpAntes,meta:db.goalHitDays.includes(todayStr())};}""")
        print('   %s'%r)
        assert r['ganhou']==20 and r['meta']
        print('   OK\n')

        print('=== C) o mesmo dia nao paga a meta duas vezes ===')
        r=await page.evaluate("""async()=>{
          const xpAntes=db.xp;logStudySeconds(10*60);
          await new Promise(r=>setTimeout(r,20));
          return db.xp-xpAntes;}""")
        print('   ganho extra: %s'%r)
        assert r==0
        print('   OK\n')

        print('=== D) sétimo dia seguido paga o marco de sequencia ===')
        r=await page.evaluate("""async()=>{
          db.sessions={};db.goalHitDays=[todayStr()];db.streakXpMilestone=0;db.longestStreak=0;
          for(let i=1;i<=6;i++)db.sessions[addDays(todayStr(),-i)]=600;
          const xpAntes=db.xp;logStudySeconds(60);
          await new Promise(r=>setTimeout(r,20));
          return {ganhou:db.xp-xpAntes,marco:db.streakXpMilestone,recorde:db.longestStreak};}""")
        print('   %s'%r)
        assert r['ganhou']>=50 and r['marco']==7 and r['recorde']==7  # +conquista de sequencia, se cruzar nivel
        print('   OK\n')

        print('=== E) sequencia que tinha caido fica marcada antes do estudo religar ===')
        r=await page.evaluate("""async()=>{
          db.sessions={};db.longestStreak=5;db.streakHadDrop=false;
          logStudySeconds(60);
          await new Promise(r=>setTimeout(r,20));
          return db.streakHadDrop;}""")
        print('   streakHadDrop: %s'%r)
        assert r is True
        print('   OK\n')

        print('=== F) baixar a meta abaixo do ja estudado tambem paga na hora ===')
        r=await page.evaluate("""async()=>{
          await new Promise(r=>setTimeout(r,20));
          db.sessions={};db.sessions[todayStr()]=20*60;db.goalHitDays=[];db.dailyGoalMinutes=60;
          // conquistas ja em dia, pra o XP medido aqui ser so o da meta
          db.achievementsState={};ACHIEVEMENTS_REGISTRY.forEach(a=>db.achievementsState[a.id]=achievementStatus(a).tierIdx);
          const xpAntes=db.xp;
          openDailyGoalModal();
          document.getElementById('daily-goal-input').value='15';
          saveDailyGoal();
          return {ganhou:db.xp-xpAntes,meta:db.goalHitDays.includes(todayStr())};}""")
        print('   %s'%r)
        assert r['ganhou']==20 and r['meta']
        print('   OK\n')

        print('=== G) conquista pendente: ver Painel e Conquistas nao grava; o proximo XP desbloqueia ===')
        r=await page.evaluate("""async()=>{
          await new Promise(r=>setTimeout(r,20));
          db.achievementsState={};       // tudo que ja foi alcancado vira "novo"
          window.__saves=0;const xpAntes=db.xp;
          for(let i=0;i<3;i++){showScreen('dashboard');showScreen('conquistas');}
          const savesVendo=window.__saves,xpVendo=db.xp-xpAntes;
          gainXP(1);
          await new Promise(r=>setTimeout(r,20));
          return {savesVendo,xpVendo,desbloqueou:Object.keys(db.achievementsState).length>0,
                  xpDepois:db.xp-xpAntes};}""")
        print('   %s'%r)
        assert r['savesVendo']==0 and r['xpVendo']==0, 'visualizar Painel/Conquistas nao pode gravar'
        assert r['desbloqueou'] and r['xpDepois']>1, 'o proximo ganho de XP tem que pagar a conquista pendente'
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
