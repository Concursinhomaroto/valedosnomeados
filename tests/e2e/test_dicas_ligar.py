# -*- coding: utf-8 -*-
# Dicas: "Ligar ao assunto" em lote. Um arquivo grande importado deixa muita dica so com a
# materia; ligar uma a uma, escolhendo o miniboss so da mesma materia, nao da conta. Aqui:
# cada linha ja vem com sugestao (apelido, nome, conteudo das dicas — nessa ordem, primeiro
# na mesma materia, depois em todas), a IA preenche as linhas sem sugestao (so com ids do
# mapa), a escolha manual nao e sobrescrita, e "Ligar todas" aplica tudo — levando a dica
# pra outra materia quando o miniboss escolhido e de la, menos a que repetiria titulo.
import asyncio, json, os, re, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, make_seed
from test_aba_dicas import abrir, graves, OUT

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'kEnf','name':'Enfermagem','icon':'💉','color':'#22d3ee'},
                  {'id':'kSus','name':'SUS','icon':'🏥','color':'#a3e635'}],
      'topics':{'kEnf':[{'id':'tD','name':'Doenças transmissíveis','icon':'🦠','subtopics':[
                    {'id':'sNot','name':'Doenças de notificação compulsória','priority':70,'studied':True},
                    {'id':'sTb','name':'Tuberculose','priority':70,'studied':True}]},
                  {'id':'tU','name':'Urgência','icon':'🚑','subtopics':[
                    {'id':'sPcr','name':'Parada cardiorrespiratória','priority':70,'studied':True}]},
                  {'id':'tI','name':'Imunização','icon':'💉','subtopics':[
                    {'id':'sImu','name':'Imunização','priority':70,'studied':True}]}],
                'kSus':[{'id':'tS','name':'Políticas','icon':'🏥','subtopics':[
                    {'id':'sCs','name':'Controle social','priority':70,'studied':True},
                    {'id':'sAb','name':'Atenção básica','priority':70,'studied':True}]}]},
      'geminiApiKey':'CHAVE-DE-TESTE'})

def n(assunto,grupo,titulo,valor):
    return {'tipo':'numero','materia':'Enfermagem','assunto':assunto,'grupo':grupo,'titulo':titulo,'valor':valor,'rotulo':titulo}

ARQUIVO=[
  n('Imunização','Imunização e rede de frio','Rotavírus: número de doses','2 doses'),                 # liga ja na importacao
  n('Botulismo','Doenças transmissíveis e notificação','Botulismo: notificação compulsória','imediata'),  # sugestao pelo conteudo
  n('PCR','Urgência e emergência','Epinefrina na PCR','1 mg a cada 3 a 5 min'),                     # so a IA acha
  n('PCR','Urgência e emergência','Amiodarona na PCR','300 mg'),
  n('Controle social','SUS e políticas','Composição do conselho','50% usuários'),                  # nome, em outra materia
  n('Controle social','SUS e políticas','Conselho: paridade','50%'),                               # titulo ja existe no SUS
  n('Ortografia','Português','Assunto que nao existe','—'),                                        # ninguem acha
  n('Sintomático','Doenças transmissíveis e notificação','Sintomático respiratório','3 semanas'),  # escolha manual
]

