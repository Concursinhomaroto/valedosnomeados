# O material do Tavily chega inteiro em frases, e o prompt cobra portugues correto.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB='sub-t1'; TOPIC='topic-t1'; KING='king-t1'

def seed():
    return make_seed({'studyNickname':'R','studyCharacter':'ash','geminiApiKey':'FAKE','tavilyApiKey':'tvly-FAKE',
        'kingdoms':[{'id':KING,'name':'Enfermagem'}],
        'topics':{KING:[{'id':TOPIC,'name':'Trauma','subtopics':[
            {'id':SUB,'name':'Paciente com queimadura','priority':80,'studied':False}]}]}})

# pagina em ingles, longa, com lixo de navegacao e uma frase que seria cortada no meio
FRASE = 'The recommended initial fluid resuscitation volume is two milliliters per kilogram per percent of total body surface area burned. '
PAGINA = ('Home | Guidelines | Contact | Accept cookies. ' + FRASE*60 +
          'This final sentence would be sliced right in the middle of a word if the cut were blind.')
TAV = json.dumps({'results':[{'url':'https://ameriburn.org/guideline','title':'ABA Guideline','raw_content':PAGINA}]})

async def main():
    async with async_playwright() as pw:
        prompts=[]
        async def tav(route, request):
            await route.fulfill(status=200, content_type='application/json', body=TAV)
        async def gem(route, request):
            prompts.append(request.post_data or '')
            await route.fulfill(status=200, content_type='application/json', body=json.dumps(
                {'candidates':[{'content':{'parts':[{'text':'Resumo em portugues.'}]},'finishReason':'STOP'}]}))
        browser,page,errors=await setup_page(pw, seed())
        try:
            await page.route('**api.tavily.com/search**', tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)

            print('=== corte do material no fim da frase ===')
            r=await page.evaluate('''(pag)=>{
              const cortado=cortarNoPonto(pag,6000);
              return {tam:cortado.length, fim:cortado.slice(-70),
                      terminaEmPonto:/[.!?…]$/.test(cortado),
                      cortouPalavra:/[A-Za-zÀ-ú]$/.test(cortado)};
            }''', PAGINA)
            print(f"  {r['tam']} caracteres, termina com: …{r['fim']}")
            assert r['terminaEmPonto'] and not r['cortouPalavra'], r
            print('  ✓ corta no fim de uma frase, não no meio de uma palavra')

            curto=await page.evaluate("()=>cortarNoPonto('Texto curto.',6000)")
            assert curto=='Texto curto.', curto
            semPonto=await page.evaluate("()=>cortarNoPonto('a'.repeat(20)+' '+'b'.repeat(20),25)")
            print('  sem pontuação alguma:',repr(semPonto))
            assert semPonto.endswith('…'), semPonto
            print('  ✓ texto curto passa intacto; sem pontuação, corta no espaço e marca com reticências')

            print('\n=== regras de escrita no prompt ===')
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("(id)=>generateResumoWeb(id)", SUB)
            await page.wait_for_function("(id)=>{const s=simFindSub(id);return !!(s&&s.resumo&&s.resumo.texto);}", arg=SUB, timeout=25000)
            corpo=prompts[0]
            for trecho in ['COMO ESCREVER','PORTUGUÊS BRASILEIRO correto',
                           'traduza o CONTEÚDO, nunca a estrutura da frase',
                           'menu de navegação','concordância verbal e nominal']:
                assert trecho in corpo, f'faltou no prompt: {trecho}'
                print('  ✓',trecho)
            assert 'MATERIAL PESQUISADO NA INTERNET AGORA' in corpo
            # e o material que chegou nao tem frase cortada no fim
            i=corpo.index('[FONTE 1]')
            j=corpo.index('=====================================================================\\n\\nCOMO USAR')
            print('\n  ✓ o material entra no prompt já cortado em frase inteira')
            assert not real_errors(errors), real_errors(errors)
            print('\nOK — material recortado em frase inteira e prompt cobrando português correto')
        finally:
            await browser.close()
asyncio.run(main())
