import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed(tavily=True):
    e={'studyNickname':'Leo','geminiApiKey':'FAKE',
       'repertorio':{'eixos':[{'id':'saude','nome':'Saúde Pública e SUS','icon':'⚕️','color':'#06b6d4'}],
                     'temas':{'rep_ja':{'id':'rep_ja','nome':'Judicialização da Saúde','eixoId':'saude'}}}}
    if tavily: e['tavilyApiKey']='tvly-FAKE'
    return make_seed(e)

TAV=json.dumps({'results':[
 {'url':'https://agenciabrasil.ebc.com.br/saude/enfermagem','title':'Agência Brasil',
  'raw_content':'Lei do piso da enfermagem teve novo repasse aprovado. Faltam 30 mil profissionais na atenção primária.'},
 {'url':'https://www.ibge.gov.br/idosos','title':'IBGE',
  'raw_content':'Populacao com 65 anos ou mais chegou a 10,9% em 2024.'}]})

# tema com aspas e HTML no meio: se escapar mal, o onclick do card quebra ou executa
TEMAS=json.dumps({'temas':[
 {'tema':'Os limites do "piso" da enfermagem <script>alert(1)</script> no SUS',
  'recorte':'Financiamento municipal, nao a categoria em geral',
  'gancho':'Novo repasse aprovado (FONTE 1); faltam 30 mil profissionais (FONTE 1)',
  'aspectos':['Financiamento','Rotatividade','Qualidade do cuidado'],
  'contraponto':'O custo recai sobre municipios pequenos',
  'fontes':[1]},
 {'tema':'Envelhecimento populacional e a atencao primaria',
  'recorte':'Rede de cuidado, nao previdencia','gancho':'10,9% com 65+ em 2024 (FONTE 2)',
  'aspectos':['Cronicidade','Cuidador familiar'],'contraponto':'Bonus demografico ainda existe','fontes':[2]}]})

def gem_resp(txt):
    return json.dumps({'candidates':[{'content':{'parts':[{'text':txt}]},'finishReason':'STOP'}]})

