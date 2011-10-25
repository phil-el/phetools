import sys
sys.path.append("/home/phe/pywikipedia")


disambiguations = {
   'old':'Disambig',
    'no':'Peker',
    'pl':'Disambig',
    'es':'Desambiguaci\xc3\xb3n',
    'it':'Disambigua',
    'sv':'F\xc3\xb6rgreningssida',
    'ca':'Desambiguaci\xc3\xb3',
    'ru':'Disambig',
    'da':'Flertydig',
    'pt':'Desambig',
    'hr':'Razdvojba',
    'la':'Discretiva',
    'et':'T\xc3\xa4psustuslehek\xc3\xbclg',
    'sl':'Razlo\xc4\x8ditev',
    'te':'\xe0\xb0\x85\xe0\xb0\xaf\xe0\xb1\x8b\xe0\xb0\xae\xe0\xb0\xaf \xe0\xb0\xa8\xe0\xb0\xbf\xe0\xb0\xb5\xe0\xb1\x83\xe0\xb0\xa4\xe0\xb1\x8d\xe0\xb0\xa4\xe0\xb0\xbf',
    'id':'Disambig',
    'vec':'Disambigua',
    'br':'Dishe\xc3\xb1velout'
}


domain_urls = {
   'old': (104,"Proofread",                 "Validated",           "Without_text",         "Problematic"                   ),
    'en': (104,"Proofread",                 "Validated",           "Without_text",         "Problematic"                   ),
    'fr': (104,"Page_corrig%C3%A9e",        "Page_valid%C3%A9e",   "Sans_texte",           "Page_\xc3\xa0_probl\xc3\xa8me" ),
    'da': (104,'Korrekturl\xc3\xa6st',      'Valideret',           'Uden_tekst',           'Problematisk'                  ),
    'de': (102,"Korrigiert",                "Fertig",              "Sofort_fertig",        "KProblem"                      ),
    'no': (104,"Korrekturlest",             "Validert",            "Uten_tekst",           "Ufullstendig"                  ),
    'it': (108,"Pagine_SAL_75%25",          "Pagine_SAL_100%25",   "Pagine_SAL_00%",       "Pagine_SAL_50%"                ),
    'sv': (104,"Korrekturl%C3%A4st",        "Validerat",           "Utan_text",            "Ofullst\xc3\xa4ndigt"          ),
    'pl': (100,"Skorygowana",               "Uwierzytelniona",     "Bez_tre\xc5\x9bci",    "Problemy"                      ),
    'es': (102,"Corregido",                 "Validado",            "Sin_texto",            "Problem\xc3\xa1tica"           ),
    'pt': (106,"%21P%C3%A1ginas_revisadas", "%21P%C3%A1ginas_validadas", '!P\xc3\xa1ginas_sem_texto', '!P\xc3\xa1ginas_problem\xc3\xa1ticas'),
    'ca': (102,"Revisada",                  "Validada",            'Sense_text',           'Problem\xc3\xa0tica'           ),
    'la': (104,"Emendata",                  "Bis_lecta",           "Without_text",         "Emendatio_difficilis"          ),
    'et': (102,"%C3%95igsus_t%C3%B5endatud","Heakskiidetud",       "Ilma_tekstita",        "Problemaatiline"               ),
    'sl': (100,"Korigirano",                "Potrjeno",            "Without_text"  ,       "Problemati\xc4\x8dne_strani"   ),
    'hr': (102,"Ispravljeno",               "Provjereno",          "Bez_teksta",           "Problemati\xc4\x8dno"          ),
    'hu': (104,"Korrekt%C3%BAr%C3%A1zva",   "J%C3%B3v%C3%A1hagyva","Sz\xc3\xb6veg_n\xc3\xa9lk\xc3\xbcl", "Problematikus"   ),
    'ru': (104,"%D0%92%D1%8B%D1%87%D0%B8%D1%82%D0%B0%D0%BD%D0%B0",
           "%D0%9F%D1%80%D0%BE%D0%B2%D0%B5%D1%80%D0%B5%D0%BD%D0%B0",
           '\xd0\x91\xd0\xb5\xd0\xb7_\xd1\x82\xd0\xb5\xd0\xba\xd1\x81\xd1\x82\xd0\xb0',
           '\xd0\x9f\xd1\x80\xd0\xbe\xd0\xb1\xd0\xbb\xd0\xb5\xd0\xbc\xd0\xbd\xd0\xb0\xd1\x8f'),
    'hy': (104,"%D5%8D%D6%80%D5%A2%D5%A1%D5%A3%D6%80%D5%BE%D5%A1%D5%AE",
           "%D5%80%D5%A1%D5%BD%D5%BF%D5%A1%D5%BF%D5%BE%D5%A1%D5%AE",
           '\xd4\xb1\xd5\xbc\xd5\xa1\xd5\xb6\xd6\x81_\xd5\xbf\xd5\xa5\xd6\x84\xd5\xbd\xd5\xbf',
           '\xd4\xbd\xd5\xb6\xd5\xa4\xd6\x80\xd5\xa1\xd5\xb0\xd5\xa1\xd6\x80\xd5\xb8\xd6\x82\xd5\xb5\xd6\x81'),
    'vi': (104,"%C4%90%C3%A3_hi%E1%BB%87u_%C4%91%C3%ADnh",
           "%C4%90%C3%A3_ph%C3%AA_chu%E1%BA%A9n",
           'Kh\xc3\xb4ng_c\xc3\xb3_n\xe1\xbb\x99i_dung',
           'C\xc3\xb3_v\xe1\xba\xa5n_\xc4\x91\xe1\xbb\x81' ),
   'vec': (102, "Pagine_trascrite","Pagine_rilete", "Pagine_sensa_testo", "Pagine_da_sistemar"),
    'br': (102,"Reizhet", "Kadarnaet", "Hep_testenn", "Kudennek"),
    'el': (100,),
    'zh': (104,),
    'te': (104,),
    'he': (104,),
    'id': (104,"Halaman_yang_telah_diuji-baca", "Halaman_yang_telah_divalidasi", "Halaman_tanpa_naskah", "Halaman_bermasalah" ),
}

notnaked_cats = {
   'fr': "SansTransclusion"
}

def decode_res(t):
    if len(t)==8 :
        return t
    elif len(t) == 7:
        a,b,c,d,e,f,g = t
        return (a,b,c,d,e,f,g,0)
    else:
        print repr(t)
        raise


if __name__ == "__main__":
    import wikipedia
    domains = domain_urls.keys()
    for dom in domains:
        if dom=='old':continue
	site = wikipedia.getSite(dom,fam='wikisource')
        page = wikipedia.Page(site,"Mediawiki:Proofreadpage_pagenum_template")
        #page = wikipedia.Page(site,"Mediawiki:Disambiguationspage")
        try:
            t = page.get()
        except:continue
        print dom, repr(t)

