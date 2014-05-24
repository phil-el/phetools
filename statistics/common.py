# -*- coding: utf-8 -*-
import sys
sys.path.append("/home/phe/pywikipedia")


disambiguations = {
    'old':'Disambig',
    'ca':'Desambiguació',
    'da':'Flertydig',
    'es':'Desambiguación',
    'et':'Täpsustuslehekülg',
    'it':'Disambigua',
    'hr':'Razdvojba',
    'id':'Disambig',
    'la':'Discretiva',
    'no':'Peker',
    'pl':'Disambig',
    'pt':'Desambig',
    'ru':'Disambig',    
    'sl':'Razločitev',
    'sv':'Förgreningssida',
    'te':'అయోమయ నివృత్తి',
    'vec':'Disambigua',
}

# Take care, this contains rtl/ltr mixed strings, many editor don't handle
# correctly cut&copy and can corrupt datas, the convenience function
# check_all_quality_cat() can be used to check for wrong data.
# check_all_quality_cat failure doesn't mean always the data are wrong, you
# must first delete the mediawiki message cache from pywikipedia to be sure
# you get the real data. That's why we don't rely on pywikipedia to get sys
# msg contents.
domain_urls = {
    'old': (
        104,
        "Proofread",
        "Validated",
        "Without_text",
        "Problematic",
        ),
    'bn': (
        104,
        "প্রুফরিড",
        "বৈধকরণ",
        "লেখাবিহীন",
        "\xe0\xa6\xb8\xe0\xa6\xae\xe0\xa6\xb8\xe0\xa7\x8d\xe0\xa6\xaf\xe0\xa6\xbe\xe0\xa6\xb8\xe0\xa6\x99\xe0\xa7\x8d\xe0\xa6\x95\xe0\xa7\x81\xe0\xa6\xb2",
        ),
    'br': (
        102,
        "Reizhet",
        "Kadarnaet",
        "Hep_testenn",
        "Kudennek",
        ),
    'ca': (
        102,
        "Revisada",
        "Validada",
        "Sense_text",
        "Problemàtica",
        ),
    'da': (
        104,
        "Korrekturlæst",
        "Valideret",
        "Uden_tekst",
        "Problematisk",
        ),
    'de': (
        102,
        "Korrigiert",
        "Fertig",
        "Sofort_fertig",
        "KProblem",
        ),
    'en': (
        104,
        "Proofread",
        "Validated",
        "Without_text",
        "Problematic",
        ),
    'el': (
        100,
        "Έχει_γίνει_proofreading",
        "Εγκρίθηκε",
        "Χωρίς_κείμενο",
        "Προβληματική",
        ),
    'es': (
        102,
        "Corregido",
        "Validado",
        "Sin_texto",
        "Problemática",
        ),
    'et': (
        102,
        "Õigsus_tõendatud",
        "Heakskiidetud",
        "Ilma_tekstita",
        "Probleemne",
        ),
    'fr': (
        104,
        "Page_corrigée",
        "Page_validée",
        "Sans_texte",
        "Page_à_problème",
        ),
    'gu' : (
        104,
        "ભૂલશુદ્ધિ_પૂર્ણ",
        "પ્રમાણિત",
        "લખાણ_રહિત",
        "સમસ્યારૂપ",
        ),
    'he': (
        104,
        "בוצעה_הגהה",
        "מאומת",
        "ללא_טקסט",
        "בעייתי",
        ),
    'hr': (
        102,
        "Ispravljeno",
        "Provjereno",
        "Bez_teksta",
        "Problematično",
        ),
    'hu': (
        104,
        "Korrektúrázva",
        "Jóváhagyva",
        "Szöveg_nélkül",
        "Problematikus",
        ),
    'hy': (
        104,
        "Սրբագրված",
        "Հաստատված",
        'Առանց_տեքստ',
        'Խնդրահարույց',
        ),
    'id': (
        104,
        "Halaman_yang_telah_diuji-baca",
        "Halaman_yang_telah_divalidasi",
        "Halaman_tanpa_naskah",
        "Halaman_bermasalah",
        ),
    'it': (
        108,
        "Pagine_SAL_75%",
        "Pagine_SAL_100%",
        "Pagine_SAL_00%",
        "Pagine_SAL_50%",
        ),
    'la': (
        104,
        "Emendata",
        "Bis_lecta",
        "Vacuus",
        "Emendatio_difficilis",
        ),
    'ml' : (
        106,
        "തെറ്റുതിരുത്തൽ_വായന_കഴിഞ്ഞവ",
        "\xe0\xb4\xb8\xe0\xb4\xbe\xe0\xb4\xa7\xe0\xb5\x82\xe0\xb4\x95\xe0\xb4\xb0\xe0\xb4\xbf\xe0\xb4\x9a\xe0\xb5\x8d\xe0\xb4\x9a\xe0\xb4\xb5",
        "\xe0\xb4\x8e\xe0\xb4\xb4\xe0\xb5\x81\xe0\xb4\xa4\xe0\xb5\x8d\xe0\xb4\xa4\xe0\xb5\x8d_\xe0\xb4\x87\xe0\xb4\xb2\xe0\xb5\x8d\xe0\xb4\xb2\xe0\xb4\xbe\xe0\xb4\xa4\xe0\xb5\x8d\xe0\xb4\xa4\xe0\xb4\xb5",
        "പ്രശ്നമുള്ളവ",
        ),
    'nl': (
        104,
        "Proefgelezen",
        "Gecontroleerd",
        "Geen_tekst",
        "Onvolledig",
        ),
    'no': (
        104,
        "Korrekturlest",
        "Validert",
        "Uten_tekst",
        "Ufullstendig",
        ),
    'pl': (
        100,
        "Skorygowana",
        "Uwierzytelniona",
        "Bez_treści",
        "Problemy",
        ),
    'pt': (
        106,
        "!Páginas_revisadas",
        "!Páginas_validadas",
        "!Páginas_sem_texto",
        "!Páginas_problemáticas",
        ),
    'ru': (
        104,
        "Вычитана",
        "Проверена",
        "Без_текста",
        "Проблемная",
        ),
    'sa' : (
        104,
        "परिष्कृतम्",
        "पुष्टितम्",
        "लेखरहितम्",
        "समस्यात्मकः",
        ),
    'sl': (
        100,
        "Korigirano",
        "Potrjeno",
        "Brez_besedila",
        "Problematične_strani",
        ),
    'sv': (
        104,
        "Korrekturläst",
        "Validerat",
        "Utan_text",
        "Ofullständigt",
        ),
    'te': (
        104,
        "అచ్చుదిద్దబడినవి",
        "ఆమోదించబడ్డవి",
        "పాఠ్యం_లేనివి",
        "అచ్చుదిద్దుడు_సమస్యాత్మకం",
        ),
    'vec': (
        102,
        "Pagine_trascrite",
        "Pagine_rilete",
        "Pagine_sensa_testo",
        "Pagine_da_sistemar",
        ),
    'vi': (
        104,
        "Đã_hiệu_đính",
        "Đã_phê_chuẩn",
        "Không_có_nội_dung",
        "Có_vấn_đề",
        ),
    'zh': (
        104,
        "已校对",
        "已核对",
        "没有文字",
        "有问题",
        ),
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

def check_quality_cat(domain):
    print domain
    result = []
    site = wikipedia.getSite(domain,fam='wikisource')
    for i in [ 3, 4, 0, 2 ]:
        cat_name = "quality%d_category" % i
        msg_name = "Proofreadpage_" + cat_name
        result.append(site.mediawiki_message(msg_name).replace(u' ', u'_'))
    if [ unicode(x, 'utf-8') for x in domain_urls[domain][1:] ] != result:
        print domain, domain_urls[domain], [x.encode('utf-8') for x in result]
        print domain_urls[domain][0],
        for r in domain_urls[domain][1:]:
            print unicode(r, 'utf-8'),
        print
        print domain_urls[domain][0],
        print result[0], result[1], result[2], result[3]

def check_all_quality_cat(domains):
    for dom in domains:
        if dom == 'old':
            continue
        check_quality_cat(dom)

def dump_pagenum_template(domain):
    site = wikipedia.getSite(domain,fam='wikisource')
    page = wikipedia.Page(site,"Mediawiki:Proofreadpage_pagenum_template")
    #page = wikipedia.Page(site,"Mediawiki:Disambiguationspage")
    print domain,
    try:
        t = page.get()
        print repr(t)
    except:
        pass

def dump_all_pagenum_template(domains):
    for dom in domains:
        if dom == 'old':
            continue
        dump_pagenum_template(dom)

if __name__ == "__main__":
    import wikipedia
    domains = domain_urls.keys()
    #dump_all_pagenum_template(domains)
    check_all_quality_cat(domains)
