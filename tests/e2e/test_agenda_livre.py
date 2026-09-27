# "Preciso conseguir colocar coisas sem precisar ser miniboss." A agenda so aceitava
# assunto cadastrado — simulado, academia, consulta, redacao nao cabiam nela.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#e11d48'}],
      'topics':{'k1':[{'id':'t1','name':'Fundamentos','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Sondagem vesical','priority':70,'studied':True}]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('dashboard');return true;}")
        hoje=await page.evaluate("()=>todayStr()")

        print('=== A) o modal abre com o campo livre em foco ===')
        r=await page.evaluate("""async(hoje)=>{db.weeklyPlan={};
          openAddPlanItem(hoje);
          await new Promise(r=>setTimeout(r,150));
          const el=document.getElementById('plan-livre');
          const sel=document.getElementById('plan-sub-sel');
          return {tem:!!el, foco:document.activeElement===el,
                  primeiraOpcao:sel?sel.options[0].textContent:null,
                  aviso:document.getElementById('modal-body').textContent
                        .indexOf('não precisa ser um assunto cadastrado')>=0};}""",hoje)
        print('   campo livre: %s · com foco: %s'%(r['tem'],r['foco']))
        print('   select começa em: %r'%r['primeiraOpcao'])
        assert r['tem'] and r['foco'] and r['aviso']
        print('   OK\n')

        print('=== B) escrever texto livre entra na agenda ===')
        r=await page.evaluate("""(hoje)=>{
          document.getElementById('plan-livre').value='Simulado de 120 questões';
          confirmAddPlanItem(hoje);
          const it=db.weeklyPlan[hoje][0];
          const col=document.querySelector('#weekly-plan .day-col');
          return {n:db.weeklyPlan[hoje].length,item:it,
                  texto:col.querySelector('.plan-item-text').textContent,
                  temSub:!!col.querySelector('.plan-item-sub'),
                  undef:col.textContent.indexOf('undefined')>=0};}""",hoje)
        print('   gravado: %s'%r['item'])
        print('   na tela: %r · mostra linha de chefão/reino: %s'%(r['texto'],r['temSub']))
        assert r['n']==1 and r['item']['livre'] and not r['item'].get('subId')
        assert r['texto']=='Simulado de 120 questões' and not r['temSub'] and not r['undef']
        print('   OK\n')

        print('=== C) DOIS itens livres diferentes no mesmo dia (o bug do dedup) ===')
        r=await page.evaluate("""async(hoje)=>{
          openAddPlanItem(hoje); await new Promise(r=>setTimeout(r,120));
          document.getElementById('plan-livre').value='Academia';
          confirmAddPlanItem(hoje);
          openAddPlanItem(hoje); await new Promise(r=>setTimeout(r,120));
          document.getElementById('plan-livre').value='Revisar redação';
          confirmAddPlanItem(hoje);
          return {n:db.weeklyPlan[hoje].length,
                  nomes:db.weeklyPlan[hoje].map(x=>x.name)};}""",hoje)
        print('   itens no dia: %s'%r['n'])
        for n in r['nomes']: print('     · %s'%n)
        assert r['n']==3
        print('   OK\n')

        print('=== D) repetir o MESMO texto e recusado ===')
        r=await page.evaluate("""async(hoje)=>{
          openAddPlanItem(hoje); await new Promise(r=>setTimeout(r,120));
          document.getElementById('plan-livre').value='  academia  ';
          confirmAddPlanItem(hoje);
          return db.weeklyPlan[hoje].length;}""",hoje)
        print('   continua com %s itens'%r); assert r==3
        print('   OK\n')

        print('=== E) miniboss continua funcionando, com chefão e reino ===')
        r=await page.evaluate("""async(hoje)=>{
          openAddPlanItem(hoje); await new Promise(r=>setTimeout(r,120));
          const sel=document.getElementById('plan-sub-sel');
          sel.value=[...sel.options].find(o=>o.value.startsWith('s1|')).value;
          confirmAddPlanItem(hoje);
          const it=db.weeklyPlan[hoje].find(x=>x.subId==='s1');
          const subs=[...document.querySelectorAll('#weekly-plan .plan-item-sub')];
          return {it,linhasSub:subs.length,sub:subs[0]?subs[0].textContent:null};}""",hoje)
        print('   gravado: %s'%r['it'])
        print('   linhas de chefão/reino na coluna: %s → %r'%(r['linhasSub'],r['sub']))
        assert r['it']['subId']=='s1' and r['it']['topic']=='Fundamentos'
        assert r['linhasSub']==1 and 'Fundamentos' in r['sub']
        print('   OK\n')

        print('=== F) campo vazio e select vazio: nao grava nada ===')
        r=await page.evaluate("""async(hoje)=>{
          const antes=db.weeklyPlan[hoje].length;
          openAddPlanItem(hoje); await new Promise(r=>setTimeout(r,120));
          confirmAddPlanItem(hoje);
          return {antes,depois:db.weeklyPlan[hoje].length,
                  modalAberto:!!document.getElementById('plan-livre')};}""",hoje)
        print('   %s → %s itens · modal continua aberto: %s'
              %(r['antes'],r['depois'],r['modalAberto']))
        assert r['antes']==r['depois'] and r['modalAberto']
        print('   OK\n')

        print('=== G) texto livre nao vira HTML ===')
        r=await page.evaluate("""async(hoje)=>{
          db.weeklyPlan={};
          openAddPlanItem(hoje); await new Promise(r=>setTimeout(r,120));
          document.getElementById('plan-livre').value='<img src=x onerror="window.__X=1"> prova';
          confirmAddPlanItem(hoje);
          const col=document.querySelector('#weekly-plan .day-col');
          return {img:!!col.querySelector('img'),x:window.__X||0,
                  texto:col.querySelector('.plan-item-text').textContent};}""",hoje)
        print('   virou <img>: %s · executou: %s · texto: %r'%(r['img'],r['x'],r['texto'][:36]))
        assert not r['img'] and not r['x']
        print('   OK\n')

        print('=== H) remover um item livre nao mexe nos outros ===')
        r=await page.evaluate("""async(hoje)=>{
          db.weeklyPlan={};db.weeklyPlan[hoje]=[
            {name:'A',livre:true},{name:'B',livre:true},{name:'C',livre:true}];
          renderWeeklyPlan();
          removePlanItem(hoje,1);
          return db.weeklyPlan[hoje].map(x=>x.name);}""",hoje)
        print('   sobraram: %s'%r); assert r==['A','C']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
