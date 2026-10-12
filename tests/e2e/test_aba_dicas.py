# -*- coding: utf-8 -*-
# Aba Dicas (etapa 1): a revisao rapida de vespera ganhou lugar proprio em Treinar, em vez
# de virar chefao "Foco para nao errar!" dentro da materia. O conteudo mora num no proprio
# (vdn_dicas, como o vdn_acervo) e o "ja sei" no registro principal (dicasEstado). Diferente
# do acervo, dica e editada e apagada — por isso a uniao entre aparelhos e por id + data, e
# apagar deixa lapide. Este teste cobre a aba, criar/editar/apagar, importar o pacote de
# Portugues, busca, filtros, "ja sei", a lista "sem assunto", a persistencia (recarregar e
# trocar de aparelho), o backup, a trava de plano e o layout em 375/1440, claro e escuro.
import asyncio, json, os, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, INIT_JS, LOCAL_PHASER, BASE, make_seed

AQUI=os.path.dirname(os.path.abspath(__file__))
PACOTE=os.path.join(AQUI,'..','..','docs','dicas','portugues-25-pontos.json')
OUT=os.path.join(AQUI,'_out')

def seed(extra=None):
    d={'studyNickname':'Leo',
       'kingdoms':[{'id':'kPt','name':'Português','icon':'📖','color':'#f472b6'},
                   {'id':'kEnf','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
       'topics':{'kPt':[{'id':'tP','name':'Gramática','icon':'✏️','subtopics':[
                    {'id':'sCrase','name':'Crase','priority':70,'studied':True},
                    {'id':'sReg','name':'Regência verbal','priority':70,'studied':True},
                    {'id':'sCol','name':'Colocação pronominal','priority':70,'studied':True},
                    {'id':'sPron','name':'Pronomes','priority':70,'studied':True}]}],
                 'kEnf':[{'id':'tE','name':'Imunização','icon':'💉','subtopics':[
                    {'id':'sFrio','name':'Rede de frio','priority':70,'studied':True}]}]}}
    d.update(extra or {})
    return make_seed(d)

# Mesmo que setup_page, mas aceita um contexto existente (= o MESMO aparelho, com o cache
# local dele) e um vdn_dicas ja gravado na "nuvem" — e o que permite recarregar a pagina e
# trocar de aparelho sem perder o estado do Firebase mockado.
async def abrir(browser,vdn_v1,vdn_dicas=None,ctx=None,viewport=None):
    if ctx is None:
        ctx=await browser.new_context(service_workers='block',viewport=viewport or {'width':1200,'height':900})
    page=await ctx.new_page()
    errs=[]
    page.on('pageerror',lambda e:errs.append(str(e)))
    async def phaser(route): await route.fulfill(path=LOCAL_PHASER)
    await page.route('**cdnjs.cloudflare.com/ajax/libs/phaser/**',phaser)
    for padrao in ['**://www.gstatic.com/**','**://fonts.googleapis.com/**',
                   '**://cdn.jsdelivr.net/**','**://www.googletagmanager.com/**']:
        await page.route(padrao,lambda r:r.abort())
    await page.add_init_script(INIT_JS.replace('__SEED__',json.dumps(vdn_v1)))
    if vdn_dicas is not None:
        await page.add_init_script('window.__root.users.TEST_UID_LEO.vdn_dicas=%s;'%json.dumps(vdn_dicas))
    await page.add_init_script('window.confirm=()=>true;window.__toasts=[];')
    await page.goto(BASE)
    await page.wait_for_timeout(2000)
    # toast real continua aparecendo; so guarda o texto pra conferir
    await page.evaluate("()=>{const t=window.toast;window.toast=(m,c)=>{window.__toasts.push(m);return t(m,c);};}")
    return ctx,page,errs

def graves(errs):
    return [e for e in errs if 'selectedPixTier' not in e]

async def nuvem(page):
    return await page.evaluate("()=>JSON.parse(JSON.stringify({v1:window.__root.users.TEST_UID_LEO.vdn_v1,dicas:window.__root.users.TEST_UID_LEO.vdn_dicas||null}))")

async def main():
    os.makedirs(OUT,exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctxA,page,errs=await abrir(browser,seed())

        print('=== A) a aba entra nas quatro barras de Treinar e ganha a propria tela ===')
        r=await page.evaluate("""()=>{
          const telas=['simgeral','provas','caderno','banco','dicas'];
          const out={};
          telas.forEach(t=>{
            const bs=[...document.querySelectorAll('#screen-'+t+' .rd-conectivos-tabs button')];
            out[t]={n:bs.length,labels:bs.map(b=>b.textContent.trim()),
                    ativos:bs.filter(b=>b.classList.contains('active')).map(b=>b.textContent.trim())};
          });
          showScreen('dicas');
          return {barras:out,
                  ativa:document.getElementById('screen-dicas').classList.contains('active'),
                  telasAtivas:document.querySelectorAll('.screen.active').length,
                  menu:(document.querySelector('.nav-btn.active')||{}).id,
                  travada:LOCKED_SCREENS.includes('dicas')};}""")
        for t,v in r['barras'].items():
            print('   %-9s %s abas · ativa: %s'%(t,v['n'],v['ativos']))
            assert v['n']==5 and v['labels'][4]=='Dicas' and len(v['ativos'])==1, v
        assert r['barras']['dicas']['ativos']==['Dicas']
        assert r['ativa'] and r['telasAtivas']==1 and r['menu']=='nav-simgeral' and r['travada'], r
        print('   abre, só uma tela ativa, o menu lateral segue em Treinar, e está em LOCKED_SCREENS')
        print('   OK\n')

        print('=== B) vazia, a aba convida a importar ou criar ===')
        r=await page.evaluate("""()=>{const el=document.getElementById('dicas-content');
          return {txt:el.innerText,botoes:[...el.querySelectorAll('button')].map(b=>b.getAttribute('onclick'))};}""")
        print('   "%s"'%r['txt'].split('\n')[2])
        assert 'Nenhuma dica ainda' in r['txt']
        assert 'dicasImportarAbrir()' in r['botoes'] and 'dicasCriarAbrir()' in r['botoes']
        print('   OK\n')

        print('=== C) criar pelo formulario: dica, numero e par ===')
        await page.click('#dicas-content button:has-text("Nova dica")')
        await page.fill('#dica-novo-titulo','Crase antes de hora')
        await page.select_option('#dica-novo-materia','kPt')
        await page.select_option('#dica-novo-assunto','sCrase')
        await page.fill('#dica-novo-grupo','Regência e preposições')
        await page.fill('#dica-novo-regra','Hora determinada leva artigo: às 14h.')
        await page.fill('#dica-novo-aplicar','Troque por meio-dia: apareceu "ao", tem crase.')
        await page.fill('#dica-novo-cuidado','Desde, após e entre não pedem crase.')
        await page.fill('#dica-novo-exemplos','✔ A prova começa às 13h.\n✖ Aberto desde às 7h.\n+ Das 8h às 12h.')
        await page.fill('#dica-novo-bancas','IGEDUC, Cebraspe, igeduc')
        await page.click('#dica-novo-form button:has-text("Salvar")')
        r=await page.evaluate("""()=>{const d=db.dicas[0];const card=document.getElementById('dica-'+d.id);
          return {n:db.dicas.length,d,
                  rotulos:[...card.querySelectorAll('.dica-linha dt')].map(x=>x.textContent.trim()),
                  certos:card.querySelectorAll('.dica-ex-ok').length,errados:card.querySelectorAll('.dica-ex-nok').length,
                  sinalErrado:(card.querySelector('.dica-ex-nok .dica-ex-sinal')||{}).textContent,
                  etiquetas:[...card.querySelectorAll('.banco-tag,.dica-etq')].map(x=>x.textContent.trim()),
                  origem:card.querySelector('.dica-origem').textContent.trim()};}""")
        d=r['d']
        print('   %s · tipo %s · assunto %s · bancas %s'%(d['titulo'],d['tipo'],d.get('subId'),d['bancas']))
        print('   rótulos: %s'%r['rotulos'])
        print('   exemplos: %s certos, %s errado (sinal "%s") · etiquetas %s · origem "%s"'
              %(r['certos'],r['errados'],r['sinalErrado'],r['etiquetas'],r['origem']))
        assert r['n']==1 and d['tipo']=='dica' and d['subId']=='sCrase' and d['kingdomId']=='kPt'
        assert d['bancas']==['IGEDUC','Cebraspe'], d['bancas']     # banca repetida (caixa diferente) entra uma vez
        assert [x.split(' ',1)[1] for x in r['rotulos']]==['Regra','Como aplicar','Cuidado'], r['rotulos']
        assert r['rotulos'][0].startswith('📐') and r['rotulos'][1].startswith('🔑') and r['rotulos'][2].startswith('⚠️')
        assert r['certos']==2 and r['errados']==1 and 'errado' in r['sinalErrado']
        assert 'Crase' in r['etiquetas'] and 'IGEDUC' in r['etiquetas'] and 'minha' in r['origem']
        assert d['criadaEm'] and d['editadaEm']

        # numero: trocar o tipo esconde Regra/Como aplicar/Cuidado e mostra Valor/Rotulo
        await page.click('#dicas-content button:has-text("Nova dica")')
        await page.select_option('#dica-novo-tipo','numero')
        vis=await page.evaluate("""()=>({regra:!!document.getElementById('dica-novo-regra').offsetParent,
                                        valor:!!document.getElementById('dica-novo-valor').offsetParent})""")
        assert not vis['regra'] and vis['valor'], vis
        await page.select_option('#dica-novo-materia','kEnf')
        await page.select_option('#dica-novo-assunto','sFrio')
        await page.fill('#dica-novo-valor','+2 a +8 °C')
        await page.fill('#dica-novo-rotulo','Rede de frio, instância local')
        # texto sobrando num campo de outro tipo (escondido) nao pode ir junto
        await page.evaluate("()=>{document.getElementById('dica-novo-regra').value='isto não pode ir junto';}")
        await page.click('#dica-novo-form button:has-text("Salvar")')
        # par
        await page.click('#dicas-content button:has-text("Nova dica")')
        await page.select_option('#dica-novo-tipo','par')
        await page.select_option('#dica-novo-materia','kPt')
        await page.fill('#dica-novo-titulo','Mau × mal')
        await page.fill('#dica-novo-a','mau')
        await page.fill('#dica-novo-b','mal')
        await page.fill('#dica-novo-diferenca','Mau é adjetivo (oposto de bom); mal é advérbio (oposto de bem).')
        await page.click('#dica-novo-form button:has-text("Salvar")')
        r=await page.evaluate("""()=>{
          const num=db.dicas.find(x=>x.tipo==='numero'),par=db.dicas.find(x=>x.tipo==='par');
          dicasFiltrarMateria('');
          const cn=document.getElementById('dica-'+num.id),cp=document.getElementById('dica-'+par.id);
          return {num,par,
                  valorTela:cn&&cn.querySelector('.dica-num-valor').textContent,
                  rotuloTela:cn&&cn.querySelector('.dica-num-rotulo').textContent,
                  numNaGrade:!!(cn&&cn.closest('.dica-numeros')),
                  ladosPar:cp?[...cp.querySelectorAll('.dica-par-lado')].map(x=>x.textContent):[]};}""")
        print('   número: "%s" / "%s" (em grade: %s) · sobra do campo escondido: %s'
              %(r['valorTela'],r['rotuloTela'],r['numNaGrade'],'regra' in r['num']))
        print('   par: %s'%' × '.join(r['ladosPar']))
        assert r['valorTela']=='+2 a +8 °C' and r['rotuloTela']=='Rede de frio, instância local' and r['numNaGrade']
        assert r['num']['titulo']=='Rede de frio, instância local'   # numero sem titulo usa o rotulo
        assert 'regra' not in r['num'] and r['ladosPar']==['mau','mal']

        # recusas do formulario
        r=await page.evaluate("""()=>{
          const antes=db.dicas.length;
          dicasCriarAbrir();
          document.getElementById('dica-novo-regra').value='sem titulo';
          dicasCriarSalvar();
          const semTitulo=window.__toasts.slice(-1)[0];
          document.getElementById('dica-novo-titulo').value='  CRASE antes de HORA!  ';
          dicasCriarSalvar();
          const dup=window.__toasts.slice(-1)[0];
          dicasCriarCancelar();
          return {antes,depois:db.dicas.length,semTitulo,dup};}""")
        print('   sem título: "%s"'%r['semTitulo'])
        print('   mesmo título com caixa/pontuação diferentes: "%s"'%r['dup'][:60])
        assert r['depois']==r['antes']==3 and 'sem título' in r['semTitulo'] and 'Já existe' in r['dup']
        print('   OK\n')

        print('=== D) editar ===')
        did=await page.evaluate("()=>db.dicas[0].id")
        await page.click('[id="dica-%s"] button:has-text("Editar")'%did)
        pre=await page.evaluate("""()=>({titulo:document.getElementById('dica-edit-titulo').value,
          assunto:document.getElementById('dica-edit-assunto').value,
          exemplos:document.getElementById('dica-edit-exemplos').value})""")
        print('   formulário vem preenchido: "%s" · assunto %s · %s exemplos'
              %(pre['titulo'],pre['assunto'],len(pre['exemplos'].split('\n'))))
        assert pre['titulo']=='Crase antes de hora' and pre['assunto']=='sCrase' and pre['exemplos'].startswith('✔ ')
        await page.wait_for_timeout(20)   # editadaEm precisa ser de outro milissegundo
        await page.fill('#dica-edit-regra','Hora exata é feminina e leva artigo: às 14h, à 1h.')
        await page.click('#dica-edit-form button:has-text("Salvar")')
        r=await page.evaluate("""(id)=>{const d=db.dicas.find(x=>x.id===id);
          return {regra:d.regra,criada:d.criadaEm,editada:d.editadaEm,
                  tela:document.getElementById('dica-'+id).innerText.includes('Hora exata é feminina'),
                  formAberto:!!document.getElementById('dica-edit-form')};}""",did)
        print('   regra nova na tela: %s · editadaEm (%s) > criadaEm (%s)'%(r['tela'],r['editada'][11:23],r['criada'][11:23]))
        assert r['tela'] and not r['formAberto'] and r['editada']>r['criada']
        print('   OK\n')

        print('=== E) importar o pacote de Portugues (pelo arquivo) ===')
        await page.click('#dicas-content button:has-text("Importar em lote")')
        await page.set_input_files('#dicas-importar-arq',PACOTE)
        await page.wait_for_function("()=>dicasImportarRelatorio&&dicasImportarRelatorio.lidos===25",timeout=5000)
        r=await page.evaluate("""()=>{
          const rel=dicasImportarRelatorio;
          dicasFiltrarMateria('kPt');
          const titulos=el=>[...el.querySelectorAll('.dica-grupo')].map(s=>
            s.querySelector('.dica-grupo-tit').innerText.replace(/\\s+/g,' ').trim());
          const grupos=titulos(document.getElementById('dicas-corpo'));
          const pacote=db.dicas.filter(d=>d.origem==='ia');
          // a ordem dos grupos e a da primeira aparicao: so com o pacote, e a do arquivo
          const so=document.createElement('div');so.innerHTML=dicasCorpoHTML(pacote);
          return {rel,grupos,ordemPacote:titulos(so),
                  tela:document.getElementById('dicas-relatorio').innerText,
                  aprox:(document.getElementById('dicas-rel-aprox')||{}).innerText||'',
                  semAssunto:pacote.filter(d=>!d.subId).length,
                  comNome:pacote.filter(d=>!d.subId&&d.assuntoNome).length,
                  tipos:[...new Set(pacote.map(d=>d.tipo))].sort(),
                  todasComExemplo:pacote.every(d=>(d.exemplos||[]).some(e=>e.ok)&&(d.exemplos||[]).some(e=>!e.ok)),
                  ordem:pacote.slice(0,2).map(d=>d.titulo)};}""")
        rel=r['rel']
        print('   %s lidos · %s entraram (%s com assunto, %s só com a matéria) · %s recusadas · %s esperando'
              %(rel['lidos'],rel['entraram'],rel['comAssunto'],rel['semAssunto'],len(rel['recusadas']),rel['aguardando']))
        print('   ligadas por aproximação, listadas no relatório: %s'%r['aprox'].replace('\n',' | '))
        for g in r['grupos']: print('     %s'%g)
        print('   ordem dos grupos só com o pacote: %s'%[g.rsplit(' ',1)[0] for g in r['ordemPacote']])
        assert rel['lidos']==25 and rel['entraram']==25 and not rel['recusadas'] and rel['aguardando']==0
        assert rel['comAssunto']+rel['semAssunto']==25 and r['semAssunto']==rel['semAssunto']==r['comNome']
        assert 'Concordância verbal' in r['aprox'] and 'Regência verbal' in r['aprox']
        assert [g.upper() for g in r['ordemPacote']]==['CLASSES E PRONOMES 6','REGÊNCIA E PREPOSIÇÕES 6','VERBOS E CONCORDÂNCIA 6',
               'COLOCAÇÃO PRONOMINAL 3','ORTOGRAFIA E SENTIDO 4'], r['ordemPacote']
        # na tela: o grupo de regencia tem as 6 do pacote + a dica de crase criada a mao em C
        assert 'REGÊNCIA E PREPOSIÇÕES 7' in r['grupos'] and 'CLASSES E PRONOMES 6' in r['grupos'], r['grupos']
        assert r['tipos']==['dica','par'] and r['todasComExemplo'] and r['ordem'][0].startswith('Pronome indefinido')
        print('   o pacote entra inteiro, nos 5 grupos, na ordem do arquivo, cada dica com certo e errado')

        r=await page.evaluate("""(txt)=>{
          dicasImportarAbrir();
          document.getElementById('dicas-importar-txt').value=txt;
          dicasImportarProcessar();
          const rel=dicasImportarRelatorio;
          return {entraram:rel.entraram,recusadas:rel.recusadas.length,
                  motivo:rel.recusadas[0].motivo,painelAberto:!!document.getElementById('dicas-importar')};}""",
          open(PACOTE,encoding='utf-8').read())
        print('   reimportar o mesmo pacote: %s entraram, %s recusadas ("%s")'%(r['entraram'],r['recusadas'],r['motivo']))
        assert r['entraram']==0 and r['recusadas']==25 and 'já existe' in r['motivo'] and r['painelAberto']

        lote=[{'materia':'Português','titulo':'Sem regra nenhuma'},
              {'tipo':'tabela','materia':'Português','titulo':'Tipo inventado','regra':'x'},
              {'titulo':'Sem matéria','regra':'x'},
              {'materia':'Gramática Normativa','assunto':'Crase','titulo':'Crase com até','regra':'Com até, a crase é facultativa.'},
              {'materia':'Língua Portuguesa','titulo':'Acento diferencial','regra':'Pôr (verbo) × por (preposição).'},
              {'materia':'Química','titulo':'Mol','regra':'x'},
              'texto solto',
              {'tipo':'Número','materia':'enfermagem','titulo':'Temperatura do refrigerador','valor':'+2 a +8 °C'}]
        r=await page.evaluate("""(lote)=>{
          dicasImportarAbrir();
          document.getElementById('dicas-importar-txt').value='```json\\n'+JSON.stringify(lote)+'\\n```';
          dicasImportarProcessar();
          const rel=dicasImportarRelatorio;
          const pend=dicasImportarPendentes.map(p=>p.nome+':'+p.itens.length);
          return {entraram:rel.entraram,aguardando:rel.aguardando,pend,
                  aprox:(document.getElementById('dicas-rel-aprox')||{}).innerText||'',
                  acento:(db.dicas.find(d=>d.titulo==='Acento diferencial')||{}).kingdomId,
                  motivos:rel.recusadas.map(x=>x.n+' '+x.motivo),
                  telaPend:!!document.getElementById('dicas-importar-pendentes')};}""",lote)
        print('   lote com problemas: %s entraram · esperando matéria: %s · recusadas:'%(r['entraram'],r['pend']))
        for m in r['motivos']: print('     item %s'%m)
        print('   matéria por nome parecido entra e aparece no relatório: %s'%r['aprox'])
        assert r['entraram']==2 and r['aguardando']==2 and r['telaPend']   # "Número"/"enfermagem" normalizados
        assert r['acento']=='kPt' and '"Língua Portuguesa" → Português' in r['aprox']
        assert sorted(r['pend'])==['Gramática Normativa:1','Química:1']
        assert len(r['motivos'])==4 and any('sem "materia"' in m for m in r['motivos'])
        assert any('tipo "tabela"' in m for m in r['motivos']) and any('não é um objeto' in m for m in r['motivos'])
        r=await page.evaluate("""()=>{
          const i=dicasImportarPendentes.findIndex(p=>p.nome==='Gramática Normativa');
          document.getElementById('dicas-pend-'+i).value='kPt';
          dicasImportarPendenteUsar(i);
          const nova=db.dicas.find(d=>d.titulo==='Crase com até');
          dicasImportarPendenteDescartar(0);
          const rel=dicasImportarRelatorio;
          return {nova:nova&&{k:nova.kingdomId,s:nova.subId},aguardando:rel.aguardando,
                  ultima:rel.recusadas.slice(-1)[0].motivo,pend:dicasImportarPendentes.length};}""")
        print('   "Gramática Normativa" → Português (escolhido): entrou e achou o assunto %s dentro do reino'%r['nova']['s'])
        print('   "Química" descartada → vira recusa com motivo: "%s"'%r['ultima'])
        assert r['nova']=={'k':'kPt','s':'sCrase'} and r['aguardando']==0 and r['pend']==0
        assert 'descartada por você' in r['ultima']
        r=await page.evaluate("""()=>{const antes=db.dicas.length;window.__toasts=[];
          dicasImportarProcessar('isto não é json');
          return {antes,depois:db.dicas.length,toast:window.__toasts.slice(-1)[0]};}""")
        print('   texto que não é JSON: "%s"'%r['toast'])
        assert r['antes']==r['depois'] and 'Não achei' in r['toast']
        print('   OK\n')

        print('=== F) busca e filtros (materia, grupo, banca) ===')
        await page.evaluate("()=>{dicasImportando=false;dicasRelatorioFechar();dicasFiltroLimpar();}")
        await page.click('#dicas-busca')
        await page.keyboard.type('cujo')
        r=await page.evaluate("""()=>({foco:document.activeElement&&document.activeElement.id,
          titulos:[...document.querySelectorAll('#dicas-corpo .dica-titulo')].map(x=>x.textContent),
          conta:document.getElementById('dicas-conta').innerText})""")
        print('   digitando "cujo": %s · foco continua no campo: %s'%(r['titulos'],r['foco']=='dicas-busca'))
        assert r['titulos']==['Cujo'] and r['foco']=='dicas-busca'
        await page.fill('#dicas-busca','')
        await page.keyboard.type('desde as 7h')   # texto de exemplo, sem acento
        r=await page.evaluate("()=>[...document.querySelectorAll('#dicas-corpo .dica-titulo')].map(x=>x.textContent)")
        print('   busca dentro dos exemplos, sem acento: %s'%r)
        assert set(r)=={'Crase antes de hora','Crase antes de horas'}, r
        r=await page.evaluate("""()=>{
          dicasFiltroLimpar();
          const chips=[...document.querySelectorAll('#dicas-chips-materia .banco-chip')].map(x=>x.textContent.trim());
          dicasFiltrarMateria('kEnf');
          const enf=[...document.querySelectorAll('#dicas-corpo .dica-card')].length;
          dicasFiltrarMateria('kPt');
          dicasFiltrarGrupo('Colocação pronominal');
          const col=[...document.querySelectorAll('#dicas-corpo .dica-titulo')].map(x=>x.textContent);
          dicasFiltroLimpar();
          dicasFiltrarBanca('cebraspe');
          const banca=[...document.querySelectorAll('#dicas-corpo .dica-titulo')].map(x=>x.textContent);
          const opcoes=[...document.querySelectorAll('#dicas-filtro-banca option')].map(o=>o.textContent);
          dicasFiltroLimpar();
          return {chips,enf,col,banca,opcoes};}""")
        print('   chips de matéria: %s'%r['chips'])
        print('   Enfermagem: %s cartões · Colocação pronominal: %s'%(r['enf'],len(r['col'])))
        print('   banca "cebraspe" (sem diferenciar caixa): %s · opções: %s'%(r['banca'],r['opcoes']))
        assert r['chips'][0].startswith('Todas · ') and any(c.endswith('Português · 29') for c in r['chips']), r['chips']
        assert any(c.endswith('Enfermagem · 2') for c in r['chips'])
        assert r['enf']==2 and len(r['col'])==3 and all('Colocação' in t for t in r['col'])
        assert r['banca']==['Crase antes de hora'] and r['opcoes']==['Qualquer banca','Cebraspe','IGEDUC']
        print('   OK\n')

        print('=== G) "Ja sei" esconde; o chip traz de volta ===')
        alvo=await page.evaluate("()=>db.dicas.find(d=>d.titulo==='Cujo').id")
        await page.click('[id="dica-%s"] .dica-btn-sei'%alvo)
        r=await page.evaluate("""(id)=>({est:db.dicasEstado[id],naTela:!!document.getElementById('dica-'+id),
          conta:document.getElementById('dicas-conta').innerText,
          chip:[...document.querySelectorAll('#dicas-chips-mostrar .banco-chip')].map(x=>x.textContent.trim())})""",alvo)
        print('   estado: %s · ainda na lista: %s'%(r['est'],r['naTela']))
        print('   contagem: "%s"'%r['conta'])
        assert r['est']['sei'] is True and r['est']['vistaEm'] and not r['naTela']
        assert '1 que você já sabe está escondida' in r['conta'] and 'mostrar as que já sei · 1' in r['chip'][0]
        await page.click('#dicas-chips-mostrar .banco-chip:has-text("mostrar as que já sei")')
        r=await page.evaluate("""(id)=>{const c=document.getElementById('dica-'+id);
          return {volta:!!c,classe:c&&c.classList.contains('dica-sei'),selo:c&&c.innerText.includes('já sei'),
                  botao:c&&c.querySelector('.dica-btn-sei').textContent};}""",alvo)
        print('   com o chip: volta=%s, marcada=%s, botão "%s"'%(r['volta'],r['classe'],r['botao']))
        assert r['volta'] and r['classe'] and r['selo'] and 'Rever' in r['botao']
        # uma segunda, que fica marcada pra conferir depois de recarregar
        alvo2=await page.evaluate("()=>db.dicas.find(d=>d.titulo==='Meio × meia').id")
        await page.click('[id="dica-%s"] .dica-btn-sei'%alvo)       # desmarca a primeira
        await page.click('[id="dica-%s"] .dica-btn-sei'%alvo2)
        await page.evaluate("()=>dicasAlternarJaSei()")
        r=await page.evaluate("(ids)=>ids.map(id=>dicaSei(id))",[alvo,alvo2])
        assert r==[False,True], r
        print('   desmarcar devolve à lista; a marcação é por dica')
        print('   OK\n')

        print('=== H) "sem assunto": ligar em grupo, pelo nome que o pacote escreveu ===')
        # o caso real: o miniboss que o pacote citava passa a existir DEPOIS da importacao
        await page.evaluate("""()=>{db.topics.kPt[0].subtopics.push({id:'sVoz',name:'Vozes verbais',priority:70,studied:false});
          db.topics.kPt[0].subtopics.push({id:'sFig',name:'Figuras de linguagem',priority:70,studied:false});}""")
        await page.click('#dicas-chips-mostrar .banco-chip:has-text("sem assunto")')
        r=await page.evaluate("""()=>({linhas:[...document.querySelectorAll('#dicas-resolver .dicas-ligar-nome')].map(x=>x.innerText),
          sug:dicasResolverGrupos.map((g,i)=>g.nome+'='+document.getElementById('dicas-ligar-'+i).value)})""")
        print('   %s linhas, ex.: %s'%(len(r['linhas']),r['linhas'][:3]))
        nomes=[x.split('=')[0] for x in r['sug']]
        i=nomes.index('Vozes verbais')
        print('   sugestão já marcada pra "Vozes verbais": %s (só sugere; nada foi ligado sozinho)'%r['sug'][i].split('=')[1])
        assert r['sug'][i].split('=')[1]=='sVoz'
        assert r['sug'][nomes.index('Ortografia')].split('=')[1]==''      # sem candidato, sem sugestao
        r=await page.evaluate("""(i)=>{
          const ids=dicasResolverGrupos[i].ids;
          dicasLigarAssunto(i);
          const ds=db.dicas.filter(d=>ids.includes(d.id));
          return {n:ds.length,todas:ds.every(d=>d.subId==='sVoz'&&!d.assuntoNome),
                  apelido:(db.simColarApelidos||{})['vozes verbais'],
                  linhas:document.querySelectorAll('#dicas-resolver .dicas-ligar-linha').length,
                  antes:dicasResolverGrupos.length};}""",i)
        print('   ligou %s dica a "Vozes verbais" · o nome vira apelido pra próxima importação: %s'%(r['n'],r['apelido']))
        assert r['n']==1 and r['todas'] and r['apelido']=='sVoz'
        # a outra linha se liga escolhendo o miniboss a mao
        r=await page.evaluate("""()=>{const i=dicasResolverGrupos.findIndex(g=>g.nome==='Figuras de linguagem');
          dicasLigarAssunto(i);
          return db.dicas.filter(d=>d.titulo==='Figuras de linguagem').map(d=>d.subId);}""")
        assert r==['sFig'], r
        await page.evaluate("()=>dicasFiltroLimpar()")
        print('   OK\n')

        print('=== I) apagar ===')
        apagada=await page.evaluate("()=>db.dicas.find(d=>d.titulo==='Mau × mal').id")
        await page.click('[id="dica-%s"] button:has-text("Editar")'%apagada)
        await page.click('#dica-edit-form button:has-text("Apagar dica")')
        r=await page.evaluate("""(id)=>({existe:db.dicas.some(d=>d.id===id),lapide:!!dicasLapides[id],
          naTela:!!document.getElementById('dica-'+id)})""",apagada)
        print('   sumiu da lista: %s · deixou lápide: %s'%(not r['existe'],r['lapide']))
        assert not r['existe'] and r['lapide'] and not r['naTela']
        print('   OK\n')

        print('=== J) gravacao: no proprio, so quando muda; o registro principal leva so o estado ===')
        await page.wait_for_timeout(1900)
        r=await page.evaluate("""async()=>{
          const raiz=window.__root.users.TEST_UID_LEO;
          const noNo=raiz.vdn_dicas||[];
          window.__updateCalls=[];
          dicasSalvar(true);dicasSalvar(true);          // nada mudou
          for(let i=0;i<3;i++)saveDB();
          await new Promise(r=>setTimeout(r,1200));
          const caminhos=window.__updateCalls.map(c=>c.path);
          return {vivas:noNo.filter(x=>!x.apagada).length,lapides:noNo.filter(x=>x.apagada).length,
                  memoria:db.dicas.length,
                  regravouNo:caminhos.filter(c=>/vdn_dicas/.test(c)).length,
                  registro:caminhos.filter(c=>/vdn_v1$/.test(c)).length,
                  dicasNoRegistro:'dicas' in raiz.vdn_v1,estadoNoRegistro:Object.keys(raiz.vdn_v1.dicasEstado||{}).length,
                  noPayload:'dicas' in payloadParaFirebase()};}""")
        print('   vdn_dicas: %s vivas + %s lápide (em memória: %s)'%(r['vivas'],r['lapides'],r['memoria']))
        print('   2 dicasSalvar sem mudança + 3 saveDB → %s gravações no nó das dicas, %s no registro'%(r['regravouNo'],r['registro']))
        print('   registro principal: dicas=%s · dicasEstado com %s entrada(s)'%(r['dicasNoRegistro'],r['estadoNoRegistro']))
        assert r['vivas']==r['memoria'] and r['lapides']==1 and r['regravouNo']==0 and r['registro']>=1
        assert not r['dicasNoRegistro'] and not r['noPayload'] and r['estadoNoRegistro']==2
        print('   OK\n')

        print('=== K) backup: as dicas vao na copia de seguranca e voltam no restaurar ===')
        r=await page.evaluate("""async()=>{
          // o backup do dia ja rodou no boot (sem dicas); sem a meta, o "forcar" grava de novo
          delete window.__root.users.TEST_UID_LEO.vdn_v1_bkpMeta;
          forcarBackupAgora();
          await new Promise(r=>setTimeout(r,600));
          const raiz=window.__root.users.TEST_UID_LEO;
          const meta=raiz.vdn_v1_bkpMeta||{};
          const slot=Object.keys(meta).find(s=>meta[s].data===todayStr());
          const noBkp=((raiz.vdn_v1_bkp||{})[slot]||{}).dicas||[];
          // apaga uma dica depois do backup e cria outra; restaurar traz a apagada de volta e
          // nao some com a criada depois
          const alvo=db.dicas.find(d=>d.titulo==='Cujo');
          dicaApagar(alvo.id);
          db.dicas.push(dicaNormalizar({tipo:'dica',kingdomId:'kPt',titulo:'Depois do backup',regra:'x'}));
          const antes=db.dicas.length;
          restoreFromBackup(slot);
          await new Promise(r=>setTimeout(r,300));
          return {slot,noBkp:noBkp.length,antes,depois:db.dicas.length,
                  voltou:db.dicas.some(d=>d.id===alvo.id),lapide:!!dicasLapides[alvo.id],
                  ficou:db.dicas.some(d=>d.titulo==='Depois do backup')};}""")
        print('   cópia "%s" tem %s dicas · restaurar: %s → %s (a apagada voltou: %s, a nova ficou: %s)'
              %(r['slot'],r['noBkp'],r['antes'],r['depois'],r['voltou'],r['ficou']))
        assert r['noBkp']>=28 and r['voltou'] and not r['lapide'] and r['ficou'] and r['depois']==r['antes']+1
        await page.wait_for_timeout(1900)
        print('   OK\n')

        print('=== L) recarregar a pagina (mesmo aparelho) ===')
        estadoA=await page.evaluate("()=>({n:db.dicas.length,ids:db.dicas.map(d=>d.id).sort(),sei:Object.keys(db.dicasEstado).filter(dicaSei)})")
        salvo=await nuvem(page)
        await page.close()
        _,page,errs2=await abrir(browser,salvo['v1'],salvo['dicas'],ctx=ctxA)
        r=await page.evaluate("""()=>{showScreen('dicas');
          return {n:db.dicas.length,ids:db.dicas.map(d=>d.id).sort(),sei:Object.keys(db.dicasEstado).filter(dicaSei),
                  apagadaVoltou:db.dicas.some(d=>d.titulo==='Mau × mal'),
                  cards:document.querySelectorAll('#dicas-corpo .dica-card').length};}""")
        print('   %s dicas (antes: %s) · "já sei": %s · a apagada voltou: %s · cartões na tela: %s'
              %(r['n'],estadoA['n'],r['sei'],r['apagadaVoltou'],r['cards']))
        assert r['ids']==estadoA['ids'] and r['sei']==estadoA['sei'] and not r['apagadaVoltou']
        assert r['cards']==r['n']-len(r['sei'])
        print('   OK\n')

        print('=== M) outro aparelho (sem cache local nenhum) ===')
        ctxB,pageB,errsB=await abrir(browser,salvo['v1'],salvo['dicas'])
        r=await pageB.evaluate("""()=>({n:db.dicas.length,ids:db.dicas.map(d=>d.id).sort(),
          sei:Object.keys(db.dicasEstado).filter(dicaSei)})""")
        print('   %s dicas, "já sei" %s — igual ao primeiro aparelho: %s'%(r['n'],r['sei'],r['ids']==estadoA['ids']))
        assert r['ids']==estadoA['ids'] and r['sei']==estadoA['sei']
        # A apaga uma dica e edita outra; B abre de novo com o cache dele (que ainda tem as
        # duas como eram). A lapide e a edicao mais nova tem que vencer o cache velho de B.
        r=await page.evaluate("""async()=>{
          const a=db.dicas.find(d=>d.titulo==='Implicar (= acarretar)');
          dicaApagar(a.id);
          const i=db.dicas.findIndex(d=>d.titulo==='Preferir');
          db.dicas[i]={...db.dicas[i],regra:'Editada no aparelho A.',editadaEm:dicasAgora()};
          dicasSalvar(true);
          await new Promise(r=>setTimeout(r,300));
          return a.id;}""")
        apagadaEmA=r
        salvoA=await nuvem(page)
        # B ficou com o cache local antigo e, sem internet, criou uma dica que a nuvem nao viu
        await pageB.evaluate("""async()=>{DICAS_REF=null;
          db.dicas.push(dicaNormalizar({tipo:'dica',kingdomId:'kEnf',titulo:'Criada offline no B',regra:'x'}));
          dicasSalvar(true);await new Promise(r=>setTimeout(r,300));}""")
        await pageB.close()
        _,pageB,errsB2=await abrir(browser,salvoA['v1'],salvoA['dicas'],ctx=ctxB)
        r=await pageB.evaluate("""(id)=>({apagadaVoltou:db.dicas.some(d=>d.id===id),
          preferir:db.dicas.find(d=>d.titulo==='Preferir').regra,
          offline:db.dicas.some(d=>d.titulo==='Criada offline no B')})""",apagadaEmA)
        await pageB.wait_for_timeout(400)
        subiu=await pageB.evaluate("()=>(window.__root.users.TEST_UID_LEO.vdn_dicas||[]).some(d=>d.titulo==='Criada offline no B')")
        print('   B reabre: apagada em A voltou=%s · edição de A chegou: "%s" · criada offline em B ficou=%s e subiu=%s'
              %(r['apagadaVoltou'],r['preferir'],r['offline'],subiu))
        assert not r['apagadaVoltou'] and r['preferir']=='Editada no aparelho A.' and r['offline'] and subiu
        print('   OK\n')

        print('=== N) trava de plano ===')
        ctxT,pageT,errsT=await abrir(browser,seed({'plan':'trial','trialStartedAt':'2020-01-01'}))
        r=await pageT.evaluate("""()=>{showScreen('dicas');
          return {acesso:hasFullAccess(),travada:document.getElementById('screen-locked').classList.contains('active'),
                  dicas:document.getElementById('screen-dicas').classList.contains('active'),
                  titulo:document.getElementById('upsell-title').textContent,
                  menu:(document.querySelector('.nav-btn.active')||{}).id};}""")
        print('   teste grátis vencido: acesso=%s · tela travada=%s · "%s" · menu %s'
              %(r['acesso'],r['travada'],r['titulo'],r['menu']))
        assert not r['acesso'] and r['travada'] and not r['dicas'] and 'Dicas' in r['titulo'] and r['menu']=='nav-simgeral'
        await ctxT.close()
        print('   OK\n')

        print('=== O) 375 px e 1440 px, claro e escuro ===')
        await page.evaluate("()=>{dicasFiltroLimpar();showScreen('dicas');window.scrollTo(0,0);}")
        medidas=[]
        for tema in ['light','dark']:
            await page.evaluate("(t)=>{document.documentElement.setAttribute('data-theme',t);}",tema)
            for larg,alt in [(375,812),(1440,900)]:
                await page.set_viewport_size({'width':larg,'height':alt})
                await page.wait_for_timeout(250)
                m=await page.evaluate("""()=>{
                  const card=document.querySelector('#dicas-corpo .dica-card');
                  const grade=document.querySelector('#dicas-corpo .dica-grade');
                  const vaza=[...document.querySelectorAll('#screen-dicas *')].filter(e=>{
                    const r=e.getBoundingClientRect();return r.width&&r.right>window.innerWidth+1;}).length;
                  return {rolagemLateral:document.documentElement.scrollWidth>window.innerWidth+1,vaza,
                          colunas:new Set([...grade.children].map(c=>Math.round(c.getBoundingClientRect().left))).size,   // colunas de texto: conta pelas posicoes
                          fundo:getComputedStyle(card).backgroundColor,
                          texto:getComputedStyle(card.querySelector('.dica-titulo')).color};}""")
                m.update({'tema':tema,'largura':larg})
                medidas.append(m)
                await page.screenshot(path=os.path.join(OUT,'dicas_%s_%s.png'%(larg,'claro' if tema=='light' else 'escuro')),
                                      full_page=True,clip={'x':0,'y':0,'width':larg,'height':1500 if larg==375 else 1250})
                print('   %-5s %4spx: %s coluna(s) · rolagem lateral: %s · elementos vazando: %s · cartão %s / título %s'
                      %(tema,larg,m['colunas'],m['rolagemLateral'],m['vaza'],m['fundo'],m['texto']))
        for m in medidas:
            assert not m['rolagemLateral'] and m['vaza']==0, m
            assert m['colunas']==(1 if m['largura']==375 else 3), m
        claro=[m for m in medidas if m['tema']=='light'][0]; escuro=[m for m in medidas if m['tema']=='dark'][0]
        assert claro['fundo']=='rgb(255, 255, 255)' and escuro['fundo']=='rgb(26, 24, 48)'   # --panel dos dois temas
        assert claro['texto']!=escuro['texto']
        print('   capturas em tests/e2e/_out/dicas_{375,1440}_{claro,escuro}.png')
        print('   OK\n')

        todos=graves(errs)+graves(errs2)+graves(errsB)+graves(errsB2)+graves(errsT)
        print('erros de JS: %s'%(todos or 'nenhum'))
        assert not todos, todos
        await browser.close()
        print('OK')

# importavel (abrir() serve pra outros testes) sem rodar este
if __name__=='__main__':
    asyncio.run(main())
