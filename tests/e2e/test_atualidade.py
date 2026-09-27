import asyncio, json, sys, datetime
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB='sub-q1'; TOPIC='topic-q1'; KING='king-q1'
pedidos=[]

async def gemini(route, request):
    body=request.post_data or ''
    pedidos.append(body)
    payload={'candidates':[{
        'content':{'parts':[{'text':'RESUMO: reposição volêmica em queimado. ATUALIZAÇÕES RECENTES: (diretriz de 2023) volume inicial menor.'}]},
        'finishReason':'STOP',
        'groundingMetadata':{
            'webSearchQueries':['diretriz queimado reposição volêmica 2026','cristaloide queimadura atualização'],
            'groundingChunks':[
                {'web':{'uri':'https://ameriburn.org/guideline-2023','title':'ABA — Guideline'}},
                {'web':{'uri':'https://www.gov.br/saude/protocolo','title':'Ministério da Saúde — Protocolo'}},
                {'web':{'uri':'https://ameriburn.org/guideline-2023','title':'duplicada, deve ser removida'}},
                {'web':{'title':'sem url, deve ser ignorada'}},
            ]}}]}
    await route.fulfill(status=200, content_type='application/json', body=json.dumps(payload))

async def main():
    seed=make_seed({'studyNickname':'Reitor','studyCharacter':'ash','geminiApiKey':'FAKE',
        'kingdoms':[{'id':KING,'name':'Medicina'}],
        'topics':{KING:[{'id':TOPIC,'name':'Trauma','subtopics':[
            {'id':SUB,'name':'Paciente com queimadura','priority':80,'studied':False}]}]}})
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p,seed)
        try:
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gemini)
            await page.evaluate("""([k]) => { currentKingdom = db.kingdoms.find(x=>x.id===k); }""",[KING])
            await page.evaluate("(id) => generateResumoWeb(id)", SUB)
            await page.wait_for_function("(id)=>{const s=simFindSub(id);return !!(s&&s.resumo&&s.resumo.texto);}", arg=SUB, timeout=15000)

            corpo=pedidos[0]
            hoje=datetime.date.today()
            mes=['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'][hoje.month-1]
            print('--- o que foi enviado ao Gemini ---')
            for marca,rot in [
                (f'de {mes} de {hoje.year}', 'ÂNCORA DE DATA (dia de hoje)'),
                ('não use a data em que seu treinamento terminou','proíbe usar a data de corte'),
                ('a pesquisa vence','pesquisa vence o treinamento'),
                ('FONTE PRIMÁRIA','exige fonte primária'),
                ('não confirmei a versão vigente','manda admitir quando não confirma'),
                ('ATUALIZAÇÕES RECENTES','exige seção de atualizações'),
                ('"google_search"','ferramenta de busca ligada'),
            ]:
                ok = marca in corpo
                print(f'  [{"x" if ok else " "}] {rot}')
                assert ok, f'faltou no prompt: {rot}'

            # data tem que ser a de HOJE, não uma fixa no código
            assert str(hoje.year) in corpo, 'ano corrente não foi para o prompt'

            r = await page.evaluate("""(id)=>{const s=simFindSub(id);return {
                grounded:s.resumo.grounded, fontes:s.resumo.fontes, consultas:s.resumo.consultas};}""", SUB)
            print('\n--- fontes guardadas ---')
            print('  grounded:', r['grounded'])
            print('  consultas:', r['consultas'])
            for f in r['fontes']: print('   -', f['titulo'], '|', f['url'])
            assert r['grounded'] is True
            assert len(r['fontes'])==2, f"esperava 2 fontes (duplicada e sem-url descartadas), veio {len(r['fontes'])}"
            assert len(r['consultas'])==2

            html = await page.evaluate("(id)=>fontesHTML(simFindSub(id).resumo.fontes,simFindSub(id).resumo.consultas,simFindSub(id).resumo.diag)", SUB)
            assert 'ameriburn.org' in html and 'gov.br' in html, html[:300]
            assert 'Fontes usadas na pesquisa (2)' in html, html[:300]
            assert html.count('<li>')==2
            print('\n✓ painel de fontes renderiza as 2 fontes, sem duplicata')

            # sem grounding, o aviso tem que ser explícito
            aviso = await page.evaluate("""(id)=>{const s=simFindSub(id);s.resumo.grounded=false;
                const h=resumoPanelHTML(s); s.resumo.grounded=true; return h;}""", SUB)
            assert 'SEM pesquisa na internet' in aviso, 'não avisa quando a busca não aconteceu'
            print('✓ aviso claro quando a busca não aconteceu')

            print('\nErros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — prompt ancorado na data de hoje, regras de atualidade e fontes à vista')
        finally:
            await browser.close()
asyncio.run(main())
