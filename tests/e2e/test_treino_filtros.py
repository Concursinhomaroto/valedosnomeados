# -*- coding: utf-8 -*-
# Filtros do Treino: Banca, Mundo, Chefe, Miniboss (cascata), status pessoal e extras; chips, quantidade/ordem, URL e gaveta.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed():
    sub=lambda i,n:{'id':i,'name':n,'priority':70,'studied':True,'studiedAt':'2026-01-01'}
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'},{'id':'k2','name':'Português','icon':'📖'}],
      'topics':{'k1':[{'id':'t1','name':'Saúde da Mulher','icon':'⚔️','subtopics':[sub('s1','Pré-natal'),sub('s2','Puerpério')]},
                      {'id':'t2','name':'Saúde da Criança','icon':'⚔️','subtopics':[sub('s3','Aleitamento')]}],
                'k2':[{'id':'t3','name':'Sintaxe','icon':'⚔️','subtopics':[sub('s4','Regência')]}]}})

# 4 questões por miniboss (16). s1: 2 com banca FGV; s4: 1 favorita; s2: 1 errada, 1 acertada, 1 vista
ACERVO="""()=>{db.acervo=[];const subs=[['s1','Pré-natal','Saúde da Mulher','k1','Enfermagem'],['s2','Puerpério','Saúde da Mulher','k1','Enfermagem'],
  ['s3','Aleitamento','Saúde da Criança','k1','Enfermagem'],['s4','Regência','Sintaxe','k2','Português']];
  subs.forEach(([sid,sn,tn,kid,kn])=>{for(let j=0;j<4;j++){const q={questao:'Q'+j+' '+sid+': julgue o tema '+(j===3?'zebra':'comum')+'.',correta:'C',formato:j===2?'multipla':'certoerrado',
    alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],explicacao:'.',subId:sid,subName:sn,topicName:tn,kingdomId:kid,kingdomName:kn,kingdomIcon:'x'};
    if(sid==='s1'&&j<2)q.banca='FGV';
    if(sid==='s4'&&j===0)q.favorita=true;
    if(sid==='s2'&&j===0){q.vezesRespondida=2;q.acertos=0;q.ultimoResultado='X';}
    if(sid==='s2'&&j===1){q.vezesRespondida=1;q.acertos=1;q.ultimoResultado='C';}
    const it={...q,_chaveForte:acervoChave2(q),...acervoCamposNovos('ia')};
    if(q.banca)it.banca=q.banca;if(q.favorita)it.favorita=true;
    if(q.vezesRespondida){it.vezesRespondida=q.vezesRespondida;it.acertos=q.acertos;it.ultimoResultado=q.ultimoResultado;}
    db.acervo.push(it);}});return db.acervo.length;}"""
