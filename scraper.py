import requests
import csv
import datetime
import locale
locale.setlocale(locale.LC_ALL, 'it_IT.UTF-8')
from bs4 import BeautifulSoup
import os.path
import sys
reload(sys)
sys.setdefaultencoding("utf8")
import json
import scraperwiki

def get_politico(uri):
    session = requests.Session()
    i=0
    while i<10:
        try:
            page = session.get(uri)
            break
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            print uri+' - tentativo n. '+str(i)
            i=i+1
            print e
    if i==10:
        sys.exit(1)
    soup = BeautifulSoup(page.text.replace("<!--- <SENATO.IT:SEN.ANAGRAFICA> -->","<span id='anagrafica'>").replace('<!--- </SENATO.IT:SEN.ANAGRAFICA> -->',"</span>"),"lxml")
    nome_cognome=soup.find("h1",{ "class" : "titolo" })
    info= soup.find("span",{ "id" : "anagrafica" })
    nome_cognome=nome_cognome.text.split(' ')
    nome=''
    cognome=''
    senato_id=uri.split('id=')
    senato_id=senato_id[1].split('&')
    senato_id=senato_id[0]
    # last_name e given_name
    for n in nome_cognome:
        if n.isupper():
            cognome=cognome + ' '+ n
        else:
            nome=nome + ' ' + n
    
    # sex        
    if 'Nat' in info.text:
        info_sex=info.text.split('Nat')
        if info_sex[1][0]=='o':
            sex='M'
        elif info_sex[1][0]=='a':
            sex='F'
    else:
        sex=''
    
    nascita=info.find_all('strong')
    if len(nascita)==0:
        luogo=''
        studioprof=''
        data=''
    elif len(nascita)==1:
        luogo=''
        studioprof=''
    elif len(nascita)==2:
        studioprof=''

    for x,n in enumerate(nascita):
        # data_nascita
        if x==0:
            data=n.text.replace("il ","").replace("l'","").strip()
            ctrl=data.strip().split(' ')
            if int(ctrl[2])>=1900:
                data=get_date(data.strip())
            else:
                # hack per strptime
                data=get_date(ctrl[0]+' '+ctrl[1]+ ' 1900')
                data=data.replace('1900',ctrl[2])
        elif x==1:
            luogo=n.text.replace("\n","").replace("\r","").strip()
        else:
            if 'Professione' in n.previousSibling.strip():
                studioprof=n.text.replace("\n","").replace("\r","").strip()
            else:
                studioprof=''
    
    # ctrl data di decesso
    strongs=soup.find_all('strong')
    for n in strongs:
        if 'Deceduto' in n.text:
            death_date=n.text.replace("il ","").replace("l'","").replace('Deceduto','').strip()
            ctrl=death_date.strip().split(' ')
            if int(ctrl[2])>=1900:
                death_date=get_date(death_date.strip())
            else:
                # hack per strptime
                death_date=get_date(ctrl[0]+' '+ctrl[1]+ ' 1900')
                death_date=death_date.replace('1900',ctrl[2])
            break
        else:
            death_date=''
    
    # get_foto se esiste
    foto= soup.find("img",{ "class" : "foto" })
    if foto:
        if 'http://www.senato.it' in foto['src']:
            img=foto['src']
        else:
            img='http://www.senato.it'+foto['src']
    else:
        img=''
    return [nome.strip(),cognome.strip(),sex,data,luogo,studioprof,img,senato_id,death_date]
    

def get_date(stringa):
    stringa=stringa.replace(',','').replace(')','').strip()
    stringa=stringa.split(' ')
    if len(stringa)>2:
        s=stringa[0]+' '+stringa[1]+' '+stringa[2]
        if stringa[0].isdigit() and stringa[2].isdigit():
            return datetime.datetime.strptime(s,'%d %B %Y').strftime('%Y-%m-%d')
        else:
            return ''
    else:
        return ''


governiList = {}
output= {}


# prende la pagina di indice generale dei governi e la mette nella lista governiList
url_lista="http://www.senato.it/leg/ElencoMembriGoverno/Governi.html"
session = requests.Session()
i=0
while i<10:
    try:
        page = session.get(url_lista)
        break
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        print url_lista+' - tentativo n. '+str(i)
        i=i+1
        print e
