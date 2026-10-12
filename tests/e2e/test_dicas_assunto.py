# -*- coding: utf-8 -*-
# Dicas, etapa 2: a dica aparece onde o assunto esta acontecendo. (1) bloco "Dicas" na
# tela do miniboss, com criar ja ligado ao assunto; (2) ao corrigir uma questao errada
# (simulado do miniboss, Simulado Geral, Modo Treino e Banco de Erros), as dicas do mesmo
# assunto aparecem — as mais ligadas ao que a questao cobrou primeiro, fora da zona de
# grifo; (3) "Virar dica" no Banco de Erros (e no resultado do simulado), no padrao do
# simEnviarParaFlashcard: abre o editor ja com o Cuidado preenchido, e a mesma questao nao
# vira duas dicas.
import asyncio, json, os, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, make_seed
from test_aba_dicas import abrir, graves, nuvem, PACOTE, OUT

Q_CE={'questao':'Na frase "O portão fica aberto desde às 7h", o uso do acento grave está correto.',
      'formato':'certoerrado','alternativas':[{'letra':'C','texto':'Certo'},{'letra':'E','texto':'Errado'}],
      'correta':'E','userAnswer':'C',
      'explicacao':'Errado. REGRA: Hora exata leva artigo: às 7h. PEGADINHA: depois de "desde" não há crase — "desde as 7h".'}
Q_ME={'questao':'Assinale a frase em que o acento grave foi empregado corretamente.','formato':'multipla',
      'alternativas':[{'letra':'A','texto':'Entregou o relatório às 14h em ponto.'},
                      {'letra':'B','texto':'Entregou o relatório à partir das 14h.'},
                      {'letra':'C','texto':'Chegou à pé ao prédio do fórum.'}],
      'correta':'A','userAnswer':'B','explicacao':'Antes de verbo não há crase, e "a partir" começa com verbo.'}
Q_OK={'questao':'Item que acertei sobre crase.','formato':'certoerrado',
      'alternativas':[{'letra':'C','texto':'Certo'},{'letra':'E','texto':'Errado'}],'correta':'C','userAnswer':'C'}
# questao de regencia que fala de "preferir": a dica "Preferir" tem que vir primeiro
Q_PREF={'questao':'A frase "Prefiro estudar de manhã do que à noite" respeita a regência do verbo.','formato':'certoerrado',
        'alternativas':[{'letra':'C','texto':'Certo'},{'letra':'E','texto':'Errado'}],'correta':'E','userAnswer':'C',
        'explicacao':'Errado. Prefere-se uma coisa a outra.'}

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'kPt','name':'Português','icon':'📖','color':'#f472b6'}],
      'topics':{'kPt':[{'id':'tP','name':'Gramática','icon':'✏️','subtopics':[
        {'id':'sCrase','name':'Crase','priority':70,'studied':True,
         'simHistorico':[{'id':'h1','data':'2026-10-10','acertos':1,'total':3,'questoes':[Q_CE,Q_ME,Q_OK]}]},
        {'id':'sReg','name':'Regência verbal','priority':70,'studied':True},
        {'id':'sCol','name':'Colocação pronominal','priority':70,'studied':True}]}]}})

