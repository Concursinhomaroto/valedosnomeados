import asyncio, sys
sys.path.insert(0, '.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

K1, K2, K3 = 'k1', 'k2', 'k3'
TA, TB = 'ta', 'tb'
SUB1 = 'sub1'

async def main():
    seed = make_seed({
        'kingdoms': [{'id': K1, 'name': 'Reino Um'}, {'id': K2, 'name': 'Reino Dois'}],
        'topics': {
            K1: [
                {'id': TA, 'name': 'Chefão Promover', 'icon': '⚔️', 'priority': 1, 'subtopics': [
                    {'id': SUB1, 'name': 'Miniboss X', 'priority': 70, 'studied': True},
                ]},
                {'id': TB, 'name': 'Chefão Mover', 'icon': '⚔️', 'priority': 1, 'subtopics': []},
            ],
            K2: [],
        },
        'times': {SUB1: 500},
        'revisions': {SUB1: [{'date': '2026-01-01', 'completed': False}]},
        'flashcards': {'fc1': {'id': 'fc1', 'mbId': TA, 'subId': SUB1, 'pergunta': 'P?', 'resposta': 'R', 'tags': ''}},
    })
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, seed)
        try:
            await page.evaluate("""() => {
                currentKingdom = db.kingdoms.find(k => k.id === '%s');
                showScreen('kingdom'); renderTopics();
            }""" % K1)
            await page.wait_for_timeout(200)

            # --- Transformar Chefão A em Reino ---
            await page.evaluate("() => promptPromoteTopic('%s')" % TA)
            await page.wait_for_timeout(100)
            await page.evaluate("""() => {
                document.getElementById('promote-kingdom-name').value = 'Reino Promovido';
                promoteTopicToKingdom('%s');
            }""" % TA)
            await page.wait_for_timeout(200)

            estado1 = await page.evaluate("""() => {
                const k1 = db.topics['%s'];
                const novoReino = db.kingdoms.find(k => k.name === 'Reino Promovido');
                return {
                    saiuDeK1: !k1.some(t => t.id === '%s'),
                    reinoExiste: !!novoReino,
                    reinoTemChefao: novoReino && (db.topics[novoReino.id]||[]).some(t => t.id === '%s'),
                    minibossFoiJunto: novoReino && (db.topics[novoReino.id]||[])
                        .find(t => t.id === '%s').subtopics.some(s => s.id === '%s'),
                    tempoPreservado: db.times['%s'],
                    revisoesPreservadas: (db.revisions['%s']||[]).length,
                    fcContinuaComMbId: db.flashcards['fc1'].mbId === '%s',
                };
            }""" % (K1, TA, TA, TA, SUB1, SUB1, SUB1, TA))
            print('Transformar chefão em reino ->', estado1)
            assert estado1['saiuDeK1'], 'chefão não saiu do reino 1'
            assert estado1['reinoExiste'], 'reino novo não foi criado'
            assert estado1['reinoTemChefao'], 'reino novo não contém o chefão'
            assert estado1['minibossFoiJunto'], 'o miniboss não seguiu junto com o chefão'
            assert estado1['tempoPreservado'] == 500, 'tempo estudado se perdeu'
            assert estado1['revisoesPreservadas'] == 1, 'revisões se perderam'
            assert estado1['fcContinuaComMbId'], 'flashcard perdeu o vínculo (mbId não devia mudar)'

            # --- Mover Chefão B (ainda no Reino 1) para o Reino 2 ---
            await page.evaluate("() => openMoveTopicModal('%s')" % TB)
            await page.wait_for_timeout(100)
            opcoes = await page.evaluate("() => Array.from(document.getElementById('move-topic-target').options).map(o => o.textContent)")
            print('opções de reino destino:', opcoes)
            assert 'Reino Dois' in opcoes and 'Reino Promovido' in opcoes
            assert 'Reino Um' not in opcoes, 'não deveria listar o próprio reino atual'

            await page.evaluate("""() => {
                document.getElementById('move-topic-target').value = '%s';
                moveTopicToKingdom('%s');
            }""" % (K2, TB))
            await page.wait_for_timeout(200)

            estado2 = await page.evaluate("""() => ({
                saiuDeK1: !(db.topics['%s']||[]).some(t => t.id === '%s'),
                chegouEmK2: (db.topics['%s']||[]).some(t => t.id === '%s'),
            })""" % (K1, TB, K2, TB))
            print('Mover chefão entre reinos ->', estado2)
            assert estado2['saiuDeK1'] and estado2['chegouEmK2']

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK: transformar chefão em reino e mover para outro reino funcionam, preservando dados')
        finally:
            await browser.close()

asyncio.run(main())
