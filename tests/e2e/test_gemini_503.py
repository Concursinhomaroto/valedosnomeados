import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

OK=json.dumps({'candidates':[{'content':{'parts':[{'text':'RESPOSTA BOA'}]},'finishReason':'STOP'}]})
ERR503=json.dumps({'error':{'code':503,'message':'The model is overloaded. Please try again later.'}})

async def main():
    async with async_playwright() as p:
        seed=make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE'})
        browser,page,errors=await setup_page(p,seed)
        try:
            estado={'n':0,'modo':'sempre503'}
            async def gem(route,request):
                estado['n']+=1
                if estado['modo']=='cura_na_terceira' and estado['n']>=3:
                    await route.fulfill(status=200,content_type='application/json',body=OK)
                else:
                    await route.fulfill(status=503,content_type='application/json',body=ERR503)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
            await page.route('**generativelanguage.googleapis.com/v1beta/models?**', lambda r: asyncio.ensure_future(
                r.fulfill(status=200,content_type='application/json',body='{"models":[]}')))

            print('=== 1) 503 nas duas primeiras, sucesso na terceira ===')
            estado.update(n=0,modo='cura_na_terceira')
            r=await page.evaluate("""async()=>{try{
                return {ok:true,txt:await callGeminiGenerate(db.geminiApiKey,'oi')};
              }catch(e){return {ok:false,msg:e.message};}}""")
            print('   chamadas feitas:',estado['n'],'| resultado:',r)
            assert r['ok'] and r['txt']=='RESPOSTA BOA', 'devia ter se recuperado sozinho'
            assert estado['n']==3, f"esperava 3 chamadas (2 falhas + 1 boa), foram {estado['n']}"
            print('   OK — tentou de novo o mesmo modelo e conseguiu')

            print('\n=== 2) 503 sempre: mensagem certa, tenta a reserva por último, sem varrer a lista de modelos ===')
            estado.update(n=0,modo='sempre503')
            r=await page.evaluate("""async()=>{try{
                await callGeminiGenerate(db.geminiApiKey,'oi'); return {ok:true};
              }catch(e){return {ok:false,msg:e.message};}}""")
            print('   chamadas feitas:',estado['n'])
            print('   mensagem:',r['msg'])
            assert not r['ok']
            assert 'sobrecarregada' in r['msg'], 'a mensagem tem que dizer que e a Google, nao a chave'
            assert 'chave' not in r['msg'].lower().replace('sua chave nem','') or 'não é problema da sua chave' in r['msg'], r['msg']
            # 3 modelos candidatos x 3 tentativas cada = 9, mais UMA tentativa (sem retry)
            # no modelo de reserva (Lite, pool separado dos Flash — o unico que ainda
            # responde quando os Flash estao todos lotados) = 10. NAO pode sair perguntando
            # a lista de modelos por cima de uma sobrecarga (isso so faz sentido em 404).
            assert estado['n']==10, f"esperava 10 (3 modelos x 3 tentativas + 1 na reserva), foram {estado['n']}"
            print('   OK — 3 modelos x 3 tentativas + 1 tentativa na reserva, sem varrer a lista de modelos por cima da sobrecarga')

            # O caso 2 varreu TUDO e caiu em 503 — isso liga o disjuntor de verdade
            # (geminiMarcarSobrecarga, 3 min), que é o comportamento certo pra sobrecarga
            # real. Mas os próximos casos testam OUTRO diagnóstico (chave inválida, cota),
            # que não tem nada a ver com essa sobrecarga específica — sem limpar aqui, o
            # disjuntor do caso 2 responderia por eles, e os dois nunca chegariam a testar
            # o que dizem testar.
            await page.evaluate("()=>geminiLimparSobrecarga()")

            print('\n=== 3) erro de verdade (chave invalida) continua dizendo pra conferir a chave ===')
            await page.unroute('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**')
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**',
                lambda r: asyncio.ensure_future(r.fulfill(status=400,content_type='application/json',
                    body=json.dumps({'error':{'code':400,'message':'API key not valid'}}))))
            r=await page.evaluate("""async()=>{try{
                await callGeminiGenerate(db.geminiApiKey,'oi'); return {ok:true};
              }catch(e){return {ok:false,msg:e.message};}}""")
            print('   mensagem:',r['msg'][:120])
            assert 'chave' in r['msg'] and 'sobrecarregada' not in r['msg']
            print('   OK — diagnóstico continua certo pro erro que É da chave')


            print('\n=== 4) 429 (cota da chave): UMA requisicao, sem repetir ===')
            await page.unroute('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**')
            n429={'n':0}; modelos429=[]
            async def gem429(route,request):
                n429['n']+=1; modelos429.append(request.url.split('/models/')[1].split(':')[0])
                await route.fulfill(status=429,content_type='application/json',body=json.dumps(
                  {'error':{'code':429,'message':'Quota exceeded for quota metric requests',
                            'details':[{'@type':'type.googleapis.com/google.rpc.RetryInfo','retryDelay':'31s'}]}}))
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem429)
            r=await page.evaluate("""async()=>{try{
                await callGeminiGenerate(db.geminiApiKey,'oi'); return {ok:true};
              }catch(e){return {ok:false,msg:e.message};}}""")
            print('   requisicoes disparadas:',n429['n'],'(1 por modelo, sem repetir o mesmo)')
            print('   mensagem:',r['msg'][:150])
            # Limite no Gemini e POR MODELO: um 429 na 3.8 nao diz nada sobre a 3.6.
            # Entao tenta cada modelo UMA vez — o que nao pode e repetir o mesmo modelo.
            assert n429['n']==len(set(modelos429)), f"repetiu modelo: {modelos429}"
            # 4 candidatos + a reserva de cota (flash-lite), que so entra quando alguem
            # recusou por 429 — e o unico caminho que ainda funciona quando a cota
            # DIARIA dos Flash acabou.
            assert n429['n']<=4, f"esperava no maximo 4 (3 modelos + reserva), foram {n429['n']}"
            assert modelos429[-1]=='gemini-flash-lite-latest', f"a reserva nao foi tentada: {modelos429}"
            assert 'limite de uso' in r['msg'] and '31s' in r['msg']
            assert 'sobrecarregada' not in r['msg'], 'nao pode dizer que e sobrecarga: e cota'
            print('   modelos tentados:',[m.replace('gemini-','') for m in modelos429])
            print('   OK — uma tentativa por modelo, causa certa e tempo do Google na mensagem')

            assert not real_errors(errors), real_errors(errors)
            print('\nOK')
        finally:
            await browser.close()
asyncio.run(main())
