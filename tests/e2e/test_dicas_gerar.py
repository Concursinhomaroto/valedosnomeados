# -*- coding: utf-8 -*-
# Dicas, etapa 5: gerar dicas com a IA a partir do resumo do miniboss e das questoes reais
# do Acervo daquele assunto, com a chave da propria pessoa (callGeminiJSON, sem busca na
# web). Entram como origem "ia" e RASCUNHO — fora da lista, da correcao e da colinha ate
# serem aprovadas — e a dica que cita lei/artigo que nao esta no material e recusada, com
# o motivo no relatorio. A IA e simulada pela rota do generateContent, como nos outros testes.
import asyncio, json, os, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, make_seed
from test_aba_dicas import abrir, graves, nuvem, PACOTE, OUT

RESUMO=('Crase é a fusão da preposição "a" com o artigo "a". Antes de hora determinada há crase: às 14h. '
        'Depois de "desde" não há crase. Para o teste, o material cita o art. 5º do manual de redação.')

def q(i):
    return {'questao':'Item %d: "O portão abre desde às 7h" está correto.'%i,'formato':'certoerrado','correta':'E',
            'alternativas':[{'letra':'C','texto':'Certo'},{'letra':'E','texto':'Errado'}],
            'explicacao':'Depois de desde não há crase.','subId':'sCrase','subName':'Crase','topicName':'Gramática',
            'kingdomId':'kPt','kingdomName':'Português','kingdomIcon':'📖','status':'ativa'}

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'kPt','name':'Português','icon':'📖','color':'#f472b6'}],
      'topics':{'kPt':[{'id':'tP','name':'Gramática','icon':'✏️','subtopics':[
        {'id':'sCrase','name':'Crase','priority':70,'studied':True,'resumo':{'texto':RESUMO}},
        {'id':'sReg','name':'Regência verbal','priority':70,'studied':True}]}]},
      'acervo':[q(1),q(2)]})

GERADAS=[
  {'tipo':'dica','titulo':'Crase antes de hora exata','regra':'Hora exata leva artigo: às 14h.',
   'aplicar':'Troque por meio-dia: apareceu "ao", tem crase.','cuidado':'Depois de "desde" não há crase.',
   'exemplos':[{'txt':'A aula começa às 14h.','ok':True},{'txt':'Aberto desde às 7h.','ok':False}]},
  {'tipo':'numero','titulo':'Hora no exemplo','valor':'14h','rotulo':'Hora usada no exemplo de crase'},
  {'tipo':'dica','titulo':'Regra com lei inventada','regra':'Segundo a Lei nº 8.112, a crase é obrigatória.','cuidado':'x'},
  {'tipo':'dica','titulo':'Regra do artigo do manual','regra':'Pelo art. 5º do manual de redação, use crase antes de hora.','cuidado':'y'},
  {'tipo':'dica','titulo':'Crase antes de horas','regra':'Repetida do pacote.','cuidado':'z'},
  {'tipo':'dica','titulo':'Sem conteúdo nenhum'},
  {'tipo':'par','titulo':'À × a','a':'à','b':'a','diferenca':'"À" é preposição + artigo; "a" sozinho é só um deles.',
   'exemplos':[{'txt':'Vou à escola.','ok':True}]},
]
RESP=json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(GERADAS,ensure_ascii=False)}]},'finishReason':'STOP'}]})

