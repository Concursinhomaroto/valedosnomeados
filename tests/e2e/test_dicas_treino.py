# -*- coding: utf-8 -*-
# Dicas, etapa 4: treino por dica. O cartao mostra quantas questoes do Acervo sao do mesmo
# assunto e o seu acerto nelas, e o botao "Treinar" monta o Modo Treino so com elas (o
# mesmo treinoTreinarAssunto do Treinar). Responder no treino muda o numero do cartao.
import asyncio, os, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, make_seed
from test_aba_dicas import abrir, graves, PACOTE, OUT

def q(i,acertos,vezes,sub='sCrase',nome='Crase'):
    return {'questao':'Item %d de %s para o treino por dica.'%(i,nome),'formato':'certoerrado','correta':'E',
            'alternativas':[{'letra':'C','texto':'Certo'},{'letra':'E','texto':'Errado'}],'explicacao':'x',
            'subId':sub,'subName':nome,'topicName':'Gramática','kingdomId':'kPt','kingdomName':'Português',
            'kingdomIcon':'📖','status':'ativa','vezesRespondida':vezes,'acertos':acertos,'erros':vezes-acertos}

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'kPt','name':'Português','icon':'📖','color':'#f472b6'}],
      'topics':{'kPt':[{'id':'tP','name':'Gramática','icon':'✏️','subtopics':[
        {'id':'sCrase','name':'Crase','priority':70,'studied':True},
        {'id':'sReg','name':'Regência verbal','priority':70,'studied':True},
        {'id':'sCol','name':'Colocação pronominal','priority':70,'studied':True}]}]},
      # quem ja tinha acervo no registro: acervoCarregar leva pro no proprio
      'acervo':[q(1,2,3),q(2,1,2),q(3,2,3),q(4,0,0),q(5,1,1,'sCol','Colocação pronominal')]})

async def main():
    os.makedirs(OUT,exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(browser,seed(),viewport={'width':1440,'height':900})
        await page.evaluate("(t)=>{dicasImportarProcessar(t);dicasRelatorioFechar();}",open(PACOTE,encoding='utf-8').read())

        print('=== A) o cartao mostra o Acervo do assunto ===')
        r=await page.evaluate("""()=>{showScreen('dicas');
          const linha=t=>{const d=db.dicas.find(x=>x.titulo===t);const c=document.getElementById('dica-'+d.id);
            const l=c&&c.querySelector('.dica-treino');return l?{txt:l.innerText.replace(/\\s+/g,' ').trim(),botao:!!l.querySelector('button')}:null;};
          return {crase:linha('Crase antes de horas'),col:linha('Colocação pronominal: as 3 proibições'),
                  reg:linha('Preferir'),semAssunto:linha('Os porquês')};}""")
        for k,v in r.items(): print('   %-10s %s'%(k,v))
        assert r['crase']['txt'].startswith('📚 4 questões no Acervo · você acerta 63% (5 de 8)') and r['crase']['botao']
        assert 'pouca amostra' in r['col']['txt'] and '100%' in r['col']['txt']
        assert r['reg']['txt']=='📚 Nenhuma questão deste assunto no Acervo ainda' and not r['reg']['botao']
        assert r['semAssunto'] is None
        print('   OK\n')

        print('=== B) "Treinar" monta o Modo Treino so com o assunto ===')
        await page.click('[id="dica-%s"] .dica-treino button'%(await page.evaluate("()=>db.dicas.find(x=>x.titulo==='Crase antes de horas').id")))
        r=await page.evaluate("""()=>({tela:document.getElementById('screen-simgeral').classList.contains('active'),
          titulo:treinoSessao&&treinoSessao.titulo,n:treinoSessao&&treinoSessao.itens.length,
          assuntos:treinoSessao?[...new Set(treinoSessao.itens.map(i=>i.subId))]:[],
          naTela:!!document.querySelector('#simgeral-content .sim-q')})""")
        print('   tela Treinar: %s · sessão "%s" com %s questões de %s · questão na tela: %s'
              %(r['tela'],r['titulo'],r['n'],r['assuntos'],r['naTela']))
        assert r['tela'] and r['titulo']=='Crase' and r['n']==4 and r['assuntos']==['sCrase'] and r['naTela']
        # responde uma errada e volta: o numero do cartao acompanha
        r=await page.evaluate("""()=>{
          const it=treinoSessao.itens[treinoSessao.idx];
          treinoSelecionar(it.alternativas.find(a=>a.letra!==it.correta).letra);
          treinoConfirmarResposta();
          treinoSessao=null;treinoResumo=null;treinoTempoParar();
          showScreen('dicas');
          const d=db.dicas.find(x=>x.titulo==='Crase antes de horas');
          return document.getElementById('dica-'+d.id).querySelector('.dica-treino').innerText.replace(/\\s+/g,' ');}""")
        print('   depois de errar uma no treino: "%s"'%r.strip())
        assert '(5 de 9)' in r and '56%' in r
        print('   OK\n')

        print('=== C) tambem no painel do miniboss, e a busca nao recalcula o Acervo ===')
        r=await page.evaluate("""()=>{
          openKingdom(db.kingdoms[0]);
          toggleDicasSub('sCrase');
          const l=document.querySelector('#dicas-sub-sCrase .dica-treino');
          showScreen('dicas');
          let chamadas=0;const orig=window.montarAcervo;window.montarAcervo=function(){chamadas++;return orig.apply(this,arguments);};
          const b=document.getElementById('dicas-busca');
          ['c','cr','cra','cras'].forEach(t=>{b.value=t;dicasBuscar(b);});
          window.montarAcervo=orig;
          return {painel:l&&l.innerText.replace(/\\s+/g,' ').trim(),chamadas};}""")
        print('   painel do miniboss: "%s"'%r['painel'])
        print('   4 letras na busca → montarAcervo chamado %s vez(es)'%r['chamadas'])
        assert r['painel'].startswith('📚 4 questões no Acervo') and r['chamadas']==0
        print('   OK\n')

        print('=== D) 375 px ===')
        await page.evaluate("()=>{dicasFiltroLimpar();document.documentElement.setAttribute('data-theme','dark');}")
        await page.set_viewport_size({'width':375,'height':812})
        r=await page.evaluate("""()=>{const d=db.dicas.find(x=>x.titulo==='Crase antes de horas');
          const c=document.getElementById('dica-'+d.id);c.scrollIntoView({block:'center'});
          return [...document.querySelectorAll('#screen-dicas *')].filter(e=>{const r=e.getBoundingClientRect();
            return r.width&&r.right>window.innerWidth+1;}).length;}""")
        await page.wait_for_timeout(3500)
        await page.screenshot(path=os.path.join(OUT,'dicas_treino_375_escuro.png'))
        print('   elementos vazando: %s'%r)
        assert r==0
        print('   OK\n')

        todos=graves(errs)
        print('erros de JS: %s'%(todos or 'nenhum'))
        assert not todos, todos
        await browser.close()
        print('OK')

if __name__=='__main__':
    asyncio.run(main())