ABRIR="()=>{window.__tfReset&&0;tf=TF_VAZIO();tfIniciado=true;tfAberto=null;tfGaveta=false;history.replaceState(null,'',location.pathname);try{localStorage.clear();}catch(e){};showScreen('simgeral');renderSimGeralScreen();return true;}"
ESTADO="""()=>{const ent=tfMontarEntradas();const o=d=>tfOpcoes(ent,d).map(x=>[x.nome,x.n]);
  return {banca:o('banca'),mundo:o('mundo'),chefe:o('chefe'),mini:o('mini'),n:tfFiltradas().length,
   bloq:[...document.querySelectorAll('.tf-sel')].map(e=>e.classList.contains('tf-bloq')),
   contador:(document.querySelector('.tf-contador b')||{}).textContent,tf:JSON.parse(JSON.stringify(tf))};}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)
        await page.evaluate(ABRIR)

        print('=== A) padrao: banca "Cebraspe (estilo)" para quem nao tem; Chefe e Miniboss bloqueados ===')
        r=await page.evaluate(ESTADO); print('   ',r['banca'],r['bloq'],r['contador'])
        assert r['banca']==[['Cebraspe (estilo)',14],['FGV',2]] and r['n']==16 and r['contador']=='16'
        assert r['bloq']==[False,False,True,True]
        print('   OK\n')

        print('=== B) cascata Mundo -> Chefe -> Miniboss, e limpeza ao trocar o de cima ===')
        await page.evaluate("()=>tfAlternar('mundo','Enfermagem',true)")
        r=await page.evaluate(ESTADO); print('   ',r['chefe'],r['bloq'])
        assert r['chefe']==[['Saúde da Mulher',8],['Saúde da Criança',4]] and r['bloq']==[False,False,False,True] and r['n']==12
        await page.evaluate("()=>tfAlternar('chefe','t1',true)")
        r=await page.evaluate(ESTADO); print('   ',r['mini'],r['bloq'])
        assert [x[0] for x in r['mini']]==['Pré-natal','Puerpério'] and r['bloq']==[False,False,False,False] and r['n']==8
        await page.evaluate("()=>tfAlternar('mini','s2',true)")
        r=await page.evaluate(ESTADO); assert r['n']==4 and r['tf']['minis']==['s2']
        await page.evaluate("()=>{tfAlternar('mundo','Português',true);tfAlternar('mundo','Enfermagem',false);}")
        r=await page.evaluate(ESTADO); print('   ',r['tf']['chefes'],r['tf']['minis'],r['chefe'])
        assert r['tf']['chefes']==[] and r['tf']['minis']==[] and r['chefe']==[['Sintaxe',4]] and r['n']==4
        print('   OK\n')

        print('=== C) Banca + Miniboss; contagem de cada opcao respeita os outros filtros ===')
        await page.evaluate("()=>{tfLimparTudo();tfAlternar('mundo','Enfermagem',true);tfAlternar('chefe','t1',true);tfAlternar('mini','s1',true);tfAlternar('banca','FGV',true);}")
        r=await page.evaluate(ESTADO); print('   ',r['n'],r['banca'])
        assert r['n']==2
        # com banca FGV marcada, as opcoes de Chefe so contam o que e FGV
        await page.evaluate("()=>{tfLimparTudo();tfAlternar('banca','FGV',true);tfAlternar('mundo','Enfermagem',true);}")
        r=await page.evaluate(ESTADO); print('   ',r['chefe'],r['mundo'])
        assert r['chefe']==[['Saúde da Mulher',2],['Saúde da Criança',0]] or r['chefe']==[['Saúde da Mulher',2]]
        assert r['mundo'][0]==['Enfermagem',2]
        print('   OK\n')

        print('=== D) contador = numero de questoes do treino gerado; quantidade e ordem ===')
        await page.evaluate("()=>{tfLimparTudo();tfAlternar('mundo','Enfermagem',true);tfAlternar('chefe','t1',true);}")
        r=await page.evaluate("""()=>{const n=tfFiltradas().length,c=document.querySelector('.tf-contador b').textContent;
          tfQtd=n;tfOrdem='aleatoria';tfComecar();const s=treinoSessao;const todas=s.itens.length;
          treinoSessao=null;treinoResumo=null;renderSimGeralScreen();
          tfQtd=3;tfOrdem='sequencial';tfComecar();const s2=treinoSessao;const seq=s2.itens.map(q=>q.subId);
          const dlg=(tfIniciarDialogo(),document.getElementById('tf-dlg')?1:0);closeModal();
          treinoSessao=null;treinoResumo=null;renderSimGeralScreen();return {n,c,todas,qtd3:s2.itens.length,seq,titulo:s2.titulo,dlg};}""")
        print('   ',r)
        assert r['c']==str(r['n']) and r['todas']==r['n']==8 and r['qtd3']==3 and r['seq']==['s1','s1','s1'] and r['titulo']=='Chefão · Saúde da Mulher'
        print('   OK\n')

        print('=== E) status pessoal, palavra-chave, formato, favoritas (filtro avancado) ===')
        r=await page.evaluate("""()=>{tfLimparTudo();const c=()=>tfFiltradas().length;const out={};
          tfSet('estado','errei');out.errei=c();tfSet('estado','acertei');out.acertei=c();tfSet('estado','resolvidas');out.resolvidas=c();tfSet('estado','naoresolvidas');out.nao=c();tfSet('estado','');
          tfSet('avancado',true);tfSet('busca','zebra');out.zebra=c();tfSet('busca','');tfSet('formato','multipla');out.multipla=c();tfSet('formato','');tfSet('fav',true);out.fav=c();tfSet('fav',false);
          out.campos=!!document.getElementById('tf-busca-txt');tfSet('avancado',false);out.simples=!document.getElementById('tf-busca-txt');return out;}""")
        print('   ',r)
        assert r=={'errei':1,'acertei':1,'resolvidas':2,'nao':14,'zebra':4,'multipla':4,'fav':1,'campos':True,'simples':True}
        print('   OK\n')

        print('=== F) chips com X e Limpar filtros ===')
        r=await page.evaluate("""()=>{tfLimparTudo();tfAlternar('banca','FGV',true);tfAlternar('mundo','Enfermagem',true);tfSet('estado','resolvidas');
          const chips=[...document.querySelectorAll('.tf-chip')].map(x=>x.textContent.replace(/\\s+/g,' ').trim());
          document.querySelector('.tf-chip .tf-x').click();const dep=[...document.querySelectorAll('.tf-chip')].length;
          tfLimparTudo();return {chips,dep,fin:document.querySelectorAll('.tf-chip').length,n:tfFiltradas().length};}""")
        print('   ',r)
        assert r['chips'][0].startswith('Banca: FGV') and len(r['chips'])==3 and r['dep']==2 and r['fin']==0 and r['n']==16
        print('   OK\n')

        print('=== G) filtros na URL e na memoria do aparelho ===')
        r=await page.evaluate("""()=>{tfLimparTudo();tfAlternar('banca','FGV',true);tfAlternar('mundo','Enfermagem',true);tfAlternar('chefe','t1',true);tfSet('estado','naoresolvidas');tfSet('busca','tema');
          const url=location.search,guard=localStorage.getItem('vdn_tf_'+((typeof currentUser!=='undefined'&&currentUser&&currentUser.uid)||''));
          tf=TF_VAZIO();tfIniciado=false;tfIniciar();const daUrl=JSON.parse(JSON.stringify(tf));
          history.replaceState(null,'',location.pathname);tf=TF_VAZIO();tfIniciado=false;tfIniciar();const daMemoria=JSON.parse(JSON.stringify(tf));
          history.replaceState(null,'',location.pathname+'?f_mundo=Inexistente&f_estado=lixo&f_formato=x&f_nivel=y');tf=TF_VAZIO();tfIniciado=false;tfIniciar();const ruim=JSON.parse(JSON.stringify(tf));
          const lixoLimpo=(()=>{showScreen('simgeral');renderSimGeralScreen();return tfFiltradas().length;})();
          return {url,guard:!!guard,daUrl,daMemoria,ruim,lixoLimpo,filtroAposLimpar:JSON.parse(JSON.stringify(tf)),outros:new URLSearchParams(url).get('plano')};}""")
        print('   ',r['url'])
        assert 'f_banca=FGV' in r['url'] and 'f_mundo=Enfermagem' in r['url'] and 'f_chefe=t1' in r['url'] and r['guard']
        for k in ('daUrl','daMemoria'):
            assert r[k]['bancas']==['FGV'] and r[k]['mundos']==['Enfermagem'] and r[k]['chefes']==['t1'] and r[k]['estado']=='naoresolvidas' and r[k]['busca']=='tema'
        assert r['ruim']['estado']=='' and r['ruim']['formato']=='' and r['ruim']['nivel']==''
        assert r['filtroAposLimpar']['mundos']==[],'filtro que nao existe mais e descartado'
        print('   OK\n')

        print('=== H) celular: gaveta de filtros ===')
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("""()=>{tfLimparTudo();tfAlternar('banca','FGV',true);
          const fechada=getComputedStyle(document.querySelector('.tf-corpo')).display;
          tfGavetaAlternar();const rc=document.querySelector('.tf-corpo').getBoundingClientRect();const aberta=getComputedStyle(document.querySelector('.tf-corpo')).display;const pos=getComputedStyle(document.querySelector('.tf-corpo')).position;
          const w=document.documentElement.scrollWidth;const botao=document.querySelector('.tf-abre-gaveta').textContent.trim();
          tfGavetaAlternar();return {fechada,aberta,pos,w,iw:innerWidth,botao,visivel:rc.top<innerHeight&&rc.bottom<=innerHeight+1&&rc.height>100};}""")
        print('   ',r)
        assert r['fechada']=='none' and r['aberta']=='flex' and r['pos']=='fixed' and r['w']<=r['iw']+1 and '(1)' in r['botao'] and r['visivel'],'a gaveta tem que aparecer na tela (nao presa no cartao)'
        await page.set_viewport_size({'width':1200,'height':900})
        print('   OK\n')

        print('=== I) banca definida a mao (editor) aparece como opcao ===')
        r=await page.evaluate("""()=>{tfLimparTudo();const it=db.acervo.find(q=>q.subId==='s3');
          bancoAplicarEdicao(it,{questao:it.questao,formato:it.formato,alternativas:it.alternativas,correta:it.correta,explicacao:'.',fonte:'',tags:[],favorita:false,status:'ativa',banca:'Cebraspe'});
          const o=tfOpcoes(tfMontarEntradas(),'banca').map(x=>[x.nome,x.n]);return {o,ed:!!(bancoEditorHTML||0)};}""") if False else None
        r=await page.evaluate("""()=>{tfLimparTudo();const it=db.acervo.find(q=>q.subId==='s3');
          bancoAplicarEdicao(it,{questao:it.questao,formato:it.formato,alternativas:it.alternativas,correta:it.correta,explicacao:'.',fonte:'',tags:[],favorita:false,status:'ativa',banca:'Cebraspe'});
          return tfOpcoes(tfMontarEntradas(),'banca').map(x=>[x.nome,x.n]);}""")
        print('   ',r)
        assert ['Cebraspe',1] in r and ['Cebraspe (estilo)',13] in r
        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')
asyncio.run(main())
