from data.models import Story, User, text2im, upload_im, yandex_rss, globo_rss, spacy_proc, reverso_proc, StoryGen
from data import db_session
import os,json,random
from flask import Flask, request
import ru_core_news_sm
import pt_core_news_sm
#import atexit
#from apscheduler.schedulers.background import BackgroundScheduler



app = Flask(__name__)
@app.route('/post', methods=['POST'])
def main():
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False,

        },
    }
    user_id = request.json['session']['user_id']
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(
            id= user_id,
            state=0,
            response='',
            image_id=''
        )
        db_sess.add(user)
    if request.json['request']['command'] == 'помощь':
        state_101(response, request.json, user, db_sess)
    elif request.json['session']['new']:
        state_0(response, request.json, user, db_sess)
    else:
        # предварительно проверим ожидается ли такой запрос
        a = json.loads(user.response)
        b = [i['title'].lower() for i in a['response']['buttons']]
        #db_sess.commit()
        if request.json['request']['command'] in b:
            dialogue_states[user.state](response, request.json, user, db_sess)
        else:
            state_201(response, request.json, user, db_sess)
    # сохранить response
    user.response = json.dumps({
        'response': response['response']
    },ensure_ascii=False)
    db_sess.commit()
    return json.dumps(response)

# отработка запроса помощь
def state_101(res, req, user, db_sess):
    res['response']['text'] = 'Помощь'
    res['response']['buttons'] = [
        {
            'title': 'Выйти',
            'hide': 'True'
        },
        {
            'title': 'В начало',
            'hide': 'True'
        },
        {
            'title': 'Возобновить',
            'hide': 'True'
        }
    ]
    user.state_old = user.state
    user.response_old = user.response
    user.state = 102
    return

def state_102(res,req, user, db_sess):
    if req['request']['command'] == 'выйти':
        res['response']['text'] = 'До свидания!'
        res['response']['end_session'] = True
    elif req['request']['command'] == 'в начало':
        # начинаем сессию
        state_0(res, req, user, db_sess)
    else:
        a = json.loads(user.response_old)
        res['response'] = a['response']
        user.state = user.state_old
    return

def state_201(res,req, user, db_sess):
    res['response']['text'] = 'Некорректный запрос'
    a = json.loads(user.response)
    res['response']['buttons'] = a['response']['buttons']
    return

def state_0(res, req, user, db_sess):
    res['response']['text'] = 'Приложение Идиомотека работает в режиме чтения новостей и спряжения глаголов'
    res['response']['buttons'] = [
        {
            'title': 'Хочу спрягать',
            'hide': 'True'
        },

        {
            'title': 'Хочу читать',
            'hide': 'True'
        }
    ]
    user.state = 1
    return

def state_1(res, req, user, db_sess):
    if req['request']['command'] == 'хочу спрягать':
        user.mode = 'conjugation'
    if req['request']['command'] == 'хочу читать':
        user.mode = 'reading'
    res['response']['text'] = 'Выберите язык'
    res['response']['buttons'] = [
        {
            'title': 'Русский',
            'hide': 'True'
        },

        {
            'title': 'Португальский',
            'hide': 'True'
        }
    ]
    user.state = 2
    return

def state_2(res, req, user, db_sess):
    if req['request']['command'] == 'русский':
        user.language = 'russian'
    if req['request']['command'] == 'португальский':
        user.language = 'portuguese'
    #Проводим проверку наличия рассказов
    if user.stories:
        for i in user.stories:
            a = json.loads(i.content)
            # если рассказ найден, предлагаем заменить
            if a['language'] == user.language:
                res['response']['text'] = 'Обновить рассказ?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': 'True'
                    },
                    {
                        'title': 'Нет',
                        'hide': 'True'
                    },
                ]
                user.state = 3
                return
    #в противном случае загружаем новый
    with open(story_dict[user.language][0], 'rt', encoding='utf8') as f:
        a = json.load(f)
    story = Story(
        content=json.dumps(a, ensure_ascii=False),
        user_id=request.json['session']['user_id'],
        counter=0
    )
    db_sess.add(story)
    user.stories += [story]
    if user.mode == 'reading':
        state_4(res, req, user, db_sess)
    else:
        state_6(res, req, user, db_sess)
    return

def state_3(res,req, user, db_sess):
    if req['request']['command'] == 'да':
        for i in user.stories:
            a = json.loads(i.content)
            if a['language']==user.language:
                user.stories.remove(i)
                break
        with open(story_dict[user.language][0], 'rt', encoding='utf8') as f:
            a = json.load(f)
        print('рассказ обновлен')
        story = Story(
            content=json.dumps(a, ensure_ascii=False),
            user_id=request.json['session']['user_id'],
            counter=0
        )
        db_sess.add(story)
        user.stories += [story]
    if user.mode == 'reading':
        state_4(res, req, user, db_sess)
    else:
        state_6(res, req, user, db_sess)
    return