if i==10:
    sys.exit(1)
    
soup = BeautifulSoup(page.text,"lxml")
govs= soup.find_all('li')
for gov in govs:
    if gov.parent.parent.parent['id']=='content':
        item = gov.text.split('(')
        nome_governo = item[0].strip()
        date= item[1].replace(')','')
        if '-' in date:
            date=date.split('-')
            data_inizio= get_date(date[0].strip())
            data_fine= get_date(date[1].strip())
        else:
            date=date.replace('dal ', '')
            data_inizio=get_date(date.strip())
            data_fine=''
        url= gov.find('a')
        
        # escludi governi precedenti alla I legislatura
        leg=url['href'].split('leg=')
        leg=leg[1].split('&')
        if '-' not in leg[0]:
            if data_fine=='':
                governiList.update({nome_governo : {'data_inizio':data_inizio, 'data_fine':data_fine, 'url':url['href'], 'legislatura':leg[0]}})
                

print governiList
# prende la pagina di ogni singolo governo
for x in range(0,1):
    for gov in governiList:
        if x==0:
            uri='http://www.senato.it'+governiList[gov]['url']
            print 'ministri governo '+gov
        else:
            uri='http://www.senato.it'+governiList[gov]['url']+'&tipo=S'
            print 'sottosegretari governo '+gov
        i=0
        while i<10:
            try:
                page = session.get(uri)
                break
            except requests.exceptions.RequestException as e:  # This is the correct syntax
                print uri+' - tentativo n. '+str(i)
                i=i+1
                print e
        if i==10:
            sys.exit(1)

        soup = BeautifulSoup(page.text,"lxml")
        cariche=soup.find_all("div",{ "class" : "componenti" })
        for c in cariche:
            ministero= c.previousSibling.previousSibling.text.strip()
            if '(' in ministero:
                ministero=ministero.split('(')
                ministero=ministero[0].strip()
            if x==0:
                if ministero=='Presidente del Consiglio dei ministri':
                    carica='Presidente del Consiglio dei ministri'
                else:
                    carica='Ministro'
            else:
                carica='Sottosegretario'
            
            membri=c.find_all('li')
            for m in membri:
                data_inizio=''
                data_fine=''
                if 'Vice Ministro' in m.text:
                    carica='Vice Ministro'
                if '(' in m.text:
                    tmps=m.text.split('(')
                    for tmp in tmps:
                        #print tmp.strip()
                        if "dal " in tmp:
                            data_inizio=tmp.split("dal ")
                            data_inizio=get_date(data_inizio[1].replace(')',''))
                        elif "dall'" in tmp:
                            data_inizio=tmp.split("dall'")
                            data_inizio=get_date(data_inizio[1].replace(')',''))
                        if " al " in tmp:
                            data_fine=tmp.split(" al ")
                            data_fine=get_date(data_fine[1].replace(')',''))
                        elif " all'" in tmp:
                            data_fine=tmp.split(" all'")
                            data_fine=get_date(data_fine[1].replace(')',''))
                            
                if data_inizio=='':
                    data_inizio=governiList[gov]['data_inizio']
                if data_fine=='':
                    data_fine=governiList[gov]['data_fine']
                    
                url_politico=m.find('a')
                info=get_politico('http://www.senato.it'+url_politico['href'])
                if gov not in output.keys():
                    output.update({gov:{'start_date':governiList[gov]['data_inizio'], 'end_date':governiList[gov]['data_fine'], 'legislatura': governiList[gov]['legislatura']}})
                output[gov][len(output[gov])-2]={'given_name':info[0], 'family_name': info[1],'gender':info[2],'birth_date':info[3],'birth_location':info[4],'profession':info[5],'image': info[6], 'senato_identifier':info[7], 'label':carica,'role':ministero,'start_date':data_inizio, 'end_date':data_fine, 'death_date': info[8]}

print "FINE"
output['date'] = '20180408'
print json.dumps(output)
scraperwiki.sqlite.save(unique_keys=['date'], data=json.dumps(output))


