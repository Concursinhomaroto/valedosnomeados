# Domingo era fixo como "Descanso": sem botao de adicionar e, se houvesse item gravado
# naquela data, ele nem era desenhado. A prova e num domingo — simulado de domingo de
# manha e o treino mais parecido com o dia real.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Fundamentos','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Sondagem vesical','priority':70,'studied':True}]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('dashboard');return true;}")
        info=await page.evaluate("""()=>{
          const hoje=todayStr();
          for(let i=0;i<7;i++){const ds=addDays(hoje,i);
            if(new Date(ds+'T00:00:00').getDay()===0)return {hoje,domingo:ds,idx:i};}
          return null;}""")
        dom=info['domingo']
        print('hoje=%s · domingo da semana=%s (coluna %s)\n'%(info['hoje'],dom,info['idx']+1))

        print('=== A) domingo vazio: continua dizendo Descanso, mas agora clicavel ===')
        r=await page.evaluate("""(i)=>{db.weeklyPlan={};renderWeeklyPlan();
          const col=document.querySelectorAll('#weekly-plan .day-col')[i];
          const vazio=col.querySelector('.plan-empty-day');
          return {texto:col.textContent.replace(/\\s+/g,' ').trim(),
                  temBotaoMais:!!col.querySelector('.plan-add-btn'),
                  vazioClicavel:!!(vazio&&vazio.getAttribute('onclick')),
                  titulo:vazio?vazio.getAttribute('title'):null};}""",info['idx'])
        print('   coluna: %r'%r['texto'])
        print('   botão ＋ no cabeçalho: %s · o "Descanso" também abre: %s'
              %(r['temBotaoMais'],r['vazioClicavel']))
        print('   dica: %r'%r['titulo'])
        assert r['temBotaoMais'] and r['vazioClicavel'] and 'Descanso' in r['texto']
        print('   OK\n')

        print('=== B) dá pra marcar coisa no domingo ===')
        r=await page.evaluate("""async([dom,i])=>{
          openAddPlanItem(dom); await new Promise(r=>setTimeout(r,140));
          document.getElementById('plan-livre').value='Simulado de 120 questões';
          confirmAddPlanItem(dom);
          const col=document.querySelectorAll('#weekly-plan .day-col')[i];
          return {n:(db.weeklyPlan[dom]||[]).length,
                  texto:col.textContent.replace(/\\s+/g,' ').trim(),
                  temDescanso:!!col.querySelector('.plan-empty-day'),
                  temCartao:!!col.querySelector('.plan-item')};}""",[dom,info['idx']])
        print('   gravados: %s · cartão na tela: %s · sumiu o "Descanso": %s'
              %(r['n'],r['temCartao'],not r['temDescanso']))
        print('   coluna: %r'%r['texto'])
        assert r['n']==1 and r['temCartao'] and not r['temDescanso']
        print('   OK\n')

        print('=== C) miniboss no domingo também ===')
        r=await page.evaluate("""async([dom,i])=>{
          openAddPlanItem(dom); await new Promise(r=>setTimeout(r,140));
          const sel=document.getElementById('plan-sub-sel');
          sel.value=[...sel.options].find(o=>o.value.startsWith('s1|')).value;
          confirmAddPlanItem(dom);
          const col=document.querySelectorAll('#weekly-plan .day-col')[i];
          return {n:db.weeklyPlan[dom].length,
                  cartoes:col.querySelectorAll('.plan-item').length,
                  nomes:[...col.querySelectorAll('.plan-item-text')].map(e=>e.textContent)};}""",
          [dom,info['idx']])
        print('   %s itens · %s cartões: %s'%(r['n'],r['cartoes'],r['nomes']))
        assert r['n']==2 and r['cartoes']==2
        print('   OK\n')

        print('=== D) remover o último devolve o "Descanso" ===')
        r=await page.evaluate("""([dom,i])=>{
          removePlanItem(dom,0); removePlanItem(dom,0);
          const col=document.querySelectorAll('#weekly-plan .day-col')[i];
          return {n:(db.weeklyPlan[dom]||[]).length,
                  texto:col.textContent.replace(/\\s+/g,' ').trim()};}""",[dom,info['idx']])
        print('   itens: %s · coluna: %r'%(r['n'],r['texto']))
        assert r['n']==0 and 'Descanso' in r['texto']
        print('   OK\n')

        print('=== E) os outros dias não mudaram ===')
        r=await page.evaluate("""(i)=>{db.weeklyPlan={};renderWeeklyPlan();
          const cols=[...document.querySelectorAll('#weekly-plan .day-col')];
          return cols.map((c,k)=>({dom:k===i,
            mais:!!c.querySelector('.plan-add-btn'),
            vazio:(c.querySelector('.plan-empty-day')||{}).textContent}));}""",info['idx'])
        for k,c in enumerate(r):
            print('   coluna %d%s ＋:%s vazio:%r'%(k+1,' (dom)' if c['dom'] else '     ',c['mais'],(c['vazio'] or '').strip()))
        assert all(c['mais'] for c in r)
        assert all(('Descanso' in (c['vazio'] or '')) == c['dom'] for c in r)
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
