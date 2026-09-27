# -*- coding: utf-8 -*-
# A lista fixa de 20/30/40/60 era chute meu. Com 245 questoes no acervo, prova de 100 e
# o tamanho normal — entao o numero e digitado e fica lembrado.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page
import test_montar as T
from test_banco_provas import LOTE

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,T.seed())
        await page.evaluate("()=>{showScreen('provas');return true;}")

        print('=== A) monta um acervo grande (3 provas de 40) ===')
        r=await page.evaluate("""async(x)=>{
          for(let k=0;k<3;k++){
            (%s)(40);
            simColarIniciar(false);
            simGeralActive.questoes.forEach((q,i)=>{
              q.userAnswer=(i%%3===0)?(q.correta==='C'?'E':'C'):q.correta;});
            simGeralActive.tempoGastoSec=60;
            simGeralCorrigir();
            await new Promise(r=>setTimeout(r,250));
            simGeralReset();
          }
          showScreen('provas');
          return {acervo:montarAcervo().length,provas:db.provas.length};}"""%LOTE,0)
        print('   acervo: %s questões · %s provas'%(r['acervo'],r['provas']))
        assert r['acervo']>=40
        print('   (o lote é o mesmo, então a dedup mantém 40 únicas)')
        print('   OK\n')

        print('=== B) o campo e digitavel e ja nasce em 100 ===')
        r=await page.evaluate("""()=>{
          const el=document.getElementById('montar-qtd');
          return {tag:el.tagName,tipo:el.type,valor:el.value,
                  min:el.min,max:el.max,lembrado:montarQtdLembrada()};}""")
        print('   <%s type=%s> valor %s (min %s, max %s)'
              %(r['tag'],r['tipo'],r['valor'],r['min'],r['max']))
        assert r['tag']=='INPUT' and r['tipo']=='number' and r['valor']=='100'
        print('   OK\n')

        print('=== C) digitar 100 e recarregar mantem 100 ===')
        r=await page.evaluate("""()=>{
          const el=document.getElementById('montar-qtd');
          el.value='100'; montarQtdGravar(el);
          renderSimGeralScreen();
          return {depois:document.getElementById('montar-qtd').value,
                  guardado:localStorage.getItem(MONTAR_QTD_KEY)};}""")
        print('   depois do redesenho: %s · no armazenamento: %s'%(r['depois'],r['guardado']))
        assert r['depois']=='100' and r['guardado']=='100'
        print('   OK\n')

        print('=== D) numero absurdo e cortado, nao aceito ===')
        r=await page.evaluate("""()=>{
          const el=document.getElementById('montar-qtd');
          el.value='9999'; montarQtdGravar(el);
          const alto=el.value;
          el.value='0'; montarQtdGravar(el);
          const baixo=el.value;
          el.value='100'; montarQtdGravar(el);
          return {alto,baixo,teto:MONTAR_QTD_MAX};}""")
        print('   9999 -> %s (teto %s) · 0 -> %s'%(r['alto'],r['teto'],r['baixo']))
        assert r['alto']==str(r['teto']) and r['baixo']=='1'
        print('   OK\n')

        print('=== E) pedir mais do que existe avisa, e monta com o que ha ===')
        r=await page.evaluate("""()=>{
          document.getElementById('montar-modo').value='errei';
          const el=document.getElementById('montar-qtd');
          el.value='100'; montarQtdGravar(el);
          const aviso=document.getElementById('banco-filtro-conta').textContent;
          const pool=montarPool('errei').length;
          montarAgora();
          return {aviso,pool,montou:db.provas[0].questoes.length};}""")
        print('   %r'%r['aviso'])
        print('   pool: %s · montou: %s'%(r['pool'],r['montou']))
        assert 'tudo que há' in r['aviso'] and r['montou']==r['pool']
        print('   OK\n')

        print('=== F) pedindo menos, sorteia a quantidade pedida ===')
        r=await page.evaluate("""()=>{
          showScreen('provas');
          document.getElementById('montar-modo').value='errei';
          const el=document.getElementById('montar-qtd');
          el.value='5'; montarQtdGravar(el);
          const aviso=document.getElementById('banco-filtro-conta').textContent;
          montarAgora();
          const el2=document.getElementById('montar-qtd');
          return {aviso,montou:db.provas[0].questoes.length,
                  aindaLembra:el2?el2.value:null};}""")
        print('   %r'%r['aviso'])
        print('   montou: %s itens · o campo lembra: %s'%(r['montou'],r['aindaLembra']))
        assert r['montou']==5 and 'tudo que há' not in r['aviso'] and r['aindaLembra']=='5'
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
