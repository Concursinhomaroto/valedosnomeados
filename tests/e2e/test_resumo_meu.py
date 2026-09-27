# -*- coding: utf-8 -*-
# "Um sofrimento pra colocar resumo mesmo que escrito, pra a IA so organizar." O texto
# colado so tinha UMA porta, e ela passava pelo Gemini — que estava devolvendo 503 em
# todos os modelos. E pior: o texto colado evaporava junto com o erro. Organizar nao
# precisa de modelo: a forma que o app espera e um contrato fechado, entao da pra fazer
# localmente, de graca, sem risco de alguem reescrever o que voce escreveu.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed():
    return make_seed({'studyNickname':'Leo','geminiApiKey':'chave-de-teste',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'SUS','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Lei 8080','priority':70,'studied':True}]}]}})

MEU = """## PRINCIPIOS DO SUS
O SUS organiza-se a partir de principios doutrinarios e organizativos.

**Universalidade**
- Todos tem direito, sem distincao.
- Nao existe carencia nem contribuicao previa.


INTEGRALIDADE
Conjunto articulado de acoes preventivas e curativas, em todos os niveis.
Na pratica: o paciente que chega pra vacina e sai com consulta marcada.

1. EQUIDADE:
Tratar desigualmente os desiguais, pra reduzir a diferenca de resultado."""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{goToSubtopic('s1');toggleResumo('s1');return true;}")
        await page.wait_for_timeout(300)

        print('=== A) o arrumador organiza sem chamar ninguem ===')
        r=await page.evaluate("""(t)=>{
          window.__chamou=0;
          window.callGeminiGenerate=async()=>{window.__chamou++;return 'nao devia';};
          const out=resumoArrumar(t);
          return {out, chamou:window.__chamou,
                  linhas:out.split('\\n'),
                  semMarkdown:!/[#*]|^\\s*-\\s/m.test(out),
                  temNaPratica:/^Na pratica:/m.test(out)};}""", MEU)
        print('   chamadas ao modelo: %s'%r['chamou'])
        for l in r['linhas']: print('   |%s'%l)
        assert r['chamou']==0
        assert 'PRINCIPIOS DO SUS:' in r['out'], 'o ## não virou título com dois-pontos'
        assert 'INTEGRALIDADE:' in r['out']
        assert 'EQUIDADE:' in r['out'] and '1. EQUIDADE' not in r['out']
        assert 'Universalidade' in r['out']
        assert r['semMarkdown'] and r['temNaPratica']
        assert '\n\n\n' not in r['out'], 'sobrou linha em branco dupla'
        print('   tirou ##, **, bullets e numeração; pôs dois-pontos nos títulos')
        print('   OK\n')

        print('=== B) frase nao vira titulo por engano ===')
        r=await page.evaluate("""()=>{
          const casos=['LEI 8.080/1990','ARTIGO 7º','SUS','PNI 2026',
                       'O SUS organiza-se a partir de principios.',
                       'Todos tem direito, sem distincao',
                       'A LEI diz que TODOS tem direito ao SUS de forma integral e gratuita'];
          return casos.map(c=>({c,titulo:resumoEhTitulo(c)}));}""")
        for x in r:
            print('   %-68s → %s'%(x['c'][:66],'TÍTULO' if x['titulo'] else 'texto'))
        assert [x['titulo'] for x in r]==[True,True,True,True,False,False,False]
        print('   frase longa com maiúsculas no meio continua sendo frase')
        print('   OK\n')

        print('=== C) "Usar como esta" guarda sem modelo ===')
        r=await page.evaluate("""(t)=>{
          window.__chamou=0;
          window.callGeminiGenerate=async()=>{window.__chamou++;throw new Error('503');};
          resumoAbrirColar('s1');
          document.getElementById('resumo-colar-s1').value=t;
          resumoUsarComoEsta('s1');
          const sub=simFindSub('s1');
          return {chamou:window.__chamou, tem:!!(sub.resumo&&sub.resumo.texto),
                  origem:sub.resumo.origem, tam:sub.resumo.texto.length,
                  fechouOColar:!resumoColando.has('s1'),
                  primeiraLinha:sub.resumo.texto.split('\\n')[0]};}""", MEU)
        print('   chamadas ao modelo: %s · guardou: %s · origem: "%s" · %s caracteres'
              %(r['chamou'],r['tem'],r['origem'],r['tam']))
        print('   1ª linha: "%s"'%r['primeiraLinha'])
        assert r['chamou']==0 and r['tem'] and r['origem']=='meu'
        assert r['fechouOColar'] and r['primeiraLinha']=='PRINCIPIOS DO SUS:'
        print('   OK\n')

        print('=== D) texto curto demais nao passa ===')
        r=await page.evaluate("""()=>{
          const sub=simFindSub('s1'); const antes=sub.resumo.texto;
          resumoAbrirColar('s1');
          document.getElementById('resumo-colar-s1').value='curto';
          let aviso=''; const t=window.toast; window.toast=(m)=>{aviso=m;};
          resumoUsarComoEsta('s1');
          window.toast=t;
          return {aviso, naoTrocou:simFindSub('s1').resumo.texto===antes};}""")
        print('   aviso: "%s" · resumo anterior intacto: %s'%(r['aviso'],r['naoTrocou']))
        assert 'mínimo' in r['aviso'] and r['naoTrocou']
        print('   OK\n')

        print('=== E) 503 devolve o texto na tela, em vez de perder ===')
        r=await page.evaluate("""async(t)=>{
          window.callGeminiGenerate=async()=>{throw new Error('503 Service Unavailable');};
          resumoAbrirColar('s1');
          document.getElementById('resumo-colar-s1').value=t;
          let aviso=''; const to=window.toast; window.toast=(m)=>{aviso=m;};
          resumoGerarDoTexto('s1');
          await new Promise(r=>setTimeout(r,800));
          window.toast=to;
          const ta=document.getElementById('resumo-colar-s1');
          return {voltouPraTela:resumoColando.has('s1'),
                  textoIntacto:!!ta&&ta.value===t,
                  caracteres:ta?ta.value.length:0,
                  aviso,
                  temBotao:/resumoUsarComoEsta/.test(
                    document.getElementById('resumo-'+'s1').innerHTML)};}""", MEU)
        print('   voltou pra tela de colar: %s · texto intacto: %s (%s caracteres)'
              %(r['voltouPraTela'],r['textoIntacto'],r['caracteres']))
        print('   aviso: "%s"'%r['aviso'][:90])
        assert r['voltouPraTela'] and r['textoIntacto']
        assert 'de volta na tela' in r['aviso']
        assert r['temBotao'], '"Usar como está" precisa estar ali pra ser a saída'
        print('   e "Usar como está" está do lado — a saída quando a API cai')
        print('   OK\n')

        print('=== F) os dois botoes aparecem no painel de colar ===')
        r=await page.evaluate("""()=>{
          resumoAbrirColar('s1');
          const h=document.getElementById('resumo-s1').innerHTML;
          return {usar:/Usar como está/.test(h),
                  ia:/Resumir com IA/.test(h),
                  ordemCerta:h.indexOf('Usar como está')<h.indexOf('Resumir com IA'),
                  explica:/funciona com a API\\s*\\n?\\s*fora do ar/.test(h.replace(/\\s+/g,' '))
                          ||/fora do ar/.test(h)};}""")
        print('   "Usar como está": %s · "Resumir com IA": %s · na ordem certa: %s'
              %(r['usar'],r['ia'],r['ordemCerta']))
        print('   a tela explica quando usar cada um: %s'%r['explica'])
        assert r['usar'] and r['ia'] and r['ordemCerta'] and r['explica']
        print('   OK\n')

        print('=== G) o resumo guardado renderiza como os outros ===')
        r=await page.evaluate("""(t)=>{
          resumoAbrirColar('s1');
          document.getElementById('resumo-colar-s1').value=t;
          resumoUsarComoEsta('s1');
          const h=document.getElementById('resumo-s1').innerHTML;
          return {corpo:/resumo-body/.test(h),
                  naoMenteNoRodape:!/Gerado por IA/.test(h)&&/Escrito por você/.test(h),
                  titulos:(h.match(/resumo-h/g)||[]).length,
                  pratica:/resumo-pratica/.test(h)||/Na pratica/.test(h),
                  editavel:/resumoEditar/.test(h)};}""", MEU)
        print('   bloco na tela: %s · títulos formatados: %s · "Na prática": %s'
              %(r['corpo'],r['titulos'],r['pratica']))
        print('   e continua editável à mão: %s'%r['editavel'])
        assert r['corpo'] and r['titulos']>=3 and r['editavel']
        print('   o rodapé diz "Escrito por você", não "Gerado por IA": %s'%r['naoMenteNoRodape'])
        assert r['naoMenteNoRodape'], 'o rodapé estava dando crédito à IA por texto seu'
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
