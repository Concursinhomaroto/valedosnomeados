# Simulado feito fora da plataforma (caderno, prova antiga, cursinho) nao entrava em
# lugar nenhum. Agora entra em sub.simStats — que manda no peso da fila de revisao,
# no "assuntos que mais erro" e no dashboard.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

SUB='s1'; TOPIC='t1'; KING='k1'

def seed():
    return make_seed({'studyNickname':'Leo',
        'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
        'topics':{KING:[{'id':TOPIC,'name':'Lei do Exercicio','icon':'⚔️','subtopics':[
            {'id':SUB,'name':'Lei 7.498/1986','priority':70,'studied':True,'studiedAt':'2026-01-01'},
            {'id':'s2','name':'COFEN','priority':70,'studied':True,'studiedAt':'2026-01-01'}]}]}})

MONTA = """()=>{
  const s=simFindSub('%s');
  openSim.add('%s');
  let h=document.getElementById('sim-%s');
  if(!h){h=document.createElement('div');h.id='sim-%s';document.body.appendChild(h);}
  h.innerHTML=simPanelHTML(s);
  return true;
}""" % (SUB,SUB,SUB,SUB)

PREENCHE = """([q,a,f,d,fonte])=>{
  document.getElementById('sim-ext-qtd-%s').value=q;
  document.getElementById('sim-ext-ac-%s').value=a;
  document.getElementById('sim-ext-fmt-%s').value=f;
  document.getElementById('sim-ext-data-%s').value=d;
  document.getElementById('sim-ext-fonte-%s').value=fonte;
  simExternoConfere('%s');
  return document.getElementById('sim-ext-aviso-%s').textContent;
}""" % ((SUB,)*7)

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(MONTA)
        hoje=await page.evaluate("()=>todayStr()")

        print('=== A) o painel oferece registrar ===')
        r=await page.evaluate("""()=>document.getElementById('sim-%s').textContent.indexOf('Registrar simulado feito fora')>=0"""%SUB)
        print('   botao presente: %s'%r); assert r
        print('   OK\n')

        print('=== B) o formulario abre com data de hoje e sem numeros chutados ===')
        r=await page.evaluate("""()=>{simAbrirExterno('%s');
          return {qtd:document.getElementById('sim-ext-qtd-%s').value,
                  ac:document.getElementById('sim-ext-ac-%s').value,
                  data:document.getElementById('sim-ext-data-%s').value,
                  max:document.getElementById('sim-ext-data-%s').getAttribute('max')};}"""%((SUB,)*5))
        print('   %s'%r)
        assert r['qtd']=='' and r['ac']=='' and r['data']==hoje and r['max']==hoje
        print('   OK\n')

        print('=== C) acertos > questoes e barrado, e nao gasta estatistica ===')
        aviso=await page.evaluate(PREENCHE,[30,40,'multipla',hoje,''])
        print('   aviso ao vivo: %r'%aviso)
        assert 'passar da quantidade' in aviso
        r=await page.evaluate("""()=>{simRegistrarExterno('%s');
          const s=simFindSub('%s');
          return {stats:s.simStats||null,ext:(s.simExternos||[]).length,
                  aindaNoForm:!!document.getElementById('sim-ext-qtd-%s')};}"""%((SUB,)*3))
        print('   simStats: %s · registros: %s · form aberto: %s'%(r['stats'],r['ext'],r['aindaNoForm']))
        assert r['stats'] is None and r['ext']==0 and r['aindaNoForm']
        print('   OK\n')

        print('=== D) data no futuro e barrada ===')
        r=await page.evaluate("""(f)=>{document.getElementById('sim-ext-qtd-%s').value=10;
          document.getElementById('sim-ext-ac-%s').value=7;
          document.getElementById('sim-ext-data-%s').value=f;
          simRegistrarExterno('%s');
          return (simFindSub('%s').simExternos||[]).length;}"""%((SUB,)*5),'2099-01-01')
        print('   registros: %s'%r); assert r==0
        print('   OK\n')

        print('=== E) registro valido entra em simStats e por formato ===')
        aviso=await page.evaluate(PREENCHE,[30,21,'certoerrado',hoje,'Qconcursos'])
        print('   aviso ao vivo: %r'%aviso)
        assert '70%' in aviso and '9 erros' in aviso
        r=await page.evaluate("""async()=>{simRegistrarExterno('%s');
          await new Promise(r=>setTimeout(r,500));
          const s=simFindSub('%s');
          return {st:s.simStats,ext:s.simExternos,
                  fechou:!document.getElementById('sim-ext-qtd-%s'),
                  gravou:window.__updateCalls.length>0};}"""%((SUB,)*3))
        print('   simStats: %s'%r['st'])
        print('   registro: %s'%r['ext'][0])
        print('   form fechou: %s · gravou no Firebase: %s'%(r['fechou'],r['gravou']))
        st=r['st']
        assert st['questoesTotal']==30 and st['acertosTotal']==21 and st['tentativas']==1
        assert st['porFormato']['certoerrado']=={'tentativas':1,'questoes':30,'acertos':21,'marcadas':30}
        assert r['ext'][0]['fonte']=='Qconcursos' and r['ext'][0]['data']==hoje
        assert r['fechou'] and r['gravou']
        print('   OK\n')

        print('=== F) NAO encostou no simHistorico (o Banco de Erros e de la) ===')
        r=await page.evaluate("""()=>({hist:(simFindSub('%s').simHistorico||[]).length,
                                       banco:getErrorBank().length})"""%SUB)
        print('   simHistorico: %s itens · Banco de Erros: %s'%(r['hist'],r['banco']))
        assert r['hist']==0 and r['banco']==0
        print('   OK\n')

        print('=== G) certo/errado entra corrigido, nao pelo bruto ===')
        r=await page.evaluate("""()=>{const st=simFindSub('%s').simStats;
          return {efetivo:simPctEfetivo(st)};}"""%SUB)
        print('   bruto %s%% · corrigido %s%% (desconta o chute de 50%%)'
              %(r['efetivo']['bruto'],r['efetivo']['corrigido']))
        assert r['efetivo']['bruto']==70 and r['efetivo']['corrigido']<70
        print('   OK\n')

        print('=== H) mexe no peso da fila de revisao ===')
        r=await page.evaluate("""()=>{
          const a=simFindSub('%s'), b=simFindSub('s2');
          const pesoAntes=revPeso(b,'%s');
          const pesoRuim=revPeso(a,'%s');
          // agora um assunto em que ele vai BEM
          const c=simFindSub('s2');
          c.simStats={tentativas:1,questoesTotal:30,acertosTotal:29,porFormato:{multipla:{tentativas:1,questoes:30,acertos:29}}};
          return {semDado:pesoAntes,errando:pesoRuim,acertando:revPeso(c,'%s'),
                  acerto:revAcerto(a)};}"""%(SUB,TOPIC,TOPIC,TOPIC))
        print('   sem dado nenhum: %.3f'%r['semDado'])
        print('   errando (21/30): %.3f  ← sobe na fila'%r['errando'])
        print('   acertando (29/30): %.3f  ← desce'%r['acertando'])
        assert r['errando']>r['acertando']
        assert abs(r['acerto']-0.7)<0.001
        print('   OK\n')

        print('=== I) desfazer devolve as estatisticas ao que eram ===')
        r=await page.evaluate("""()=>{
          window.confirm=()=>true;
          const s=simFindSub('%s');
          const id=s.simExternos[0].id;
          simRemoverExterno('%s',id);
          const st=s.simStats;
          return {st,ext:(s.simExternos||[]).length,acerto:revAcerto(s)};}"""%(SUB,SUB))
        print('   simStats: %s · registros: %s · revAcerto: %s'%(r['st'],r['ext'],r['acerto']))
        assert r['st']['questoesTotal']==0 and r['st']['acertosTotal']==0 and r['st']['tentativas']==0
        assert r['st']['porFormato']['certoerrado']=={'tentativas':0,'questoes':0,'acertos':0,'marcadas':0}
        assert r['ext']==0 and r['acerto'] is None
        print('   OK\n')

        print('=== J) desfazer cancelado nao apaga nada ===')
        r=await page.evaluate("""async()=>{
          simAbrirExterno('%s');
          document.getElementById('sim-ext-qtd-%s').value=10;
          document.getElementById('sim-ext-ac-%s').value=6;
          simRegistrarExterno('%s');
          window.confirm=()=>false;
          const s=simFindSub('%s');
          simRemoverExterno('%s',s.simExternos[0].id);
          return {ext:s.simExternos.length,q:s.simStats.questoesTotal};}"""%((SUB,)*6))
        print('   registros: %s · questoesTotal: %s'%(r['ext'],r['q']))
        assert r['ext']==1 and r['q']==10
        print('   OK\n')

        print('=== K) o painel mostra quanto veio de fora, e a lista ===')
        r=await page.evaluate("""(id)=>{const t=document.getElementById('sim-'+id).textContent;
          return {deFora:t.indexOf('10 de fora')>=0, secao:t.indexOf('Feitos fora daqui')>=0,
                  pct:t.indexOf('60%')>=0};}""",SUB)
        print('   "de fora" no badge: %s · seção da lista: %s · %% do registro: %s'
              %(r['deFora'],r['secao'],r['pct']))
        assert r['deFora'] and r['secao'] and r['pct']
        print('   OK\n')

        print('=== L) guarda no maximo 20 registros, mas as estatisticas somam todos ===')
        r=await page.evaluate("""()=>{const s=simFindSub('%s');
          for(let i=0;i<25;i++){
            simAbrirExterno('%s');
            document.getElementById('sim-ext-qtd-%s').value=4;
            document.getElementById('sim-ext-ac-%s').value=2;
            simRegistrarExterno('%s');
          }
          return {lista:s.simExternos.length,q:s.simStats.questoesTotal,a:s.simStats.acertosTotal};}"""%((SUB,)*5))
        print('   lista: %s · questoesTotal: %s · acertosTotal: %s'%(r['lista'],r['q'],r['a']))
        assert r['lista']==20 and r['q']==10+25*4 and r['a']==6+25*2
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