def state_4(res, req, user, db_sess):
    # достаем рассказ
    for i in user.stories:
        #ищем рассказ по языку
        a = json.loads(i.content)
        if a['language'] == user.language:
            #проверяем наличие отрывка
            print(i.counter)
            if i.counter < len(a['abstracts']):
                res['response']['text'] = f'{a["abstracts"][i.counter]["title"]}'
                res['response']['text'] += '\n---\n'
                res['response']['text'] += f'{a["abstracts"][i.counter]["description"][:300]}'
                txt1=f'{a["abstracts"][i.counter]["title"]}\n\n'
                txt2=f'{a["abstracts"][i.counter]["description"]}'
                text2im(txt1, txt2, '', '5.png')
                im=upload_im('5.png',user.image_id)
                print(im)
                if im:
                    user.image_id=im
                else:
                    user.image_id=''
                res['response']['card'] = {}
                res['response']['card']['type'] = 'BigImage'
                res['response']['card']['image_id'] = im
                res['response']['buttons'] = [
                    {
                        'title': 'Следующий',
                        'hide': 'True'
                    },
                ]
                i.counter += 1
                user.state = 4
            else:
                res['response']['text'] = 'Рассказов больше нет'
                res['response']['buttons'] = [
                    {
                        'title': 'Повторить',
                        'hide': 'True'
                    },
                    {
                        'title': 'Выйти',
                        'hide': 'True'
                    },
                    {
                        'title': 'В начало',
                        'hide': 'True'
                    },
                ]
                user.state = 5
    return

def state_5(res,req, user, db_sess):
    if req['request']['command'] == 'выйти':
        res['response']['text'] = 'До свидания!'
        res['response']['end_session'] = True
        return
    elif req['request']['command'] == 'в начало':
        state_0(res, req, user, db_sess)
        return
    else:
        # Повторить
        for i in user.stories:
            # ищем рассказ по языку
            a = json.loads(i.content)
            if a['language'] == user.language:
                i.counter = 0
    state_4(res,req, user, db_sess)
    return

def state_6(res,req, user, db_sess):
    for i in user.stories:
        #ищем рассказ по языку
        a = json.loads(i.content)
        if a['language'] == user.language:
            print(i.counter)
            if i.counter < len(a['abstracts']):
                res['response']['text'] = f'{a["abstracts"][i.counter]["title"]}'
                res['response']['text'] += '\n---\n'
                res['response']['text'] += f'{a["abstracts"][i.counter]["description"][:300]}'
                txt1=f'{a["abstracts"][i.counter]["title"]}\n\n'
                txt2=f'{a["abstracts"][i.counter]["description"]}'
                # заменяем слово на инфинитив
                txt2=txt2.replace(a["abstracts"][i.counter]["verb"],
                             a["abstracts"][i.counter]["infinitive"],1)
                text2im(txt1, txt2, a["abstracts"][i.counter]["infinitive"], '5.png')

                im=upload_im('5.png',user.image_id)
                print(im)
                if im:
                    user.image_id=im
                else:
                    user.image_id=''
                res['response']['card'] = {}
                res['response']['card']['type'] = 'BigImage'
                res['response']['card']['image_id'] = im
                res['response']['buttons'] = []
                # достаем глагол
                wl = set([a["abstracts"][i.counter]["verb"]]+\
                     random.choices(a["abstracts"][i.counter]["conjugation"], k=5))
                for j in wl:
                    res['response']['buttons']+=[
                        {
                            'title': j,
                            'hide': 'True'
                        },
                    ]
                user.state = 7
            else:
                res['response']['text'] = 'Рассказов больше нет'
                res['response']['buttons'] = [
                    {
                        'title': 'Повторить',
                        'hide': 'True'
                    },
                    {
                        'title': 'Выйти',
                        'hide': 'True'
                    },
                    {
                        'title': 'В начало',
                        'hide': 'True'
                    },
                ]
                user.state = 8
    return

def state_7(res,req, user, db_sess):
    for i in user.stories:
        #ищем рассказ по языку
        a = json.loads(i.content)
        if a['language'] == user.language:
            v=a["abstracts"][i.counter]['verb']
            if req['request']['command'] == v:
                res['response']['text'] = 'Правильно'
            else:
                res['response']['text'] = f'Ошибка, правильное слово "{v}"'
            res['response']['buttons'] = [
                {
                    'title': 'Следующий',
                    'hide': 'True'
                },
            ]
            i.counter += 1
            break
    user.state=6
    return

def state_8(res,req, user, db_sess):
    if req['request']['command'] == 'выйти':
        res['response']['text'] = 'До свидания!'
        res['response']['end_session'] = True
        return
    elif req['request']['command'] == 'в начало':
        state_0(res, req, user, db_sess)
        return
    else:
        # Повторить
        for i in user.stories:
            # ищем рассказ по языку
            a = json.loads(i.content)
            if a['language'] == user.language:
                i.counter = 0
    state_6(res, req, user, db_sess)
    return

story_dict={
    'russian':['russian.json','Русский'],
    'portuguese':['portuguese.json','Португальский']
}
dialogue_states = {
    0: state_0,
    1: state_1,
    2: state_2,
    3: state_3,
    4: state_4,
    5: state_5,
    6: state_6,
    7: state_7,
    8: state_8,
    #состояние помощи
    101: state_101,
    102: state_102,
    #состояние некорретного запроса
    201: state_201
}

def russ():
    a=StoryGen(yandex_rss['20'], lang='russian').basic(n=3)
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

#scheduler = BackgroundScheduler()
#scheduler.add_job(func=russ, trigger="interval", minutes=1)
#scheduler.start()
#atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    if os.path.exists('db/stories.db'):
        os.remove('db/stories.db')
    db_session.global_init("db/stories.db")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    #app.run()

#pipreqs --encoding --force utf-8 "./"


