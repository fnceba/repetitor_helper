import telebot
import datetime
import sqlite3
import time
import threading

token=''
repetid=307518206
hour, minute = 8, 00
remind=False

bot = telebot.TeleBot(token)
conn = sqlite3.connect('myrepet.db',  check_same_thread=False)
curs = conn.cursor()
curs.execute('CREATE TABLE IF NOT EXISTS lessons (name TEXT, day INTEGER, time INTEGER, money INTEGER)')

daysofweek = ['ПН','ВТ','СР','ЧТ','ПТ','СБ','ВС']


def get_keyboard(day):
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=6)
    btnlist = []
    curs.execute(f'SELECT time FROM lessons WHERE day={day}')
    zanyato = curs.fetchall()
    for hour in range(9,22):
        btnlist.append(telebot.types.InlineKeyboardButton(str(hour)+['','🟡'][int((hour,) in zanyato)],callback_data=f'{day} {hour}'))

    keyboard.add(*btnlist)

    nextandprevious=[]
    if day==0:
        nextandprevious.append(telebot.types.InlineKeyboardButton('->', callback_data='1'))
    elif day==6:
        nextandprevious.append(telebot.types.InlineKeyboardButton('<-', callback_data='5'))
    else:
        nextandprevious.append(telebot.types.InlineKeyboardButton('<-', callback_data=str(day - 1)))
        nextandprevious.append(telebot.types.InlineKeyboardButton('->', callback_data=str(day + 1)))
    
    keyboard.add(*nextandprevious)
    return keyboard

@bot.message_handler(commands=['remind_now'])
def remind_now(message):
    if message.chat.id == repetid:
        global remind
        remind=True

@bot.message_handler(commands=['money'])
def get_money(message):
    if message.chat.id == repetid:
        curs.execute('SELECT SUM(money) FROM lessons')
        money=curs.fetchone()[0]
        if money and money!=0:
            bot.send_message(message.chat.id,f'💰Ты зарабатываешь {money}р!💰')
        else:
            bot.send_message(message.chat.id,f'Ты нисколько не зарабатываешь :(')

@bot.message_handler(commands=['schedule'])
def get_schedule(message):
    if message.chat.id == repetid:
        wd = datetime.datetime.today().weekday()
        bot.send_message(message.chat.id,daysofweek[wd]+':', reply_markup=get_keyboard(wd))

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.id!=repetid:
        msg = bot.send_message(message.chat.id,f'Я буду присылать тебе уведомления, {message.chat.firstname}. Для этого отправь мне свой номер телефона в формате +71234567890')
        bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
        bot.register_next_step_handler(msg, save_id_step)
    else:
        bot.send_message(message.chat.id,f'Выберите команду:\n Просмотреть или изменить расписание: /schedule\n Чтобы узнать, когда ты занимаешься с конкретным учеником, отправь команду /get_lessons_by_name.\n Чтобы получить всех учеников, с которыми ты занимаешься, отправь /get_all\nЧтобы узнать, сколько ты зарабатываешь за неделю, напиши /money')

def save_id_step(message):
    curs.execute(f'DELETE FROM usernames WHERE id="{message.chat.id}"')
    curs.execute('INSERT INTO usernames VALUES(?,?)',(message.text,message.chat.id))
    conn.commit()
    bot.send_message(message.chat.id,f'Теперь я могу присылать тебе уведомления!')


@bot.message_handler(commands=['get_all'])
def get_username(message):
    if message.chat.id == repetid:
        curs.execute('SELECT DISTINCT name FROM lessons')
        fetall=curs.fetchall()
        mestosend=f'Ты занимаешься с:'
        if not fetall:
            mestosend='Ты ни с кем не занимаешься :('
        else:
            for fet in fetall:
                mestosend+=f'\n - {fet[0]}'
        bot.send_message(message.chat.id,mestosend)    

@bot.message_handler(commands=['get_lessons_by_name'])
def get_username(message):
    if message.chat.id == repetid:
        msg = bot.send_message(message.chat.id,f'Введи его имя')
        bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
        bot.register_next_step_handler(msg, get_username_step)