async def main():
    os.makedirs(OUT,exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(browser,seed())
        await page.evaluate("(t)=>{dicasImportarProcessar(t);dicasRelatorioFechar();}",open(PACOTE,encoding='utf-8').read())
        n=await page.evaluate("()=>({crase:dicasDoAssunto('sCrase').length,reg:dicasDoAssunto('sReg').length,col:dicasDoAssunto('sCol').length})")
        print('pacote importado: Crase %(crase)s · Regência verbal %(reg)s · Colocação %(col)s dicas ligadas'%n)
        assert n['crase']==1 and n['reg']>=4 and n['col']==3, n

        print('\n=== A) bloco Dicas na tela do miniboss ===')
        r=await page.evaluate("""()=>{
          openKingdom(db.kingdoms.find(k=>k.id==='kPt'));
          const btn=document.getElementById('dicas-sub-btn-sCrase');
          const vazioAntes=document.getElementById('dicas-sub-sCrase').innerHTML.trim()==='';
          btn.click();
          const wrap=document.getElementById('dicas-sub-sCrase');
          return {botao:btn.textContent.trim(),vazioAntes,aberto:wrap.classList.contains('flash-open'),
                  cards:[...wrap.querySelectorAll('.dica-card .dica-titulo')].map(x=>x.textContent),
                  botaoReg:document.getElementById('dicas-sub-btn-sReg').textContent.trim(),
                  vazioSemDica:document.getElementById('dicas-sub-btn-sCol')&&true};}""")
        print('   botão "%s" · painel só monta ao abrir: %s · aberto: %s · cartões: %s'
              %(r['botao'],r['vazioAntes'],r['aberto'],r['cards']))
        assert r['botao']=='💡 Dicas (1)' and r['vazioAntes'] and r['aberto'] and r['cards']==['Crase antes de horas']
        # "Já sei" no painel do miniboss
        r=await page.evaluate("""()=>{
          document.querySelector('#dicas-sub-sCrase .dica-btn-sei').click();
          const id=dicasDoAssunto('sCrase')[0].id;
          const card=document.querySelector('#dicas-sub-sCrase .dica-card');
          return {sei:dicaSei(id),marcado:card.classList.contains('dica-sei'),
                  ainda:!!card,botao:card.querySelector('.dica-btn-sei').textContent};}""")
        print('   "Já sei" no painel: estado %s · o cartão fica, marcado: %s · botão "%s"'%(r['sei'],r['marcado'],r['botao']))
        assert r['sei'] and r['marcado'] and r['ainda'] and 'Rever' in r['botao']
        # Nova dica no painel: modal ja ligado a materia e assunto
        await page.evaluate("()=>[...document.querySelectorAll('#dicas-sub-sCrase .dicas-sub-acoes button')].find(b=>/Nova dica/.test(b.textContent)).click()")
        r=await page.evaluate("""()=>({aberto:document.getElementById('modal').classList.contains('open'),
          titulo:document.getElementById('modal-title').textContent,
          materia:document.getElementById('dica-modal-materia').value,
          assunto:document.getElementById('dica-modal-assunto').value,
          foco:document.activeElement&&document.activeElement.id})""")
        print('   "Nova dica": modal "%s" · matéria %s · assunto %s · foco no %s'
              %(r['titulo'].strip(),r['materia'],r['assunto'],r['foco']))
        assert r['aberto'] and 'Crase' in r['titulo'] and r['materia']=='kPt' and r['assunto']=='sCrase'
        assert r['foco']=='dica-modal-titulo'
        await page.fill('#dica-modal-titulo','Crase com até')
        await page.fill('#dica-modal-regra','Com "até", a crase antes de hora é facultativa.')
        await page.click('#dica-modal-form button:has-text("Salvar")')
        r=await page.evaluate("""()=>({fechou:!document.getElementById('modal').classList.contains('open'),
          botao:document.getElementById('dicas-sub-btn-sCrase').textContent.trim(),
          cards:[...document.querySelectorAll('#dicas-sub-sCrase .dica-card .dica-titulo')].map(x=>x.textContent),
          nova:db.dicas.find(d=>d.titulo==='Crase com até')})""")
        print('   salvou: modal fechou %s · botão "%s" · cartões %s'%(r['fechou'],r['botao'],r['cards']))
        assert r['fechou'] and r['botao']=='💡 Dicas (2)' and r['cards']==['Crase antes de horas','Crase com até']
        assert r['nova']['subId']=='sCrase' and r['nova']['kingdomId']=='kPt' and r['nova']['origem']=='minha'
        # Editar a partir do miniboss leva pra aba, com o editor aberto
        r=await page.evaluate("""()=>{
          const id=db.dicas.find(d=>d.titulo==='Crase com até').id;
          document.querySelector('[id="dica-sub-'+id+'"] .dica-btn-editar').click();
          return {aba:document.getElementById('screen-dicas').classList.contains('active'),
                  editor:document.getElementById('dica-edit-titulo').value};}""")
        print('   "Editar" no painel → aba Dicas com o editor aberto: %s ("%s")'%(r['aba'],r['editor']))
        assert r['aba'] and r['editor']=='Crase com até'
        # "Ver na aba Dicas": filtro de assunto, com as que ja sei
        r=await page.evaluate("""()=>{
          dicaEditarCancelar();
          openKingdom(db.kingdoms.find(k=>k.id==='kPt'));
          [...document.querySelectorAll('#dicas-sub-sCrase .dicas-sub-acoes button')].find(b=>/Ver na aba/.test(b.textContent)).click();
          const tit=()=>[...document.querySelectorAll('#dicas-corpo .dica-titulo')].map(x=>x.textContent);
          const r={aba:document.getElementById('screen-dicas').classList.contains('active'),
                   chip:(document.querySelector('#dicas-chips-assunto .banco-chip')||{}).textContent,cards:tit()};
          // etiqueta de assunto clicavel na aba: troca o filtro pro assunto dela
          document.querySelector('#dicas-chips-assunto .banco-chip').click();
          const semFiltro=tit().length;
          const reg=db.dicas.find(d=>d.subId==='sReg');
          document.querySelector('[id="dica-'+reg.id+'"] .dica-etq-assunto').click();
          r.semFiltro=semFiltro;
          r.porEtiqueta=[...new Set([...document.querySelectorAll('#dicas-corpo .dica-card')].map(c=>
            db.dicas.find(d=>'dica-'+d.id===c.id).subId))];
          dicasFiltroLimpar();
          return r;}""")
        print('   "Ver na aba Dicas": chip "%s" · cartões %s (a "já sei" aparece)'%(r['chip'],r['cards']))
        print('   tirar o chip → %s cartões · clicar na etiqueta "Regência verbal" → só %s'%(r['semFiltro'],r['porEtiqueta']))
        assert r['aba'] and 'Crase' in r['chip'] and sorted(r['cards'])==['Crase antes de horas','Crase com até']
        assert r['semFiltro']>2 and r['porEtiqueta']==['sReg']
        print('   OK')

        print('\n=== B) ao corrigir uma questao errada, as dicas do mesmo assunto ===')
        # B1) simulado do miniboss
        r=await page.evaluate("""(qs)=>{
          const sub=simFindSub('sReg');
          simActive['sReg']={corrected:true,histId:'hx',questoes:qs};
          const div=document.createElement('div');div.innerHTML=simPanelHTML(sub);
          const caixas=[...div.querySelectorAll('.sim-q')].map(q=>!!q.querySelector('.dicas-correcao'));
          const cx=div.querySelector('.dicas-correcao');
          delete simActive['sReg'];
          return {caixas,primeira:cx.querySelector('.dica-corr-tit').textContent,
                  linhas:cx.querySelectorAll('.dica-corr').length,cab:cx.querySelector('.dicas-correcao-cab').textContent.trim(),
                  rotulo:cx.querySelector('.dica-corr-txt b').textContent};}""",[Q_PREF,Q_OK])
        print('   simulado do miniboss: caixa na errada/na certa = %s'%r['caixas'])
        print('   "%s" · %s linhas · a primeira é "%s" (linha: %s)'%(r['cab'].replace('\n',' '),r['linhas'],r['primeira'],r['rotulo']))
        assert r['caixas']==[True,False] and r['primeira']=='Preferir' and r['linhas']==3
        assert 'ver as' in r['cab'] and r['rotulo']=='Cuidado'
        # B2) Simulado Geral: fora do marca-zona, e "Virar dica" so na errada
        r=await page.evaluate("""(qs)=>{
          const meta={subId:'sReg',subName:'Regência verbal',topicName:'Gramática',kingdomId:'kPt',kingdomName:'Português',kingdomIcon:'📖'};
          simGeralActive={corrected:true,formato:'certoerrado',nivel:'medio',tempoGastoSec:60,
            questoes:qs.map(q=>({...q,...meta}))};
          showScreen('simgeral');
          const q0=document.getElementById('sgres-0'),q1=document.getElementById('sgres-1');
          return {naZona:!!q0.querySelector('.marca-zona .dicas-correcao'),
                  fora:!!q0.querySelector(':scope > .dicas-correcao'),
                  naCerta:!!q1.querySelector('.dicas-correcao'),
                  virar0:[...q0.querySelectorAll('button')].some(b=>/Virar dica/.test(b.textContent)),
                  virar1:[...q1.querySelectorAll('button')].some(b=>/Virar dica/.test(b.textContent))};}""",[Q_PREF,Q_OK])
        print('   Simulado Geral: caixa fora da zona de grifo=%s (dentro=%s) · na certa=%s · "Virar dica" errada/certa=%s/%s'
              %(r['fora'],r['naZona'],r['naCerta'],r['virar0'],r['virar1']))
        assert r['fora'] and not r['naZona'] and not r['naCerta'] and r['virar0'] and not r['virar1']
        await page.evaluate("()=>[...document.querySelectorAll('#sgres-0 button')].find(b=>/Virar dica/.test(b.textContent)).click()")
        await page.fill('#dica-modal-titulo','Preferir do que (errei no simulado)')
        await page.click('#dica-modal-form button:has-text("Salvar")')
        r=await page.evaluate("""()=>({botao:[...document.querySelectorAll('#sgres-0 button')].map(b=>b.textContent.trim()).find(t=>/dica/.test(t)),
          d:db.dicas.find(d=>d.titulo==='Preferir do que (errei no simulado)')})""")
        print('   virou dica no resultado: botão agora "%s" · origem %s · assunto %s'%(r['botao'],r['d']['origem'],r['d']['subId']))
        assert r['botao']=='💡 Já virou dica' and r['d']['origem']=='erro' and r['d']['subId']=='sReg' and r['d']['deQuestao']
        await page.evaluate("()=>{simGeralActive=null;}")
        # B3) Modo Treino: so quando erra
        r=await page.evaluate("""(qs)=>{
          db.acervo=[];
          qs.forEach((q,i)=>{const{userAnswer,...limpa}=q;
            db.acervo.push({...limpa,questao:limpa.questao+' (treino)',subId:'sReg',subName:'Regência verbal',topicName:'Gramática',
              kingdomId:'kPt',kingdomName:'Português',kingdomIcon:'📖',tags:[],status:'ativa',criacao:new Date().toISOString()});});
          db.acervo.forEach(q=>q._chaveForte=acervoChave2(q));
          treinoIniciar(treinoPoolCompleto(),{titulo:'Teste dicas',ordenado:true});
          showScreen('simgeral');
          const out={};
          treinoSessao.itens.forEach((item,i)=>{
            treinoSessao.idx=i;
            const errar=item.questao.startsWith('A frase');
            treinoSelecionar(errar?item.alternativas.find(a=>a.letra!==item.correta).letra:item.correta);
            treinoConfirmarResposta();
            renderSimGeralScreen();
            out[errar?'errou':'acertou']=!!document.querySelector('#simgeral-content .dicas-correcao');
          });
          return out;}""",[Q_PREF,Q_OK])
        print('   Modo Treino: caixa quando errou=%s · quando acertou=%s'%(r['errou'],r['acertou']))
        assert r['errou'] and not r['acertou']
        # B4) dica marcada "ja sei" e errada mesmo assim: aparece com o selo e o "Rever"
        r=await page.evaluate("""()=>{
          const pref=db.dicas.find(d=>d.titulo==='Preferir');
          dicaJaSei(pref.id,'aba');
          treinoSessao.idx=treinoSessao.itens.findIndex(it=>it.questao.startsWith('A frase'));
          renderSimGeralScreen();
          const linha=()=>[...document.querySelectorAll('#simgeral-content .dica-corr')].find(l=>l.dataset.dica===pref.id);
          const antes={selo:linha().innerText.includes('já sei'),rever:!!linha().querySelector('button')};
          linha().querySelector('button').click();
          return {antes,sei:dicaSei(pref.id),depoisSelo:linha().innerText.includes('já sei'),
                  depoisBotao:!!linha().querySelector('button')};}""")
        print('   já sei + errou: selo=%s, "Rever"=%s → clicou: estado %s, selo some=%s'
              %(r['antes']['selo'],r['antes']['rever'],r['sei'],not r['depoisSelo']))
        assert r['antes']['selo'] and r['antes']['rever'] and r['sei'] is False and not r['depoisSelo'] and not r['depoisBotao']
        await page.evaluate("()=>{treinoSessao=null;treinoResumo=null;treinoTempoParar();}")
        print('   OK')

        print('\n=== C) "Virar dica" no Banco de Erros ===')
        async def erros():
            await page.evaluate("""()=>{showScreen('simgeral');
              let c=document.getElementById('treino-erros-card');
              if(!c){c=document.createElement('div');c.id='treino-erros-card';c.innerHTML='<div id="erros-list"></div>';
                document.getElementById('simgeral-content').appendChild(c);}
              errFilter='all';renderErrosScreen();}""")
        await erros()
        r=await page.evaluate("""()=>{
          const itens=[...document.querySelectorAll('#erros-list .err-item')];
          return itens.map(it=>({caixa:!!it.querySelector('.dicas-correcao'),
            virar:[...it.querySelectorAll('button')].map(b=>b.textContent.trim()).filter(t=>/dica/.test(t))}));}""")
        print('   %s erros no banco: %s'%(len(r),r))
        assert len(r)==2 and all(x['caixa'] for x in r) and all(x['virar']==['💡 Virar dica'] for x in r)
        ce=await page.evaluate("()=>getErrorBank().findIndex(it=>it.formato==='certoerrado')")
        await page.evaluate("(i)=>[...document.querySelectorAll('#erros-list .err-item')][i].querySelector('button[title^=\"Abre uma dica\"]').click()",ce)
        r=await page.evaluate("""()=>{const v=id=>document.getElementById('dica-modal-'+id).value;
          return {titulo:document.getElementById('modal-title').textContent.trim(),
                  materia:v('materia'),assunto:v('assunto'),origem:v('origem'),tituloDica:v('titulo'),
                  cuidado:v('cuidado'),regra:v('regra'),exemplos:v('exemplos')};}""")
        print('   modal "%s" · matéria %s · assunto %s · origem %s · título "%s"'
              %(r['titulo'],r['materia'],r['assunto'],r['origem'],r['tituloDica']))
        print('   Cuidado: "%s"'%r['cuidado'])
        print('   Regra:   "%s"'%r['regra'])
        print('   Exemplos: "%s"'%r['exemplos'])
        assert r['materia']=='kPt' and r['assunto']=='sCrase' and r['origem']=='erro' and r['tituloDica']==''
        assert r['cuidado']=='depois de "desde" não há crase — "desde as 7h".' and r['regra']=='Hora exata leva artigo: às 7h.'
        assert r['exemplos'].startswith('✖ ') and 'desde às 7h' in r['exemplos']
        r=await page.evaluate("""()=>{window.__toasts=[];const antes=db.dicas.length;dicasModalSalvar();
          return {antes,depois:db.dicas.length,aberto:document.getElementById('modal').classList.contains('open'),
                  toast:window.__toasts.slice(-1)[0]};}""")
        print('   sem título: "%s" · modal continua aberto: %s'%(r['toast'],r['aberto']))
        assert r['antes']==r['depois'] and r['aberto'] and 'sem título' in r['toast']
        await page.fill('#dica-modal-titulo','Crase depois de "desde"')
        await page.click('#dica-modal-form button:has-text("Salvar")')
        r=await page.evaluate("""(i)=>{
          const q=getErrorBank()[i];
          const d=db.dicas.find(x=>x.titulo==='Crase depois de "desde"');
          const itens=[...document.querySelectorAll('#erros-list .err-item')];
          return {d,chave:acervoChave2(q),
                  botoes:itens.map(it=>[...it.querySelectorAll('button')].map(b=>b.textContent.trim()).filter(t=>/dica/.test(t))[0]),
                  caixa:itens[i].querySelector('.dicas-correcao .dicas-correcao-cab').textContent};}""",ce)
        d=r['d']
        print('   salvou: origem %s · deQuestao = chave da questão: %s · exemplo errado: %s'
              %(d['origem'],d['deQuestao']==r['chave'],d['exemplos'][0]['ok'] is False))
        print('   botões agora: %s · a caixa do assunto já conta a nova: "%s"'%(r['botoes'],r['caixa'].strip()))
        assert d['origem']=='erro' and d['deQuestao']==r['chave'] and d['subId']=='sCrase' and d['exemplos'][0]['ok'] is False
        assert r['botoes'][ce]=='💡 Já virou dica' and r['botoes'][1-ce]=='💡 Virar dica' and '· 3' in r['caixa']
        # a mesma questao nao vira duas dicas: o botao leva pra dica que ja existe
        await page.evaluate("(i)=>[...document.querySelectorAll('#erros-list .err-item')][i].querySelector('.btn-green-s').click()",ce)
        r=await page.evaluate("""()=>{const d=db.dicas.find(x=>x.titulo==='Crase depois de \"desde\"');
          return {aba:document.getElementById('screen-dicas').classList.contains('active'),card:!!document.getElementById('dica-'+d.id)};}""")
        print('   "Já virou dica" leva à dica na aba: %s'%(r['aba'] and r['card']))
        assert r['aba'] and r['card']
        # multipla sem marca no comentario: o Cuidado conta o que aconteceu
        await erros()
        await page.evaluate("(i)=>[...document.querySelectorAll('#erros-list .err-item')][i].querySelector('button[title^=\"Abre uma dica\"]').click()",1-ce)
        r=await page.evaluate("""()=>({cuidado:document.getElementById('dica-modal-cuidado').value,
          exemplos:document.getElementById('dica-modal-exemplos').value})""")
        print('   múltipla, sem PEGADINHA no comentário → Cuidado: "%s"'%r['cuidado'])
        print('   exemplos: %s'%r['exemplos'].replace('\n',' | '))
        assert r['cuidado'].startswith('Marquei a B; a certa é a A (Entregou o relatório às 14h em ponto.).')
        assert 'Antes de verbo' in r['cuidado']
        assert r['exemplos']=='✔ Entregou o relatório às 14h em ponto.\n✖ Entregou o relatório à partir das 14h.'
        await page.click('#dica-modal-form button:has-text("Cancelar")')
        assert not await page.evaluate("()=>document.getElementById('modal').classList.contains('open')")
        print('   cancelar fecha sem criar nada')
        print('   OK')

        print('\n=== D) grava e sobrevive a recarregar ===')
        await page.wait_for_timeout(1900)
        salvo=await nuvem(page)
        no=[x for x in salvo['dicas'] if not x.get('apagada')]
        print('   vdn_dicas: %s dicas · de erro: %s · com deQuestao: %s'
              %(len(no),sum(1 for x in no if x.get('origem')=='erro'),sum(1 for x in no if x.get('deQuestao'))))
        assert sum(1 for x in no if x.get('deQuestao'))==2
        await page.close()
        _,page,errs2=await abrir(browser,salvo['v1'],salvo['dicas'],ctx=ctx)
        await erros()
        r=await page.evaluate("""()=>{
          openKingdom(db.kingdoms.find(k=>k.id==='kPt'));
          return {botao:document.getElementById('dicas-sub-btn-sCrase').textContent.trim(),
                  erros:[...document.querySelectorAll('#erros-list .err-item')].map(it=>
                    [...it.querySelectorAll('button')].map(b=>b.textContent.trim()).filter(t=>/dica/.test(t))[0])};}""")
        print('   depois de recarregar: miniboss "%s" · Banco de Erros %s'%(r['botao'],r['erros']))
        assert r['botao']=='💡 Dicas (3)' and '💡 Já virou dica' in r['erros'] and '💡 Virar dica' in r['erros']
        print('   OK')

        print('\n=== E) 375 px: miniboss e Banco de Erros sem vazar ===')
        for tema,larg in [('light',375),('dark',375),('light',1440)]:
            await page.evaluate("(t)=>document.documentElement.setAttribute('data-theme',t)",tema)
            await page.set_viewport_size({'width':larg,'height':900})
            r=await page.evaluate("""()=>{
              openKingdom(db.kingdoms.find(k=>k.id==='kPt'));
              // o chefao abre recolhido: sem abrir, a medida abaixo leria elementos de largura 0
              if(document.getElementById('tb-tP').style.display==='none')toggleTopic('tP');
              if(!openDicasSub.has('sCrase'))toggleDicasSub('sCrase');
              document.getElementById('dicas-sub-sCrase').scrollIntoView();
              const vaza=sel=>[...document.querySelectorAll(sel+' *')].filter(e=>{const r=e.getBoundingClientRect();
                return r.width&&r.right>window.innerWidth+1;}).length;
              const cards=[...document.querySelectorAll('#dicas-sub-sCrase .dica-card')];
              return {miniboss:vaza('#si-sCrase'),rolagem:document.documentElement.scrollWidth>window.innerWidth+1,
                      visiveis:cards.filter(c=>c.getBoundingClientRect().width>0).length,
                      colunas:getComputedStyle(document.querySelector('#dicas-sub-sCrase .dica-grade')).gridTemplateColumns.split(' ').length};}""")
            await page.wait_for_timeout(200)
            await page.screenshot(path=os.path.join(OUT,'dicas_miniboss_%s_%s.png'%(larg,tema)))
            print('   %-5s %4spx miniboss: %s cartões visíveis em %s coluna(s) · elementos vazando %s · rolagem lateral %s'
                  %(tema,larg,r['visiveis'],r['colunas'],r['miniboss'],r['rolagem']))
            assert r['visiveis']==3 and r['miniboss']==0 and not r['rolagem'], r
        await page.evaluate("()=>document.documentElement.setAttribute('data-theme','dark')")
        await page.set_viewport_size({'width':375,'height':900})
        await erros()
        await page.evaluate("()=>{document.querySelector('#erros-list .err-item .dicas-correcao').scrollIntoView({block:'center'});}")
        r=await page.evaluate("""()=>[...document.querySelectorAll('#erros-list *')].filter(e=>{const r=e.getBoundingClientRect();
                return r.width&&r.right>window.innerWidth+1;}).length""")
        await page.screenshot(path=os.path.join(OUT,'dicas_erros_375_dark.png'))
        print('   Banco de Erros 375px: elementos vazando %s'%r)
        assert r==0
        print('   capturas em tests/e2e/_out/dicas_miniboss_*.png e dicas_erros_375_dark.png')
        print('   OK\n')

        todos=graves(errs)+graves(errs2)
        print('erros de JS: %s'%(todos or 'nenhum'))
        assert not todos, todos
        await browser.close()
        print('OK')

if __name__=='__main__':
    asyncio.run(main())
