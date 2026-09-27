# Marca-texto no resumo. A marca nao pode ser guardada como posicao no HTML:
# resumoFormatar reescreve o HTML a cada render. Ela guarda o TRECHO e qual ocorrencia,
# e e reencontrada por busca — sobrevive a render, troca de tela e edicao do resumo.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

TEXTO=("CHOQUE SEPTICO:\n"
       "A reposicao inicial e de 30 mL/kg de cristaloide na primeira hora. "
       "O lactato serve de alvo, e a reposicao segue guiada por ele.\n\n"
       "Na pratica: paciente hipotenso no plantao recebe a reposicao inicial.")
SUB='s1'

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':SUB,'name':'Choque septico','priority':100,'studied':True,
           'resumo':{'texto':TEXTO,'geradoEm':'2026-09-01T10:00:00.000Z','origem':'web'}}]}]}})

MONTA = """()=>{
  const s=simFindSub('%s');
  openResumo.add('%s');
  let h=document.getElementById('resumo-%s');
  if(!h){h=document.createElement('div');h.id='resumo-%s';document.body.appendChild(h);}
  resumoRefreshPanel('%s');
  return true;
}""" % ((SUB,)*5)

# seleciona um trecho dentro do .resumo-body procurando no texto
SELECIONA = """(alvo)=>{
  const root=document.querySelector('#resumo-s1 .resumo-body[data-sub]');
  const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null);
  let n;
  while((n=w.nextNode())){
    const i=n.nodeValue.indexOf(alvo);
    if(i>=0){
      const r=document.createRange();
      r.setStart(n,i); r.setEnd(n,i+alvo.length);
      const sel=window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
      return true;
    }
  }
  return false;
}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(MONTA)

        print('=== A) marcar um trecho ===')
        ok=await page.evaluate(SELECIONA,'30 mL/kg')
        assert ok, 'nao achei o trecho pra selecionar'
        r=await page.evaluate("""()=>{
          const salvou=marcaSalvarSelecao('%s');
          marcaAplicarTodas();
          const mks=[...document.querySelectorAll('#resumo-s1 mark.resumo-marca')];
          return {salvou,marcas:simFindSub('%s').resumo.marcas,
                  naTela:mks.map(m=>m.textContent)};}"""%(SUB,SUB))
        print('   salvou: %s · guardado: %s'%(r['salvou'],r['marcas']))
        print('   na tela: %s'%r['naTela'])
        assert r['salvou'] and len(r['marcas'])==1 and r['marcas'][0]['t']=='30 mL/kg'
        assert r['naTela']==['30 mL/kg']
        print('   OK\n')

        print('=== B) sobrevive ao redesenho do painel ===')
        r=await page.evaluate("""()=>{resumoRefreshPanel('%s');
          return [...document.querySelectorAll('#resumo-s1 mark.resumo-marca')].map(m=>m.textContent);}"""%SUB)
        print('   depois de redesenhar: %s'%r); assert r==['30 mL/kg']
        print('   OK\n')

        print('=== C) aparece tambem na tela de revisao ===')
        r=await page.evaluate("""async()=>{revAbrirTela('%s');
          await new Promise(r=>setTimeout(r,250));
          const body=document.querySelector('#modal-body .resumo-body[data-sub]');
          const mks=body?[...body.querySelectorAll('mark.resumo-marca')].map(m=>m.textContent):null;
          revFecharTela();
          return mks;}"""%SUB)
        print('   na tela de revisão: %s'%r); assert r==['30 mL/kg']
        print('   OK\n')

        print('=== D) trecho repetido: marca so a ocorrencia escolhida ===')
        r=await page.evaluate("""()=>{
          const root=document.querySelector('#resumo-s1 .resumo-body[data-sub]');
          const {full}=marcaMapa(root);
          return (full.match(/reposicao/g)||[]).length;}""")
        print('   "reposicao" aparece %s vezes no resumo'%r); assert r>=3
        ok=await page.evaluate("""(alvo)=>{
          const root=document.querySelector('#resumo-s1 .resumo-body[data-sub]');
          const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null);
          let n,vistos=0;
          while((n=w.nextNode())){
            let de=-1;
            while((de=n.nodeValue.indexOf(alvo,de+1))>=0){
              vistos++;
              if(vistos===2){   // a SEGUNDA ocorrencia
                const r=document.createRange();
                r.setStart(n,de); r.setEnd(n,de+alvo.length);
                const sel=window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
                return true;
              }
            }
          }
          return false;}""",'reposicao')
        assert ok
        r=await page.evaluate("""()=>{marcaSalvarSelecao('%s');marcaAplicarTodas();
          const ms=simFindSub('%s').resumo.marcas;
          const root=document.querySelector('#resumo-s1 .resumo-body[data-sub]');
          const {full}=marcaMapa(root);
          const mk=[...root.querySelectorAll('mark.resumo-marca')].find(m=>m.textContent==='reposicao');
          // posicao real da marca no texto da tela
          const antes=full.indexOf('reposicao'), dela=ms[ms.length-1].n;
          return {marcas:ms,ocorrencia:dela,
                  quantasMarcadas:[...root.querySelectorAll('mark.resumo-marca')].filter(m=>m.textContent==='reposicao').length};}"""%(SUB,SUB))
        print('   guardou ocorrência nº %s · marcas na tela com esse texto: %s'
              %(r['ocorrencia'],r['quantasMarcadas']))
        assert r['ocorrencia']==1 and r['quantasMarcadas']==1
        print('   OK\n')

        print('=== E) clicar na marca tira a marcacao ===')
        r=await page.evaluate("""()=>{
          const mk=document.querySelector('#resumo-s1 mark.resumo-marca');
          const antes=simFindSub('%s').resumo.marcas.length;
          mk.click();
          return {antes,depois:simFindSub('%s').resumo.marcas.length,
                  naTela:document.querySelectorAll('#resumo-s1 mark.resumo-marca').length};}"""%(SUB,SUB))
        print('   marcas: %s → %s · na tela: %s'%(r['antes'],r['depois'],r['naTela']))
        assert r['depois']==r['antes']-1
        print('   OK\n')

        print('=== F) corrigir o resumo a mao: marca que sobreviveu continua ===')
        r=await page.evaluate("""()=>{
          const s=simFindSub('%s');
          s.resumo.marcas=[{t:'30 mL/kg',n:0},{t:'lactato',n:0}];
          // troca "lactato" por "clearance" — a marca dele tem que sumir, a outra fica
          s.resumo.texto=s.resumo.texto.replace('lactato','clearance');
          resumoRefreshPanel('%s');
          return {guardadas:s.resumo.marcas.length,
                  naTela:[...document.querySelectorAll('#resumo-s1 mark.resumo-marca')].map(m=>m.textContent)};}"""%(SUB,SUB))
        print('   guardadas: %s · desenhadas: %s'%(r['guardadas'],r['naTela']))
        assert r['guardadas']==2 and r['naTela']==['30 mL/kg']
        print('   OK\n')

        print('=== G) selecao curta demais nao vira marca ===')
        await page.evaluate(SELECIONA,'de')
        r=await page.evaluate("""()=>{const antes=simFindSub('%s').resumo.marcas.length;
          const ok=marcaSalvarSelecao('%s');
          return {ok,antes,depois:simFindSub('%s').resumo.marcas.length};}"""%((SUB,)*3))
        print('   salvou: %s · marcas: %s → %s'%(r['ok'],r['antes'],r['depois']))
        assert not r['ok'] and r['antes']==r['depois']
        print('   OK\n')

        print('=== H) o texto marcado nao vira HTML ===')
        r=await page.evaluate("""()=>{
          const s=simFindSub('%s');
          s.resumo.texto='CUIDADO:\\nO valor <img src=x onerror="window.__X=1"> nao pode executar.';
          s.resumo.marcas=[{t:'<img src=x onerror="window.__X=1">',n:0}];
          resumoRefreshPanel('%s');
          const root=document.querySelector('#resumo-s1 .resumo-body[data-sub]');
          return {img:!!root.querySelector('img'),x:window.__X||0,
                  marcado:(root.querySelector('mark.resumo-marca')||{}).textContent};}"""%(SUB,SUB))
        print('   virou <img>: %s · executou: %s'%(r['img'],r['x']))
        print('   marcado como texto: %r'%(r['marcado'] or '')[:40])
        assert not r['img'] and not r['x'] and r['marcado']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
