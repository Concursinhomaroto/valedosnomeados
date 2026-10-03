# -*- coding: utf-8 -*-
# Redesign, Parte B — Missão do dia. A missão só LÊ o banco (o plano mora no localStorage)
# e cada item abre a tela de sempre; o progresso sai do que o app já grava. Este teste
# percorre: montagem sem gravar, um item de cada tipo concluído pelos caminhos normais,
# pular, recarregar no meio, chave desligada, "tudo em dia", meta batida, localStorage
# indisponível, virada de dia e o mesmo efeito no banco que o caminho antigo.
import asyncio, json, sys, datetime
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

hoje=(datetime.datetime.utcnow()-datetime.timedelta(hours=3)).date()
def d(n): return (hoje+datetime.timedelta(days=n)).isoformat()

def seed(extra=None):
    subsE=[{'id':'e%d'%i,'name':'Enf %d'%i,'priority':70,'studied':True,'studiedAt':d(-60)} for i in range(3)]
    subsP=[{'id':'p%d'%i,'name':'Port %d'%i,'priority':70,'studied':True,'studiedAt':d(-60),
            'simStats':{'questoesTotal':10,'acertosTotal':2,'tentativas':1}} for i in range(2)]
    fc={}
    for i in range(6):
        cid='c%d'%i
        fc[cid]={'id':cid,'mbId':'tP','subId':'p0','pergunta':'P%d?'%i,'resposta':'R','acertos':1,'erros':1,
                 'dificuldade':2,'criacao':d(-30)+'T12:00:00.000Z','ultimaRevisao':d(-10)+'T12:00:00.000Z','sm2':{'interval':2}}
    s=make_seed({'studyNickname':'Leo','dailyGoalMinutes':60,'xp':500,
      'kingdoms':[{'id':'kE','name':'Enfermagem','icon':'💉'},{'id':'kP','name':'Português','icon':'📖'}],
      'topics':{'kE':[{'id':'tE','name':'Urgência','icon':'⚔️','subtopics':subsE}],
                'kP':[{'id':'tP','name':'Gramática','icon':'⚔️','subtopics':subsP}]},
      'revisions':{'p0':[{'date':d(-20),'completed':False}],'p1':[{'date':d(-5),'completed':False}],
                   'e0':[{'date':d(-2),'completed':False}],'e1':[{'date':d(30),'completed':False}],
                   'e2':[{'date':d(40),'completed':False}]},
      'flashcards':fc})
    if extra: s.update(extra)
    return s

ACERVO="""()=>{db.acervo=[];
  for(let j=0;j<12;j++){const q={questao:'Questão '+j+' de Port 0: julgue o item.',correta:j%2?'C':'E',formato:'certoerrado',
    alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],explicacao:'x',subId:'p0',subName:'Port 0',
    topicName:'Gramática',kingdomId:'kP',kingdomName:'Português',kingdomIcon:'📖'};
    db.acervo.push({...q,_chaveForte:acervoChave2(q),...acervoCamposNovos('ia'),vezesRespondida:3,acertos:0,erros:3,ultimoResultado:'X'});}
  return db.acervo.length;}"""
