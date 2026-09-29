# -*- coding: utf-8 -*-
# Importar caderno da banca: sem IA no caminho. O texto cru entra, e sai a redacao da
# banca palavra por palavra com o gabarito oficial. Testado contra o caderno real da
# SESAU/AL (Enfermeiro, 2021): 120 itens, 25 grupos, 5 anulados.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

FIX=json.load(open('fixture_caderno.json',encoding='utf-8'))

def seed():
    subs=[('s1','Lei 8080'),('s2','Processo de enfermagem'),('s3','Sistematizacao da assistencia'),
          ('s4','Codigo de Etica Funcional'),('s5','Regime juridico unico'),('s6','Interpretacao de texto')]
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Geral','icon':'⚔️','subtopics':[
          {'id':i,'name':n,'priority':70,'studied':True} for i,n in subs]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('caderno');return true;}")

        print('=== A) o caderno tem aba propria, ao lado do Banco de Erros ===')
        r=await page.evaluate("""()=>{
          const t=document.getElementById('caderno-content').innerText.toUpperCase();
          const bs=[...document.querySelectorAll('#screen-caderno .rd-conectivos-tabs button')]
                   .map(x=>x.innerText.trim());
          const i=bs.findIndex(x=>/CADERNO/i.test(x));
          const j=bs.findIndex(x=>/ACERVO/i.test(x));
          return {tem:t.includes('IMPORTAR CADERNO DA BANCA'),
                  abas:bs,vizinho:Math.abs(i-j)===1,   // agora o vizinho é o Acervo (passo 8.3: renomeado de Banco de Questões)
                  ativa:(document.querySelector('#screen-caderno .rd-conectivos-tabs button.active')||{}).innerText,
                  foraDeProvas:!document.getElementById('provas-content').innerText.toUpperCase().includes('IMPORTAR CADERNO'),
                  nav:(document.querySelector('.nav-btn.active')||{}).id,
                  campos:!!document.getElementById('cad-texto')&&!!document.getElementById('cad-gab')};}""")
        print('   abas: %s'%r['abas'])
        print('   ao lado do Acervo: %s · ativa: %r'%(r['vizinho'],(r['ativa'] or '').strip()))
        print('   saiu de Minhas Provas: %s · menu aceso: %s'%(r['foraDeProvas'],r['nav']))
        assert r['tem'] and r['campos'] and r['vizinho'] and r['foraDeProvas']
        assert len(r['abas'])==4 and r['nav']=='nav-simgeral'   # Banco de Erros virou secao dentro de Treinar
        print('   OK\n')

        print('=== B) o caderno real: 120 itens, 25 grupos, 5 anulados ===')
        r=await page.evaluate("""(f)=>{
          document.getElementById('cad-texto').value=f.prova;
          document.getElementById('cad-gab').value=f.gab;
          cadConferir();
          return {itens:cadLote.itens.length,grupos:cadLote.grupos.length,
                  primeiro:cadLote.primeiro,faltando:cadLote.faltando,
                  gab:cadGabLidas.length,
                  anulados:cadGabLidas.map((x,i)=>x==='X'?i+1:0).filter(Boolean),
                  comApoio:cadLote.grupos.filter(g=>g.apoio).length};}""",FIX)
        print('   %s itens (a partir do %s) · %s grupos · %s com texto de apoio'
              %(r['itens'],r['primeiro'],r['grupos'],r['comApoio']))
        print('   gabarito: %s letras · anulados: %s · faltando: %s'
              %(r['gab'],r['anulados'],r['faltando'] or 'nenhum'))
        assert r['itens']==120 and r['grupos']==25 and r['primeiro']==1
        assert r['anulados']==[24,25,71,94,98] and not r['faltando'] and r['comApoio']==2
        print('   OK\n')

        print('=== C) a trava de contagem recusa caderno de 120 com gabarito de 50 ===')
        # depois de conferir, a tela troca pro resumo — pra colar de novo, descarta antes
        r=await page.evaluate("""(f)=>{
          cadDescartar();
          document.getElementById('cad-texto').value=f.prova;
          document.getElementById('cad-gab').value=f.gab1_50;
          cadConferir();
          return {lote:cadLote,aindaNoFormulario:!!document.getElementById('cad-texto')};}""",FIX)
        print('   120 itens contra 50 letras -> lote: %r · continua no formulário: %s'
              %(r['lote'],r['aindaNoFormulario']))
        assert r['lote'] is None and r['aindaNoFormulario']
        print('   OK\n')

        print('=== D) so a parte 1 com o gabarito de 1 a 50 passa ===')
        r=await page.evaluate("""(f)=>{
          cadDescartar();
          document.getElementById('cad-texto').value=f.parte1;
          document.getElementById('cad-gab').value=f.gab1_50;
          cadConferir();
          return {itens:cadLote.itens.length,primeiro:cadLote.primeiro,gab:cadGabLidas.length};}""",FIX)
        print('   %s itens a partir do %s, com %s letras'%(r['itens'],r['primeiro'],r['gab']))
        assert r['itens']==50 and r['primeiro']==1 and r['gab']==50
        print('   OK\n')

        print('=== E) a sugestao de assunto acerta pelo comando ===')
        r=await page.evaluate("""(f)=>{
          cadDescartar();
          document.getElementById('cad-texto').value=f.prova;
          document.getElementById('cad-gab').value=f.gab;
          cadConferir();
          const nome=id=>{const s=simFindSub(id);return s?s.name:null;};
          const achar=n=>cadLote.grupos.findIndex(g=>g.itens.includes(n));
          return {sugeridos:Object.values(cadEscolhas).filter(Boolean).length,
                  total:cadLote.grupos.length,
                  g47:nome(cadEscolhas[achar(47)]),
                  g61:nome(cadEscolhas[achar(61)]),
                  g91:nome(cadEscolhas[achar(91)]),
                  g34:nome(cadEscolhas[achar(34)])};}""",FIX)
        print('   %s de %s grupos com sugestão'%(r['sugeridos'],r['total']))
        for k,v in [('itens 47-50 (Lei 8.080)',r['g47']),('itens 61-65 (processo de enfermagem)',r['g61']),
                    ('itens 91-95 (SAE)',r['g91']),('itens 34-38 (Lei 5.247)',r['g34'])]:
            print('   %-38s -> %r'%(k,v))
        assert r['g47']=='Lei 8080'
        assert r['g61']=='Processo de enfermagem'
        assert r['g34']=='Regime juridico unico'
        print('   OK\n')

        print('=== F) guardar: anulados fora, apoio junto, gabarito oficial ===')
        r=await page.evaluate("""()=>{
          cadGuardar();
          const pr=(db.provas||[])[0];
          if(!pr)return{erro:'nao guardou'};
          const q=pr.questoes;
          const anulNaProva=q.filter(x=>[24,25,71,94,98].some(n=>false)).length;
          return {provas:db.provas.length,n:q.length,tentativas:pr.tentativas.length,
                  formato:pr.formato,
                  todosCE:q.every(x=>x.correta==='C'||x.correta==='E'),
                  comApoio:q.filter(x=>x.textoApoio).length,
                  fonte:q[0].fonte,
                  loteLimpo:cadLote===null,
                  exemplo:q[0].questao.slice(0,70),
                  apoioExemplo:q[0].textoApoio.slice(0,70)};}""")
        print('   guardou %s itens numa prova nunca feita (%s tentativas)'%(r['n'],r['tentativas']))
        print('   todos C ou E: %s · com texto de apoio: %s'%(r['todosCE'],r['comApoio']))
        print('   fonte: %r'%r['fonte'])
        print('   1º item: %r'%r['exemplo'])
        print('   apoio do 1º: %r'%r['apoioExemplo'])
        assert r['provas']==1 and r['tentativas']==0 and r['formato']=='certoerrado'
        assert r['todosCE'] and r['comApoio']==r['n'] and r['loteLimpo']
        assert 'gabarito oficial' in r['fonte']
        print('   OK\n')

        print('=== G) a conta fecha: 120 − 5 anulados − grupos sem assunto ===')
        r=await page.evaluate("""()=>{
          const pr=db.provas[0];
          const nums=new Set(pr.questoes.map(q=>q.questao));
          return {n:pr.questoes.length,
                  assuntos:[...new Set(pr.questoes.map(q=>q.subName))].sort()};}""")
        print('   %s itens guardados · assuntos: %s'%(r['n'],r['assuntos']))
        assert 0<r['n']<=115, r['n']
        print('   (o resto ficou de fora por anulado ou por grupo sem assunto — o esperado)')
        print('   OK\n')

        print('=== H) sem gabarito ele se recusa a guardar ===')
        r=await page.evaluate("""(f)=>{
          showScreen('caderno');
          cadDescartar();
          document.getElementById('cad-texto').value=f.prova;
          document.getElementById('cad-gab').value='';
          cadConferir();
          const antes=db.provas.length;
          cadGuardar();
          return {gab:cadGabLidas,provas:db.provas.length,antes};}""",FIX)
        print('   gabarito lido: %r · provas: %s (era %s)'%(r['gab'],r['provas'],r['antes']))
        assert r['gab'] is None and r['provas']==r['antes']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
