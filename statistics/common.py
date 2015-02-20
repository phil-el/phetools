# -*- coding: utf-8 -*-
import sys

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
    'ro':'Dezambig',
    'ru':'Disambig',    
    'sl':'Razločitev',
    'sv':'Förgreningssida',
    'te':'అయోమయ నివృత్తి',
    'vec':'Disambigua',
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
    pass
