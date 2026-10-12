# -*- coding: utf-8 -*-
# Dicas, etapa 6: pacotes publicados. O admin publica dicas num no compartilhado
# (dicas_pacotes: le quem esta logado, grava so o admin — a regra do sala_mapa) e cada
# assinante adiciona a sua lista. Materia e assunto vao por NOME (cada conta tem ids
# proprios). Numa versao nova do pacote, a dica que o assinante nao mexeu e trocada; a que
# ele editou fica a dele; a que ele apagou nao volta; o "ja sei" e o assunto que ele ligou
# continuam. Sem as regras publicadas no Firebase, o painel diz o que falta em vez de
# parecer vazio. Admin e assinante sao dois navegadores, cada um com o seu Firebase mockado.
import asyncio, json, os, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, make_seed
from test_aba_dicas import abrir, graves, nuvem, seed, PACOTE, OUT

AQUI=os.path.dirname(os.path.abspath(__file__))
REGRAS=os.path.join(AQUI,'..','..','firebase.rules.json')

# Assinante: a mesma materia com OUTROS ids, e um assunto ("Grafia") que o pacote nao
# chama pelo nome — e o que ele liga a mao.
def seed_assinante():
    return make_seed({'studyNickname':'Ana','accountEmail':'ana@exemplo.com',
      'kingdoms':[{'id':'kLP','name':'Português','icon':'📖','color':'#f472b6'}],
      'topics':{'kLP':[{'id':'tX','name':'Gramática','icon':'✏️','subtopics':[
        {'id':'xCrase','name':'Crase','priority':70,'studied':True},
        {'id':'xReg','name':'Regência verbal','priority':70,'studied':True},
        {'id':'xCol','name':'Colocação pronominal','priority':70,'studied':True},
        {'id':'xOrt','name':'Grafia','priority':70,'studied':True}]}]}})

NEGADO="""()=>{
  const orig=firebaseDB.ref;
  const nega=()=>Promise.reject(Object.assign(new Error("permission_denied at /dicas_pacotes: Client doesn't have permission to access the desired data."),{code:'PERMISSION_DENIED'}));
  window.__refOriginal=orig;
  firebaseDB.ref=p=>String(p||'').startsWith('dicas_pacotes')?{once:nega,set:nega,remove:nega}:orig(p);
}"""

def por_titulo(t):
    return "db.dicas.find(d=>d.titulo===%s)"%json.dumps(t,ensure_ascii=False)

