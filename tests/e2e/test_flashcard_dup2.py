import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

KING='k1'; TOPIC='t1'; SUB='s1'
def seed():
    return make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE',
      'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
      'topics':{KING:[{'id':TOPIC,'name':'Urgência','subtopics':[
        {'id':SUB,'name':'Choque Séptico','priority':70,'studied':True}]}]},
      # card vindo de PDF: tem mbId, NAO tem subId. Antes ele nao ia no prompt.
      'flashcards':{'fc_pdf':{'id':'fc_pdf','mbId':TOPIC,'pergunta':'Qual o agente mais comum na sepse hospitalar?',
                              'resposta':'Gram-negativos.','tags':'pdf','dificuldade':2,'acertos':0,'erros':0}}})

def resp(cards):
    return json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps({'cards':cards})}]},'finishReason':'STOP'}]})

LOTE=[{'pergunta':'Qual o prazo para iniciar o antibiótico na sepse?','resposta':'1 hora.'},
      {'pergunta':'Qual a meta de PAM no choque séptico?','resposta':'65 mmHg.'}]
# so PARECIDA com a 1a (nao identica) -> tem que ser MARCADA, nunca apagada
LOTE2=[{'pergunta':'Qual é o prazo para iniciar os antibióticos na sepse?','resposta':'1 hora.'},
       {'pergunta':'Qual a meta de lactato no choque séptico?','resposta':'Clareamento.'}]

async def main():
    async with async_playwright() as p:
        atual=[LOTE]; prompts=[]
        async def gem(route,request):
            try:
                body=json.loads(request.post_data or '{}')
                prompts.append(body['contents'][0]['parts'][0]['text'])
            except Exception as e: prompts.append('ERRO:'+str(e))
            await route.fulfill(status=200,content_type='application/json',body=resp(atual[0]))
        browser,page,errors=await setup_page(p, seed())
        try:
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
            await page.route('**api.tavily.com/search**', lambda r: asyncio.ensure_future(
                r.fulfill(status=200,content_type='application/json',body='{"results":[]}')))
            await page.route('**generativelanguage.googleapis.com/v1beta/models?**', lambda r: asyncio.ensure_future(
                r.fulfill(status=200,content_type='application/json',body='{"models":[]}')))

            async def gerar(lote):
                atual[0]=lote
                await page.evaluate("(s)=>generateFlashcardsSub(s)",SUB)
                await page.wait_for_timeout(2500)

            await gerar(LOTE)
            pr=prompts[-1]
            print('1) card de PDF entra na lista mandada pra IA ->', 'Qual o agente mais comum na sepse hospitalar?' in pr)
            assert 'Qual o agente mais comum na sepse hospitalar?' in pr, 'card de PDF nao foi mandado pra IA'
            print('2) a trava fica no FIM do prompt ->', 'cards do que devolver repetição.' in pr[-400:])
            assert pr.rstrip().endswith('cards do que devolver repetição.'), 'trava nao esta no fim:\n...'+pr[-200:]

            await gerar(LOTE2)
            r=await page.evaluate("""(s)=>{
              const cs=Object.values(db.flashcards||{}).filter(c=>c.subId===s);
              const sus=flashSuspeitasDup(cs);
              return {n:cs.length, suspeitas:sus.size, perguntas:cs.map(c=>c.pergunta)};}""",SUB)
            print('3) reformulacao parecida NAO foi apagada ->', r['n'], 'cards')
            for q in r['perguntas']: print('     -',q)
            assert r['n']==4, f'esperava 4 cards (2+2), veio {r["n"]}'
            print('4) marcadas como suspeita ->', r['suspeitas'])
            assert r['suspeitas']==1, f'esperava 1 suspeita, veio {r["suspeitas"]}'

            # painel: badge de suspeita + botao de apagar em cada card
            html=await page.evaluate("(s)=>flashPanelHTML({id:s,name:'Choque Séptico'})",SUB)
            print('5) painel mostra aviso de repetida ->','Parece repetir' in html)
            assert 'Parece repetir' in html and 'possível repetida' in html
            print('6) painel tem botao de apagar por card ->', html.count('flashApagarCard'),'botoes /',r['n'],'cards')
            assert html.count('flashApagarCard')==r['n']

            # apagar de verdade
            alvo=await page.evaluate("""(s)=>{const cs=Object.values(db.flashcards).filter(c=>c.subId===s);
              return [...flashSuspeitasDup(cs).keys()][0];}""",SUB)
            await page.evaluate("()=>{window.confirm=()=>true;}")
            await page.evaluate("([id,s])=>flashApagarCard(id,s)",[alvo,SUB])
            n=await page.evaluate("(s)=>Object.values(db.flashcards).filter(c=>c.subId===s).length",SUB)
            print('7) apagar o card marcado ->', n, 'cards restantes')
            assert n==3

            # import JSON duas vezes nao pode duplicar
            imp=await page.evaluate("""()=>{
              fcSelectedMb={id:'%s'};
              const antes=Object.keys(db.flashcards).length;
              const arq=JSON.stringify({cards:[{pergunta:'Card do arquivo',resposta:'X'},{pergunta:'Outro do arquivo',resposta:'Y'}]});
              const faz=()=>fcImportDeckFile({files:[new File([arq],'d.json')],value:''});
              return {antes,arq};}""" % TOPIC)
            async def importar(txt):
                await page.evaluate("""(txt)=>{
                  fcSelectedMb={id:'%s'};
                  const dt=new DataTransfer(); dt.items.add(new File([txt],'d.json',{type:'application/json'}));
                  fcImportDeckFile({files:dt.files,value:''});}""" % TOPIC, txt)
                await page.wait_for_timeout(400)
            await importar(imp['arq']); n1=await page.evaluate("()=>Object.keys(db.flashcards).length")
            await importar(imp['arq']); n2=await page.evaluate("()=>Object.keys(db.flashcards).length")
            print('8) import JSON: 1x ->',n1-imp['antes'],'novos | 2x (mesmo arquivo) ->',n2-n1,'novos')
            assert n1-imp['antes']==2 and n2==n1, f'reimportar duplicou: {n1} -> {n2}'

            assert not real_errors(errors), real_errors(errors)
            print('\nOK')
        finally:
            await browser.close()
asyncio.run(main())
