# "Revisão Geral · Enfermagem" contava tempo no reino, mas o relogio do chefao ficava
# eternamente em 0m (db.times so recebe o cronometro POR MINIBOSS) e a fila de revisao
# nao sabia de nada. Agora a sessao tem alvo de chefao.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def subs(nomes,pref,estudado=True):
    return [{'id':pref+str(i),'name':n,'priority':70,'studied':estudado,
             'studiedAt':'2026-01-01'} for i,n in enumerate(nomes)]

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'},
                  {'id':'k2','name':'Portugues','icon':'📖','color':'#3b82f6'}],
      'topics':{
        'k1':[{'id':'t1','name':'Urgencia e Emergencia','icon':'⚔️','subtopics':subs(
                 ['Choque septico','PCR','Trauma'],'u')},
              {'id':'t2','name':'Legislacao','icon':'⚔️','subtopics':subs(['Lei 7.498'],'l')}],
        'k2':[{'id':'t3','name':'Gramatica','icon':'⚔️','subtopics':subs(['Crase'],'g')}]},
      'revisions':{'u0':[{'date':'2026-01-10','completed':False}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{openKingdom(db.kingdoms[0]);return true;}")

        print('=== A) o chip do chefao mostra 0m antes de qualquer sessao ===')
        r=await page.evaluate("""()=>{renderTopics();
          const c=document.getElementById('tc-t1');
          return c.querySelector('.time-chip').textContent.trim();}""")
        print('   chip: %r'%r); assert '0m' in r
        print('   OK\n')

        print('=== B) o seletor de chefao segue o reino escolhido ===')
        r=await page.evaluate("""async()=>{floatTimerOpen();
          const rein=document.getElementById('ft-reino'), chef=document.getElementById('ft-chefao');
          const semReino={n:chef.options.length,txt:chef.options[0].textContent,off:chef.disabled};
          rein.value='k1'; ftPreencherChefoes();
          const comK1=[...chef.options].map(o=>o.textContent.trim());
          rein.value='k2'; ftPreencherChefoes();
          const comK2=[...chef.options].map(o=>o.textContent.trim());
          return {semReino,comK1,comK2};}""")
        print('   sem reino: %s opção(ões), desabilitado: %s → %r'
              %(r['semReino']['n'],r['semReino']['off'],r['semReino']['txt']))
        print('   Enfermagem: %s'%r['comK1'])
        print('   Portugues:  %s'%r['comK2'])
        assert r['semReino']['off'] and len(r['comK1'])==3 and len(r['comK2'])==2
        print('   OK\n')

        print('=== C) salvar 45min em "Urgencia e Emergencia" ===')
        r=await page.evaluate("""async()=>{
          document.getElementById('ft-reino').value='k1'; ftPreencherChefoes();
          document.getElementById('ft-chefao').value='t1';
          ftAccumulated=45*60; ftRunning=false; ftStartedAt=null;
          floatTimerSave();
          await new Promise(r=>setTimeout(r,250));
          const s=(db.freeSessions||[]).slice(-1)[0];
          return {topicSeconds:db.topicSeconds,kingdomSeconds:db.kingdomSeconds,
                  lifetime:db.lifetimeSeconds,sessao:s,
                  modal:document.getElementById('modal').classList.contains('open')};}""")
        print('   tempo do chefão: %s · do reino: %s · total: %s'
              %(r['topicSeconds'],r['kingdomSeconds'],r['lifetime']))
        print('   sessão gravada: %s'%{k:r['sessao'][k] for k in ['tipo','reinoName','chefaoName','segundos']})
        assert r['topicSeconds']['t1']==2700 and r['kingdomSeconds']['k1']==2700
        assert r['sessao']['chefaoName']=='Urgencia e Emergencia'
        assert r['modal'], 'devia abrir a pergunta de revisão'
        print('   OK\n')

        print('=== D) a pergunta de revisao vem so com os assuntos DAQUELE chefao ===')
        r=await page.evaluate("""()=>{
          const chks=[...document.querySelectorAll('.ftrev-chk')];
          const t=document.getElementById('modal-body').innerText;
          return {n:chks.length,ids:chks.map(c=>c.value),
                  marcados:chks.filter(c=>c.checked).map(c=>c.value),
                  temLei:t.indexOf('Lei 7.498')>=0, temCrase:t.indexOf('Crase')>=0};}""")
        print('   %s assuntos: %s · pré-marcados: %s'%(r['n'],r['ids'],r['marcados']))
        print('   trouxe assunto de outro chefão: %s · de outro reino: %s'%(r['temLei'],r['temCrase']))
        assert r['n']==3 and not r['temLei'] and not r['temCrase']
        assert r['marcados']==['u0'], 'só o que está na fila/atrasado vem marcado'
        print('   OK\n')

        print('=== E) "Só o tempo" nao mexe na fila ===')
        r=await page.evaluate("""()=>{
          const antes=JSON.stringify(db.revisions);
          closeModal();
          return antes===JSON.stringify(db.revisions);}""")
        print('   fila intacta: %s'%r); assert r
        print('   OK\n')

        print('=== F) marcar revisao tira da fila de verdade ===')
        r=await page.evaluate("""async()=>{
          const antes=revDiasParado(simFindSub('u0'));
          ftOferecerRevisao('t1');
          await new Promise(r=>setTimeout(r,120));
          document.querySelectorAll('.ftrev-chk').forEach(c=>{c.checked=(c.value==='u0'||c.value==='u1');});
          document.getElementById('ftrev-nota').value='4';
          ftConfirmarRevisao();
          await new Promise(r=>setTimeout(r,250));
          const feitas=id=>(db.revisions[id]||[]).filter(r=>r.completed).length;
          return {antes,depois:revDiasParado(simFindSub('u0')),
                  u0:feitas('u0'),u1:feitas('u1'),u2:feitas('u2'),
                  hoje:todayStr(),
                  ultima:(db.revisions['u0']||[]).filter(r=>r.completed).slice(-1)[0]};}""")
        print('   u0 estava há %s dias sem contato → agora %s'%(r['antes'],r['depois']))
        print('   revisões concluídas: u0=%s u1=%s u2=%s (o não marcado fica em 0)'
              %(r['u0'],r['u1'],r['u2']))
        print('   registro: %s'%r['ultima'])
        assert r['u0']==1 and r['u1']==1 and r['u2']==0 and r['depois']==0
        assert r['ultima']['date']==r['hoje'] and r['ultima']['quality']==4
        print('   OK\n')

        print('=== G) o chip do chefao agora mostra as horas ===')
        r=await page.evaluate("""()=>{renderTopics();
          const c=document.getElementById('tc-t1'), o=document.getElementById('tc-t2');
          return {t1:c.querySelector('.time-chip').textContent.trim(),
                  t2:o.querySelector('.time-chip').textContent.trim()};}""")
        print('   Urgência e Emergência: %r · Legislação (sem sessão): %r'%(r['t1'],r['t2']))
        assert '45m' in r['t1'] and '0m' in r['t2']
        print('   OK\n')

        print('=== H) tempo do miniboss e da sessao somam no mesmo chip ===')
        r=await page.evaluate("""()=>{db.times['u1']=15*60;renderTopics();
          return document.getElementById('tc-t1').querySelector('.time-chip').textContent.trim();}""")
        print('   45m da sessão + 15m do cronômetro do miniboss = %r'%r)
        assert '1h' in r
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