def get_username_step(message):
    username= message.text
    mestosend=f'С {username} ты занимаешься:'
    curs.execute(f'SELECT day,time,money FROM lessons WHERE name="{username}"')
    fetall=curs.fetchall()
    if not fetall:
        mestosend='Ты с ним не занимаешься!'
    else:
        for fet in fetall:
            mestosend+=f'\n - по {daysofweek[fet[0]]} в {fet[1]}:00 за {fet[2]}руб'
    bot.send_message(message.chat.id,mestosend)
    

@bot.message_handler(content_types=['text'])
def text(message):
    send_welcome(message)

@bot.callback_query_handler(func=lambda call: ' ' in call.data)
def callback_inline_time_click(call):
    date  = call.data.split(' ')
    curs.execute(f'SELECT name,money FROM lessons WHERE day={int(date[0])} and time={int(date[1])}')
    namemoney = curs.fetchone()
    if namemoney:
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton('Удалить', callback_data=f'{date[0]}_{date[1]}'), telebot.types.InlineKeyboardButton('Изменить', callback_data=f'{date[0]}-{date[1]}'))
        bot.send_message(call.message.chat.id,f'По {daysofweek[int(date[0])]} в {int(date[1])}:00 ты занимаешься с {namemoney[0]} за {namemoney[1]} руб.', reply_markup=keyboard)
    else:
        msg = bot.send_message(call.message.chat.id,f'Введи имя ученика:')
        bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
        bot.register_next_step_handler(msg,lambda m: name_step(m,date))


@bot.callback_query_handler(func=lambda call: '_' in call.data)
def callback_inline_delete(call):
    datte = call.data.split('_')
    curs.execute(f'DELETE FROM lessons WHERE day="{datte[0]}" and time="{datte[1]}"')
    conn.commit()
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: '-' in call.data)
def callback_inline_time_click(call):
    msg = bot.send_message(call.message.chat.id,f'Введи имя ученика:')
    bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
    bot.register_next_step_handler(msg,lambda m: name_step(m, date=call.data.split('-')))
    
def name_step(message,date):
    msg = bot.send_message(message.chat.id,f'За сколько ты будешь с ним заниматься?')
    bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
    bot.register_next_step_handler(msg, lambda m: money_step(m,date, message.text))

def strAsInt(s):
    try:
        return int(s)
    except:
        return -1

def money_step(message,date,name):
    money = strAsInt(message.text)
    if money==-1:
        msg = bot.send_message(message.chat.id,f'Ошибка! Должно быть числом.')
        bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
        bot.register_next_step_handler(msg, lambda m: money_step(m,date,name))
    else:
        curs.execute(f'DELETE FROM lessons WHERE day="{date[0]}" and time="{date[1]}"')
        curs.execute('INSERT INTO lessons VALUES(?,?,?,?)',(name, date[0],date[1],money))
        conn.commit()
        bot.send_message(message.chat.id,f'Занятие сохранено!')

@bot.callback_query_handler(func=lambda call: call.data in ['0','1','2','3','4','5','6'])
def callback_inline_time_click(call):
    bot.edit_message_text(chat_id= call.message.chat.id, message_id=call.message.message_id,text=f'{daysofweek[int(call.data)]}:', reply_markup=get_keyboard(int(call.data)))
    

        
def reminder():
    global remind
    while True:
        if datetime.datetime.now().hour == hour and datetime.datetime.now().minute == minute or remind:
            curs.execute(f'SELECT name,time FROM lessons WHERE day={datetime.datetime.today().isoweekday()-1}')
            fetall = curs.fetchall()
            for f in fetall:
                bot.send_message(repetid,f'Сегодня у тебя занятие с {f[0]} в {f[1]}:00')
            remind=False
        time.sleep(60)

th = threading.Thread(target=reminder)
th.setDaemon(True)
th.start()
bot.polling()
