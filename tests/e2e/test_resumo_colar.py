# Nem todo material vem em PDF. Puxando o texto direto da lei (Planalto), antes era
# preciso salvar num arquivo so pra poder fazer upload. Agora da pra colar.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

SUB='s1'; TOPIC='t1'; KING='k1'
LEI=("Art. 11. O Enfermeiro exerce todas as atividades de enfermagem, cabendo-lhe "
     "privativamente: cuidados diretos de enfermagem a pacientes graves com risco de vida; "
     "cuidados de enfermagem de maior complexidade tecnica e que exijam conhecimentos "
     "cientificos adequados e capacidade de tomar decisoes imediatas.")

def seed():
    return make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE',
        'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
        'topics':{KING:[{'id':TOPIC,'name':'Lei do Exercicio','icon':'⚔️','subtopics':[
            {'id':SUB,'name':'Lei 7.498/1986','priority':100,'studied':True}]}]}})

MOCK = """()=>{
  window.__prompts=[];
  window.callGeminiGenerate=async(k,prompt)=>{
    window.__prompts.push(prompt);
    return 'COMPETENCIA PRIVATIVA:\\nCabe privativamente ao Enfermeiro o cuidado direto a paciente grave.\\n\\nNa pratica: paciente em choque no plantao.';
  };
  const s=simFindSub('%s');
  openResumo.add('%s');
  let h=document.getElementById('resumo-%s');
  if(!h){h=document.createElement('div');h.id='resumo-%s';document.body.appendChild(h);}
  h.innerHTML=resumoPanelHTML(s);
  return true;
}""" % (SUB,SUB,SUB,SUB)

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(MOCK)

        print('=== A) sem resumo, o painel oferece colar ===')
        r=await page.evaluate("""()=>{const h=document.getElementById('resumo-%s');
          return {colar:h.textContent.indexOf('Colar o texto direto')>=0,
                  arquivo:h.textContent.indexOf('arraste um arquivo')>=0,
                  web:h.textContent.indexOf('buscando na internet')>=0};}"""%SUB)
        print('   colar:%s · arquivo:%s · internet:%s'%(r['colar'],r['arquivo'],r['web']))
        assert r['colar'] and r['arquivo'] and r['web']
        print('   OK\n')

        print('=== B) abre a caixa vazia, com contador ===')
        r=await page.evaluate("""()=>{resumoAbrirColar('%s');
          const ta=document.getElementById('resumo-colar-%s');
          const n=document.getElementById('resumo-colar-n-%s');
          return {existe:!!ta,valor:ta?ta.value:null,contador:n?n.textContent:null,
                  foco:document.activeElement===ta};}"""%(SUB,SUB,SUB))
        print('   textarea:%s valor:%r contador:%r foco:%s'
              %(r['existe'],r['valor'],r['contador'],r['foco']))
        assert r['existe'] and r['valor']=='' and '0' in r['contador']
        print('   OK\n')

        print('=== C) texto curto demais nao gasta chamada ===')
        r=await page.evaluate("""async()=>{
          const ta=document.getElementById('resumo-colar-%s');
          ta.value='Art. 11.'; resumoGerarDoTexto('%s');
          await new Promise(r=>setTimeout(r,300));
          return {chamadas:window.__prompts.length,
                  aindaNaCaixa:!!document.getElementById('resumo-colar-%s'),
                  resumo:!!(simFindSub('%s').resumo)};}"""%(SUB,SUB,SUB,SUB))
        print('   chamadas a IA: %s · continua na caixa: %s · criou resumo: %s'
              %(r['chamadas'],r['aindaNaCaixa'],r['resumo']))
        assert r['chamadas']==0 and r['aindaNaCaixa'] and not r['resumo']
        print('   OK\n')

        print('=== D) contador acompanha o que foi colado ===')
        r=await page.evaluate("""(lei)=>{
          const ta=document.getElementById('resumo-colar-%s');
          ta.value=lei; resumoColarContou('%s');
          return {n:document.getElementById('resumo-colar-n-%s').textContent,
                  real:lei.trim().length};}"""%(SUB,SUB,SUB),LEI)
        print('   contador: %s (texto tem %s)'%(r['n'],r['real']))
        assert str(r['real']) in r['n'].replace('.','')
        print('   OK\n')

        print('=== E) gerar usa o texto colado como MATERIAL, e so ele ===')
        r=await page.evaluate("""async()=>{
          resumoGerarDoTexto('%s');
          await new Promise(r=>setTimeout(r,600));
          const s=simFindSub('%s');
          const p=window.__prompts[0]||'';
          return {chamadas:window.__prompts.length,
                  temMaterial:p.indexOf('privativamente: cuidados diretos')>=0,
                  temFechamento:p.indexOf('LEMBRETE FINAL —')>=0,
                  origem:s.resumo?s.resumo.origem:null,
                  fileName:s.resumo?s.resumo.fileName:null,
                  texto:s.resumo?s.resumo.texto.slice(0,25):null};}"""%(SUB,SUB))
        print('   chamadas: %s · material no prompt: %s · lembrete final: %s'
              %(r['chamadas'],r['temMaterial'],r['temFechamento']))
        print('   origem=%s fileName=%s texto=%r'%(r['origem'],r['fileName'],r['texto']))
        assert r['chamadas']==1 and r['temMaterial'] and r['temFechamento']
        assert r['origem']=='colado' and r['fileName']=='Texto colado'
        print('   OK\n')

        print('=== F) o painel diz de onde veio ===')
        r=await page.evaluate("""()=>{const h=document.getElementById('resumo-%s');
          return {titulo:h.querySelector('.resumo-title').textContent.trim(),
                  rodape:h.querySelector('.resumo-disclaimer').textContent.replace(/\\s+/g,' ').trim(),
                  corpo:!!h.querySelector('.resumo-body')};}"""%SUB)
        print('   titulo: %s'%r['titulo'])
        print('   rodape: %s'%r['rodape'])
        assert 'Texto colado' in r['titulo'] and 'texto que você colou' in r['rodape']
        assert 'internet' not in r['rodape'] and r['corpo']
        print('   OK\n')

        print('=== G) com resumo pronto, o botao Colar texto avisa que substitui ===')
        r=await page.evaluate("""()=>{const h=document.getElementById('resumo-%s');
          const temBtn=h.textContent.indexOf('Colar texto')>=0;
          resumoAbrirColar('%s');
          const t=document.getElementById('resumo-%s').textContent;
          return {temBtn, avisa:t.indexOf('resumo atual vai ser substituído')>=0};}"""%(SUB,SUB,SUB))
        print('   botao no cabecalho: %s · avisa que substitui: %s'%(r['temBtn'],r['avisa']))
        assert r['temBtn'] and r['avisa']
        print('   OK\n')

        print('=== H) Cancelar volta pro resumo que ja existia ===')
        r=await page.evaluate("""()=>{resumoCancelarColar('%s');
          const h=document.getElementById('resumo-%s');
          return {caixa:!!document.getElementById('resumo-colar-%s'),
                  corpo:!!h.querySelector('.resumo-body'),
                  texto:simFindSub('%s').resumo.texto.slice(0,25)};}"""%(SUB,SUB,SUB,SUB))
        print('   caixa fechou: %s · resumo de volta: %s · %r'
              %(not r['caixa'],r['corpo'],r['texto']))
        assert not r['caixa'] and r['corpo']
        print('   OK\n')

        print('=== I) texto longo vai pelo caminho de partes + consolidacao ===')
        r=await page.evaluate("""async()=>{
          window.__prompts=[];
          resumoAbrirColar('%s');
          document.getElementById('resumo-colar-%s').value='Art. 11 do Enfermeiro. '.repeat(7000);
          resumoGerarDoTexto('%s');
          await new Promise(r=>setTimeout(r,1500));
          const ps=window.__prompts;
          return {n:ps.length,
                  parciais:ps.filter(x=>x.indexOf('Isto é a parte')>=0).length,
                  consolida:ps.filter(x=>x.indexOf('Consolide tudo')>=0).length,
                  origem:simFindSub('%s').resumo.origem};}"""%(SUB,SUB,SUB,SUB))
        print('   chamadas: %s (parciais %s + consolidacao %s) · origem=%s'
              %(r['n'],r['parciais'],r['consolida'],r['origem']))
        assert r['n']>2 and r['parciais']>=2 and r['consolida']==1 and r['origem']=='colado'
        print('   OK\n')

        print('=== J) colar e corrigir nao ficam abertos ao mesmo tempo ===')
        r=await page.evaluate("""()=>{resumoAbrirColar('%s');resumoEditar('%s');
          const a=!!document.getElementById('resumo-colar-%s');
          const e=!!document.getElementById('resumo-edit-%s');
          resumoAbrirColar('%s');
          const a2=!!document.getElementById('resumo-colar-%s');
          const e2=!!document.getElementById('resumo-edit-%s');
          resumoCancelarColar('%s');
          return {depoisDeEditar:[a,e],depoisDeColar:[a2,e2]};}"""%((SUB,)*8))
        print('   apos Corrigir -> colar:%s editar:%s'%tuple(r['depoisDeEditar']))
        print('   apos Colar    -> colar:%s editar:%s'%tuple(r['depoisDeColar']))
        assert r['depoisDeEditar']==[False,True] and r['depoisDeColar']==[True,False]
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
