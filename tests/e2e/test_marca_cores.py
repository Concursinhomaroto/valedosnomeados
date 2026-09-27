# Marca-texto: grifo cobrindo a linha inteira (era um degrade nos 45% de baixo, com
# cara de sublinhado) e quatro cores escolhidas na paleta do cabecalho.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

TEXTO=("CLASSIFICACAO:\nA NANDA International foca no julgamento clinico sobre as "
       "respostas humanas, a NOC cuida dos resultados e a NIC das intervencoes.\n\n"
       "Na pratica: o enfermeiro escolhe o diagnostico e depois a intervencao.")
SUB='s1'

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'d'}],
      'topics':{'k1':[{'id':'t1','name':'SAE','icon':'x','subtopics':[
          {'id':SUB,'name':'Diagnostico de enfermagem','priority':100,'studied':True,
           'studiedAt':'2026-01-01',
           'resumo':{'texto':TEXTO,'geradoEm':'2026-09-01T10:00:00.000Z','origem':'web'}}]}]}})

MONTA = """()=>{
  const s=simFindSub('%s');
  openResumo.add('%s');
  let h=document.getElementById('resumo-%s');
  if(!h){h=document.createElement('div');h.id='resumo-%s';document.body.appendChild(h);}
  resumoRefreshPanel('%s');
  return true;
}""" % ((SUB,)*5)

SELECIONA = """(alvo)=>{
  const root=document.querySelector('#resumo-s1 .resumo-body[data-sub]');
  const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null);
  let n;
  while((n=w.nextNode())){
    const i=n.nodeValue.indexOf(alvo);
    if(i>=0){const r=document.createRange();r.setStart(n,i);r.setEnd(n,i+alvo.length);
      const sel=window.getSelection();sel.removeAllRanges();sel.addRange(r);return true;}
  }
  return false;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(MONTA)

        print('=== A) o grifo cobre a linha, nao so o rodape dela ===')
        ok=await page.evaluate(SELECIONA,'NANDA International')
        assert ok
        r=await page.evaluate("""()=>{marcaSalvarSelecao('s1');marcaAplicarTodas();
          const mk=document.querySelector('#resumo-s1 mark.resumo-marca');
          const st=getComputedStyle(mk);
          const alturaTexto=parseFloat(getComputedStyle(mk.parentNode).fontSize);
          return {bg:st.backgroundImage,cor:st.backgroundColor,
                  padTop:st.paddingTop,padBot:st.paddingBottom,
                  altura:Math.round(mk.getBoundingClientRect().height),
                  fonte:Math.round(alturaTexto)};}""")
        print('   background-image: %s'%r['bg'])
        print('   cor de fundo: %s · padding: %s/%s'%(r['cor'],r['padTop'],r['padBot']))
        print('   altura do grifo: %spx (fonte de %spx)'%(r['altura'],r['fonte']))
        assert r['bg']=='none', 'nao pode mais ser degrade'
        assert r['altura']>=r['fonte'], 'o grifo tem que cobrir pelo menos a altura da fonte'
        print('   OK\n')

        print('=== B) a paleta esta no cabecalho, com 4 cores ===')
        r=await page.evaluate("""()=>{const ps=[...document.querySelectorAll('#resumo-s1 .marca-pen')];
          return {n:ps.length,cores:ps.map(p=>p.getAttribute('data-cor')),
                  ativa:ps.filter(p=>p.classList.contains('ativa')).map(p=>p.getAttribute('data-cor'))};}""")
        print('   %s canetas: %s · ativa: %s'%(r['n'],r['cores'],r['ativa']))
        assert r['n']==4 and r['cores']==['a','v','r','z'] and r['ativa']==['a']
        print('   OK\n')

        print('=== C) clicar numa cor com trecho selecionado marca NA HORA ===')
        ok=await page.evaluate(SELECIONA,'julgamento clinico')
        assert ok
        r=await page.evaluate("""()=>{
          const pen=document.querySelector('#resumo-s1 .marca-pen[data-cor="v"]');
          pen.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true}));
          const ms=simFindSub('s1').resumo.marcas;
          const mks=[...document.querySelectorAll('#resumo-s1 mark.resumo-marca')];
          return {marcas:ms,corAtual:marcaCor,
                  naTela:mks.map(m=>[m.textContent,m.getAttribute('data-cor')])};}""")
        print('   caneta atual: %s'%r['corAtual'])
        print('   guardado: %s'%r['marcas'])
        print('   na tela: %s'%r['naTela'])
        assert r['corAtual']=='v' and len(r['marcas'])==2
        assert r['marcas'][1]['c']=='v' and r['marcas'][0].get('c')=='a'
        assert sorted(x[1] for x in r['naTela'])==['a','v']
        print('   OK\n')

        print('=== D) cada cor pinta diferente ===')
        r=await page.evaluate("""()=>{
          const mks=[...document.querySelectorAll('#resumo-s1 mark.resumo-marca')];
          const o={};mks.forEach(m=>{o[m.getAttribute('data-cor')]=getComputedStyle(m).backgroundColor;});
          return o;}""")
        for k,v in r.items(): print('   %s -> %s'%(k,v))
        assert len(set(r.values()))==len(r)
        print('   OK\n')

        print('=== E) marca antiga, sem cor guardada, continua amarela ===')
        r=await page.evaluate("""()=>{
          const s=simFindSub('s1');
          s.resumo.marcas=[{t:'NOC',n:0}];      // formato antigo, sem c
          resumoRefreshPanel('s1');
          const mk=document.querySelector('#resumo-s1 mark.resumo-marca');
          return {cor:mk.getAttribute('data-cor'),texto:mk.textContent};}""")
        print('   %r -> cor %s'%(r['texto'],r['cor'])); assert r['cor']=='a'
        print('   OK\n')

        print('=== F) a cor escolhida sobrevive ao recarregar ===')
        r=await page.evaluate("()=>localStorage.getItem('vdn_marca_cor')")
        print('   gravado no aparelho: %r'%r); assert r=='v'
        await page.reload(); await page.wait_for_timeout(1200)
        r=await page.evaluate("()=>marcaCor")
        print('   depois de recarregar: %r'%r); assert r=='v'
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
