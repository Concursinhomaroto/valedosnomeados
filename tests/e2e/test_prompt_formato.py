# -*- coding: utf-8 -*-
# O simulado que o usuario trouxe tinha 119 itens e ZERO textoApoio: 119 proposicoes
# gerais em sequencia, nenhuma situacao. O prompt nunca pediu situacao — o bloco de
# texto de apoio era condicional ("se um grupo depender"), e o modelo sempre respondia
# que nenhum dependia.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page
import test_colar_cotas as T

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,T.seed())
        await page.evaluate("()=>{showScreen('simgeral');return true;}")
        t=await page.evaluate("()=>{document.getElementById('sg-colar-qtd').value='120';return simColarPromptTexto();}")

        print('=== A) o prompt agora exige situacao ===')
        for m in ['FORMATO DO ITEM — situação antes de definição',
                  'Pelo menos 40%','SITUAÇÃO HIPOTÉTICA BREVE',
                  'não só para os clínicos','2 a 4 itens diferentes sobre ela',
                  'não passa de 1 em cada 3']:
            assert m in t, m
        print('   cota de 40% situados · situação no textoApoio · 2 a 4 itens por bloco')
        print('   definição pura limitada a 1 em cada 3')
        print('   OK\n')

        print('=== B) o texto de apoio deixou de ser condicional ===')
        assert 'Se um grupo de itens depender' not in t
        assert 'sem NENHUM "textoApoio" preenchido está errada de formato' in t
        assert 'Uma prova de 120 itens sem NENHUM' in t
        print('   o prompt diz explicitamente que prova sem textoApoio está errada')
        print('   OK\n')

        print('=== C) a escada de dificuldade esta la, com os quatro degraus ===')
        for m in ['NÍVEL DE DIFICULDADE','no máximo 20% — LEMBRAR',
                  'pelo menos 40% — APLICAR','pelo menos 30% — QUASE-CERTO',
                  'pelo menos 10% — VERDADEIRO QUE PARECE FALSO']:
            assert m in t, m
        print('   lembrar ≤20% · aplicar ≥40% · quase-certo ≥30% · verdadeiro-que-parece-falso ≥10%')
        assert 'entre 45% e 55% de CERTO' in t
        assert 'trocar por 20 é difícil' in t
        assert 'explicação com número errado ensina o erro' in t
        print('   equilíbrio do gabarito, erro plausível e explicação conferida: ok')
        print('   OK\n')

        print('=== D) legislacao tambem tem que ser cobrada por caso ===')
        assert 'Em legislação, a versão difícil não é citar o artigo' in t
        assert 'Nada de par mecânico' in t
        print('   e o par mecânico C+E sobre o mesmo assunto foi proibido')
        print('   OK\n')

        print('=== E) multipla escolha: o texto acompanha o formato ===')
        m=await page.evaluate("""()=>{document.getElementById('sg-colar-fmt').value='multipla';
          return simColarPromptTexto();}""")
        assert 'FORMATO DO ENUNCIADO' in m and 'das questões' in m
        assert 'entre 45% e 55% de CERTO' not in m   # so faz sentido no C/E
        assert 'a alternativa vizinha' in m
        print('   sem a regra de gabarito C/E, que ali não faz sentido')
        print('   OK\n')

        print('=== F) os simulados internos usam a versao sem textoApoio ===')
        r=await page.evaluate("""()=>{
          const comApoio=promptFormatoCebraspe(true,true), sem=promptFormatoCebraspe(true,false);
          return {apoioCita:comApoio.includes('"textoApoio"'),
                  semCita:sem.includes('"textoApoio"'),
                  semAbre:sem.includes('A situação abre o próprio item'),
                  noMiniboss:(generateQuestionsForSubject.toString().match(/promptFormatoCebraspe/g)||[]).length,
                  noChefao:(generateQuestionsForTopic.toString().match(/promptFormatoCebraspe/g)||[]).length};}""")
        print('   miniboss: %s uso · chefão: %s uso'%(r['noMiniboss'],r['noChefao']))
        print('   versão com textoApoio cita o campo: %s · versão sem: %s'
              %(r['apoioCita'],r['semCita']))
        assert r['noMiniboss']==1 and r['noChefao']==1
        assert r['apoioCita'] and not r['semCita'] and r['semAbre']
        print('   OK\n')

        print('=== G) nada do que ja existia se perdeu ===')
        await page.evaluate(T.EDITAL,[20,10,20,70])   # cotas so existem com edital em foco
        t2=await page.evaluate("""()=>{document.getElementById('sg-colar-fmt').value='certoerrado';
          document.getElementById('sg-colar-qtd').value='120';
          return simColarPromptTexto();}""")
        for m in ['O QUE COBRAR DENTRO DE CADA ASSUNTO','A COTA DE CADA BLOCO É OBRIGATÓRIA',
                  'Conferência: 20 + 10 + 20 + 70 = 120','ALGARISMO','competência privativa',
                  'CONTINUA — faltam N itens','SESAU/AL 2026']:
            assert m in t2, m
        print('   recorte, cotas do edital, algarismo, privativa e regra de corte: ok')
        print('   tamanho do prompt: %s caracteres'%len(t2))
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
