import asyncio, json, sys
sys.path.insert(0, '.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB_ID, TOPIC_ID, KINGDOM_ID = 'sub-fc-1', 'topic-fc-1', 'kingdom-fc-1'
pedidos = []

async def handle_gemini(route, request):
    body = request.post_data or ''
    pedidos.append(body)
    cards = {'cards': [{'pergunta': f'Pergunta {i} do assunto?', 'resposta': f'Resposta {i}.'}
                       for i in range(1, 11)]}
    payload = {'candidates': [{'content': {'parts': [{'text': json.dumps(cards)}]},
                               'finishReason': 'STOP'}]}
    await route.fulfill(status=200, content_type='application/json', body=json.dumps(payload))

async def main():
    seed = make_seed({
        'studyNickname': 'FC Tester', 'studyCharacter': 'ash', 'geminiApiKey': 'FAKE',
        'kingdoms': [{'id': KINGDOM_ID, 'name': 'Reino Teste'}],
        'topics': {KINGDOM_ID: [{'id': TOPIC_ID, 'name': 'Chefão Teste', 'subtopics': [
            {'id': SUB_ID, 'name': 'Miniboss Teste', 'priority': 70, 'studied': True,
             'resumo': {'texto': 'RESUMO JA ESTUDADO: prazo antigo de 5 dias.',
                        'geradoEm': '2026-01-01T00:00:00.000Z', 'origem': 'web'}}]}]},
        'flashcards': {},
    })
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, seed)
        try:
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', handle_gemini)

            # 1) a Base Legal não deve mais existir
            sumiu = await page.evaluate("""() => ({
                temToggleLegis: typeof toggleLegis !== 'undefined',
                temGenLegis:    typeof generateLegislacao !== 'undefined',
                temFlash:       typeof toggleFlash === 'function',
            })""")
            print('base legal removida / flashcards presentes:', sumiu)
            assert sumiu['temToggleLegis'] is False and sumiu['temGenLegis'] is False
            assert sumiu['temFlash'] is True

            # 2) o botão do miniboss agora é Flashcards
            html = await page.evaluate("(id)=>subItemHTML(simFindSub(id),'%s')" % TOPIC_ID, SUB_ID)
            assert 'Flashcards' in html, 'botão Flashcards não aparece no card do miniboss'
            assert 'Base Legal' not in html, 'ainda há Base Legal no card'
            print('botão do miniboss OK')

            # 3) clicar em Flashcards gera com a IA
            await page.evaluate("(id)=>toggleFlash(id)", SUB_ID)
            await page.wait_for_function(
                "(id)=>Object.values(db.flashcards||{}).filter(c=>c.subId===id).length>0",
                arg=SUB_ID, timeout=15000)
            estado = await page.evaluate("""(id)=>{
                const cs=Object.values(db.flashcards||{}).filter(c=>c.subId===id);
                return {n:cs.length, mbId:cs[0].mbId, subNome:cs[0].subNome,
                        tags:cs[0].tags, p:cs[0].pergunta, r:cs[0].resposta};
            }""", SUB_ID)
            print('gerados:', estado)
            assert estado['n'] == 10
            assert estado['mbId'] == TOPIC_ID, 'card precisa continuar ligado ao chefão (tela de Flashcards)'
            assert estado['subNome'] == 'Miniboss Teste'
            assert 'Miniboss Teste' in pedidos[0], 'o prompt não citou o assunto do miniboss'
            # REGRA: mesmo com resumo, a busca na internet tem que estar ativa,
            # e o resumo tem que ir junto pra ser confrontado.
            assert '"google_search"' in pedidos[0], 'gerou flashcard sem pesquisar na internet'
            assert 'RESUMO JA ESTUDADO' in pedidos[0], 'o resumo não foi enviado pra comparação'
            assert 'mais ATUAIS' in pedidos[0], 'o prompt não pediu a informação mais atual'
            print('busca na web ativa + resumo enviado pra comparação: OK')

            # 4) gerar de novo não repete perguntas: manda as existentes no prompt
            await page.evaluate("(id)=>generateFlashcardsSub(id,true)", SUB_ID)
            await page.wait_for_function(
                "(id)=>Object.values(db.flashcards||{}).filter(c=>c.subId===id).length>10",
                arg=SUB_ID, timeout=15000)
            print('nº de chamadas à IA:', len(pedidos))
            achou = [i for i, b in enumerate(pedidos) if 'repita' in b and 'Pergunta 1' in b]
            print('chamadas que mandaram as perguntas já existentes:', achou)
            assert achou, 'nenhuma chamada avisou pra não repetir as perguntas existentes'
            print('2ª geração manda as perguntas já existentes: OK')

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK: Base Legal virou Flashcards e a geração por IA funciona')
        finally:
            await browser.close()

asyncio.run(main())
