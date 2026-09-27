import asyncio, sys
sys.path.insert(0, '.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

K1, K2 = 'k1', 'k2'
TA, TB, TC = 'ta', 'tb', 'tc'   # ta em K1, tb em K1, tc em K2
SUB1, SUB2 = 'sub1', 'sub2'

async def main():
    seed = make_seed({
        'kingdoms': [{'id': K1, 'name': 'Reino Um'}, {'id': K2, 'name': 'Reino Dois'}],
        'topics': {
            K1: [
                {'id': TA, 'name': 'Chefão A', 'icon': '⚔️', 'priority': 1, 'subtopics': [
                    {'id': SUB1, 'name': 'Miniboss Promover', 'priority': 70, 'studied': True},
                    {'id': SUB2, 'name': 'Miniboss Mover', 'priority': 70, 'studied': True},
                ]},
                {'id': TB, 'name': 'Chefão B', 'icon': '⚔️', 'priority': 1, 'subtopics': []},
            ],
            K2: [{'id': TC, 'name': 'Chefão C (outro reino)', 'icon': '⚔️', 'priority': 1, 'subtopics': []}],
        },
        'times': {SUB1: 120, SUB2: 340},
        'revisions': {SUB1: [{'date': '2026-01-01', 'completed': False}], SUB2: []},
        'flashcards': {
            'fc1': {'id': 'fc1', 'mbId': TA, 'subId': SUB1, 'pergunta': 'P1?', 'resposta': 'R1', 'tags': ''},
            'fc2': {'id': 'fc2', 'mbId': TA, 'subId': SUB2, 'pergunta': 'P2?', 'resposta': 'R2', 'tags': ''},
        },
    })
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, seed)
        try:
            # entra no reino K1, abre o chefão A pra ver os minibosses
            await page.evaluate("""() => {
                currentKingdom = db.kingdoms.find(k => k.id === '%s');
                showScreen('kingdom'); renderTopics();
            }""" % K1)
            await page.wait_for_timeout(200)

            # --- Teste 1: transformar SUB1 em chefão novo ---
            await page.evaluate("(id) => promptPromoteSubtopic('%s', id)" % TA, SUB1)
            await page.wait_for_timeout(100)
            await page.evaluate("(id) => { document.getElementById('promote-topic-name').value = 'Chefão Promovido'; promoteSubtopicToTopic('%s', id); }" % TA, SUB1)
            await page.wait_for_timeout(200)

            estado1 = await page.evaluate("""() => {
                const a = db.topics['%s'].find(t => t.id === '%s');
                const novo = db.topics['%s'].find(t => t.name === 'Chefão Promovido');
                return {
                    saiuDeA: !a.subtopics.some(s => s.id === '%s'),
                    novoExiste: !!novo,
                    novoTemSub: novo && novo.subtopics.some(s => s.id === '%s'),
                    tempoPreservado: db.times['%s'],
                    revisoesPreservadas: (db.revisions['%s']||[]).length,
                    fcMovido: db.flashcards['fc1'].mbId === (novo && novo.id),
                };
            }""" % (K1, TA, K1, SUB1, SUB1, SUB1, SUB1))
            print('Promover ->', estado1)
            assert estado1['saiuDeA'], 'miniboss não saiu do chefão A'
            assert estado1['novoExiste'], 'chefão novo não foi criado'
            assert estado1['novoTemSub'], 'chefão novo não contém o miniboss promovido'
            assert estado1['tempoPreservado'] == 120, 'tempo estudado se perdeu'
            assert estado1['revisoesPreservadas'] == 1, 'revisões se perderam'
            assert estado1['fcMovido'], 'flashcard do miniboss não seguiu pro novo chefão'

            # --- Teste 2: mover SUB2 de A para C (outro REINO) ---
            await page.evaluate("(id) => openMoveSubtopicModal('%s', id)" % TA, SUB2)
            await page.wait_for_timeout(100)
            opcoes = await page.evaluate("() => Array.from(document.getElementById('move-sub-target').options).map(o => o.textContent)")
            print('opções de destino:', opcoes)
            assert any('Reino Dois' in o and 'Chefão C' in o for o in opcoes), 'chefão de outro reino não apareceu na lista'
            assert not any('Chefão A' in o for o in opcoes), 'o próprio chefão atual não deveria aparecer na lista'

            await page.evaluate("""(id) => {
                const sel = document.getElementById('move-sub-target');
                sel.value = '%s::%s';
                moveSubtopicToTopic('%s', id);
            }""" % (K2, TC, TA), SUB2)
            await page.wait_for_timeout(200)

            estado2 = await page.evaluate("""() => {
                const a = db.topics['%s'].find(t => t.id === '%s');
                const c = db.topics['%s'].find(t => t.id === '%s');
                return {
                    saiuDeA: !a.subtopics.some(s => s.id === '%s'),
                    chegouEmC: c.subtopics.some(s => s.id === '%s'),
                    tempoPreservado: db.times['%s'],
                    fcMovido: db.flashcards['fc2'].mbId === '%s',
                };
            }""" % (K1, TA, K2, TC, SUB2, SUB2, SUB2, TC))
            print('Mover entre reinos ->', estado2)
            assert estado2['saiuDeA'], 'miniboss não saiu do chefão A'
            assert estado2['chegouEmC'], 'miniboss não chegou no chefão C (outro reino)'
            assert estado2['tempoPreservado'] == 340, 'tempo estudado se perdeu no move'
            assert estado2['fcMovido'], 'flashcard não seguiu o miniboss pro chefão C'

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK: transformar em chefão e mover para outro chefão funcionam, preservando dados')
        finally:
            await browser.close()

asyncio.run(main())
