import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

KING='k1'; TOPIC='t1'; SUB='s1'; SUB2='s2'
def seed():
    return make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE',
      'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
      'topics':{KING:[{'id':TOPIC,'name':'Urgência e Emergência','subtopics':[
        {'id':SUB,'name':'Choque Séptico','priority':70,'studied':True},
        {'id':SUB2,'name':'Trauma','priority':70,'studied':True}]}]}})

def resp(cards):
    return json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps({'cards':cards})}]},
                                      'finishReason':'STOP'}]})

LOTE1=[{'pergunta':'Qual o prazo para iniciar o antibiótico na sepse?','resposta':'1 hora.'},
       {'pergunta':'Qual a meta de PAM no choque séptico?','resposta':'65 mmHg.'}]
# mesma coisa reescrita — e o que a IA faz de verdade entre uma geracao e outra
LOTE2=[{'pergunta':'QUAL O PRAZO PARA INICIAR O ANTIBIÓTICO NA SEPSE?','resposta':'Uma hora.'},
       {'pergunta':'Qual a meta de PAM, no choque séptico?','resposta':'65 mmHg.'},
       {'pergunta':'Qual o volume inicial de cristaloide?','resposta':'30 mL/kg.'}]
# duplicata DENTRO do proprio lote
LOTE3=[{'pergunta':'O que é lactato sérico?','resposta':'Marcador de hipoperfusão.'},
       {'pergunta':'O que é lactato sérico???','resposta':'Marcador de hipoperfusão.'}]

async def main():
    async with async_playwright() as p:
        atual=[LOTE1]
        async def gem(route,request):
            await route.fulfill(status=200,content_type='application/json',body=resp(atual[0]))
        async def tav(route,request):
            await route.fulfill(status=200,content_type='application/json',body='{"results":[]}')
        browser,page,errors=await setup_page(p, seed())
        try:
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
            await page.route('**api.tavily.com/search**', tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models?**',
                lambda r: asyncio.ensure_future(r.fulfill(status=200,content_type='application/json',body='{"models":[]}')))

            async def gerar(lote):
                atual[0]=lote
                await page.evaluate("(s) => generateFlashcardsSub(s)",SUB)
                await page.wait_for_timeout(2500)
                return await page.evaluate("""(s) => {
                  const cs=Object.values(db.flashcards||{}).filter(c=>c.subId===s);
                  return {n:cs.length, perguntas:cs.map(c=>c.pergunta)};}""",SUB)

            r1=await gerar(LOTE1)
            print('1) 1ª geração ->', r1['n'], 'cards')
            assert r1['n']==2

            r2=await gerar(LOTE2)
            print('2) 2ª geração (2 das 3 são as MESMAS reescritas) ->', r2['n'], 'cards no total')
            for q in r2['perguntas']: print('     -', q)
            assert r2['n']==3, f'esperava 3 (2 antigos + 1 novo), veio {r2["n"]} — duplicou'

            r3=await gerar(LOTE3)
            print('3) 3ª geração (lote com duplicata interna) ->', r3['n'], 'cards no total')
            assert r3['n']==4, f'esperava 4 (3 + 1), veio {r3["n"]} — duplicata dentro do lote passou'

            # outro miniboss do mesmo chefao NAO pode ser bloqueado
            atual[0]=LOTE1
            await page.evaluate("(s) => generateFlashcardsSub(s)",SUB2)
            await page.wait_for_timeout(2500)
            n2=await page.evaluate("(s) => Object.values(db.flashcards||{}).filter(c=>c.subId===s).length",SUB2)
            print('4) outro miniboss do mesmo chefão ->', n2, 'cards (não pode ser bloqueado)')
            assert n2==2, f'a trava vazou pro outro assunto ({n2} cards)'

            assert not real_errors(errors), real_errors(errors)
            print('\nOK — repetição descartada no mesmo assunto, dentro do lote, e sem afetar outros minibosses')
        finally:
            await browser.close()
asyncio.run(main())
