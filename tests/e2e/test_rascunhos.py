import asyncio, sys
sys.path.insert(0, '.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, make_seed({'studyNickname':'Reitor','studyCharacter':'ash'}))
        try:
            respostas = ['Minha planta']
            def dialogo(d):
                asyncio.ensure_future(d.accept(respostas.pop(0) if respostas and d.type=='prompt' else '40'))
            page.on('dialog', dialogo)

            await page.evaluate("() => showScreen('mapaeditor')")
            await page.wait_for_function("() => !!mapedMapa", timeout=20000)

            # 1) editar liga o autosave no navegador
            assert await page.evaluate("() => mapedAutoGuardado()") is None, 'começou com autosave sujo'
            await page.evaluate("""() => {
                mapedSelectTileset('Museum'); mapedSel={c:1,r:1,w:1,h:1};
                mapedSetMode('objeto'); mapedSnapshot(); mapedAplicar(7,7);
            }""")
            await page.wait_for_function("() => !!mapedAutoGuardado()", timeout=5000)
            auto = await page.evaluate("() => { const a=mapedAutoGuardado(); const m=JSON.parse(a.json); return {em:!!a.em, w:m.width, museu:(m.layers.find(l=>l.name==='Obj_Museum')||{objects:[]}).objects.length}; }")
            print('autosave:', auto)
            assert auto['em'] and auto['w'] == 92 and auto['museu'] == 1, auto

            # 2) salvar rascunho com nome NÃO toca na planta publicada
            await page.evaluate("() => mapedSalvarRascunho()")
            await page.wait_for_function("() => window.__updateCalls.some(c=>c.path.startsWith('sala_mapa/rascunhos/'))", timeout=8000)
            chamadas = await page.evaluate("() => window.__updateCalls.map(c=>c.path)")
            assert not any(c == 'sala_mapa/atual' for c in chamadas), 'salvar rascunho publicou sem querer!'
            r = await page.evaluate("""() => {
                const c=window.__updateCalls.filter(c=>c.path.startsWith('sala_mapa/rascunhos/')).pop();
                const m=JSON.parse(c.val.json);
                return {path:c.path, nome:c.val.nome, w:c.val.w, h:c.val.h,
                        museu:(m.layers.find(l=>l.name==='Obj_Museum')||{objects:[]}).objects.length};
            }""")
            print('rascunho salvo:', r)
            assert r['path'] == 'sala_mapa/rascunhos/minha-planta', r
            assert r['nome'] == 'Minha planta' and r['w'] == 92 and r['museu'] == 1, r
            assert await page.evaluate("() => mapedSujo") is False, 'salvar rascunho devia zerar a pendência'

            # 3) a Sala continua vendo a planta antiga (rascunho não publica)
            sala = await page.evaluate("async () => { const m = await salaMapaFetchMap(); return (m.layers.find(l=>l.name==='Obj_Museum')||{objects:[]}).objects.length; }")
            print('museu visível na Sala:', sala)
            assert sala == 0, 'o rascunho vazou pra Sala'

            # 4) abrir o rascunho de volta traz a edição
            await page.evaluate("""() => { mapedCarregar(JSON.parse(JSON.stringify(mapedMapa))); 
                const l=mapedMapa.layers.find(l=>l.name==='Obj_Museum'); if(l)l.objects=[]; }""")
            assert await page.evaluate("() => (mapedMapa.layers.find(l=>l.name==='Obj_Museum')||{objects:[]}).objects.length") == 0
            await page.evaluate("() => mapedAbrirRascunho('minha-planta')")
            await page.wait_for_function("() => (mapedMapa.layers.find(l=>l.name==='Obj_Museum')||{objects:[]}).objects.length===1", timeout=8000)
            print('rascunho reaberto com a edição de volta')

            # 5) recuperação automática (o cenário "fechei a aba")
            await page.evaluate("""() => {
                const l=mapedMapa.layers.find(l=>l.name==='Obj_Museum'); l.objects=[];
                mapedSujo=false;
            }""")
            await page.evaluate("() => mapedRecuperarAuto()")
            await page.wait_for_function("() => (mapedMapa.layers.find(l=>l.name==='Obj_Museum')||{objects:[]}).objects.length===1", timeout=8000)
            assert await page.evaluate("() => mapedSujo") is True, 'recuperado devia ficar marcado como não publicado'
            print('recuperação automática trouxe o trabalho de volta')

            # 6) apagar rascunho
            await page.evaluate("() => mapedApagarRascunho('minha-planta')")
            await page.wait_for_function("() => window.__updateCalls.some(c=>c.path==='sala_mapa/rascunhos/minha-planta'&&c.op==='remove')", timeout=8000)
            print('rascunho apagado')

            # 7) publicar continua funcionando e limpa a recuperação
            await page.evaluate("() => mapedSalvar()")
            await page.wait_for_function("() => window.__updateCalls.some(c=>c.path==='sala_mapa/atual')", timeout=8000)
            assert await page.evaluate("() => mapedAutoGuardado()") is None, 'publicar devia limpar o autosave'
            print('publicar limpou o autosave')

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — rascunho salva sem publicar, reabre, recupera sozinho e não vaza pra Sala')
        finally:
            await browser.close()

asyncio.run(main())
