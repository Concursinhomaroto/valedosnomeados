# -*- coding: utf-8 -*-
# Conquistas de Questões & Missões + dash de acompanhamento na tela Conquistas: números
# gerais, conquistas recentes (data e XP), "quase lá" e progresso por categoria.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,make_seed({'studyNickname':'Leo'}))

        print('=== A) categoria nova com 11 conquistas + 1 secreta ===')
        r=await page.evaluate("""()=>({q:ACHIEVEMENTS_REGISTRY.filter(a=>a.categoria==='questoes').map(a=>a.id),
          sec:!!ACHIEVEMENTS_REGISTRY.find(a=>a.id==='revisor_banca'&&a.secreta),
          ids:new Set(ACHIEVEMENTS_REGISTRY.map(a=>a.id)).size===ACHIEVEMENTS_REGISTRY.length})""")
        print('   %s'%r)
        assert len(r['q'])==11 and r['sec'] and r['ids']
        print('   OK\n')

        print('=== B) valores lidos do registro de questões por dia ===')
        r=await page.evaluate("""()=>{const h=todayStr();db.metaQuestoesDia=30;
          db.questoesPorDia={};db.questoesPorDia[addDays(h,-2)]={n:25,c:22,x:3};
          db.questoesPorDia[addDays(h,-1)]={n:40,c:30,x:10};db.questoesPorDia[h]={n:12,c:10,x:2};
          db.questoesPorDia[addDays(h,-10)]={n:5,c:5,x:0};
          const v=id=>achievementStatus(ACHIEVEMENTS_REGISTRY.find(a=>a.id===id)).val;
          return {feitas:v('q_feitas'),certas:v('q_certas'),recorde:v('q_recorde'),meta:v('q_meta'),sniper:v('q_sniper'),seq:v('q_sequencia')};}""")
        print('   %s'%r)
        assert r=={'feitas':82,'certas':67,'recorde':40,'meta':1,'sniper':1,'seq':3}
        print('   OK\n')

        print('=== C) missão concluída vira registro (uma vez por dia) ===')
        r=await page.evaluate("""()=>{db.missoesConcluidas=[];
          try{Object.keys(localStorage).filter(k=>k.indexOf('vdn_missao')===0).forEach(k=>localStorage.removeItem(k));}catch(e){}
          missaoMem=null;const m=missaoMontar();m.iniciada=true;missaoGuardar(m);
          const real=window.missaoEstado;window.missaoEstado=()=>({itens:[],feitos:1,total:1,acabou:true});
          try{missaoTick();const m2=missaoAtual();m2.concluida=false;missaoGuardar(m2);missaoTick();}finally{window.missaoEstado=real;}
          closeModal();
          return {reg:db.missoesConcluidas,val:achievementStatus(ACHIEVEMENTS_REGISTRY.find(a=>a.id==='missoes')).val};}""")
        print('   %s'%r)
        assert len(r['reg'])==1 and r['val']==1
        print('   OK\n')

        print('=== D) desbloqueio entra no histórico com data e XP; o dash mostra ===')
        r=await page.evaluate("""()=>{db.achievementsLog=[];['q_feitas','q_certas','q_recorde','q_meta','q_sniper','q_sequencia','missoes'].forEach(id=>delete db.achievementsState[id]);checkAchievementUnlocks();
          const log=db.achievementsLog;
          showScreen('conquistas');
          const d=document.getElementById('conquistas-dash');
          return {log:log.filter(x=>['q_feitas','q_recorde','missoes'].includes(x.id)).map(x=>x.id),
            comData:log.every(x=>x.em&&typeof x.xp==='number'),
            recentes:d.querySelectorAll('.cd-rec').length,quase:d.querySelectorAll('.cd-quase').length,
            cats:[...d.querySelectorAll('.cd-cat span')].map(x=>x.textContent),
            topo:[...d.querySelectorAll('.cd-topo>div span')].map(x=>x.textContent),
            primeiroRecente:(d.querySelector('.cd-rec small')||{}).textContent};}""")
        print('   %s'%r)
        assert set(r['log'])>={'q_feitas','q_recorde','missoes'} and r['comData']
        assert r['recentes']>=3 and r['quase']>=1 and r['primeiroRecente']=='hoje'
        assert r['cats'][0]=='📝 Questões & Missões' and len(r['topo'])==4
        print('   OK\n')

        print('=== E) filtro da categoria nova e tela sem gravar ao abrir ===')
        r=await page.evaluate("""()=>{window.__s=0;const o=window.saveDB;window.saveDB=function(){window.__s++;return o.apply(this,arguments)};
          conqSetFilter('cat','questoes');const n=document.querySelectorAll('#conquistas-grid .conq-card').length;
          conqSetFilter('cat','all');showScreen('dashboard');showScreen('conquistas');return {n,saves:window.__s};}""")
        print('   %s'%r)
        assert r['n']==11 and r['saves']==0
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