async def main():
    os.makedirs(OUT,exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')

        print('=== 0) regra do no compartilhado, igual a do sala_mapa ===')
        regras=json.load(open(REGRAS,encoding='utf-8'))['rules']
        print('   dicas_pacotes: %s'%regras['dicas_pacotes'])
        assert regras['dicas_pacotes']==regras['sala_mapa']
        assert regras['dicas_pacotes']['.read']=='auth != null'
        assert "auth.token.email === 'leonardobrunotlc@gmail.com'" in regras['dicas_pacotes']['.write']
        print('   OK\n')

        # A a J testam os pacotes publicados no Firebase; o pronto que vem com o site (K) sai
        # da lista aqui pra nao se misturar com eles.
        ctxA,adm,errsA=await abrir(browser,seed(),viewport={'width':1440,'height':900})
        await adm.evaluate("(t)=>{DICAS_PACOTES_PRONTOS.splice(0);dicasImportarProcessar(t);dicasRelatorioFechar();showScreen('dicas');}",open(PACOTE,encoding='utf-8').read())

        print('=== A) admin: painel vazio, com o formulario de publicar ===')
        await adm.click('#dicas-content button:has-text("Pacotes")')
        await adm.wait_for_timeout(200)
        r=await adm.evaluate("""()=>{const el=document.getElementById('dicas-pacotes');
          return {txt:el.innerText,form:!!document.getElementById('dicas-pacote-publicar'),
                  conta:document.getElementById('dicas-pub-conta').textContent.replace(/\\s+/g,' ')};}""")
        print('   "%s"'%r['conta'].strip()[:70])
        assert 'Nenhum pacote publicado ainda' in r['txt'] and r['form'] and 'as 25 dicas' in r['conta'], r

        # a contagem acompanha o filtro sem apagar o que ja foi digitado
        await adm.fill('#dicas-pub-nome','Português — 25 pontos')
        await adm.fill('#dicas-pub-desc','Os 25 pontos que mais caem.')
        r=await adm.evaluate("""()=>{dicasFiltrarGrupo('Colocação pronominal');
          const a=document.getElementById('dicas-pub-conta').textContent.replace(/\\s+/g,' ');
          dicasFiltrarGrupo('Colocação pronominal');
          return {comFiltro:a,semFiltro:document.getElementById('dicas-pub-conta').textContent.replace(/\\s+/g,' '),
                  nome:document.getElementById('dicas-pub-nome').value};}""")
        print('   filtro de grupo: "%s" · sem filtro: 25 · nome digitado ficou: %s'%(r['comFiltro'].strip()[:22],r['nome']))
        assert 'as 3 dicas' in r['comFiltro'] and 'as 25 dicas' in r['semFiltro'] and r['nome']=='Português — 25 pontos', r
        print('   OK\n')

        print('=== B) admin publica a v1 ===')
        await adm.click('#dicas-pub-btn')
        await adm.wait_for_timeout(400)
        r=await adm.evaluate("""()=>{const raiz=window.__root.dicas_pacotes||{};const ids=Object.keys(raiz);const pk=raiz[ids[0]];
          const linha=document.querySelector('#dicas-pacotes .dicas-pacote');
          return {ids,pk,linha:linha&&linha.innerText,
                  marcadas:db.dicas.filter(d=>d.pacote===ids[0]&&d.pacoteVersao===1&&d.pacoteEm===d.editadaEm).length,
                  idsItens:db.dicas.every(d=>pk.dicas.some(it=>it.id===d.pacoteItem))};}""")
        pk=r['pk']
        it7=[x for x in pk['dicas'] if x['titulo']=='Crase antes de horas'][0]
        print('   %s pacote · v%s · %s itens · "%s"'%(len(r['ids']),pk['versao'],len(pk['dicas']),pk['nome']))
        print('   item: %s'%{k:it7[k] for k in ['materia','assunto','grupo','tipo']})
        print('   linha no painel do admin: %s'%r['linha'].replace('\n',' | '))
        assert len(r['ids'])==1 and pk['versao']==1 and len(pk['dicas'])==25 and pk['nome']=='Português — 25 pontos'
        assert pk['descricao']=='Os 25 pontos que mais caem.'
        assert it7['materia']=='Português' and it7['assunto']=='Crase'
        assert all('kingdomId' not in x and 'subId' not in x and 'pacote' not in x for x in pk['dicas'])  # conteudo, nao ids da conta
        assert r['marcadas']==25 and r['idsItens'], r
        assert 'em dia (v1)' in r['linha'] and 'Remover' in r['linha']
        PID=r['ids'][0]
        print('   OK\n')

        ctxB,ana,errsB=await abrir(browser,seed_assinante(),viewport={'width':1440,'height':900})
        await ana.evaluate("(pk)=>{window.__root.dicas_pacotes=pk;currentUser={...currentUser,email:'ana@exemplo.com'};DICAS_PACOTES_PRONTOS.splice(0);showScreen('dicas');}",
                           await adm.evaluate("()=>window.__root.dicas_pacotes"))

        print('=== C) assinante: aba vazia mostra Pacotes; adiciona; nao ve publicar ===')
        r=await ana.evaluate("()=>[...document.querySelectorAll('#dicas-content button')].map(b=>b.textContent.trim())")
        print('   botões da aba vazia: %s'%r)
        assert 'Pacotes publicados' in r and not await ana.evaluate("()=>isAdmin()")
        await ana.click('#dicas-content button:has-text("Pacotes publicados")')
        await ana.wait_for_timeout(300)
        r=await ana.evaluate("""()=>({linha:document.querySelector('#dicas-pacotes .dicas-pacote').innerText,
                                     publicar:!!document.getElementById('dicas-pacote-publicar')})""")
        print('   linha: %s · formulário de publicar: %s'%(r['linha'].replace('\n',' | '),r['publicar']))
        assert 'Adicionar às minhas dicas' in r['linha'] and 'Remover' not in r['linha'] and not r['publicar']
        await ana.click('#dicas-pacotes button:has-text("Adicionar às minhas dicas")')
        await ana.wait_for_timeout(300)
        r=await ana.evaluate("""()=>({n:db.dicas.length,
          marcadas:db.dicas.filter(d=>d.pacote===%s&&d.pacoteVersao===1&&d.pacoteEm===d.editadaEm&&d.pacoteItem).length,
          crase:%s,reinos:[...new Set(db.dicas.map(d=>d.kingdomId))],
          rel:document.getElementById('dicas-relatorio').innerText,
          linha:document.querySelector('#dicas-pacotes .dicas-pacote').innerText,toast:window.__toasts.slice(-1)[0]})"""
          %(json.dumps(PID),por_titulo('Crase antes de horas')))
        print('   %s dicas · reinos %s · "Crase antes de horas" → %s · fonte "%s"'%(r['n'],r['reinos'],r['crase']['subId'],r['crase'].get('fonte')))
        print('   relatório: %s'%r['rel'].split('\n')[0])
        print('   toast: %s · linha agora: %s'%(r['toast'],r['linha'].split('\n')[-1]))
        assert r['n']==25 and r['marcadas']==25 and r['reinos']==['kLP'] and r['crase']['subId']=='xCrase'
        assert r['rel'].startswith('📦 Pacote "Português — 25 pontos"') and 'em dia (v1)' in r['linha']
        print('   OK\n')

        print('=== D) assinante: ja sei, edita, apaga e liga assunto ===')
        await ana.evaluate("()=>dicaJaSei(%s.id)"%por_titulo('Crase antes de horas'))
        idPref=await ana.evaluate("()=>{const d=%s;dicaEditarAbrir(d.id);return d.id;}"%por_titulo('Preferir'))
        await ana.wait_for_timeout(200)
        await ana.fill('#dica-edit-regra','MINHA REGRA: preferir uma coisa A outra, sem "do que".')
        await ana.click('#dica-edit-form button:has-text("Salvar")')
        await ana.evaluate("()=>dicaApagar(%s.id)"%por_titulo('Cujo'))
        # "Semântica" (2 dicas) nao casa com nenhum assunto da Ana: ela liga o grupo a "Grafia"
        r=await ana.evaluate("""()=>{dicasVerSemAssunto();
          const i=dicasResolverGrupos.findIndex(g=>g.nome==='Semântica');
          document.getElementById('dicas-ligar-'+i).value='xOrt';dicasLigarAssunto(i);dicasFiltroLimpar();
          const pq=%s,pref=%s;
          return {pq:{subId:pq.subId,intacta:pq.pacoteEm===pq.editadaEm},
                  pref:{regra:pref.regra,editada:pref.pacoteEm!==pref.editadaEm,pacote:pref.pacote,item:pref.pacoteItem,v:pref.pacoteVersao},
                  lapide:dicasLapidesPacote};}"""%(por_titulo('Homônimos × parônimos'),por_titulo('Preferir')))
        print('   ligada: %s · editada: %s · lápide do pacote: %s'%(r['pq'],r['pref']['editada'],list(r['lapide'].values())))
        assert r['pq']=={'subId':'xOrt','intacta':True}, r['pq']        # ligar assunto nao conta como editar
        assert r['pref']['regra'].startswith('MINHA REGRA') and r['pref']['editada'] and r['pref']['pacote']==PID and r['pref']['item'] and r['pref']['v']==1
        assert len(r['lapide'])==1 and list(r['lapide'].values())[0]['pacote']==PID
        print('   OK\n')

        print('=== E) admin publica a v2: muda 4 dicas e acrescenta 1 ===')
        await adm.evaluate("""()=>{const agora=dicasAgora();
          ['Crase antes de horas','Preferir','Cujo','Homônimos × parônimos'].forEach(t=>{const d=db.dicas.find(x=>x.titulo===t);d.regra='V2: '+d.regra;d.editadaEm=agora;});
          db.dicas.push(dicaNormalizar({tipo:'dica',titulo:'Mal × mau',kingdomId:'kPt',grupo:'Ortografia e sentido',
            regra:'Mal se opõe a bem; mau se opõe a bom.',origem:'minha'}));
          dicasRefrescar();}""")
        await adm.click('#dicas-content button:has-text("Pacotes")')
        await adm.wait_for_timeout(300)
        await adm.select_option('#dicas-pub-alvo',PID)
        await adm.click('#dicas-pub-btn')
        await adm.wait_for_timeout(400)
        r=await adm.evaluate("""(pid)=>{const raiz=window.__root.dicas_pacotes;
          return {ids:Object.keys(raiz),v:raiz[pid].versao,n:raiz[pid].dicas.length,nome:raiz[pid].nome,desc:raiz[pid].descricao,
                  linha:document.querySelector('#dicas-pacotes .dicas-pacote').innerText};}""",PID)
        v2=await adm.evaluate("(pid)=>window.__root.dicas_pacotes[pid]",PID)
        mesmos=len({x['id'] for x in v2['dicas']}&{x['id'] for x in pk['dicas']})
        print('   v%s · %s itens · %s ids de item iguais aos da v1 · nome/descrição mantidos: %s'%(r['v'],r['n'],mesmos,r['nome']==pk['nome'] and r['desc']==pk['descricao']))
        assert r['ids']==[PID] and r['v']==2 and r['n']==26 and mesmos==25
        assert r['nome']==pk['nome'] and r['desc']==pk['descricao'] and 'em dia (v2)' in r['linha']
        print('   OK\n')

        print('=== F) assinante atualiza para a v2 ===')
        await ana.evaluate("(pk)=>{window.__root.dicas_pacotes=pk;dicasPacotesCarregar();}",await adm.evaluate("()=>window.__root.dicas_pacotes"))
        await ana.wait_for_timeout(300)
        linha=await ana.evaluate("()=>document.querySelector('#dicas-pacotes .dicas-pacote').innerText")
        print('   linha: %s'%linha.replace('\n',' | '))
        assert 'Atualizar para a v2' in linha
        await ana.click('#dicas-pacotes button:has-text("Atualizar para a v2")')
        await ana.wait_for_timeout(300)
        r=await ana.evaluate("""()=>{const c=%s,pref=%s,pq=%s,mal=%s;
          return {n:db.dicas.length,crase:{regra:c.regra,sei:dicaSei(c.id),v:c.pacoteVersao},
                  pref:{regra:pref.regra,id:pref.id,v:pref.pacoteVersao},
                  pq:{regra:pq.regra,subId:pq.subId},mal:mal&&{materia:mal.kingdomId,pacote:!!mal.pacote},
                  cujo:db.dicas.some(d=>d.titulo==='Cujo'),
                  rel:document.getElementById('dicas-relatorio').innerText,
                  linha:document.querySelector('#dicas-pacotes .dicas-pacote').innerText,toast:window.__toasts.slice(-1)[0]};}"""
          %(por_titulo('Crase antes de horas'),por_titulo('Preferir'),por_titulo('Homônimos × parônimos'),por_titulo('Mal × mau')))
        print('   já sei:   %s'%r['crase'])
        print('   editada:  %s'%{'regra':r['pref']['regra'][:30],'v':r['pref']['v']})
        print('   ligada:   %s'%{'regra':r['pq']['regra'][:12],'subId':r['pq']['subId']})
        print('   nova: %s · "Cujo" voltou: %s · total %s'%(r['mal'],r['cujo'],r['n']))
        print('   toast: %s'%r['toast'])
        for l in r['rel'].split('\n')[:7]: print('   | '+l)
        assert r['crase']['regra'].startswith('V2:') and r['crase']['sei'] and r['crase']['v']==2
        assert r['pref']['regra'].startswith('MINHA REGRA') and r['pref']['id']==idPref and r['pref']['v']==2
        assert r['pq']['regra'].startswith('V2:') and r['pq']['subId']=='xOrt'
        assert r['mal']=={'materia':'kLP','pacote':True} and not r['cujo'] and r['n']==25
        rel=r['rel']
        assert '1 entrou' in rel and '2 atualizadas' in rel and '1 ficou como você editou' in rel
        assert '21 sem mudança' in rel and '1 que você tinha apagado ficou de fora' in rel
        assert 'em dia (v2)' in r['linha']
        print('   OK\n')

        print('=== G) tudo isso sobrevive a recarregar (lápide guarda o item do pacote) ===')
        await ana.wait_for_timeout(1900)
        salvo=await nuvem(ana)
        lap=[x for x in salvo['dicas'] if x.get('apagada')]
        print('   lápide na nuvem: %s'%{k:lap[0][k] for k in ['apagada','pacote'] if k in lap[0]})
        assert len(lap)==1 and lap[0]['pacote']==PID and lap[0]['pacoteItem']
        await ana.close()
        _,ana,errsB2=await abrir(browser,salvo['v1'],salvo['dicas'],ctx=ctxB,viewport={'width':1440,'height':900})
        await ana.evaluate("(pk)=>{window.__root.dicas_pacotes=pk;currentUser={...currentUser,email:'ana@exemplo.com'};DICAS_PACOTES_PRONTOS.splice(0);showScreen('dicas');dicasPacotesAbrir();}",
                           await adm.evaluate("()=>window.__root.dicas_pacotes"))
        await ana.wait_for_timeout(300)
        r=await ana.evaluate("""()=>{const pref=%s,c=%s;
          return {n:db.dicas.length,editada:pref.pacoteEm!==pref.editadaEm,sei:dicaSei(c.id),lap:Object.keys(dicasLapidesPacote).length,
                  linha:document.querySelector('#dicas-pacotes .dicas-pacote').innerText};}"""%(por_titulo('Preferir'),por_titulo('Crase antes de horas')))
        print('   %s'%r)
        assert r['n']==25 and r['editada'] and r['sei'] and r['lap']==1 and 'em dia (v2)' in r['linha']
        print('   OK\n')

        print('=== H) assinante nao publica nem remove, mesmo chamando a funcao ===')
        r=await ana.evaluate("""async(pid)=>{const antes=JSON.stringify(window.__root.dicas_pacotes);
          await dicasPacotePublicar();await dicasPacoteRemover(pid);
          return antes===JSON.stringify(window.__root.dicas_pacotes);}""",PID)
        print('   nó intacto: %s'%r)
        assert r
        print('   OK\n')

        print('=== I) regras ainda nao publicadas: o painel diz o que falta ===')
        await ana.evaluate(NEGADO)
        await ana.evaluate("()=>dicasPacotesCarregar()")
        await ana.wait_for_timeout(300)
        r=await ana.evaluate("()=>document.getElementById('dicas-pacotes').innerText")
        aviso=[l for l in r.split('\n') if 'regras' in l][0]
        print('   assinante: %s'%aviso)
        assert 'falta publicar as regras do Firebase' in aviso and 'dicas_pacotes' in aviso
        # sem internet o once do Firebase nunca responde: o painel desiste e diz, em vez de girar pra sempre
        await ana.evaluate("()=>{const o=window.__refOriginal;firebaseDB.ref=p=>String(p||'').startsWith('dicas_pacotes')?{once:()=>new Promise(()=>{})}:o(p);dicasPacotesCarregar();}")
        await ana.wait_for_timeout(500)
        girando=await ana.evaluate("()=>!!document.querySelector('#dicas-pacotes .fa-spinner')")
        await ana.wait_for_timeout(10000)
        r=await ana.evaluate("()=>({txt:document.getElementById('dicas-pacotes').innerText,gira:!!document.querySelector('#dicas-pacotes .fa-spinner')})")
        aviso=[l for l in r['txt'].split('\n') if 'servidor' in l][0]
        print('   sem resposta: girando antes %s · depois de 10 s: %s'%(girando,aviso))
        assert girando and not r['gira'] and 'o servidor não respondeu' in aviso
        await adm.evaluate(NEGADO)
        await adm.evaluate("()=>{dicasPacotesCarregar();}")
        await adm.wait_for_timeout(300)
        r=await adm.evaluate("""async()=>{const antes=db.dicas.map(d=>d.pacoteVersao+'|'+d.editadaEm).join();
          document.getElementById('dicas-pub-nome').value='Outro pacote';
          await dicasPacotePublicar();
          return {toast:window.__toasts.slice(-1)[0],intactas:antes===db.dicas.map(d=>d.pacoteVersao+'|'+d.editadaEm).join(),
                  form:!!document.getElementById('dicas-pacote-publicar')};}""")
        print('   admin publicando: %s · dicas sem marca nova: %s'%(r['toast'],r['intactas']))
        assert 'falta publicar as regras do Firebase' in r['toast'] and r['intactas'] and r['form']
        await adm.evaluate("()=>{firebaseDB.ref=window.__refOriginal;dicasPacotesCarregar();}")
        await adm.wait_for_timeout(300)
        print('   OK\n')

        print('=== J) 375 px e 1440 px, claro e escuro ===')
        alvos=[('admin',adm),('assinante',ana)]
        await ana.evaluate("()=>{firebaseDB.ref=window.__refOriginal;dicasPacotesCarregar();}")
        await ana.wait_for_timeout(300)
        for quem,pg in alvos:
            await pg.evaluate("()=>{dicasRelatorioFechar();const el=document.getElementById('dicas-pacotes');window.scrollTo(0,el.getBoundingClientRect().top+window.scrollY-80);}")
            for tema in ['light','dark']:
                await pg.evaluate("(t)=>document.documentElement.setAttribute('data-theme',t)",tema)
                for larg,alt in [(375,812),(1440,900)]:
                    await pg.set_viewport_size({'width':larg,'height':alt})
                    await pg.wait_for_timeout(250)
                    m=await pg.evaluate("""()=>{const el=document.getElementById('dicas-pacotes');
                      el.scrollIntoView({block:'start'});window.scrollBy(0,-70);
                      const vaza=[...el.querySelectorAll('*')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.right>window.innerWidth+1;}).length;
                      return {rolagem:document.documentElement.scrollWidth>window.innerWidth+1,vaza,
                              fundo:getComputedStyle(el).backgroundColor,linhas:el.querySelectorAll('.dicas-pacote').length};}""")
                    nome='dicas_pacotes_%s_%s_%s.png'%(quem,larg,'claro' if tema=='light' else 'escuro')
                    # a captura do cartao inteiro e costurada: as barras fixas (topo e menu de baixo)
                    # cobririam o painel no meio dela — saem so durante a foto
                    barras="(v)=>['toast','sidebar','nav-principal'].forEach(id=>{const e=document.getElementById(id);if(e)e.style.visibility=v;})"
                    await pg.evaluate(barras,'hidden')
                    await pg.locator('#screen-dicas .section-card').first.screenshot(path=os.path.join(OUT,nome))
                    await pg.evaluate(barras,'')
                    print('   %-9s %-5s %4spx: rolagem lateral %s · vazando %s · fundo %s'%(quem,tema,larg,m['rolagem'],m['vaza'],m['fundo']))
                    assert not m['rolagem'] and m['vaza']==0 and m['linhas']==1, m
        print('   capturas em tests/e2e/_out/dicas_pacotes_*.png')
        print('   OK\n')

        print('=== K) pacote pronto que vem com o site: aparece pra todos sem publicar ===')
        ctxC,adm2,errsC=await abrir(browser,seed(),viewport={'width':1440,'height':900})
        await adm2.evaluate("()=>showScreen('dicas')")
        await adm2.wait_for_timeout(600)
        r=await adm2.evaluate("""()=>({linhas:[...document.querySelectorAll('#dicas-pacotes .dicas-pacote')].map(l=>l.innerText.replace(/\\n/g,' | ')),
          opcoes:[...document.querySelectorAll('#dicas-pub-alvo option')].map(o=>o.textContent)})""")
        print('   admin, aba vazia abre sozinha: %s'%r['linhas'])
        print('   opções de publicar: %s'%r['opcoes'])
        assert len(r['linhas'])==1 and 'Português — 25 pontos' in r['linhas'][0] and 'pronto do Vale' in r['linhas'][0]
        assert 'Remover' not in r['linhas'][0] and r['opcoes']==['Novo pacote']   # nao da pra publicar por cima dele

        ctxD,bia,errsD=await abrir(browser,seed_assinante(),viewport={'width':1440,'height':900})
        await bia.evaluate("()=>{currentUser={...currentUser,email:'bia@exemplo.com'};showScreen('dicas');}")
        await bia.wait_for_timeout(600)
        r=await bia.evaluate("()=>[...document.querySelectorAll('#dicas-pacotes .dicas-pacote')].map(l=>l.innerText.replace(/\\n/g,' | '))")
        print('   assinante, aba vazia: %s'%r)
        assert len(r)==1 and 'Adicionar às minhas dicas' in r[0]
        await bia.click('#dicas-pacotes button:has-text("Adicionar às minhas dicas")')
        await bia.wait_for_timeout(300)
        r=await bia.evaluate("""()=>{const c=db.dicas.find(d=>d.titulo==='Crase antes de horas');
          return {n:db.dicas.length,todas:db.dicas.every(d=>d.pacote==='pk-portugues-25'&&/^pt25-\\d\\d$/.test(d.pacoteItem)),
                  crase:{item:c.pacoteItem,subId:c.subId},painel:!!document.getElementById('dicas-pacotes'),
                  rel:(document.getElementById('dicas-relatorio')||{}).innerText||''};}""")
        print('   adicionou: %s dicas · "Crase antes de horas" = %s · painel aberto sozinho fechou: %s'%(r['n'],r['crase'],not r['painel']))
        print('   relatório: %s'%r['rel'].split('\n')[0])
        assert r['n']==25 and r['todas'] and r['crase']=={'item':'pt25-08','subId':'xCrase'} and not r['painel']
        assert r['rel'].startswith('📦 Pacote "Português — 25 pontos"')

        # versao nova publicada no Firebase com o MESMO id passa na frente da que vem com o site
        await bia.evaluate("""async()=>{const r=await fetch('/docs/dicas/portugues-25-pontos.json');const dicas=await r.json();
          dicas[7].regra='V2: '+dicas[7].regra;
          window.__root.dicas_pacotes={'pk-portugues-25':{id:'pk-portugues-25',nome:'Português — 25 pontos',versao:2,publicadoEm:'2026-11-01T00:00:00.000Z',dicas}};
          dicasPacotesAbrir();}""")
        await bia.wait_for_timeout(400)
        r=await bia.evaluate("()=>[...document.querySelectorAll('#dicas-pacotes .dicas-pacote')].map(l=>l.innerText.replace(/\\n/g,' | '))")
        print('   com v2 no Firebase: %s'%r)
        assert len(r)==1 and 'Atualizar para a v2' in r[0] and 'pronto do Vale' not in r[0]
        await bia.click('#dicas-pacotes button:has-text("Atualizar para a v2")')
        await bia.wait_for_timeout(300)
        r=await bia.evaluate("()=>db.dicas.find(d=>d.titulo==='Crase antes de horas').regra.slice(0,3)")
        assert r=='V2:', r

        # sem o Firebase (regra fora do ar), o pronto continua na lista, com o aviso
        await bia.evaluate("()=>{window.__root.dicas_pacotes=null;}")
        await bia.evaluate(NEGADO)
        await bia.evaluate("()=>dicasPacotesAbrir()")
        await bia.wait_for_timeout(400)
        r=await bia.evaluate("()=>document.getElementById('dicas-pacotes').innerText")
        print('   Firebase negando: aviso %s · pronto listado %s'%('falta publicar as regras' in r,'pronto do Vale' in r))
        assert 'falta publicar as regras' in r and 'pronto do Vale' in r and 'em dia (v2)' in r
        await ctxC.close();await ctxD.close()
        print('   OK\n')

        todos=graves(errsA)+graves(errsB)+graves(errsB2)+graves(errsC)+graves(errsD)
        print('erros de JS: %s'%(todos or 'nenhum'))
        assert not todos, todos
        await browser.close()
        print('OK')

if __name__=='__main__':
    asyncio.run(main())
