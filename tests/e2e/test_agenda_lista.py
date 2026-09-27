# "Ainda nao consigo ver o que eu faco." Sete colunas no cartao do painel dao ~130px
# cada; "Teorias de Enfermagem - Resumo" precisa de ~190px. Empilhado, cada dia e uma
# linha e o nome fica com a largura inteira do cartao.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

N1='Teorias de Enfermagem - Resumo'
N2='Bloco 1: Princípios Fundamentais'

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'},
                  {'id':'k2','name':'Constituição','icon':'📖','color':'#f59e0b'}],
      'topics':{'k1':[{'id':'t1','name':'Teorias de Enfermagem','icon':'⚔️','subtopics':[
                    {'id':'s1','name':N1,'priority':70,'studied':True}]}],
                'k2':[{'id':'t2','name':'Constituição do Brasil','icon':'⚔️','subtopics':[
                    {'id':'s2','name':N2,'priority':70,'studied':True}]}]}})

MEDE = """([hoje,nomes])=>{
  db.weeklyPlan={};db.weeklyPlan[hoje]=[
    {subId:'s1',name:nomes[0],topic:'Teorias de Enfermagem',kingdom:'Enfermagem',kColor:'#22d3ee'},
    {subId:'s2',name:nomes[1],topic:'Constituição do Brasil',kingdom:'Constituição',kColor:'#f59e0b'}];
  renderWeeklyPlan();
  const grid=document.querySelector('.week-plan-grid');
  const cols=[...document.querySelectorAll('#weekly-plan .day-col')];
  const txts=[...cols[0].querySelectorAll('.plan-item-text')];
  const larg=n=>Math.round(n.getBoundingClientRect().width);
  const cortado=n=>n.scrollWidth>n.clientWidth+1;
  const f=getComputedStyle(txts[0]).font;
  const probe=document.createElement('span');
  probe.style.cssText='position:absolute;visibility:hidden;white-space:nowrap;font:'+f;
  document.body.appendChild(probe);
  const precisa=nomes.map(n=>{probe.textContent=n;return Math.round(probe.getBoundingClientRect().width);});
  document.body.removeChild(probe);
  const r=grid.getBoundingClientRect();
  return {dias:cols.length,
    empilhado:cols[0].getBoundingClientRect().bottom<=cols[1].getBoundingClientRect().top+1,
    larguraTexto:txts.map(larg),precisa,cortados:txts.map(cortado),
    textos:txts.map(n=>n.textContent),
    alturaGrade:Math.round(r.height),
    rolaLado:grid.scrollWidth>grid.clientWidth+1};
}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('dashboard');return true;}")
        hoje=await page.evaluate("()=>todayStr()")

        for larg,alt,rotulo in [(1194,834,'iPad paisagem'),(1560,900,'desktop'),(414,896,'celular')]:
            await page.set_viewport_size({'width':larg,'height':alt})
            await page.wait_for_timeout(150)
            r=await page.evaluate(MEDE,[hoje,[N1,N2]])
            print('=== %s (%spx) ==='%(rotulo,larg))
            print('   dias visíveis: %s · empilhados: %s · rola de lado: %s'
                  %(r['dias'],r['empilhado'],r['rolaLado']))
            for i,t in enumerate(r['textos']):
                print('   %-34r %spx de espaço · precisa %spx · cortado: %s'
                      %(t,r['larguraTexto'][i],r['precisa'][i],r['cortados'][i]))
            assert r['dias']==7 and r['empilhado'] and not r['rolaLado']
            if larg>=1194:
                assert not any(r['cortados']), 'no iPad/desktop o nome tem que caber inteiro'
            print('   OK\n')

        print('=== altura: a semana inteira cabe sem virar rolagem infinita ===')
        await page.set_viewport_size({'width':1194,'height':834})
        r=await page.evaluate("""(hoje)=>{db.weeklyPlan={};renderWeeklyPlan();
          const g=document.querySelector('.week-plan-grid');
          const cols=[...document.querySelectorAll('.day-col')];
          return {grade:Math.round(g.getBoundingClientRect().height),
                  linha:Math.round(cols[0].getBoundingClientRect().height)};}""",hoje)
        print('   semana vazia: %spx no total, %spx por dia'%(r['grade'],r['linha']))
        assert r['linha']<=40
        print('   OK\n')

        print('=== o dia continua identificado, com HOJE e o ＋ ===')
        r=await page.evaluate("""()=>{const c=document.querySelector('.day-col');
          return {texto:c.querySelector('.day-header').textContent.replace(/\\s+/g,' ').trim(),
                  pill:!!c.querySelector('.day-today-pill'),
                  mais:!!c.querySelector('.plan-add-btn'),
                  hoje:c.classList.contains('today-col')};}""")
        print('   cabeçalho: %r · pill HOJE: %s · ＋: %s'%(r['texto'],r['pill'],r['mais']))
        assert r['pill'] and r['mais'] and r['hoje']
        print('   OK\n')

        print('=== chefão · reino continua aparecendo ===')
        r=await page.evaluate(MEDE,[hoje,[N1,N2]])
        r2=await page.evaluate("""()=>[...document.querySelectorAll('.day-col .plan-item-sub')]
            .map(e=>e.textContent)""")
        print('   %s'%r2)
        assert len(r2)==2 and 'Teorias de Enfermagem' in r2[0]
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
