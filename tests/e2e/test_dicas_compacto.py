# -*- coding: utf-8 -*-
# Aba Dicas enxuta: cartao de texto vem FECHADO (so o titulo — da pra tentar lembrar antes de
# abrir), abre/fecha so ele sem refazer a lista, "Expandir tudo", rascunho e dica recem-criada
# vem aberta; filtros menos usados moram numa gaveta (com contagem de ativos e estado que
# sobrevive ao refazer dos chips); Importar/Pacotes/Colinha moram no menu "Mais"; no celular a
# primeira dica aparece sem rolar a pagina.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright
from test_aba_dicas import abrir, seed, graves

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(browser,seed(),viewport={'width':390,'height':844})
        await page.evaluate("""()=>{
          db.dicas=[];
          for(let i=0;i<12;i++)db.dicas.push(dicaNormalizar({id:'d'+i,kingdomId:'kPt',subId:'sCrase',grupo:'G'+(i%3),titulo:'Titulo '+i,
            regra:'Regra '+i,aplicar:'Aplicar '+i,cuidado:'Cuidado '+i,exemplos:'✔ ok '+i,bancas:i%2?'Cebraspe':''},'minha'));
          db.dicas.push(dicaNormalizar({id:'n',kingdomId:'kPt',tipo:'numero',titulo:'Prazo',rotulo:'Prazo do recurso',valor:'10 dias'},'minha'));
          db.dicas.push(dicaNormalizar({id:'p',kingdomId:'kPt',tipo:'par',titulo:'Mal x Mau',a:'Mal',b:'Mau',diferenca:'oposto de bom'},'minha'));
          db.dicas.push(dicaNormalizar({id:'r',kingdomId:'kPt',subId:'sCrase',titulo:'Rascunho',regra:'z',rascunho:true},'ia'));
          dicasFiltro={...DICAS_FILTRO_VAZIO};dicasFiltrosAberto=false;dicasAbertas.clear();dicasTudoAberto=false;
          showScreen('dicas');renderDicasScreen();}""")

        print('=== A) cartao de texto fechado: so titulo; numero e par seguem como eram ===')
        r=await page.evaluate("""()=>{const c=id=>document.getElementById('dica-'+id);
          return {linhasD0:c('d0').querySelectorAll('.dica-linha').length,tit:c('d0').querySelector('.dica-titulo').innerText,
                  exp:c('d0').querySelector('.dica-toggle').getAttribute('aria-expanded'),
                  numValor:!!c('n').querySelector('.dica-num-valor'),par:!!c('p').querySelector('.dica-par'),
                  rascunhoAberto:(()=>{const h=document.createElement('div');h.innerHTML=dicaCardHTML(db.dicas.find(x=>x.id==='r'),'aba');return h.querySelectorAll('.dica-linha').length;})(),rodape:!!c('d0').querySelector('.dica-rodape')};}""")
        print('   %s'%r)
        assert r['linhasD0']==0 and r['exp']=='false' and r['numValor'] and r['par'] and r['rodape'] and r['rascunhoAberto']==1   # rascunho vem aberto
        print('   OK\n')

        print('=== B) abrir um cartao nao refaz os outros ===')
        r=await page.evaluate("""()=>{const outro=document.getElementById('dica-d1');outro.__marca=1;
          document.querySelector('#dica-d0 .dica-toggle').click();
          const c0=document.getElementById('dica-d0');
          return {linhas:[...c0.querySelectorAll('.dica-linha dt')].map(x=>x.textContent.trim().replace(/^\\S+\\s/,'')),
                  ex:c0.querySelectorAll('.dica-ex').length,exp:c0.querySelector('.dica-toggle').getAttribute('aria-expanded'),
                  outroIntacto:document.getElementById('dica-d1')===outro&&outro.__marca===1,
                  foco:document.activeElement.className};}""")
        print('   %s'%r)
        assert r['linhas']==['Regra','Como aplicar','Cuidado'] and r['ex']==1 and r['exp']=='true' and r['outroIntacto'] and 'dica-toggle' in r['foco']
        await page.evaluate("()=>document.querySelector('#dica-d0 .dica-toggle').click()")
        assert await page.evaluate("()=>document.querySelectorAll('#dica-d0 .dica-linha').length")==0
        print('   OK\n')

        print('=== C) expandir tudo / recolher tudo ===')
        r=await page.evaluate("""()=>{document.querySelector('.dicas-tudo').click();
          const abertas=document.querySelectorAll('.dica-linha').length;
          const rot=document.querySelector('.dicas-tudo').textContent;
          document.querySelector('.dicas-tudo').click();
          return {abertas,rot,fechadas:document.querySelectorAll('#dica-d3 .dica-linha').length};}""")
        print('   %s'%r)
        assert r['abertas']>=36 and 'Fechar' in r['rot'] and r['fechadas']==0
        print('   OK\n')

        print('=== D) gaveta de filtros: fechada, conta ativos e nao fecha ao filtrar ===')
        r=await page.evaluate("""()=>{const g=document.getElementById('dicas-filtros');
          const antes={aberta:g.open,n:!!g.querySelector('.dicas-gaveta-n')};
          g.open=true;g.dispatchEvent(new Event('toggle'));return antes;}""")
        assert not r['aberta'] and not r['n']
        await page.wait_for_timeout(100)
        await page.click('#dicas-chips-mostrar .banco-chip:has-text("mostrar as que já sei")')
        r=await page.evaluate("""()=>{const g=document.getElementById('dicas-filtros');
          return {aberta:g.open,n:(g.querySelector('.dicas-gaveta-n')||{}).textContent,
                  temGrupo:!!g.querySelector('#dicas-chips-grupo'),temBanca:!!g.querySelector('#dicas-filtro-banca'),
                  fora:!!document.querySelector('.banco-chips-faixa > #dicas-chips-mostrar')};}""")
        print('   %s'%r)
        assert r['aberta'] and r['n']=='1' and r['temBanca'] and not r['fora']
        print('   OK\n')

        print('=== E) menu Mais guarda importar/pacotes/colinha e fecha ao usar ===')
        r=await page.evaluate("""()=>{const m=document.querySelector('.dicas-menu');
          const rot=[...m.querySelectorAll('button')].map(b=>b.textContent.trim());
          m.open=true;m.querySelector('button').click();
          return {rot,fechou:!m.open,painel:!!document.getElementById('dicas-importar')};}""")
        print('   %s'%r)
        assert len(r['rot'])==3 and r['fechou'] and r['painel']
        await page.evaluate("()=>dicasImportarCancelar()")
        print('   OK\n')

        print('=== F) celular: a primeira dica aparece sem rolar ===')
        r=await page.evaluate("""()=>{dicasFiltro={...DICAS_FILTRO_VAZIO};dicasFiltrosAberto=false;dicasFiltrarMateria('kPt');renderDicasScreen();window.scrollTo(0,0);
          const c=document.querySelector('#dicas-corpo .dica-card');const t=c.getBoundingClientRect().top;
          return {topo:Math.round(t),vh:innerHeight,w:document.documentElement.scrollWidth};}""")
        print('   %s'%r)
        assert r['topo']<600 and r['w']<=391
        print('   OK\n')

        print('=== G) dica recem-criada vem aberta ===')
        r=await page.evaluate("""()=>{dicasCriarAbrir();
          document.getElementById('dica-novo-titulo').value='Nova do teste';
          document.getElementById('dica-novo-materia').value='kPt';
          document.getElementById('dica-novo-regra').value='Conteudo novo';
          dicasCriarSalvar();
          const d=db.dicas.find(x=>x.titulo==='Nova do teste');
          return {linhas:document.querySelectorAll('#dica-'+d.id+' .dica-linha').length};}""")
        assert r['linhas']==1, r
        print('   OK\n')

        assert not graves(errs),graves(errs)
        print('erros de JS: nenhum\nOK')
        await browser.close()
asyncio.run(main())
