#!/usr/bin/env python3
"""
Atualiza o painel da diretoria Avos a partir das 3 planilhas.

Uso:
  pip install pyxlsb openpyxl cryptography
  python ferramentas/atualizar_dados.py CAIXA.xlsb VGV.xlsx CONTAS_A_RECEBER.xlsb --usuario avos --senha 7542

Gera dados/dados.enc.js (criptografado com AES-256-GCM; a chave vem de usuário+senha).
As planilhas e os dados abertos NUNCA devem ser enviados ao GitHub.
"""
import re, json, datetime, sys, os, base64, argparse, tempfile, secrets
from pyxlsb import open_workbook
import openpyxl
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITER = 600000
ABAS_CX = ['Painel executivo','Fluxo grupo','DRE por empreendimento','Intercompany','Investimento','Sócios e Terceiros','Impostos']
ABAS_CR = ['1_Dashboard','2_Carteira','3_Cobranca','4_Fluxo','Base_Resumo']
ABAS_VGV = ['Dashboard','Resumo']

def dump_xlsb(f, sheets, out):
    with open_workbook(f) as wb, open(out,'w') as o:
        for s in sheets:
            o.write(f'\n######## {s}\n')
            with wb.get_sheet(s) as sh:
                for r,row in enumerate(sh.rows()):
                    cells=[(c.c,c.v) for c in row if c.v not in (None,'')]
                    if cells: o.write(f'R{r+1}: '+' | '.join(f'{c}:{v}' for c,v in cells)+'\n')

def dump_xlsx(f, sheets, out):
    wb=openpyxl.load_workbook(f,data_only=True,read_only=True)
    with open(out,'w') as o:
        for s in sheets:
            o.write(f'######## {s}\n'); ws=wb[s]
            for r in ws.iter_rows():
                cells=[(c.column,c.row,c.value) for c in r if hasattr(c,'row') and c.value not in (None,'')]
                if cells:
                    out_=[]
                    for col,_,v in cells:
                        if isinstance(v,float): v=round(v,4)
                        out_.append(f'{col}:{v}')
                    o.write(f'R{cells[0][1]}: '+' | '.join(out_)+'\n')

def load(path):
    S={};cur=None
    for line in open(path):
        line=line.rstrip('\n')
        m=re.match(r'#+ (.*)',line)
        if m: cur=m.group(1).strip(); S[cur]={}; continue
        m=re.match(r'R(\d+): (.*)',line)
        if m and cur:
            row={}
            for part in m.group(2).split(' | '):
                k,_,v=part.partition(':')
                try: k=int(k)
                except: continue
                try: v=float(v)
                except: pass
                row[k]=v
            S[cur][int(m.group(1))]=row
    return S
