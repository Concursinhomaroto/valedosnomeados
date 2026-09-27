# Casar pelo NOME so pega o card que escreve o nome do assunto — no banco do usuario,
# 594 de 3683 (16%). Um card que fala em "reposicao volemica" e nunca soletra "Choque
# Hipovolemico" fica de fora. Mas o miniboss TEM resumo, e o termo esta la dentro.
# So serve o vocabulario DISTINTIVO: palavra que aparece no resumo de todos os irmaos
# ("paciente", "conduta") nao identifica ninguem.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

COMUM='O paciente deve ser avaliado pela equipe de enfermagem com conduta imediata. '
def sub(i,nome,resumo):
    return {'id':'s%d'%i,'name':nome,'priority':70,'studied':True,'studiedAt':'2026-01-01',
            'resumo':{'texto':COMUM*3+resumo,'geradoEm':'2026-08-01T10:00:00Z','origem':'web'}}
SUBS=[
 sub(1,'Choque Hipovolemico',
     'A reposicao volemica agressiva com cristaloides aquecidos e a base do tratamento. '
     'A perda sanguinea estimada orienta a classificacao em quatro classes hemorragicas. '*3),
 sub(2,'Choque Cardiogenico',
     'O suporte inotropico com dobutamina e a pedra angular, associado ao balao intraaortico. '
     'A disfuncao ventricular esquerda grave reduz o debito cardiaco de forma critica. '*3),
 sub(3,'Sepse e Choque Septico',
     'O pacote da primeira hora inclui lactato serico, hemoculturas e antibiotico de amplo espectro. '
     'O foco infeccioso deve ser controlado precocemente. '*3),
]
def card(i,perg,tags='',resp='Resposta padrao.'):
    return {'id':'c%d'%i,'mbId':'t1','pergunta':perg,'resposta':resp,'tags':tags,
            'acertos':0,'erros':0}
