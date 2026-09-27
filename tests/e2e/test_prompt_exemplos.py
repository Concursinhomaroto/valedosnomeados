import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, make_seed({'studyNickname':'Leo'}))
        try:
            r=await page.evaluate("""() => ({
              resumoWeb: resumoPromptWeb('MINIBOSS: Choque Séptico',''),
              resumoArquivo: resumoPromptUnico('MINIBOSS: Choque Séptico','texto qualquer'),
              resumoConsolida: resumoPromptConsolida('MINIBOSS: Choque Séptico',['parte 1','parte 2']),
              resumoParcial: resumoPromptParcial('ctx','txt',1,3),
              fluxoWeb: fluxoPromptWeb('MINIBOSS: Choque Séptico'),
              fluxoTexto: fluxoPrompt('texto qualquer'),
              fluxoComResumo: fluxoPromptWebComResumo('ctx','resumo')
            })""")
            for nome in ['resumoWeb','resumoArquivo','resumoConsolida']:
                t=r[nome]
                print(f'{nome}: pede "Na prática:" ->', 'Na prática:' in t,
                      '| proíbe inventar dado no exemplo ->', 'não pode introduzir' in t or 'NÃO pode introduzir' in t)
                assert 'Na prática:' in t, f'{nome} não pede exemplo'
                assert ('não pode introduzir' in t or 'NÃO pode introduzir' in t), \
                    f'{nome} não trava a invenção de dado dentro do exemplo'
            # a passada parcial NAO deve pedir exemplo (e so extracao; o exemplo entra na consolidacao)
            print('resumoParcial (extração) sem pedir exemplo ->', 'Na prática:' not in r['resumoParcial'])
            assert 'Na prática:' not in r['resumoParcial']

            for nome in ['fluxoWeb','fluxoTexto','fluxoComResumo']:
                t=r[nome]
                tem='(ex.: ...)' in t
                limite='~20 com o exemplo' in t
                trava='não pode introduzir número' in t
                print(f'{nome}: pede "(ex.: ...)" ->', tem, '| limite ajustado ->', limite, '| trava de dado ->', trava)
                assert tem and limite and trava, f'{nome} incompleto'

            # o pedido de exemplo nao pode ter quebrado as regras que ja existiam
            assert 'sem markdown' in r['resumoWeb']
            assert 'Responda APENAS com o JSON' in r['fluxoWeb']
            assert not real_errors(errors), real_errors(errors)
            print('\nOK — os 3 prompts de resumo e os 3 de fluxograma pedem exemplo, com trava contra dado inventado')
        finally:
            await browser.close()
asyncio.run(main())
