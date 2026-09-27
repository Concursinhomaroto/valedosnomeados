# A IA escreveu no resumo que "o Tecnico de Enfermagem pode fazer sondagem vesical em
# paciente de menor complexidade". E privativa do Enfermeiro. O resumo alimenta
# fluxograma e revisao — o erro ficaria no app pra sempre, e a unica saida era gerar de
# novo (gasta cota e pode inventar outra). Agora da pra corrigir a mao.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

SUB='s1'; TOPIC='t1'; KING='k1'
ERRADO=('SONDAGEM VESICAL:\n'
        'O Tecnico de Enfermagem pode realizar a sondagem vesical de alivio ou de demora '
        'em pacientes de menor complexidade clinica, sob supervisao.')
CERTO=('SONDAGEM VESICAL:\n'
       'A sondagem vesical e privativa do Enfermeiro, em qualquer situacao.')

def seed():
    return make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE',
        'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
        'topics':{KING:[{'id':TOPIC,'name':'Procedimentos','icon':'⚔️','subtopics':[
            {'id':SUB,'name':'Sondagem','priority':100,'studied':True}]}]}})

MONTAR = """(txt)=>{
  const s=simFindSub('%s');
  s.resumo={texto:txt,geradoEm:'2026-09-01T10:00:00.000Z',origem:'web',grounded:true};
  openResumo.add('%s');
  let h=document.getElementById('resumo-%s');
  if(!h){h=document.createElement('div');h.id='resumo-%s';document.body.appendChild(h);}
  h.innerHTML=resumoPanelHTML(s);
  return true;
}""" % (SUB,SUB,SUB,SUB)

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(MONTAR,ERRADO)

        print('=== A) o painel oferece "Corrigir" ===')
        r=await page.evaluate("""()=>{const h=document.getElementById('resumo-%s');
          return {tem:h.innerHTML.indexOf('resumoEditar')>=0,
                  txt:h.textContent.indexOf('Corrigir')>=0};}"""%SUB)
        print('   botao presente: %s (%s)'%(r['tem'],r['txt']))
        assert r['tem'] and r['txt']
        print('   OK\n')

        print('=== B) abre o editor com o texto CRU, nao o formatado ===')
        r=await page.evaluate("""()=>{resumoEditar('%s');
          const ta=document.getElementById('resumo-edit-%s');
          const h=document.getElementById('resumo-%s');
          return {existe:!!ta, valor:ta?ta.value:null,
                  sumiuOResumoFormatado:!h.querySelector('.resumo-body')};}"""%(SUB,SUB,SUB))
        print('   textarea: %s · resumo formatado saiu da tela: %s'%(r['existe'],r['sumiuOResumoFormatado']))
        print('   prefixo do valor: %r'%(r['valor'] or '')[:40])
        assert r['existe'] and r['sumiuOResumoFormatado']
        assert r['valor']==ERRADO, repr(r['valor'])
        print('   OK\n')

        print('=== C) Cancelar joga a edicao fora ===')
        r=await page.evaluate("""()=>{
          document.getElementById('resumo-edit-%s').value='LIXO';
          resumoCancelarEdicao('%s');
          const s=simFindSub('%s');
          const h=document.getElementById('resumo-%s');
          return {texto:s.resumo.texto, editadoEm:s.resumo.editadoEm||null,
                  voltou:!!h.querySelector('.resumo-body')};}"""%(SUB,SUB,SUB,SUB))
        print('   texto intacto: %s · editadoEm: %s · painel voltou: %s'
              %(r['texto']==ERRADO,r['editadoEm'],r['voltou']))
        assert r['texto']==ERRADO and r['editadoEm'] is None and r['voltou']
        print('   OK\n')

        print('=== D) editor vazio nao apaga o resumo ===')
        r=await page.evaluate("""()=>{resumoEditar('%s');
          document.getElementById('resumo-edit-%s').value='   ';
          resumoSalvarEdicao('%s');
          const s=simFindSub('%s');
          return {texto:s.resumo.texto, aindaEditando:!!document.getElementById('resumo-edit-%s')};}"""
          %(SUB,SUB,SUB,SUB,SUB))
        print('   texto preservado: %s · continua no editor: %s'%(r['texto']==ERRADO,r['aindaEditando']))
        assert r['texto']==ERRADO and r['aindaEditando']
        print('   OK\n')

        print('=== E) salvar grava a correcao e persiste ===')
        r=await page.evaluate("""async(certo)=>{
          const antes=window.__updateCalls.length;
          document.getElementById('resumo-edit-%s').value=certo;
          resumoSalvarEdicao('%s');
          await new Promise(r=>setTimeout(r,900));
          const s=simFindSub('%s');
          const h=document.getElementById('resumo-%s');
          const gravou=window.__updateCalls.slice(antes).length>0;
          return {texto:s.resumo.texto, editadoEm:s.resumo.editadoEm||null,
                  gravou, naTela:h.textContent.indexOf('privativa do Enfermeiro')>=0,
                  sumiuOErro:h.textContent.indexOf('menor complexidade')<0,
                  saiuDoEditor:!document.getElementById('resumo-edit-%s')};}"""%(SUB,SUB,SUB,SUB,SUB),CERTO)
        print('   db.texto corrigido: %s'%(r['texto']==CERTO))
        print('   editadoEm: %s · gravou no Firebase: %s'%(r['editadoEm'],r['gravou']))
        print('   tela mostra o certo: %s · sumiu o errado: %s · saiu do editor: %s'
              %(r['naTela'],r['sumiuOErro'],r['saiuDoEditor']))
        assert r['texto']==CERTO and r['editadoEm'] and r['gravou']
        assert r['naTela'] and r['sumiuOErro'] and r['saiuDoEditor']
        print('   OK\n')

        print('=== F) o rodape avisa que foi voce, e que gerar de novo apaga ===')
        r=await page.evaluate("""()=>{const d=document.querySelector('#resumo-%s .resumo-disclaimer');
          return d?d.textContent.replace(/\\s+/g,' ').trim():null;}"""%SUB)
        print('   %s'%r)
        assert 'Corrigido por você' in r and 'apaga a sua correção' in r
        print('   OK\n')

        print('=== G) texto corrigido nao escapa do textarea (XSS) ===')
        r=await page.evaluate("""()=>{
          const s=simFindSub('%s');
          s.resumo.texto='</textarea><img src=x onerror="window.__X=1">';
          resumoEditar('%s');
          const ta=document.getElementById('resumo-edit-%s');
          return {valor:ta?ta.value:null, img:!!document.querySelector('#resumo-%s img'),
                  x:window.__X||0};}"""%(SUB,SUB,SUB,SUB))
        print('   valor no textarea: %r'%r['valor'])
        print('   virou <img> na pagina: %s · executou: %s'%(r['img'],r['x']))
        assert r['valor']=='</textarea><img src=x onerror="window.__X=1">'
        assert not r['img'] and not r['x']
        print('   OK\n')

        print('=== H) gerar de novo realmente apaga a marca (o aviso e verdade) ===')
        r=await page.evaluate("""()=>{
          const s=simFindSub('%s');
          s.resumo={texto:'novo texto da IA',geradoEm:new Date().toISOString(),origem:'web'};
          const h=document.getElementById('resumo-%s');
          h.innerHTML=resumoPanelHTML(s);
          return {editadoEm:s.resumo.editadoEm||null,
                  marca:h.textContent.indexOf('Corrigido por você')>=0};}"""%(SUB,SUB))
        print('   editadoEm: %s · marca na tela: %s'%(r['editadoEm'],r['marca']))
        assert r['editadoEm'] is None and not r['marca']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
