from data.models import StoryGen, yandex_rss, globo_rss, spacy_proc, reverso_proc
import json
import ru_core_news_sm
import pt_core_news_sm

# загружаем рассказ на русском языке
def russ():
    a=StoryGen(yandex_rss['24'], lang='russian').basic(n=3)
    # проходим по каждому отрывку
    to_del=[]
    for n, i in enumerate(a['abstracts']):
        print(f'Отрывок: {n+1}')
        j=spacy_proc(i['description'],ru_core_news_sm)
        k = reverso_proc(j[1], 'russian')
        print(j)
        print(k)
        #уберем слова, где есть дефисы
        k=[i for i in k if '-' not in i]
        print(k)
        #проверяем возможность применять спряжение
        if j and k:
            i['verb']=j[0]
            i['infinitive']=j[1]
            i['conjugation']=k
        else:
            to_del+=[n]
    for i in to_del:
        print('>>>>>>>>>',i)
        del a['abstracts'][i]
    with open('russian.json', 'wt', encoding='utf8') as file:
        json.dump(a, file, ensure_ascii=False,
                    indent=2)


def port():
    a=StoryGen(globo_rss['8'], lang='portuguese').basic(n=3)
    # проходим по каждому отрывку
    to_del=[]
    for n, i in enumerate(a['abstracts']):
        print(f'Отрывок: {n+1}')
        j=spacy_proc(i['description'],pt_core_news_sm)
        k = reverso_proc(j[1], 'portuguese')
        print(j)
        print(k)
        #проверяем возможность применять спряжение
        if j and k:
            i['verb']=j[0]
            i['infinitive']=j[1]
            i['conjugation']=k
        else:
            to_del+=[n]
    for i in to_del:
        print('>>>>>>>>>',i)
        del a['abstracts'][i]
    with open('portuguese.json', 'wt', encoding='utf8') as file:
        json.dump(a, file, ensure_ascii=False,
                    indent=2)
        
port()
russ()