async def main():
    os.makedirs(OUT,exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(browser,seed(),viewport={'width':1440,'height':900})
        pedidos=[]
        async def gem(route,request):
            texto=json.loads(request.post_data)['contents'][0]['parts'][0]['text']
            pedidos.append(texto)
            g=lambda nome:int(re.search(r'(\d+)\. assunto escrito: "%s"'%nome,texto).group(1))
            resp=[{'g':g('PCR'),'id':'sPcr'},{'g':g('Ortografia'),'id':'id-que-nao-existe'}]
            if re.search(r'\d+\. assunto escrito: "Sintomático"',texto): resp.append({'g':g('Sintomático'),'id':'sImu'})
            await route.fulfill(status=200,content_type='application/json',body=json.dumps(
                {'candidates':[{'content':{'parts':[{'text':json.dumps(resp)}]},'finishReason':'STOP'}]}))
        await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**',gem)

        # uma dica que ja existe no SUS com o titulo de uma das que vao mudar de materia
        await page.evaluate("""(t)=>{db.dicas.push(dicaNormalizar({tipo:'numero',titulo:'Conselho: paridade',valor:'50%',kingdomId:'kSus',subId:'sAb'}));
          showScreen('dicas');dicasImportarProcessar(t);dicasRelatorioFechar();}""",json.dumps(ARQUIVO,ensure_ascii=False))

        print('=== A) importacao: so o que casa pelo nome na mesma materia ja entra ligado ===')
        r=await page.evaluate("()=>db.dicas.filter(d=>d.kingdomId==='kEnf').map(d=>d.titulo+'='+(d.subId||''))")
        print('   %s'%r)
        assert 'Rotavírus: número de doses=sImu' in r and sum(1 for x in r if x.endswith('='))==7
        print('   OK\n')

        print('=== B) cada linha ja vem com sugestao, e diz de onde ela veio ===')
        await page.evaluate("()=>dicasVerSemAssunto()")
        def linhas():
            return page.evaluate("""()=>dicasResolverGrupos.map((g,i)=>{const l=document.getElementById('dicas-ligar-'+i).closest('.dicas-ligar-linha');
              return {nome:g.nome,n:g.ids.length,sub:document.getElementById('dicas-ligar-'+i).value,
                      via:(l.querySelector('.dicas-ligar-via')||{}).textContent||''};})""")
        L={x['nome']:x for x in await linhas()}
        for k,v in L.items(): print('   %-16s %s dica(s) → %-6s %s'%(k,v['n'],v['sub'] or '—',v['via']))
        assert L['Botulismo']['sub']=='sNot' and 'conteúdo' in L['Botulismo']['via']
        assert L['Controle social']['sub']=='sCs' and 'pelo nome' in L['Controle social']['via'] and L['Controle social']['n']==2
        # o grupo das dicas tem o nome de um boss: sugere o boss inteiro, e a IA ainda pode refinar
        assert L['PCR']['sub']=='boss:tU' and 'grupo' in L['PCR']['via'] and L['Sintomático']['sub']=='boss:tD'
        assert L['Ortografia']['sub']==''
        botoes=await page.evaluate("()=>[...document.querySelectorAll('.dicas-ligar-acoes button')].map(b=>b.textContent.trim())")
        print('   botões: %s'%botoes)
        assert botoes==['Ligar todas as escolhidas (4)','🤖 Sugerir com IA (3 linhas)']
        # o select oferece miniboss de todas as materias, a da dica primeiro
        grupos=await page.evaluate("()=>[...document.querySelectorAll('#dicas-ligar-0 optgroup')].map(o=>o.label)")
        print('   opções: %s'%grupos)
        assert grupos[-1].startswith('SUS') and all(x.startswith('Enfermagem') for x in grupos[:-1])
        print('   OK\n')

        print('=== C) escolha manual fica, e a IA preenche so o resto, so com ids do mapa ===')
        await page.evaluate("()=>{const i=dicasResolverGrupos.findIndex(g=>g.nome==='Sintomático');const el=document.getElementById('dicas-ligar-'+i);el.value='sTb';el.dispatchEvent(new Event('change'));}")
        await page.click('#dicas-ligar-ia')
        await page.wait_for_timeout(800)
        L={x['nome']:x for x in await linhas()}
        for k,v in L.items(): print('   %-16s → %-6s %s'%(k,v['sub'] or '—',v['via']))
        assert len(pedidos)==1
        assert 'Sintomático' not in pedidos[0] and 'Botulismo' not in pedidos[0]        # so as linhas sem sugestao vao pra IA
        assert 'sPcr = Enfermagem › Urgência › Parada cardiorrespiratória' in pedidos[0]
        assert L['PCR']['sub']=='sPcr' and 'IA' in L['PCR']['via']
        assert L['Ortografia']['sub']==''                                                 # id inventado: ignorado
        assert L['Sintomático']['sub']=='sTb' and 'você' in L['Sintomático']['via']
        print('   OK\n')

        print('=== D) "Ligar todas": liga, muda de materia quando precisa, e nao duplica titulo ===')
        await page.click('#dicas-ligar-todas')
        await page.wait_for_timeout(200)
        r=await page.evaluate("""()=>({ds:db.dicas.map(d=>({t:d.titulo,k:d.kingdomId,s:d.subId||'',an:d.assuntoNome||''})),
          toast:window.__toasts.slice(-1)[0],apelidos:db.simColarApelidos||{},
          restam:dicasResolverGrupos.map(g=>g.nome+':'+g.ids.length)})""")
        D={(x['t'],x['k']):x for x in r['ds']}
        print('   %s'%r['toast'])
        print('   restam sem assunto: %s'%r['restam'])
        assert D[('Botulismo: notificação compulsória','kEnf')]['s']=='sNot'
        assert D[('Epinefrina na PCR','kEnf')]['s']=='sPcr' and D[('Amiodarona na PCR','kEnf')]['s']=='sPcr'
        assert D[('Composição do conselho','kSus')]['s']=='sCs'                          # foi pra materia do miniboss
        assert D[('Conselho: paridade','kEnf')]['s']=='' and D[('Conselho: paridade','kSus')]['s']=='sAb'  # ficou: titulo repetido
        assert D[('Sintomático respiratório','kEnf')]['s']=='sTb' and not D[('Sintomático respiratório','kEnf')]['an']
        assert '5 dicas ligadas em 4 assuntos' in r['toast'] and '1 ficou onde estava' in r['toast']
        assert sorted(r['restam'])==['Controle social:1','Ortografia:1']
        assert r['apelidos'].get('pcr')=='sPcr' and r['apelidos'].get('botulismo')=='sNot'
        print('   OK\n')

        print('=== E) sobrevive a recarregar ===')
        await page.wait_for_timeout(1900)
        salvo=await page.evaluate("()=>JSON.parse(JSON.stringify({v1:window.__root.users.TEST_UID_LEO.vdn_v1,dicas:window.__root.users.TEST_UID_LEO.vdn_dicas}))")
        await page.close()
        _,page,errs2=await abrir(browser,salvo['v1'],salvo['dicas'],ctx=ctx,viewport={'width':375,'height':812})
        r=await page.evaluate("()=>db.dicas.filter(d=>d.subId).length")
        print('   ligadas depois de recarregar: %s'%r)
        assert r==7      # as 5 + a do Rotavirus + a que ja estava no SUS
        print('   OK\n')

        print('=== F) 375 px, claro e escuro ===')
        await page.set_viewport_size({'width':375,'height':812})   # o contexto reaproveitado guarda o tamanho antigo
        await page.evaluate("()=>{showScreen('dicas');dicasVerSemAssunto();}")
        for tema in ['light','dark']:
            await page.evaluate("(t)=>document.documentElement.setAttribute('data-theme',t)",tema)
            await page.wait_for_timeout(200)
            m=await page.evaluate("""()=>({rolagem:document.documentElement.scrollWidth>window.innerWidth+1,
              vaza:[...document.querySelectorAll('#dicas-resolver *')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.right>window.innerWidth+1;}).length})""")
            print('   %-5s: rolagem lateral %s · vazando %s'%(tema,m['rolagem'],m['vaza']))
            assert not m['rolagem'] and m['vaza']==0, m
            await page.evaluate("()=>{['toast','sidebar','nav-principal'].forEach(id=>{const e=document.getElementById(id);if(e)e.style.visibility='hidden';});}")
            await page.locator('#dicas-resolver').screenshot(path=os.path.join(OUT,'dicas_ligar_375_%s.png'%('claro' if tema=='light' else 'escuro')))
            await page.evaluate("()=>{['toast','sidebar','nav-principal'].forEach(id=>{const e=document.getElementById(id);if(e)e.style.visibility='';});}")
        print('   OK\n')

        print('=== G) ligar ao BOSS inteiro: vale pra todos os minibosses dele ===')
        def qa(i,sub,vezes,acertos):
            return {'questao':'Item %d de vacina.'%i,'formato':'certoerrado','correta':'E',
                    'alternativas':[{'letra':'C','texto':'Certo'},{'letra':'E','texto':'Errado'}],'explicacao':'x',
                    'subId':sub,'subName':sub,'topicName':'Vacinação','kingdomId':'kEnf','kingdomName':'Enfermagem',
                    'kingdomIcon':'💉','status':'ativa','vezesRespondida':vezes,'acertos':acertos,'erros':vezes-acertos}
        seed3=make_seed({'studyNickname':'Leo',
          'kingdoms':[{'id':'kEnf','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
          'topics':{'kEnf':[{'id':'tVac','name':'Vacinação','icon':'💉','subtopics':[
                        {'id':'vBcg','name':'BCG','priority':70,'studied':True},{'id':'vHpv','name':'HPV','priority':70,'studied':True}]},
                      {'id':'tUrg','name':'Urgência e emergência','icon':'🚑','subtopics':[
                        {'id':'uPcr','name':'Parada cardiorrespiratória','priority':70,'studied':True}]}]},
          'acervo':[qa(1,'vBcg',2,1),qa(2,'vHpv',1,1)]})
        ctx3,pg3,errs3=await abrir(browser,seed3,viewport={'width':1440,'height':900})
        await pg3.evaluate("(t)=>{showScreen('dicas');dicasImportarProcessar(t);dicasRelatorioFechar();}",json.dumps([
          n('Imunização','Imunização e rede de frio','BCG sem cicatriz','não revacinar'),
          n('Imunização','Imunização e rede de frio','HPV no calendário','9 a 14 anos'),
          n('Vacinação','Imunização e rede de frio','Influenza: volume','0,5 ml'),
          n('PCR','Urgência e emergência','Epinefrina na PCR','1 mg'),
        ],ensure_ascii=False))
        r=await pg3.evaluate("()=>db.dicas.map(d=>d.titulo+'|'+(d.subId||'')+'|'+(d.topicId||'')+'|'+(d.assuntoNome||''))")
        print('   importação: %s'%r)
        assert 'Influenza: volume||tVac|' in r                       # assunto com o nome do boss liga no boss
        await pg3.evaluate("()=>dicasVerSemAssunto()")
        r=await pg3.evaluate("""()=>{const ix=n=>dicasResolverGrupos.findIndex(g=>g.nome===n);
          const sel=n=>document.getElementById('dicas-ligar-'+ix(n));
          return {pcr:sel('PCR').value,via:sel('PCR').closest('.dicas-ligar-linha').querySelector('.dicas-ligar-via').textContent,
                  opBoss:[...sel('Imunização').options].filter(o=>o.value.startsWith('boss:')).map(o=>o.value+'='+o.textContent)};}""")
        print('   PCR sugere %s (%s) · opções de boss: %s'%(r['pcr'],r['via'],r['opBoss']))
        assert r['pcr']=='boss:tUrg' and 'grupo' in r['via']                    # pelo grupo das dicas
        assert 'boss:tVac=👑 Boss inteiro: Vacinação' in r['opBoss']
        await pg3.evaluate("""()=>{const i=dicasResolverGrupos.findIndex(g=>g.nome==='Imunização');const el=document.getElementById('dicas-ligar-'+i);
          el.value='boss:tVac';el.dispatchEvent(new Event('change'));dicasLigarTodas();}""")
        r=await pg3.evaluate("""()=>({ds:db.dicas.map(d=>d.titulo+'|'+(d.subId||'')+'|'+(d.topicId||'')),toast:window.__toasts.slice(-1)[0],
          bcg:dicasDoAssunto('vBcg').map(d=>d.titulo).sort(),pcr:dicasDoAssunto('uPcr').map(d=>d.titulo),
          apelidos:Object.keys(db.simColarApelidos||{})})""")
        print('   %s'%r['toast'])
        print('   no miniboss BCG: %s'%r['bcg'])
        assert all(x.endswith('|tVac') for x in r['ds'] if not x.startswith('Epinefrina')) and 'Epinefrina na PCR||tUrg' in r['ds']
        assert r['bcg']==['BCG sem cicatriz','HPV no calendário','Influenza: volume'] and r['pcr']==['Epinefrina na PCR']
        assert r['apelidos']==[]                                                  # apelido e so pra miniboss
        # etiqueta, filtro do boss, Acervo somado e treino do boss
        await pg3.evaluate("()=>dicasFiltroLimpar()")
        r=await pg3.evaluate("""()=>{const d=db.dicas.find(x=>x.titulo==='BCG sem cicatriz');const card=document.getElementById('dica-'+d.id);
          return {etq:card.querySelector('.dica-etq-boss').textContent,treino:card.querySelector('.dica-treino').innerText.replace(/\s+/g,' ').trim()};}""")
        print('   cartão: etiqueta "%s" · %s'%(r['etq'],r['treino']))
        assert r['etq']=='👑 Vacinação' and r['treino'].startswith('📚 2 questões no Acervo · você acerta 67% (2 de 3')
        await pg3.click('.dica-etq-boss >> nth=0')
        r=await pg3.evaluate("()=>({n:dicasAplicarFiltros().length,chip:document.getElementById('dicas-chips-assunto').innerText})")
        print('   filtro do boss: %s dicas · chip "%s"'%(r['n'],r['chip'].replace(chr(10),' ')))
        assert r['n']==3 and 'Vacinação (boss inteiro)' in r['chip']
        r=await pg3.evaluate("""()=>{dicaTreinarBoss('tVac');return {titulo:treinoSessao&&treinoSessao.titulo,
          subs:treinoSessao?[...new Set(treinoSessao.itens.map(i=>i.subId))].sort():[]};}""")
        print('   treinar o boss: %s'%r)
        assert r['titulo']=='Vacinação' and r['subs']==['vBcg','vHpv']
        # editar mantem o boss; o pacote leva o nome do boss
        r=await pg3.evaluate("""()=>{treinoSessao=null;treinoResumo=null;treinoTempoParar();showScreen('dicas');dicasFiltroLimpar();
          const d=db.dicas.find(x=>x.titulo==='HPV no calendário');dicaEditarAbrir(d.id);
          const sel=document.getElementById('dica-edit-assunto').value;dicaEditarSalvar(d.id);
          const depois=db.dicas.find(x=>x.titulo==='HPV no calendário');
          return {sel,topicId:depois.topicId,subId:depois.subId||'',pacote:dicaParaPacote(depois,'pk').assunto};}""")
        print('   editar: seletor %s → %s · pacote leva "%s"'%(r['sel'],r['topicId'],r['pacote']))
        assert r['sel']=='boss:tVac' and r['topicId']=='tVac' and r['subId']=='' and r['pacote']=='Vacinação'
        # correção de uma questão do miniboss traz as dicas do boss
        r=await pg3.evaluate("()=>{const h=dicasNaCorrecaoHTML('vBcg',{questao:'BCG sem cicatriz deve ser revacinado.'});return h.includes('BCG sem cicatriz');}")
        assert r
        print('   OK\n')

        todos=graves(errs)+graves(errs2)+graves(errs3)
        print('erros de JS: %s'%(todos or 'nenhum'))
        assert not todos, todos
        await browser.close()
        print('OK')

if __name__=='__main__':
    asyncio.run(main())
