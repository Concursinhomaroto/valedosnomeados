# -*- coding: utf-8 -*-
# Com centenas de assuntos cadastrados, os que nenhuma disciplina do edital reivindica
# inflavam a lista fechada e enchiam o prompt de coisa que a prova nao cobra. Agora
# ficam de fora por padrao, e entrar e escolha explicita.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page
import test_colar_cotas as T

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,T.seed())
        await page.evaluate("()=>{showScreen('provas');return true;}")
        await page.evaluate(T.EDITAL,[20,10,20,70])
        # dois assuntos estudados que nenhuma disciplina reivindica
        await page.evaluate("""()=>{
          db.topics['k1'][0].subtopics.push(
            {id:'s90',name:'Assunto avulso A',priority:70,studied:true},
            {id:'s91',name:'Assunto avulso B',priority:70,studied:true});
          document.getElementById('sg-colar-qtd').value='120';
          renderSimGeralScreen();return true;}""")

        print('=== A) por padrao eles ficam FORA da lista fechada ===')
        r=await page.evaluate("""()=>{
          const t=simColarPromptTexto();
          return {incluiFora:colarIncluiFora(),
                  temBloco:/FORA DOS BLOCOS/.test(t),
                  temNome:/Assunto avulso/.test(t),
                  n:simColarLista.length,
                  nomes:simColarLista.map(c=>c.sub.name)};}""")
        print('   preferência "incluir fora": %s'%r['incluiFora'])
        print('   lista fechada: %s assuntos · %s'%(r['n'],r['nomes']))
        assert not r['incluiFora'] and not r['temBloco'] and not r['temNome']
        assert 'Assunto avulso A' not in r['nomes']
        print('   OK\n')

        print('=== B) a tela diz quantos ficaram de fora ===')
        r=await page.evaluate("""()=>{
          renderSimGeralScreen();
          const cx=document.querySelector('.sg-fora');
          const prev=simColarPreviaCotas(120);
          return {texto:cx?cx.innerText.replace(/\\n/g,' ').trim():null,
                  marcado:cx?cx.querySelector('input').checked:null,
                  fora:prev.fora,dentro:prev.dentro};}""")
        print('   %s fora · %s dentro de alguma disciplina'%(r['fora'],r['dentro']))
        print('   %r'%(r['texto'] or '')[:120])
        assert r['fora']==2 and r['dentro']==8
        assert r['marcado'] is False and '2 assunto(s)' in r['texto']
        print('   OK\n')

        print('=== C) ligando o interruptor, eles voltam pro fim da lista ===')
        r=await page.evaluate("""()=>{
          const cx=document.querySelector('.sg-fora input');
          cx.checked=true; colarAlternarFora(cx);
          const t=simColarPromptTexto();
          return {pref:colarIncluiFora(),temBloco:/FORA DOS BLOCOS/.test(t),
                  n:simColarLista.length,
                  ultimos:simColarLista.slice(-2).map(c=>c.sub.name)};}""")
        print('   lista: %s assuntos · últimos: %s'%(r['n'],r['ultimos']))
        assert r['pref'] and r['temBloco'] and r['n']==10
        assert r['ultimos']==['Assunto avulso A','Assunto avulso B']
        print('   OK\n')

        print('=== D) a preferencia sobrevive ao recarregar a tela ===')
        r=await page.evaluate("""()=>{renderSimGeralScreen();
          return {marcado:document.querySelector('.sg-fora input').checked};}""")
        assert r['marcado']
        await page.evaluate("()=>{const c=document.querySelector('.sg-fora input');c.checked=false;colarAlternarFora(c);return true;}")
        r=await page.evaluate("()=>({pref:colarIncluiFora(),n:(simColarPromptTexto(),simColarLista.length)})")
        print('   desligando de novo: %s assuntos'%r['n'])
        assert not r['pref'] and r['n']==8
        print('   OK\n')

        print('=== E) as cotas nao mudam, porque elas ja eram so do edital ===')
        r=await page.evaluate("""()=>{
          const t=simColarPromptTexto();
          const m=t.match(/Conferência: (.+?) = (\\d+)/);
          return {conta:m[1],soma:+m[2]};}""")
        print('   %s = %s'%(r['conta'],r['soma']))
        assert r['soma']==120
        print('   OK\n')

        print('=== F) sem edital em foco nada muda (nao ha bloco pra ficar fora) ===')
        r=await page.evaluate("""()=>{db.editalFoco=null;renderSimGeralScreen();
          const t=simColarPromptTexto();
          return {n:simColarLista.length,caixa:!!document.querySelector('.sg-fora'),
                  temAvulso:/Assunto avulso/.test(t)};}""")
        print('   %s assuntos na lista · caixa de opção: %s'%(r['n'],r['caixa']))
        assert r['n']==10 and not r['caixa'] and r['temAvulso']
        print('   todos entram, como antes')
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