async def main():
    async with async_playwright() as p:
        buscas=[]; prompts=[]
        async def tav(route, request):
            buscas.append(json.loads(request.post_data or '{}'))
            await route.fulfill(status=200, content_type='application/json', body=TAV)
        async def gem(route, request):
            prompts.append(request.post_data or '')
            await route.fulfill(status=200, content_type='application/json', body=gem_resp(TEMAS))
        browser,page,errors=await setup_page(p, seed())
        try:
            await page.route('**api.tavily.com/search**', tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
            await page.evaluate("() => showScreen('repertorio')")
            await page.wait_for_timeout(400)

            # --- 1) o botao existe na barra lateral ---
            tem=await page.evaluate("""() => !!document.querySelector('[onclick="redAbrirTemasAtualidade()"]')""")
            print('1) botão "Temas em pauta" na barra lateral:', tem)
            assert tem

            # --- 2) abre o formulario com o eixo do usuario ---
            await page.evaluate("() => redAbrirTemasAtualidade()")
            await page.wait_for_timeout(250)
            f=await page.evaluate("""() => ({eixos:[...document.querySelectorAll('#red-tema-eixo option')].map(o=>o.textContent.trim()),
                dias:document.getElementById('red-tema-dias').value, qtd:document.getElementById('red-tema-qtd').value})""")
            print('2) formulário:', f)
            assert '⚕️ Saúde Pública e SUS' in f['eixos'][0]

            # --- 3) gera ---
            await page.evaluate("() => { document.getElementById('red-tema-dias').value='30';"
                                "document.getElementById('red-tema-foco').value='enfermagem'; }")
            await page.evaluate("() => redGerarTemasAtualidade()")
            await page.wait_for_timeout(2500)

            print('3) buscas no Tavily:', len(buscas))
            for b in buscas:
                print('   query:', b.get('query'), '| topic:', b.get('topic'), '| days:', b.get('days'),
                      '| domínios:', len(b.get('include_domains') or []))
            assert len(buscas)==3, buscas
            assert all(b.get('topic')=='news' for b in buscas), 'busca não foi em modo notícia'
            assert all(b.get('days')==30 for b in buscas), 'janela de dias não chegou no Tavily'
            assert all('enfermagem' in b['query'] for b in buscas), 'o foco não entrou nas consultas'
            assert (buscas[0].get('include_domains') or []), '1ª rodada devia ser restrita a fontes boas'
            assert not (buscas[1].get('include_domains') or []), '2ª rodada devia ser aberta'

            pr=prompts[0]
            print('4) prompt: pediu pra não repetir o tema que já existe?',
                  'Judicialização da Saúde' in pr)
            assert 'Judicialização da Saúde' in pr, 'não passou os temas já existentes'
            assert 'MATERIAL PESQUISADO NA INTERNET AGORA' in pr, 'o material pesquisado não foi amarrado ao prompt'
            assert 'piso da enfermagem' in pr, 'o texto das notícias não chegou no prompt'

            # --- 5) os cards renderizam, com o HTML do tema NEUTRALIZADO ---
            r=await page.evaluate("""() => ({
                titulo:(document.getElementById('modal-title')||{}).textContent||'',
                n:document.querySelectorAll('[onclick^="redCriarTemaSugerido"]').length,
                temScript:!!document.querySelector('#modal-body script'),
                texto:(document.getElementById('modal-body')||{}).textContent||'',
                salvos:(db.temasAtualidade||{}).itens?db.temasAtualidade.itens.length:0,
                grounded:(db.temasAtualidade||{}).grounded})""")
            print('5) modal:', repr(r['titulo'].strip()), '| botões de criar:', r['n'],
                  '| salvos no banco:', r['salvos'], '| grounded:', r['grounded'])
            assert r['salvos']==2 and r['grounded'] is True
            assert not r['temScript'], 'o <script> vindo da IA foi injetado no DOM'
            assert '<script>alert(1)</script>' in r['texto'], 'o tema devia aparecer como TEXTO literal'
            assert 'Novo repasse aprovado' in r['texto'], 'o gancho não apareceu'
            assert 'Agência Brasil' in r['texto'], 'a fonte não apareceu'

            # --- 6) criar tema no repertorio leva recorte/gancho junto ---
            await page.evaluate("() => redCriarTemaSugerido(0,false)")
            await page.wait_for_timeout(500)
            t=await page.evaluate("""() => {const v=Object.values(db.repertorio.temas)
                .filter(t=>t.id!=='rep_ja'); const n=v[v.length-1];
                return {nome:n.nome, eixo:n.eixoId, ctx:n.contextoAtualidade||null,
                        panorama:n.panorama||''};}""")
            print('6) tema criado:', repr(t['nome'][:50]), '| eixo:', t['eixo'])
            print('   contexto guardado:', repr((t['ctx'] or {}).get('recorte','')[:60]))
            assert t['eixo']=='saude'
            # o recorte fica num campo proprio, FORA das secoes: dentro do panorama
            # ele fazia a geracao achar que o tema ja tinha conteudo e parar
            assert t['ctx'] and t['ctx']['recorte'] and t['ctx']['gancho']
            assert not t['panorama'], 'o contexto voltou pra dentro de uma seção'
            assert t['ctx']['fontes'], 'as fontes do tema não foram guardadas' 

            # --- 7) "escrever sobre ele" cria o topico em Minhas Redacoes ---
            await page.evaluate("() => redRenderTemasSugeridos()")
            await page.wait_for_timeout(200)
            await page.evaluate("() => redCriarTopicoRedacao(1)")
            await page.wait_for_timeout(500)
            top=await page.evaluate("""() => ({nomes:Object.values(db.redacoes.topics||{}).map(t=>t.name),
                tela:(document.querySelector('.screen.active')||{}).id})""")
            print('7) tópicos em Minhas Redações:', top['nomes'], '| tela:', top['tela'])
            assert any('Envelhecimento' in n for n in top['nomes'])
            assert top['tela']=='screen-redacoes'

            errs=real_errors(errors)
            assert not errs, errs
            print('\nTODOS OS 7 TESTES DE TEMAS DA ATUALIDADE PASSARAM')
        finally:
            await browser.close()

asyncio.run(main())