async def main():
    os.makedirs(OUT,exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(browser,seed(),viewport={'width':1440,'height':900})
        pedidos=[]
        async def gem(route,request):
            pedidos.append(request.post_data or '')
            await route.fulfill(status=200,content_type='application/json',body=RESP)
        await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**',gem)
        await page.evaluate("(t)=>{dicasImportarProcessar(t);dicasRelatorioFechar();openKingdom(db.kingdoms[0]);}",open(PACOTE,encoding='utf-8').read())

        print('=== 0) citacoes de norma reconhecidas ===')
        r=await page.evaluate("()=>[...dicasNormasCitadas('Lei nº 8.080/90, Lei n. 8080, art. 5º, Art. 37, NR-32, Súmula Vinculante 13, RDC 222, Decreto 7.508 e a parte 3')].sort()")
        print('   %s'%r)
        assert r==['art 37','art 5','decreto 7508','lei 8080','nr 32','rdc 222','sumula vinculante 13'], r
        print('   OK\n')

        print('=== A) sem chave, ou sem material: nada vai pra IA ===')
        r=await page.evaluate("""async()=>{window.__toasts=[];db.geminiApiKey='';
          await dicasGerarIA('sCrase');
          const semChave={toast:window.__toasts.slice(-1)[0],modal:document.getElementById('modal').classList.contains('open')};
          closeModal();db.geminiApiKey='CHAVE-DE-TESTE';
          await dicasGerarIA('sReg');
          return {semChave,semMaterial:window.__toasts.slice(-1)[0]};}""")
        print('   sem chave: "%s" · abre a configuração da IA: %s'%(r['semChave']['toast'],r['semChave']['modal']))
        print('   sem resumo nem questões: "%s"'%r['semMaterial'][:90])
        assert 'chave' in r['semChave']['toast'] and r['semChave']['modal'] and 'resumo nem questões' in r['semMaterial']
        assert not pedidos
        print('   OK\n')

        print('=== B) gerar a partir do resumo + questoes do Acervo ===')
        await page.evaluate("()=>{toggleDicasSub('sCrase');}")
        await page.evaluate("()=>document.querySelector('#dicas-sub-sCrase .dicas-sub-acoes .btn-purple-s').click()")
        await page.wait_for_function("()=>!dicasGerando.has('sCrase')&&dicasGerarRelatorio['sCrase']",timeout=20000)
        pedido=json.loads(pedidos[0]); texto=json.dumps(pedido,ensure_ascii=False)
        print('   1 pedido · com o resumo: %s · com as questões: %s · com a trava de norma: %s · busca na web: %s'
              %('fusão da preposição' in texto,'O portão abre desde' in texto,'NÃO cite número de lei' in texto,'google_search' in texto))
        assert len(pedidos)==1 and 'fusão da preposição' in texto and 'O portão abre desde' in texto
        assert 'NÃO cite número de lei' in texto and 'google_search' not in texto and 'Crase antes de horas' in texto
        r=await page.evaluate("""()=>{
          const rasc=db.dicas.filter(d=>d.rascunho);
          const wrap=document.getElementById('dicas-sub-sCrase');
          return {rel:dicasGerarRelatorio['sCrase'],n:rasc.length,origens:[...new Set(rasc.map(d=>d.origem))],
                  fonte:rasc[0].fonte,grupo:rasc.find(d=>d.titulo==='Crase antes de hora exata').grupo,
                  titulos:rasc.map(d=>d.titulo),
                  painelRasc:wrap.querySelectorAll('.dica-card.dica-rascunho').length,
                  aprovar:wrap.querySelectorAll('.dica-btn-aprovar').length,
                  recusasTela:wrap.querySelector('.dicas-ia-recusas').innerText,
                  botao:document.getElementById('dicas-sub-btn-sCrase').textContent.trim()};}""")
        print('   %s rascunhos (%s) · origem %s · fonte "%s" · grupo padrão "%s"'
              %(r['n'],r['titulos'],r['origens'],r['fonte'],r['grupo']))
        for x in r['rel']['recusadas']: print('   recusada: %s'%x)
        print('   painel: %s rascunhos com "Aprovar" · botão "%s"'%(r['painelRasc'],r['botao']))
        assert r['n']==4 and r['origens']==['ia'] and r['fonte']=='IA · resumo + 2 questões do Acervo' and r['grupo']=='Gramática'
        assert sorted(r['titulos'])==sorted(['Crase antes de hora exata','Hora no exemplo','Regra do artigo do manual','À × a'])
        motivos=' | '.join(x['motivo'] for x in r['rel']['recusadas'])
        assert len(r['rel']['recusadas'])==3 and 'cita lei 8112, que não está no material' in motivos
        assert 'já existe' in motivos and 'sem regra' in motivos
        assert r['painelRasc']==4 and r['aprovar']==4 and 'lei 8112' in r['recusasTela'] and r['botao']=='💡 Dicas (1) · 📝4'
        print('   OK\n')

        print('=== C) rascunho fica fora de tudo ate aprovar ===')
        r=await page.evaluate("""()=>{
          showScreen('dicas');
          const naLista=()=>[...document.querySelectorAll('#dicas-corpo .dica-titulo')].map(x=>x.textContent);
          const div=document.createElement('div');div.innerHTML=dicasNaCorrecaoHTML('sCrase',{questao:'hora exata crase'});
          const corr=[...div.querySelectorAll('.dica-corr-tit')].map(x=>x.textContent);
          const col=new DOMParser().parseFromString(dicasColinhaHTML({escopo:'materia',kingdomId:'kPt',comSei:true}),'text/html');
          const colT=[...col.querySelectorAll('.t')].map(x=>x.textContent);
          const r={lista:naLista().includes('Crase antes de hora exata'),corr,col:colT.includes('Crase antes de hora exata'),
                   chip:[...document.querySelectorAll('#dicas-chips-mostrar .banco-chip')].map(b=>b.textContent.trim()).find(t=>/rascunhos/.test(t))};
          dicasAlternarRascunhos();
          r.soRasc=[...document.querySelectorAll('#dicas-corpo .dica-card')].map(c=>db.dicas.find(d=>'dica-'+d.id===c.id).titulo);
          return r;}""")
        print('   na lista padrão: %s · na correção: %s · na colinha: %s · chip "%s"'%(r['lista'],r['corr'],r['col'],r['chip']))
        print('   recorte de rascunhos: %s'%r['soRasc'])
        assert not r['lista'] and 'Crase antes de hora exata' not in r['corr'] and not r['col']
        assert r['chip']=='📝 rascunhos da IA · 4' and len(r['soRasc'])==4
        # editar um rascunho nao aprova; aprovar sim
        r=await page.evaluate("""()=>{
          const d=db.dicas.find(x=>x.titulo==='Regra do artigo do manual');
          dicaEditarAbrir(d.id);
          document.getElementById('dica-edit-cuidado').value='Cuidado revisado por mim.';
          dicaEditarSalvar(d.id);
          const editado=db.dicas.find(x=>x.id===d.id);
          const a=db.dicas.find(x=>x.titulo==='Crase antes de hora exata');
          document.querySelector('[id="dica-'+a.id+'"] .dica-btn-aprovar').click();
          const ap=db.dicas.find(x=>x.id===a.id);
          dicasFiltroLimpar();
          const div=document.createElement('div');div.innerHTML=dicasNaCorrecaoHTML('sCrase',{questao:'hora exata crase'});
          return {editadoContinuaRascunho:!!editado.rascunho,cuidado:editado.cuidado,aprovado:!ap.rascunho,
                  naLista:!!document.getElementById('dica-'+a.id),
                  naCorrecao:[...div.querySelectorAll('.dica-corr-tit')].map(x=>x.textContent).includes('Crase antes de hora exata')};}""")
        print('   editar um rascunho mantém rascunho: %s · aprovado entra na lista: %s e na correção: %s'
              %(r['editadoContinuaRascunho'],r['naLista'],r['naCorrecao']))
        assert r['editadoContinuaRascunho'] and r['cuidado']=='Cuidado revisado por mim.' and r['aprovado'] and r['naLista'] and r['naCorrecao']
        # editar uma dica vinda de erro preserva a ligacao com a questao (correcao da etapa 2)
        r=await page.evaluate("""()=>{
          const d=dicaNormalizar({tipo:'dica',kingdomId:'kPt',subId:'sCrase',titulo:'Veio de um erro',cuidado:'c',origem:'erro',deQuestao:'certoerrado|abc-1'});
          db.dicas.push(d);renderDicasScreen();
          dicaEditarAbrir(d.id);document.getElementById('dica-edit-regra').value='regra nova';dicaEditarSalvar(d.id);
          return db.dicas.find(x=>x.id===d.id).deQuestao;}""")
        print('   editar dica nascida de erro mantém deQuestao: %s'%(r=='certoerrado|abc-1'))
        assert r=='certoerrado|abc-1'
        # descartar
        r=await page.evaluate("""()=>{dicasAlternarRascunhos();
          const d=db.dicas.find(x=>x.titulo==='Hora no exemplo');
          document.querySelector('[id="dica-'+d.id+'"] .dica-btn-descartar').click();
          return {existe:db.dicas.some(x=>x.id===d.id),lapide:!!dicasLapides[d.id],restam:db.dicas.filter(x=>x.rascunho).length};}""")
        print('   descartar: sumiu %s · lápide %s · restam %s rascunhos'%(not r['existe'],r['lapide'],r['restam']))
        assert not r['existe'] and r['lapide'] and r['restam']==2
        print('   OK\n')

        print('=== D) rascunho sobrevive a recarregar ===')
        await page.wait_for_timeout(1900)
        salvo=await nuvem(page)
        await page.close()
        _,page,errs2=await abrir(browser,salvo['v1'],salvo['dicas'],ctx=ctx,viewport={'width':1440,'height':900})
        r=await page.evaluate("()=>db.dicas.filter(d=>d.rascunho).map(d=>d.titulo).sort()")
        print('   rascunhos depois de recarregar: %s'%r)
        assert r==['Regra do artigo do manual','À × a']
        await page.evaluate("()=>{openKingdom(db.kingdoms[0]);if(document.getElementById('tb-tP').style.display==='none')toggleTopic('tP');toggleDicasSub('sCrase');document.getElementById('dicas-sub-sCrase').scrollIntoView();}")
        await page.wait_for_timeout(3500)
        await page.screenshot(path=os.path.join(OUT,'dicas_rascunhos_1440.png'))
        print('   OK\n')

        todos=graves(errs)+graves(errs2)
        print('erros de JS: %s'%(todos or 'nenhum'))
        assert not todos, todos
        await browser.close()
        print('OK')

if __name__=='__main__':
    asyncio.run(main())
