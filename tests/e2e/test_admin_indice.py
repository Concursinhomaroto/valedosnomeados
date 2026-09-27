# O Painel Admin lia ref('users') inteiro — todas as contas com flashcards, resumos e as
# duas copias de backup — pra mostrar 4 campos por linha. Agora le admin_index.
# Aqui: (1) o painel NAO toca mais em users/ ao abrir, (2) le o indice e renderiza igual,
# (3) o app escreve a propria linha do indice no save, sem repetir a cada save,
# (4) confirmar pagamento e excluir acertam a vitrine, (5) reconstruir traz tudo de volta.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
seed=make_seed({'studyNickname':'Leo','accountEmail':'leonardobrunotlc@gmail.com','plan':'full'})

# 40 contas de mentira, cada uma com banco + 2 backups (o que o painel baixava antes)
SEMEAR = """(n)=>{
  const r=window.__root;
  const gordo={flashcards:{},topics:{}};
  for(let i=0;i<400;i++)gordo.flashcards['c'+i]={id:'c'+i,pergunta:'x'.repeat(200),resposta:'y'.repeat(300)};
  for(let u=0;u<n;u++){
    const uid='uid'+u;
    const vdn=Object.assign({accountEmail:'aluno'+u+'@ex.com',
      plan:u%4===0?'full':'trial',
      planType:u%4===1?'anual':(u%4===2?'mensal':''),
      lastPaymentAt:u%4===0?'':'2026-09-01'},JSON.parse(JSON.stringify(gordo)));
    r.users[uid]={vdn_v1:vdn,vdn_v1_bkp:{a:vdn,b:vdn}};
  }
  // tamanho do que o painel baixava antes
  return JSON.stringify(r.users).length;
}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        bytesUsers=await page.evaluate(SEMEAR,40)

        print('=== A) abrir o painel nao le mais users/ ===')
        lidos=await page.evaluate("""async()=>{
          window.__lidos=[];
          const orig=firebaseDB.ref;
          firebaseDB.ref=function(pth){window.__lidos.push(pth===undefined?'':pth);return orig.call(this,pth);};
          adminRefresh();
          await new Promise(r=>setTimeout(r,400));
          firebaseDB.ref=orig;
          return window.__lidos;
        }""")
        print('   caminhos lidos: %s'%lidos)
        assert 'users' not in lidos, lidos
        assert 'admin_index' in lidos, lidos
        print('   OK\n')

        print('=== B) reconstruir traz as 40 contas pra vitrine ===')
        await page.evaluate("()=>{window.confirm=()=>true;}")
        await page.evaluate("()=>adminReconstruirIndice()")
        await page.wait_for_timeout(600)
        idx=await page.evaluate("()=>window.__root.admin_index")
        bytesIdx=await page.evaluate("()=>JSON.stringify(window.__root.admin_index).length")
        print('   contas no indice: %d'%len(idx))
        print('   campos por linha: %s'%sorted(idx['uid0'].keys()))
        print('   antes: %.2f MB baixados por abertura  ->  agora: %.1f KB'
              %(bytesUsers/1048576,bytesIdx/1024))
        print('   reducao: %dx'%round(bytesUsers/bytesIdx))
        assert len(idx)>=40, len(idx)
        assert sorted(idx['uid0'].keys())==['email','lastPaymentAt','plan','planType']
        assert bytesIdx<bytesUsers/1000
        print('   OK\n')

        print('=== C) a lista e os totais saem iguais lendo so o indice ===')
        await page.evaluate("()=>adminRefresh()")
        await page.wait_for_timeout(400)
        st=await page.evaluate("""()=>{
          const t=document.getElementById('admin-stats').innerText.replace(/\\s+/g,' ');
          const cards=document.querySelectorAll('#admin-results .admin-result-card').length;
          const primeiro=(document.querySelector('#admin-results .admin-result-email')||{}).textContent||'';
          const status=(document.querySelector('#admin-results .admin-result-status')||{}).textContent||'';
          return {t,cards,primeiro,status};
        }""")
        print('   totais: %s'%st['t'])
        print('   cards na pagina: %d | primeiro: %s -> %s'%(st['cards'],st['primeiro'],st['status']))
        assert st['cards']>0 and '@' in st['primeiro'] and st['status'].strip()
        assert 'Total de contas' in st['t']
        print('   OK\n')

        print('=== D) o app escreve a propria linha no save, e so quando muda ===')
        n1=await page.evaluate("""async()=>{
          window.__w=0;
          const orig=firebaseDB.ref;
          firebaseDB.ref=function(pth){const r=orig.call(this,pth);
            if(String(pth).indexOf('admin_index/')===0){const s=r.set;r.set=function(v){window.__w++;return s.call(this,v);};}
            return r;};
          adminIndexUltimo='';
          saveDB(); await new Promise(r=>setTimeout(r,50));
          saveDB(); await new Promise(r=>setTimeout(r,50));
          saveDB(); await new Promise(r=>setTimeout(r,50));
          const depoisDeIguais=window.__w;
          db.planType='anual'; saveDB(); await new Promise(r=>setTimeout(r,50));
          firebaseDB.ref=orig;
          return {depoisDeIguais, total:window.__w, linha:window.__root.admin_index[currentUser.uid]};
        }""")
        print('   3 saves sem mudanca -> %d escrita(s) no indice'%n1['depoisDeIguais'])
        print('   depois de mudar o plano -> %d no total'%n1['total'])
        print('   minha linha: %s'%n1['linha'])
        assert n1['depoisDeIguais']==1 and n1['total']==2, n1
        assert n1['linha']['email']=='leonardobrunotlc@gmail.com' and n1['linha']['planType']=='anual'
        print('   OK\n')

        print('=== E) confirmar pagamento e excluir acertam a vitrine ===')
        await page.evaluate("()=>adminConfirmPayment('uid1','mensal')")
        await page.wait_for_timeout(400)
        l1=await page.evaluate("()=>window.__root.admin_index.uid1")
        real=await page.evaluate("()=>window.__root.users.uid1.vdn_v1.planType")
        print('   uid1 no indice: %s | no registro real: %s'%(l1,real))
        assert l1['planType']=='mensal' and real=='mensal'
        antes=await page.evaluate("()=>Object.keys(window.__root.admin_index).length")
        await page.evaluate("""()=>{window.fetch=()=>Promise.resolve({ok:true,json:()=>Promise.resolve({ok:true})});
                                   return adminDeleteUser('uid2','aluno2@ex.com');}""")
        await page.wait_for_timeout(500)
        depois=await page.evaluate("()=>Object.keys(window.__root.admin_index).length")
        temUid2=await page.evaluate("()=>'uid2' in window.__root.admin_index")
        print('   linhas antes/depois de excluir: %d -> %d | uid2 ainda na vitrine: %s'%(antes,depois,temUid2))
        assert depois==antes-1 and not temUid2
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
