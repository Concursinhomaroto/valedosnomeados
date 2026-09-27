import asyncio, json, sys, io
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

FIX=json.load(io.open('qa_fixture.json',encoding='utf-8'))
LIVRE=("A Lei Estadual 5.247 de 1991 dispoe sobre o regime juridico dos servidores civis. "
       "O prazo de posse e de trinta dias contados da publicacao. O exercicio deve iniciar "
       "em trinta dias da posse. ")*40   # texto corrido, sem pergunta e resposta

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE'}))
        try:
            r=await page.evaluate("""([a,b,livre]) => ({
                arq1: fcExtrairPares(a).length,
                arq2: fcExtrairPares(b).length,
                juntos: fcExtrairPares(a+b).length,
                livre: fcExtrairPares(livre).length,
                vazio: fcExtrairPares('').length,
                curto: fcExtrairPares('Questão 1 oi Resposta: ok').length,
                amostra: fcExtrairPares(a)[44],
                ultima: fcExtrairPares(b)[fcExtrairPares(b).length-1]
            })""",[FIX['a'],FIX['b'],LIVRE])
            print('1) PDF com 70 perguntas ->', r['arq1'], 'pares')
            print('   PDF com 30 perguntas ->', r['arq2'], 'pares')
            print('   os dois juntos       ->', r['juntos'], 'pares')
            assert r['arq1']==70, f"esperava 70, veio {r['arq1']}"
            assert r['arq2']==30, f"esperava 30, veio {r['arq2']}"
            assert r['juntos']==100, f"esperava 100, veio {r['juntos']}"

            print('\n2) a Questão 45, que a regex antiga engolia:')
            print('   P:', r['amostra']['pergunta'][:88])
            print('   R:', r['amostra']['resposta'][:88])
            assert 'Rito Sumário' in r['amostra']['pergunta']
            assert 'Abandono' in r['amostra']['resposta']

            print('\n3) última do 2º arquivo:')
            print('   P:', r['ultima']['pergunta'][:80])
            assert len(r['ultima']['resposta'])>30

            print('\n4) texto corrido (sem P/R) ->', r['livre'], 'pares (tem que ser 0, cai pra IA)')
            print('   vazio ->', r['vazio'], '| 1 par só ->', r['curto'], '(abaixo do mínimo de 5)')
            assert r['livre']==0, 'reconheceu par onde não existe'
            assert r['vazio']==0

            # nenhuma resposta pode ter engolido a pergunta seguinte
            longas=await page.evaluate("""(a) => fcExtrairPares(a).filter(p=>/quest[aã]o\\s*\\d/i.test(p.resposta)).length""",FIX['a'])
            print('\n5) respostas que engoliram a pergunta seguinte:', longas, '(tem que ser 0)')
            assert longas==0

            assert not real_errors(errors), real_errors(errors)
            print('\nOK — 100 de 100 pares extraídos do próprio documento, sem IA')
        finally:
            await browser.close()
asyncio.run(main())
