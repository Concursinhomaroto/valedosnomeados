# O simulado do miniboss ia so ate 20 questoes. Subindo pra 50 aparece uma armadilha:
# a resposta e UM JSON, e se ela e cortada pelo teto de saida o parse falha inteiro e se
# perdem TODAS as questoes daquela chamada. Pedir 50 de uma vez voltava zero — e as
# tentativas pediam 50 de novo, queimando o teto diario pra terminar sem nada.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
seed=make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE',
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'🏥'}],
  'topics':{'k1':[{'id':'t1','name':'Urgencia','subtopics':[
    {'id':'s1','name':'Choque','priority':70,'studied':True,'studiedAt':'2026-01-01'}]}]}})

ALTS=[{'letra':L,'texto':'Alternativa '+L} for L in 'ABCD']
def questoes(n,off=0):
    return [{'questao':'Pergunta numero %d sobre choque?'%(i+off),
             'alternativas':[dict(a) for a in ALTS],'correta':'A',
             'explicacao':'Explicacao da questao %d.'%(i+off)} for i in range(n)]

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        chamadas=[]
        async def g(route,request):
            body=json.loads(request.post_data or '{}')
            txt=body['contents'][0]['parts'][0]['text']
            teto=(body.get('generationConfig') or {}).get('maxOutputTokens')
            import re as _re
            m=_re.search(r'(\d+)\s+quest', txt)
            chamadas.append({'teto':teto,'pediu':int(m.group(1)) if m else None})
            n=chamadas[-1]['pediu'] or 10
            off=sum(c['pediu'] or 0 for c in chamadas[:-1])
            await route.fulfill(status=200,content_type='application/json',
              body=json.dumps({'candidates':[{'content':{'parts':[
                {'text':json.dumps(questoes(n,off))}]},'finishReason':'STOP'}]}))
        await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', g)
        await page.route('**api.tavily.com/**', lambda r: asyncio.ensure_future(
          r.fulfill(status=200,content_type='application/json',body=json.dumps({'results':[]}))))

        print('=== A) o seletor do miniboss vai ate 50 ===')
        # o painel do simulado vive dentro do miniboss: monta ele num container solto,
        # que e o que generateSimulado le pra saber a quantidade
        r=await page.evaluate("""()=>{
          const d=document.createElement('div');
          d.innerHTML=simPanelHTML(simFindSub('s1'));
          document.body.appendChild(d);
          const sel=document.getElementById('sim-qtd-s1');
          return [].map.call(sel.options,o=>o.value);
        }""")
        print('   opcoes: %s'%r)
        assert r==['5','10','15','20','30','40','50'], r
        print('   OK\n')

        print('=== B) 50 questoes saem em lotes, nao numa resposta so ===')
        chamadas.clear()
        r2=await page.evaluate("""async()=>{
          document.getElementById('sim-qtd-s1').value='50';
          await generateSimulado('s1');
          const a=simActive['s1']||{};
          return {n:(a.questoes||[]).length};
        }""")
        print('   chamadas ao modelo: %d · pedidos por chamada: %s'
              %(len(chamadas),[c['pediu'] for c in chamadas]))
        print('   teto de saida por chamada: %s'%[c['teto'] for c in chamadas])
        print('   questoes no simulado: %d'%r2['n'])
        assert r2['n']==50, r2
        assert all((c['pediu'] or 0)<=20 for c in chamadas), chamadas
        assert len(chamadas)>=3, chamadas
        assert all(c['teto'] and c['teto']<=32768 for c in chamadas), chamadas
        print('   OK\n')

        print('=== C) 10 questoes continuam numa chamada so ===')
        chamadas.clear()
        r3=await page.evaluate("""async()=>{
          simActive={}; document.getElementById('sim-qtd-s1').value='10';
          await generateSimulado('s1');
          return {n:((simActive['s1']||{}).questoes||[]).length};
        }""")
        print('   chamadas: %d · questoes: %d · teto: %s'
              %(len(chamadas),r3['n'],[c['teto'] for c in chamadas]))
        assert len(chamadas)==1 and r3['n']==10
        print('   OK\n')

        print('=== D) o teto acompanha o lote (nao pede o maximo a toa) ===')
        r4=await page.evaluate("()=>[5,10,20,50].map(n=>[n,simTetoSaida(n)])")
        for n,t in r4: print('   lote de %2d questoes -> teto %d tokens'%(n,t))
        assert r4[0][1]>=4096 and r4[2][1]>r4[1][1] and r4[3][1]<=32768
        print('   OK\n')

        print('=== E) lote que falha nao derruba os que ja vieram ===')
        chamadas.clear()
        falhou={'n':0}
        async def g2(route,request):
            body=json.loads(request.post_data or '{}')
            import re as _re
            txt=body['contents'][0]['parts'][0]['text']
            m=_re.search(r'(\d+)\s+quest', txt)
            n=int(m.group(1)) if m else 10
            chamadas.append(n)
            if len(chamadas)==2:      # o segundo lote volta cortado no meio
                falhou['n']+=1
                await route.fulfill(status=200,content_type='application/json',
                  body=json.dumps({'candidates':[{'content':{'parts':[
                    {'text':'[{"questao":"cortada no me'}]},'finishReason':'STOP'}]}))
                return
            off=sum(chamadas[:-1])
            await route.fulfill(status=200,content_type='application/json',
              body=json.dumps({'candidates':[{'content':{'parts':[
                {'text':json.dumps(questoes(n,off))}]},'finishReason':'STOP'}]}))
        await page.unroute('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**')
        await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', g2)
        r5=await page.evaluate("""async()=>{
          simActive={}; document.getElementById('sim-qtd-s1').value='40';
          await generateSimulado('s1');
          return {n:((simActive['s1']||{}).questoes||[]).length};
        }""")
        print('   lotes pedidos: %s (um deles voltou cortado)'%chamadas)
        print('   questoes no simulado: %d de 40'%r5['n'])
        assert falhou['n']>=1 and r5['n']==40, (falhou,r5,chamadas)
        print('   OK — o lote cortado foi refeito, e os anteriores nao se perderam\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