def extrair(T):
    cr=load(T['cr']); cx=load(T['cx']); vg=load(T['vgv'])
    def xd(n): return (datetime.date(1899,12,30)+datetime.timedelta(days=int(n))).strftime('%Y-%m')
    def g(r,c,d=0.0): return r.get(c,d)
    D={}
    # ---------- CAIXA
    pe=cx['Painel executivo']
    r=pe[7]; D['cx_kpi']=dict(receita=r[1],custos=r[3],resultado=r[5],margem=r[7],distrib=r[9],geracao=r[11])
    D['cx_emp']=[dict(nome=pe[i][1],grupo=pe[i].get(2,''),status=pe[i].get(3,''),receita=pe[i][4],custos=pe[i][5],resultado=pe[i][6],margem=pe[i][7] if isinstance(pe[i][7],float) else None,fin=pe[i][8],aportes=pe[i][9],retirada=pe[i][10],distrib=pe[i][11],geracao=pe[i][12]) for i in range(13,26)]
    anos=[int(pe[29][c]) for c in range(5,13)]
    D['cx_anual']={'anos':anos}
    for i,k in zip(range(30,37),['receita','custos','resultado','margem','fin','socios','geracao']):
        D['cx_anual'][k]=[pe[i][c] for c in range(5,13)]
        D['cx_anual'][k+'_tot']=pe[i][4]
    fg=cx['Fluxo grupo']
    cols={3:'receita',4:'distrato',5:'avencer',7:'impostos',8:'terreno',9:'aprovacao',10:'obra',11:'comissao',12:'marketing',13:'adm',16:'fin',18:'aporte',19:'retirada',20:'lucro_grupo',21:'lucro_terc',23:'geracao',24:'saldo'}
    mens=[]
    for rn in sorted(fg):
        row=fg[rn]
        if rn>=8 and isinstance(row.get(1),float) and row[1]>40000:
            d={'m':xd(row[1])}; d.update({v:g(row,k) for k,v in cols.items()}); mens.append(d)
    D['fluxo_mensal']=mens
    D['fluxo_total']={v:g(fg[7],k) for k,v in cols.items()}
    # DRE
    try:
        dre=cx['DRE por empreendimento']
        D['dre_sel']=dre[5][2]
        D['dre_anos']=[int(dre[9][c]) for c in range(4,12)]
        D['dre']=[dict(lin=dre[i][1],tot=dre[i][2],pct=dre[i].get(3),anos=[dre[i].get(c,0) for c in range(4,12)]) for i in range(10,32) if 1 in dre[i]]
        ind=[]
        for i in range(10,35):
            if 13 in dre[i]: ind.append([dre[i][13],dre[i].get(14)])
        D['dre_ind']=ind
        D['dre_saldo']=[[xd(dre[i][17]),dre[i][19]] for i in range(10,106) if 17 in dre[i]]
    except Exception: pass
    # Intercompany
    ic=cx['Intercompany']
    # Intercompany: localiza os blocos pelo cabeçalho (o layout pode mudar de coluna)
    def acha(txt):
        for r in sorted(ic):
            for c,v in ic[r].items():
                if isinstance(v,str) and v.strip().startswith(txt): return r,c
        raise KeyError(txt)
    r0,c0=acha('Empresa')            # primeira ocorrência = SALDO POR PAR (Empresa A)
    rp,cp=acha('POSIÇÃO LÍQUIDA')
    pares=[];r=r0+1
    while r in ic and isinstance(ic[r].get(c0),str) and ic[r].get(c0).strip()!='Total':
        pares.append([ic[r][c0+5],ic[r][c0+6],ic[r][c0+7]]); r+=1
    D['ic_pares']=pares; D['ic_total']=sum(p[2] for p in pares)
    pos=[];r=rp+2
    while r in ic and isinstance(ic[r].get(cp),str):
        pos.append([ic[r][cp],ic[r][cp+1],ic[r][cp+2]]); r+=1
    D['ic_pos']=pos
    # Investimento
    iv=cx['Investimento']
    D['inv']=[[iv[i][1],iv[i][2],iv[i][3],iv[i][4],iv[i][5],iv[i][6]] for i in range(38,51)]
    # Socios
    so=cx['Sócios e Terceiros']
    D['socios']=[[so[i][1],so[i][2],so[i][3],so[i][4],so[i][5],so[i][7]] for i in range(10,28)]
    D['socios_tot']=[so[61][2],so[61][3],so[61][4],so[61][5],so[61][7]]
    D['socios_anual']=[so[127][c] for c in range(2,7)]
    D['socios_anos']=[int(so[75][c]) for c in range(2,7)]
    # Impostos
    im=cx['Impostos']
    D['imp']=[[im[i][1]]+[im[i][c] for c in range(2,10)] for i in range(34,47)]
    # ---------- VGV
    db=vg['Dashboard']
    D['vgv_kpi']=dict(vgv=db[8][2],vendido=db[8][5],estoque=db[8][8],vso=db[8][11],lotes=db[9][4],pct=db[9][7],disp=db[9][10],vendas90=db[9][13],meses=db[12][2],desc=db[12][5],inad=db[12][8],areceber=db[12][11],vendasmes=db[13][4],comissao=db[13][7],vencido=db[13][10],recebido=db[13][13])
    keys=['nome','status','lotes','vendidos','disp','proposta','pct','vgv_vendido','tabela','estoque','em_proposta','vgv_total','ticket_v','ticket_e','desconto','v90','vmes','meses','vso','com_pct','com_val','distratos','recebido','vencido','venc180','inad','areceber','alertas']
    D['vgv_emp']=[{k:db[i].get(c,'') for k,c in zip(keys,range(2,30))} for i in range(17,25)]
    top=[]
    for i in sorted(db):
        if i>=30 and isinstance(db[i].get(2),float) and 3 in db[i]: top.append([int(db[i][2]),db[i][3],db[i][5],db[i][6],db[i][7],db[i][8]])
    D['vgv_top']=top
    rs=vg['Resumo']
    emps=['ALOHI','BELLEVIE','KALA','KOA','LOTE COMERCIAL','NALU','VILLA NOAH']
    vm=[]
    for i in range(19,113):
        row=rs[i]; vm.append({'m':str(row[1])[:7],'q':[row[c] for c in range(2,16,2)],'v':[row[c] for c in range(3,17,2)],'qt':row[16],'vt':row[17]})
    D['vendas_mensais']=vm
    # ---------- CONTAS A RECEBER
    d1=cr['1_Dashboard'][8]; D['cr_kpi']=dict(recebido=d1[1],avencer=d1[5],vencido=d1[9],inad=d1[13],multa=d1[17])
    ca=cr['2_Carteira']
    D['cr_anos_venc']=['2026','2027','2028','2029','2030','2031','2032','2033+']
    D['cr_emp']=[dict(nome=ca[i][1],recebido=ca[i][2],avencer=ca[i][3],vencido=ca[i][4],pv=ca[i][5],heat=[ca[i][c] for c in range(7,15)]) for i in range(7,15)]
    D['cr_meses']=[xd(ca[18][c]) for c in range(3,26)]
    D['cr_mensal']=[dict(nome=ca[i][1],media=ca[i][2],m=[ca[i][c] for c in range(3,26)],apos=ca[i][26],tot=ca[i][27]) for i in range(19,27)]
    co=cr['3_Cobranca']; r=co[6]
    D['cob_kpi']=dict(vencido=r[1],parcelas=r[2],inad=r[3],multa=r[4])
    D['aging']=[[co[i][1],co[i][2],co[i][3],co[i][4]] for i in range(11,18)]
    D['top_dev']=[[co[i][1],co[i][2],co[i][3],co[i][4],co[i][5]] for i in range(22,32)]
    # lista de clientes vencidos: localiza cabeçalho e fim da lista (layout pode mudar)
    hdr=next(r for r in sorted(co) if co[r].get(1)=='Empreendimento' and co[r].get(3)=='Cliente')
    H={str(v).strip().lower():k for k,v in co[hdr].items() if isinstance(v,str)}
    col=lambda *names: next((H[n] for n in names if n in H),None)
    cE,cL,cC,cI,cP,cV,cPg,cA=col('empreendimento'),col('lote'),col('cliente'),col('imobiliária'),col('parcelas vencidas'),col('valor vencido (r$)'),col('valor pago (r$)'),col('a vencer (r$)')
    cEt,cD,cDs=col('etapa de cobrança'),col('data último evento'),col('descrição último evento')
    fim=next((r for r in sorted(co) if r>hdr and str(co[r].get(1,'')).startswith('Inadimplência por imobiliária')),max(co)+1)
    cl=[]
    for i in range(hdr+1,fim):
        row=co.get(i)
        if not row or not row.get(cE) or not isinstance(row.get(cV),float): continue
        g=lambda c,d='': row.get(c,d) if c is not None else d
        cl.append([g(cE),str(g(cL)).replace('.0',''),g(cC),g(cI),g(cP),g(cV),g(cPg),g(cA),g(cEt),xd(g(cD)) if isinstance(g(cD),float) else '',g(cDs)])
    D['clientes']=cl
    D['imob_inad']=[[co[i][1],co[i][2],co[i][3],co[i][4],co[i][5]] for i in range(131,162)]
    fl=cr['4_Fluxo']
    D['cr_fluxo']=[[str(fl[i][1]).replace('.0',''),fl[i][2],fl[i][3],fl[i][4],fl[i][5]] for i in range(10,26)]
    br=cr['Base_Resumo']
    D['rec12_emps']=[br[71][c] for c in range(2,9)]
    D['rec12']=[dict(m=xd(br[i][1]),v=[br[i][c] for c in range(2,9)],t=br[i][9]) for i in range(72,84)]
    D['aging_avos']=[[br[i][1],br[i][2],br[i][3],br[i][4]] for i in range(17,24)]
    D['multa_emp']=[[br[i][1],br[i][7]] for i in range(5,13)]


    return D

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('caixa'); ap.add_argument('vgv'); ap.add_argument('receber')
    ap.add_argument('--usuario',default='avos'); ap.add_argument('--senha',required=True)
    ap.add_argument('--saida',default=os.path.join(os.path.dirname(__file__),'..','dados','dados.enc.js'))
    a=ap.parse_args()
    tmp=tempfile.mkdtemp()
    T={'cx':os.path.join(tmp,'cx.txt'),'cr':os.path.join(tmp,'cr.txt'),'vgv':os.path.join(tmp,'vgv.txt')}
    dump_xlsb(a.caixa,ABAS_CX,T['cx']); dump_xlsb(a.receber,ABAS_CR,T['cr']); dump_xlsx(a.vgv,ABAS_VGV,T['vgv'])
    D=extrair(T)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import dre_calc, fluxo_calc
    for k in ('dre','dre_ind','dre_saldo','dre_sel','dre_anos'): D.pop(k,None)
    # Fluxo grupo e DRE recalculados a partir das bases (independe do filtro salvo na planilha)
    D['dre_all'],D['receita_avos'],fl,D['participacao']=fluxo_calc.todas(a.caixa)
    D['fluxo_mensal']=fl
    D['fluxo_total']={k:sum(m[k] for m in fl) for k in fl[0] if k not in ('m','saldo','avos')}
    # Recalcula em "Todos" o que nas planilhas depende de filtro (evita filtro salvo em um empreendimento)
    D['vgv_kpi']=dre_calc.vgv_kpi_todos(D['vgv_emp'])
    D['vgv_top']=dre_calc.vgv_top_todos(a.vgv)
    so,st,sa,san=dre_calc.socios_todos(a.caixa)
    D['socios'],D['socios_tot'],D['socios_anos'],D['socios_anual']=so,st,sa,san
    for k in ('dre','dre_ind','dre_saldo','dre_sel','dre_anos'): D.pop(k,None)
    D['gerado_em']=datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    criptografar(D,a.usuario,a.senha,a.saida)
    print('OK ->',os.path.abspath(a.saida))

def criptografar(D,usuario,senha,saida):
    salt=secrets.token_bytes(16); iv=secrets.token_bytes(12)
    key=PBKDF2HMAC(algorithm=hashes.SHA256(),length=32,salt=salt,iterations=ITER).derive(f'{usuario.strip().lower()}:{senha}'.encode())
    ct=AESGCM(key).encrypt(iv,json.dumps(D,ensure_ascii=False,separators=(',',':')).encode(),None)
    b=lambda x: base64.b64encode(x).decode()
    with open(saida,'w') as f:
        f.write('window.AVOS_PAYLOAD='+json.dumps({'v':1,'iter':ITER,'salt':b(salt),'iv':b(iv),'ct':b(ct)})+';\n')

if __name__=='__main__':
    main()