CONTA="""()=>{window.__saves=0;const o=window.saveDB;window.saveDB=function(){window.__saves++;return o.apply(this,arguments)};
  try{Object.keys(localStorage).filter(k=>k.indexOf('vdn_missao')===0).forEach(k=>localStorage.removeItem(k));}catch(e){}
  missaoMem=null;return true;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)
        await page.evaluate(CONTA)

        print('=== A) montar e olhar a missão não grava nada no banco ===')
        r=await page.evaluate("""()=>{window.__saves=0;
          for(let i=0;i<3;i++){showScreen('map');showScreen('dashboard');}
          missaoAbrir();closeModal();missaoAbrir();closeModal();updateRevBadge();
          const m=missaoAtual();
          return {saves:window.__saves,tipos:m.itens.map(i=>i.tipo),nomes:m.itens.map(i=>i.nome),
                  fila:revCandidatos().map(c=>c.sub.name),orc:m.orc,criada:m.criadaEm};}""")
        print('   %s'%r)
        assert r['saves']==0, 'visualizar Painel/Missão não pode chamar saveDB'
        assert r['tipos'][0]=='rev' and 'fc' in r['tipos'] and 'q' in r['tipos']
        assert r['nomes'][0]==r['fila'][0], 'a missão começa pelo topo da fila oficial'
        print('   OK\n')

        print('=== B) a missão é estável no dia (gerada uma vez) ===')
        r2=await page.evaluate("()=>{showScreen('dashboard');return missaoGarantir().criadaEm;}")
        assert r2==r['criada']
        print('   OK\n')

        print('=== C) revisão: Começar abre a tela de revisão de sempre; "Revisei" conclui o item ===')
        r=await page.evaluate("""async()=>{const m=missaoAtual();const it=m.itens[0];
          missaoComecarItem(0);
          const aberto=document.getElementById('modal').classList.contains('open')&&document.getElementById('modal').classList.contains('modal-wide');
          const barra=!!document.getElementById('missao-barra');
          const xp0=db.xp;
          revConcluirDaFila(it.subId,4);   // o mesmo que o botão "Revisei" da tela
          closeModal();missaoTick();
          const e=missaoEstado(missaoAtual());
          return {aberto,barra,feito:e.itens[0].feito,feitos:e.feitos,total:e.total,xpGanho:db.xp-xp0,
                  barraTxt:document.getElementById('missao-barra').textContent.replace(/\\s+/g,' ')};}""")
        print('   %s'%r)
        assert r['aberto'] and r['barra'] and r['feito'] and r['feitos']==1
        assert ('Missão: 1 de %d'%r['total']) in r['barraTxt']
        print('   OK\n')

        print('=== G) recarregar a página no meio: a missão e a barra continuam ===')
        criada=await page.evaluate("()=>missaoAtual().criadaEm")
        await page.reload(); await page.wait_for_timeout(2500)
        r=await page.evaluate("()=>({criada:(missaoAtual()||{}).criadaEm,barra:!!document.getElementById('missao-barra')})")
        await page.evaluate(ACERVO)   # o mock do Firebase recomeça a cada carga; o acervo volta igual
        print('   %s'%r)
        assert r['criada']==criada and r['barra']
        print('   OK\n')

        print('=== D) pular um item só mexe na missão ===')
        r=await page.evaluate("""()=>{const antes=JSON.stringify(db.revisions);
          const e0=missaoEstado(missaoAtual());const i=e0.atual.i;
          missaoPular(i);closeModal();
          const e=missaoEstado(missaoAtual());
          return {pulado:e.itens[i].pulado,mudouBanco:antes!==JSON.stringify(db.revisions),novoAtual:e.atual?e.atual.i:null,i};}""")
        print('   %s'%r)
        assert r['pulado'] and not r['mudouBanco'] and r['novoAtual']!=r['i']
        print('   OK\n')

        print('=== E) flashcards: Começar abre o estudo dos vencidos do chefão; responder conclui ===')
        r=await page.evaluate("""()=>{const m=missaoAtual();const i=m.itens.findIndex(x=>x.tipo==='fc');const it=m.itens[i];
          missaoComecarItem(i);
          const tela=document.getElementById('screen-flashcards').classList.contains('active');
          const chefao=fcSelectedMb&&fcSelectedMb.id;
          getAllFCForTopic(it.topicId).filter(c=>fcStatus(c)==='due').slice(0,it.alvo).forEach(c=>fcStudyConf(c.id,3));
          missaoTick();
          return {tela,chefao,alvo:it.alvo,feito:missaoEstado(missaoAtual()).itens[i].feito};}""")
        print('   %s'%r)
        assert r['tela'] and r['chefao']=='tP' and r['feito']
        print('   OK\n')

        print('=== F) questões: Começar abre o treino do assunto; responder o alvo conclui ===')
        r=await page.evaluate("""()=>{const m=missaoAtual();const i=m.itens.findIndex(x=>x.tipo==='q');const it=m.itens[i];
          missaoComecarItem(i);
          const sessao=!!treinoSessao&&treinoSessao.itens.every(q=>q.subId===it.subId);
          for(let k=0;k<it.alvo&&treinoSessao;k++){const q=treinoSessao.itens[treinoSessao.idx];
            treinoSelecionar(q.correta);treinoConfirmarResposta();if(k<it.alvo-1)treinoProxima();}
          missaoTick();
          return {sessao,alvo:it.alvo,feito:missaoEstado(missaoAtual()).itens[i].feito};}""")
        print('   %s'%r)
        assert r['sessao'] and r['feito']
        print('   OK\n')

        print('=== H) chave desligada: Painel volta ao botão antigo ===')
        r=await page.evaluate("""()=>{missaoLigar(false);showScreen('dashboard');
          const cta=document.getElementById('missao-cta').textContent;
          const amostraVisivel=getComputedStyle(document.getElementById('dash-overdue-revs')).display!=='none';
          let abriu='';const o=window.abrirRevisoesAtrasadas;window.abrirRevisoesAtrasadas=()=>{abriu='fila'};
          missaoAbrir();window.abrirRevisoesAtrasadas=o;
          const badge=document.getElementById('rev-badge').textContent, atr=String(numerosDoDia().atrasadas);
          const barra=!!document.getElementById('missao-barra');
          missaoLigar(true);
          return {cta,amostraVisivel,abriu,badge,atr,barra,classe:document.body.classList.contains('missao-ligada')};}""")
        print('   %s'%r)
        assert 'ligar a Missão' in r['cta'] and r['amostraVisivel'] and r['abriu']=='fila'
        assert r['badge']==r['atr'] and not r['barra'] and r['classe']
        print('   OK\n')

        print('=== I) números com unidade e iguais em todo lugar ===')
        r=await page.evaluate("""()=>{showScreen('dashboard');const n=numerosDoDia();
          showScreen('revisions');const barra=document.getElementById('revisions-list').innerText;
          showScreen('dashboard');
          return {atr:n.atrasadas,cota:n.cabemHoje,naVez:n.naVez,badge:document.getElementById('rev-badge').textContent,
            title:document.getElementById('rev-badge').title,faixa:document.getElementById('dash-atrasadas-val').textContent,
            faixaSub:document.getElementById('dash-atrasadas-sub').textContent,
            stats:[...document.querySelectorAll('#dash-stats .stat-card')].map(c=>c.querySelector('.stat-val').textContent+' '+c.querySelector('.stat-lbl').textContent),
            revTela:/ASSUNTOS NA VEZ/i.test(barra)&&/CABEM HOJE/i.test(barra)};}""")
        print('   %s'%r)
        assert r['badge']==str(r['cota']) and r['faixa']==str(r['cota'])
        assert ('%d atrasado'%r['atr']) in r['title'] and ('%d atrasado'%r['atr']) in r['faixaSub']
        assert any(('%d Assuntos atrasados'%r['atr']).upper() in s.upper() for s in r['stats'])
        assert r['revTela']
        print('   OK\n')

        print('=== J) mesmo efeito no banco que o caminho antigo ===')
        r=await page.evaluate("""()=>{
          const sub=revCandidatos()[0].sub.id;
          const snap=JSON.stringify(db.revisions);
          const limpa=v=>JSON.stringify(JSON.parse(v)[sub].map(x=>({date:x.date,completed:!!x.completed,quality:x.quality})));
          // caminho antigo equivalente: botão "Revisar" da fila (abre a tela) e concluir nela
          abrirRevisoesAtrasadas();revAbrirTela(sub);revConcluirDaFila(sub,4);closeModal();const viaAntigo=limpa(JSON.stringify(db.revisions));
          db.revisions=JSON.parse(snap);
          localStorage.removeItem('vdn_missao_'+todayStr());missaoMem=null;
          const m=missaoGarantir();const i=m.itens.findIndex(x=>x.subId===sub);
          missaoComecarItem(i);revConcluirDaFila(sub,4);closeModal();const viaMissao=limpa(JSON.stringify(db.revisions));
          return {iguais:viaAntigo===viaMissao,viaAntigo,viaMissao};}""")
        print('   %s'%r)
        assert r['iguais']
        print('   OK\n')

        print('=== K) bordas: meta batida, localStorage fora, virada do dia, tudo em dia ===')
        r=await page.evaluate("""()=>{
          db.sessions={};db.sessions[todayStr()]=70*60;
          localStorage.removeItem('vdn_missao_'+todayStr());missaoMem=null;
          const curta=missaoMontar();
          const gi=Storage.prototype.getItem,si=Storage.prototype.setItem;
          Storage.prototype.getItem=()=>{throw new Error('privado')};Storage.prototype.setItem=()=>{throw new Error('privado')};
          missaoMem=null;let semLS=null;
          try{semLS=missaoGarantir().itens.length;missaoAbrir();closeModal();}finally{Storage.prototype.getItem=gi;Storage.prototype.setItem=si;}
          const ts=window.todayStr;const amanha=addDays(ts(),1);window.todayStr=()=>amanha;
          const outroDia=missaoAtual();window.todayStr=ts;
          const k=db.kingdoms,t=db.topics,f=db.flashcards,a=db.acervo;
          db.kingdoms=[];db.topics={};db.flashcards={};db.acervo=[];missaoMem=null;localStorage.removeItem('vdn_missao_'+todayStr());
          missaoAbrir();const vazio=document.getElementById('modal-body').innerText;closeModal();
          db.kingdoms=k;db.topics=t;db.flashcards=f;db.acervo=a;
          return {curta:curta.curta,orc:curta.orc,semLS,outroDia,vazio:vazio.indexOf('Tudo em dia')>=0};}""")
        print('   %s'%r)
        assert r['curta'] and r['orc']==15 and r['semLS']>0 and r['outroDia'] is None and r['vazio']
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
