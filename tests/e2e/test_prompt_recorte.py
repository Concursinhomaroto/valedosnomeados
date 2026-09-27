# -*- coding: utf-8 -*-
# "Varie o angulo" fazia o modelo SORTEAR o que cobrar dentro do assunto, e prova
# sorteada nao parece com a da banca: a Cebraspe volta sempre nos mesmos pontos de
# cada assunto. O prompt agora manda levantar o que ela ja cobrou antes de escrever.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page
import test_colar_cotas as T

MARCAS=['O QUE COBRAR DENTRO DE CADA ASSUNTO',
        'levante o que a banca JÁ COBROU',
        'provas anteriores do próprio Cebraspe',
        'mais se repetem',
        'MODO de errar da banca',
        'Nunca copie item de prova anterior palavra por palavra',
        'não invente pegadinha exótica']

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,T.seed())
        await page.evaluate("()=>{showScreen('simgeral');return true;}")

        print('=== A) o bloco novo esta no prompt da prova colada ===')
        t=await page.evaluate("()=>simColarPromptTexto()")
        for m in MARCAS: assert m in t, m
        print('   as %s marcas do bloco: ok'%len(MARCAS))
        # e o "varie o angulo" solto virou subordinado
        assert 'variando DENTRO dos pontos que a banca mais cobra' in t
        assert 'Dentro de cada assunto, varie o ângulo: conceito' not in t
        print('   "varie o ângulo" deixou de ser regra solta e virou subordinada')
        print('   OK\n')

        print('=== B) os outros dois geradores de questao receberam igual ===')
        r=await page.evaluate("""()=>{
          const ce=promptRecorteCebraspe(true), mult=promptRecorteCebraspe(false);
          const fonte=generateQuestionsForSubject.toString()
                     +generateQuestionsForTopic.toString();
          return {itens:ce.includes('A MAIORIA dos itens'),
                  questoes:mult.includes('A MAIORIA das questões'),
                  noMiniboss:(generateQuestionsForSubject.toString().match(/promptRecorteCebraspe/g)||[]).length,
                  noChefao:(generateQuestionsForTopic.toString().match(/promptRecorteCebraspe/g)||[]).length};}""")
        print('   simulado por miniboss: %s uso · por chefão: %s uso'%(r['noMiniboss'],r['noChefao']))
        print('   o texto acompanha o formato (itens / questões): %s / %s'%(r['itens'],r['questoes']))
        assert r['noMiniboss']==1 and r['noChefao']==1
        assert r['itens'] and r['questoes']
        print('   OK\n')

        print('=== C) o exemplo de JSON parou de misturar numero de um com nome de outro ===')
        await page.evaluate(T.EDITAL,[20,10,20,70])
        r=await page.evaluate("""()=>{
          document.getElementById('sg-colar-qtd').value='120';
          const t=simColarPromptTexto();
          const m=t.match(/\\{"assunto":(\\d+),"assuntoNome":"([^"]+)"/);
          const primeiro=simColarLista[0].sub.name;
          return {num:+m[1],nome:m[2],primeiro};}""")
        print('   exemplo: "assunto":%s + "%s" · nº 1 da lista: %r'
              %(r['num'],r['nome'],r['primeiro']))
        assert r['num']==1 and r['nome']==r['primeiro']
        print('   OK\n')

        print('=== D) o conversor tambem, e sem lista ele volta pro exemplo fixo ===')
        c=await page.evaluate("()=>simColarPromptConverter()")
        assert '"assunto":1,"assuntoNome":"Concordância verbal"' in c, c[-400:]
        r=await page.evaluate("()=>{simColarLista=[];return simColarExemploJSON(true);}")
        print('   sem lista carregada: %s'%r)
        assert '"assunto":7' in r and 'Sondagem vesical' in r
        print('   OK\n')

        print('=== E) o conversor NAO ganhou o bloco (ele nao escreve questao) ===')
        assert 'O QUE COBRAR DENTRO DE CADA ASSUNTO' not in c
        assert 'NÃO elabora questão nova' in c
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