CARDS={}
for c in [
  # casa pelo RESUMO: termo distintivo na tag, sem o nome do assunto em lugar nenhum
  card(1,'Qual a conduta inicial na perda sanguinea macica?','reposicao volemica,cristaloides'),
  card(2,'Como se estima a perda sanguinea no trauma?','perda sanguinea,classes hemorragicas'),
  # casa pelo RESUMO: termo distintivo no corpo
  card(3,'O suporte inotropico com dobutamina esta indicado em qual quadro?',''),
  # casa pelo RESUMO: sepse
  card(4,'O que compoe o pacote da primeira hora?','lactato serico,hemoculturas'),
  # NAO pode casar: so vocabulario COMUM aos tres
  card(5,'O paciente deve ser avaliado pela equipe de enfermagem?',''),
  # NAO pode casar: cita termos distintivos de DOIS assuntos
  card(6,'Diferencie reposicao volemica de suporte inotropico.','reposicao volemica,suporte inotropico'),
  # casa pelo NOME (caminho antigo, tem que continuar valendo e ter prioridade)
  card(7,'O que define o choque hipovolemico?','choque hipovolemico'),
]: CARDS[c['id']]=c
seed=make_seed({'studyNickname':'Leo','flashcards':CARDS,
  'kingdoms':[{'id':'k1','name':'Enf','icon':'🏥'}],
  'topics':{'k1':[{'id':'t1','name':'Choques','subtopics':SUBS}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)

        print('=== A) o indice so guarda o vocabulario DISTINTIVO ===')
        r=await page.evaluate("""()=>{
          const ix=revIndiceChefao(db.topics.k1[0]);
          const m=ix.mapa;
          return {temReposicao:!!m['reposicao volemica'],temInotropico:!!m['suporte inotropico'],
                  temLactato:!!m['lactato serico'],
                  temPaciente:!!m['paciente'],temEnfermagem:!!m['equipe enfermagem'],
                  temConduta:!!m['conduta'],total:Object.keys(m).length};
        }""")
        print('   "reposicao volemica" no indice: %s'%r['temReposicao'])
        print('   "suporte inotropico": %s · "lactato serico": %s'%(r['temInotropico'],r['temLactato']))
        print('   palavras comuns aos tres ("paciente"/"conduta"/"equipe enfermagem"): %s/%s/%s'
              %(r['temPaciente'],r['temConduta'],r['temEnfermagem']))
        print('   termos distintivos no total: %d'%r['total'])
        assert r['temReposicao'] and r['temInotropico'] and r['temLactato']
        assert not r['temPaciente'] and not r['temConduta'] and not r['temEnfermagem']
        print('   OK\n')

        print('=== B) a varredura pega o que o nome nao pegava ===')
        r2=await page.evaluate("""()=>{
          const v=revVarrerVinculos();
          return {porVia:v.porVia,res:v.res,
                  casados:v.casados.map(x=>[x.cardId,x.subNome,x.conf,x.via])};
        }""")
        print('   por nome: %d · por resumo: %d'%(r2['porVia']['nome'],r2['porVia']['resumo']))
        for cid,nome,cf,via in r2['casados']:
            print('      %-4s -> %-22s (%s · via %s)'%(cid,nome,cf,via))
        casou={x[0]:(x[1],x[3]) for x in r2['casados']}
        assert casou['c1']==('Choque Hipovolemico','resumo'), casou
        assert casou['c2']==('Choque Hipovolemico','resumo'), casou
        assert casou['c3']==('Choque Cardiogenico','resumo'), casou
        assert casou['c4']==('Sepse e Choque Septico','resumo'), casou
        assert casou['c7'][1]=='nome', casou
        print('   OK\n')

        print('=== C) e continua nao chutando ===')
        print('   c5 (so vocabulario comum) ficou de fora:        %s'%('c5' not in casou))
        print('   c6 (termos de dois assuntos) ficou de fora:     %s'%('c6' not in casou))
        assert 'c5' not in casou and 'c6' not in casou
        print('   OK\n')

        print('=== D) chefao com UM miniboss so: todo card e dele, sem adivinhar ===')
        r3=await page.evaluate("""()=>{
          db.topics.k1.push({id:'t9',name:'Solo',subtopics:[
            {id:'s9',name:'Unico',priority:70,studied:true,studiedAt:'2026-01-01'}]});
          db.flashcards.c99={id:'c99',mbId:'t9',pergunta:'Qualquer coisa',resposta:'x',tags:'',acertos:0,erros:0};
          const v=revVarrerVinculos();
          const x=v.casados.find(y=>y.cardId==='c99');
          db.topics.k1.pop(); delete db.flashcards.c99;
          return x||null;
        }""")
        print('   c99 -> %s'%(('%s (%s · via %s)'%(r3['subNome'],r3['conf'],r3['via'])) if r3 else 'nao casou'))
        assert r3 and r3['subNome']=='Unico'
        print('   OK\n')

        print('=== E) chefao com resumo em UM irmao so nao pode puxar os cards dos outros ===')
        r4=await page.evaluate("""()=>{
          const t=db.topics.k1[0];
          const guardados=[t.subtopics[1].resumo,t.subtopics[2].resumo];
          delete t.subtopics[1].resumo; delete t.subtopics[2].resumo;
          const ix=revIndiceChefao(t);
          t.subtopics[1].resumo=guardados[0]; t.subtopics[2].resumo=guardados[1];
          return ix;
        }""")
        print('   indice com um resumo so: %s'%('null (nao distingue)' if r4 is None else r4))
        assert r4 is None
        print('   OK\n')

        print('=== F) a previa mostra por onde cada um casou ===')
        r5=await page.evaluate("""()=>{revAbrirVarredura();
          const t=document.getElementById('modal-body').textContent.replace(/\\s+/g,' ');
          return {viaNome:t.indexOf('casaram pelo nome')>=0,
                  viaResumo:t.indexOf('vocabulário do resumo')>=0,
                  amostraVia:t.indexOf('via resumo')>=0};}""")
        print('   cabecalho separa nome/resumo: %s/%s · amostra marca a via: %s'
              %(r5['viaNome'],r5['viaResumo'],r5['amostraVia']))
        assert r5['viaNome'] and r5['viaResumo'] and r5['amostraVia']
        print('   OK\n')

        print('=== G) aplicar e desfazer seguem funcionando ===')
        r6=await page.evaluate("""async()=>{
          revAplicarVarredura('tudo'); await new Promise(r=>setTimeout(r,150));
          const amarrados=Object.values(db.flashcards).filter(c=>c.subId).length;
          revAbrirVarredura(); revDesfazerVarredura(); await new Promise(r=>setTimeout(r,150));
          return {amarrados,depois:Object.values(db.flashcards).filter(c=>c.subId).length};
        }""")
        print('   amarrados: %d -> desfeitos: sobraram %d'%(r6['amarrados'],r6['depois']))
        assert r6['amarrados']==5 and r6['depois']==0
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
