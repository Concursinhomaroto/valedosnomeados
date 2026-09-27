# A agenda semanal: cartao vazando pra coluna vizinha, nome do miniboss entrando cru no
# HTML, e as datas saindo do relogio do aparelho enquanto o resto do app conta em Brasilia.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

LONGO='Teorias de Enfermagem e Sistematizacao da Assistencia de Enfermagem (SAE)'
XSS='<img src=x onerror="window.__X=1">Sondagem'

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#e11d48'}],
      'topics':{'k1':[{'id':'t1','name':'Fundamentos','icon':'⚔️','subtopics':[
          {'id':'s1','name':LONGO,'priority':70,'studied':True},
          {'id':'s2','name':XSS,'priority':70,'studied':True}]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('dashboard');return true;}")
        hoje=await page.evaluate("()=>todayStr()")

        print('=== A) os 7 dias saem de todayStr(), nao do relogio do aparelho ===')
        r=await page.evaluate("""()=>{renderWeeklyPlan();
          const cols=[...document.querySelectorAll('#weekly-plan .day-col')];
          const hoje=[...document.querySelectorAll('#weekly-plan .today-col')];
          return {n:cols.length,marcados:hoje.length,
                  primeiro:cols[0].textContent.replace(/\\s+/g,' ').trim().slice(0,30),
                  hojeNaPrimeira:cols[0].classList.contains('today-col')};}""")
        print('   colunas: %s · marcadas como HOJE: %s'%(r['n'],r['marcados']))
        print('   primeira: %r · é a de hoje: %s'%(r['primeiro'],r['hojeNaPrimeira']))
        assert r['n']==7 and r['marcados']==1 and r['hojeNaPrimeira']
        print('   OK\n')

        print('=== B) nome do miniboss nao executa nem vira HTML ===')
        r=await page.evaluate("""(hoje)=>{
          db.weeklyPlan={};db.weeklyPlan[hoje]=[
            {subId:'s2',name:'%s',topic:'Fundamentos',kingdom:'Enfermagem',kColor:'#e11d48'}];
          renderWeeklyPlan();
          const col=document.querySelector('#weekly-plan .day-col');
          return {img:!!col.querySelector('img'), x:window.__X||0,
                  texto:col.querySelector('.plan-item-text').textContent};}"""%XSS.replace('"','\\"'),hoje)
        print('   virou <img>: %s · executou: %s'%(r['img'],r['x']))
        print('   texto exibido: %r'%r['texto'][:40])
        assert not r['img'] and not r['x'] and '<img' in r['texto']
        print('   OK\n')

        print('=== C) nome comprido NAO vaza pra fora da linha do dia ===')
        r=await page.evaluate("""(hoje)=>{
          document.querySelector('#weekly-plan').closest('.section-card').classList.add('dash-fold');
          const wrap=document.getElementById('weekly-plan').parentElement;
          db.weeklyPlan={};db.weeklyPlan[hoje]=[
            {subId:'s1',name:'%s',topic:'Fundamentos',kingdom:'Enfermagem',kColor:'#e11d48'}];
          renderWeeklyPlan();
          const cols=[...document.querySelectorAll('#weekly-plan .day-col')];
          const item=cols[0].querySelector('.plan-item');
          const c=cols[0].getBoundingClientRect(), i=item.getBoundingClientRect();
          // os dias sao empilhados: o vizinho fica ABAIXO, nao ao lado
          const viz=cols[1].getBoundingClientRect();
          return {colDir:Math.round(c.right),itemDir:Math.round(i.right),
                  vizEsq:Math.round(viz.left),
                  vaza:i.right>c.right+1,
                  invade:i.bottom>viz.top+1,
                  linhas:Math.round(item.querySelector('.plan-item-text').getBoundingClientRect().height)};}"""%LONGO,hoje)
        print('   linha do dia termina em %spx · cartão termina em %spx'
              %(r['colDir'],r['itemDir']))
        print('   vaza da linha: %s · invade o dia de baixo: %s'%(r['vaza'],r['invade']))
        assert not r['vaza'] and not r['invade']
        print('   OK\n')

        print('=== D) no modo apertado o nome fica numa linha, com reticências ===')
        r=await page.evaluate("""()=>{
          const t=document.querySelector('#weekly-plan .plan-item-text');
          const st=getComputedStyle(t);
          return {clamp:st.webkitLineClamp||st.getPropertyValue('-webkit-line-clamp'),
                  wrap:st.whiteSpace,alturaPx:Math.round(t.getBoundingClientRect().height),
                  linha:parseFloat(st.lineHeight)};}""")
        linhas=round(r['alturaPx']/r['linha']) if r['linha'] else 0
        print('   white-space=%s · line-clamp=%s · ocupa ~%s linha(s)'%(r['wrap'],r['clamp'],linhas))
        # com os dias empilhados sobra largura: uma linha so, cortada com reticencias,
        # mantem a semana inteira visivel sem rolar. Nada de -webkit-line-clamp.
        assert r['wrap']=='nowrap' and str(r['clamp']) in ('none','') and linhas==1
        print('   OK\n')

        print('=== E) a grade normal (sem aperto) tambem nao estoura ===')
        r=await page.evaluate("""()=>{
          document.querySelector('#weekly-plan').closest('.section-card').classList.remove('dash-fold');
          renderWeeklyPlan();
          const col=document.querySelector('#weekly-plan .day-col');
          const item=col.querySelector('.plan-item');
          const c=col.getBoundingClientRect(), i=item.getBoundingClientRect();
          return {vaza:i.right>c.right+1,
                  sub:getComputedStyle(item.querySelector('.plan-item-sub')).textOverflow};}""")
        print('   vaza: %s · subtítulo com reticências: %s'%(r['vaza'],r['sub']))
        assert not r['vaza'] and r['sub']=='ellipsis'
        print('   OK\n')

        print('=== F) adicionar e remover continuam funcionando ===')
        r=await page.evaluate("""(hoje)=>{
          db.weeklyPlan={};
          openAddPlanItem(hoje);
          const sel=document.getElementById('plan-sub-sel');
          sel.value=[...sel.options].find(o=>o.value.startsWith('s1|')).value;
          confirmAddPlanItem(hoje);
          const depois=(db.weeklyPlan[hoje]||[]).length;
          const nome=(db.weeklyPlan[hoje][0]||{}).name;
          removePlanItem(hoje,0);
          return {depois,nome,final:(db.weeklyPlan[hoje]||[]).length};}""",hoje)
        print('   adicionou: %s item · nome gravado: %r'%(r['depois'],r['nome'][:40]))
        print('   removeu: sobrou %s'%r['final'])
        assert r['depois']==1 and r['final']==0 and r['nome']==LONGO
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
