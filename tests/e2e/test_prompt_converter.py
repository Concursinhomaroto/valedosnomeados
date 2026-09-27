# -*- coding: utf-8 -*-
# Converter prova pronta e trabalho diferente de elaborar: o texto da banca E o produto,
# e gabarito deduzido e pior do que nao importar nada (entra no Banco de Erros e vira
# flashcard errado). O prompt do conversor tem que carregar a mesma lista fechada.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'},
                  {'id':'k2','name':'Legislacao SUS','icon':'⚖️','color':'#f59e0b'},
                  {'id':'k3','name':'Reino pausado','icon':'💤','color':'#888'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
                    {'id':'s1','name':'Choque septico','priority':70,'studied':True},
                    {'id':'s2','name':'PCR','priority':70,'studied':True},
                    {'id':'s3','name':'Nao estudado','priority':70,'studied':False}]}],
                'k2':[{'id':'t2','name':'Lei 8080','icon':'📜','subtopics':[
                    {'id':'s4','name':'Principios do SUS','priority':70,'studied':True}]}],
                'k3':[{'id':'t3','name':'Qualquer','icon':'💤','subtopics':[
                    {'id':'s5','name':'Assunto do reino pausado','priority':70,'studied':True}]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        # reino pausado: mesmo sinal que tira ele da fila de revisao
        await page.evaluate("""()=>{db.revReinosFora=db.revReinosFora||{};db.revReinosFora['k3']=true;
          showScreen('simgeral');return true;}""")

        print('=== A) o prompt existe e sai com a lista fechada ===')
        txt=await page.evaluate("()=>simColarPromptConverter()")
        print('   %s caracteres'%len(txt))
        assert '1. Choque septico (Enfermagem / Urgencia)' in txt, txt[:400]
        assert 'Principios do SUS' in txt
        assert 'Nao estudado' not in txt, 'assunto nao estudado nao pode entrar na lista'
        assert 'Assunto do reino pausado' not in txt, 'reino pausado tem que ficar de fora'
        print('   entrou: Choque septico, PCR, Principios do SUS')
        print('   ficou de fora: assunto não estudado e o reino pausado')
        print('   OK\n')

        print('=== B) as duas regras sem excecao estao la ===')
        for frase in ['NÃO INVENTE GABARITO','NÃO REESCREVA O ENUNCIADO',
                      'ele NÃO entra no JSON','palavra por palavra']:
            assert frase in txt, frase
        print('   não inventar gabarito · não reescrever o enunciado · item sem gabarito fica fora')
        # e nao pode pedir pra ELABORAR
        assert 'NÃO elabora questão nova' in txt
        print('   e diz explicitamente que não é pra elaborar questão nova')
        print('   OK\n')

        print('=== C) casos reais do caderno Cebraspe ===')
        for frase in ['numeração dos itens CONTINUA','anulado','"assunto": 0','textoApoio']:
            assert frase in txt, frase
        print('   PDF partido em gerais/específicos · anulado fora · assunto 0 pra resolver na mão')
        print('   OK\n')

        print('=== D) o formato JSON dos dois tipos de item ===')
        assert '"afirmacao"' in txt and '"gabarito"' in txt
        assert '"alternativas"' in txt and '"correta"' in txt
        assert 'CONTINUA — faltam N itens' in txt
        print('   certo/errado e múltipla escolha no mesmo array · regra do corte')
        print('   OK\n')

        print('=== E) o botao esta na tela e copia ===')
        r=await page.evaluate("""()=>{
          let copiado=null;
          navigator.clipboard.writeText=(t)=>{copiado=t;return Promise.resolve();};
          const b=document.querySelector('button[onclick*="simColarCopiarConverter"]');
          if(!b)return {botao:null};
          b.click();
          return {botao:b.innerText.trim(),copiou:!!copiado&&copiado.length>500,
                  lista:(copiado||'').includes('Choque septico')};}""")
        print('   botão: %r · copiou: %s · com a lista: %s'%(r['botao'],r.get('copiou'),r.get('lista')))
        assert r['botao'] and 'converter' in r['botao'].lower()
        assert r['copiou'] and r['lista']
        print('   OK\n')

        print('=== F) o gerador continua inteiro depois da refatoracao ===')
        g=await page.evaluate("""()=>{document.getElementById('sg-colar-qtd').value='120';
          return simColarPromptTexto();}""")
        for frase in ['Gere EXATAMENTE 120','PESQUISE NA INTERNET','1. Choque septico',
                      'ALGARISMO','competência privativa','Enfermagem: cerca de']:
            assert frase in g, frase
        assert 'Assunto do reino pausado' not in g
        print('   %s caracteres · lista, pesquisa, algarismo, privativa e distribuição por reino: ok'%len(g))
        print('   OK\n')

        print('=== G) simColarLista fica apontando pra mesma lista nos dois ===')
        r=await page.evaluate("""()=>{
          simColarPromptConverter(); const a=simColarLista.map(c=>c.sub.id);
          simColarPromptTexto();     const b=simColarLista.map(c=>c.sub.id);
          return {a,b};}""")
        print('   conversor: %s · gerador: %s'%(r['a'],r['b']))
        assert r['a']==r['b']==['s1','s2','s4']
        print('   OK\n')

        print('=== H) um JSON no formato do conversor entra no lote ===')
        r=await page.evaluate("""()=>{
          simColarPromptConverter();
          document.getElementById('sg-colar-txt').value=JSON.stringify([
            {assunto:1,assuntoNome:'Choque septico',textoApoio:'Caso clinico X.',
             afirmacao:'A reposicao inicial e de 30 mL/kg.',gabarito:'C',explicacao:'Sim.'},
            {assunto:2,assuntoNome:'PCR',textoApoio:'',
             questao:'Qual a relacao compressao/ventilacao no adulto?',
             alternativas:[{letra:'A',texto:'15:2'},{letra:'B',texto:'30:2'},
                           {letra:'C',texto:'5:1'},{letra:'D',texto:'10:2'},{letra:'E',texto:'20:2'}],
             correta:'B',explicacao:'30:2.'},
            {assunto:0,assuntoNome:'Coisa fora da lista',afirmacao:'Bla.',gabarito:'E',explicacao:'Nao.'}
          ]);
          simColarAdicionar();
          const {grupos}=simColarMapa();
          return {n:simColarLote.length,
                  fmts:simColarLote.map(q=>q.formato),
                  apoio:simColarLote[0].textoApoio,
                  resolvidos:grupos.filter(g=>g.alvo).length,
                  pendentes:grupos.filter(g=>!g.alvo).reduce((a,g)=>a+g.n,0)};}""")
        print('   %s itens · formatos: %s'%(r['n'],r['fmts']))
        print('   grupos resolvidos sozinhos: %s · itens sem assunto: %s'%(r['resolvidos'],r['pendentes']))
        assert r['n']==3
        assert r['fmts']==['certoerrado','multipla','certoerrado']
        assert r['apoio']=='Caso clinico X.'
        assert r['resolvidos']==2 and r['pendentes']==1   # o assunto 0 fica pra mao
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
