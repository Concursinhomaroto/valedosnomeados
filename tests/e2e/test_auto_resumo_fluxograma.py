import asyncio, json, sys
sys.path.insert(0, '.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB_ID = 'sub-teste-1'
TOPIC_ID = 'topic-teste-1'
KINGDOM_ID = 'kingdom-teste-1'


FLASHCARD_PERGUNTA = 'Pergunta de teste do chefão?'


def make_study_seed():
    kingdom = {'id': KINGDOM_ID, 'name': 'Reino Teste'}
    topic = {
        'id': TOPIC_ID, 'name': 'Chefão Teste',
        'subtopics': [{'id': SUB_ID, 'name': 'Miniboss Teste', 'priority': 70, 'studied': False}],
    }
    seed = make_seed({
        'studyNickname': 'Auto Gen Tester', 'studyCharacter': 'ash',
        'kingdoms': [kingdom],
        'topics': {KINGDOM_ID: [topic]},
        'geminiApiKey': 'FAKE_TEST_KEY',
        'flashcards': {
            'card1': {'mbId': TOPIC_ID, 'pergunta': FLASHCARD_PERGUNTA, 'resposta': 'Resposta de teste.'},
        },
    })
    return seed


fluxo_requests = []
resumo_requests = []


async def handle_gemini(route, request):
    body = request.post_data or ''
    if 'árvore recursiva' in body or 'FORMATO EXATO' in body:
        # Chamada do Fluxograma: guarda o corpo pra confirmar depois que combinou
        # busca na internet (tools=google_search) COM o texto do resumo recém-gerado,
        # não uma coisa OU outra.
        fluxo_requests.append(body)
        tree = {
            'texto': 'Conceito inicial (auto)', 'tipo': 'inicio',
            'ramos': [{'rotulo': None, 'no': {'texto': 'Conclusão (auto)', 'tipo': 'fim', 'ramos': []}}],
        }
        payload = {
            'candidates': [{
                'content': {'parts': [{'text': json.dumps(tree)}]},
                'finishReason': 'STOP',
                'groundingMetadata': {'webSearchQueries': ['assunto de teste (fluxograma)']},
            }]
        }
    else:
        # Chamada do Resumo (com busca simulada como "grounded").
        resumo_requests.append(body)
        payload = {
            'candidates': [{
                'content': {'parts': [{'text': 'Resumo gerado automaticamente para teste do Miniboss.'}]},
                'finishReason': 'STOP',
                'groundingMetadata': {'webSearchQueries': ['assunto de teste']},
            }]
        }
    await route.fulfill(status=200, content_type='application/json', body=json.dumps(payload))


async def main():
    seed = make_study_seed()
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, seed)
        try:
            await page.route(
                '**generativelanguage.googleapis.com/v1beta/models/*:generateContent**',
                handle_gemini,
            )

            # Simula estar dentro do reino/tópico de teste (equivalente a ter navegado até lá)
            # e clica em "Estudar" pela primeira vez nesse miniboss.
            await page.evaluate(
                """([kingdomId, subId, topicId]) => {
                    currentKingdom = db.kingdoms.find(k => k.id === kingdomId);
                    toggleTimer(subId, topicId);
                }""",
                [KINGDOM_ID, SUB_ID, TOPIC_ID],
            )

            # Espera a cadeia automática (resumo -> fluxograma) terminar.
            await page.wait_for_function(
                """(subId) => {
                    const sub = simFindSub(subId);
                    return !!(sub && sub.fluxograma && sub.fluxograma.nos && Object.keys(sub.fluxograma.nos).length);
                }""",
                arg=SUB_ID,
                timeout=15000,
            )

            state = await page.evaluate(
                """(subId) => {
                    const sub = simFindSub(subId);
                    return {
                        studied: sub.studied,
                        resumoTexto: sub.resumo && sub.resumo.texto,
                        resumoOrigem: sub.resumo && sub.resumo.origem,
                        fluxoOrigem: sub.fluxograma && sub.fluxograma.origem,
                        fluxoGrounded: sub.fluxograma && sub.fluxograma.grounded,
                        fluxoNos: sub.fluxograma && Object.keys(sub.fluxograma.nos).length,
                    };
                }""",
                SUB_ID,
            )
            print('estado final:', state)

            assert state['studied'] is True
            assert state['resumoTexto'] == 'Resumo gerado automaticamente para teste do Miniboss.'
            assert state['resumoOrigem'] == 'web'
            # Fluxograma automático precisa ter pesquisado na internet (origem 'web' + grounded)
            # E usado o resumo recém-gerado como base — as duas fontes combinadas, não uma só.
            assert state['fluxoOrigem'] == 'web', f"esperava fluxograma via busca na internet (origem 'web'), veio {state['fluxoOrigem']!r}"
            assert state['fluxoGrounded'] is True
            assert state['fluxoNos'] >= 2

            assert len(resumo_requests) >= 1, 'nenhuma chamada de resumo foi feita'
            assert FLASHCARD_PERGUNTA in resumo_requests[0], 'resumo automático não incluiu os flashcards do chefão'

            assert len(fluxo_requests) >= 1, 'nenhuma chamada de fluxograma foi feita'
            fluxo_body = fluxo_requests[0]
            assert '"google_search"' in fluxo_body, 'fluxograma automático não pesquisou na internet (sem tools=google_search)'
            assert 'Resumo gerado automaticamente para teste do Miniboss.' in fluxo_body, 'fluxograma automático não usou o texto do resumo como base'

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK: resumo (web+flashcards) e fluxograma (web+resumo) gerados automaticamente ao estudar um miniboss pela 1ª vez')
        finally:
            await browser.close()

asyncio.run(main())
