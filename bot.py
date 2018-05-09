import logging
import ssl
from aiohttp import web
import telebot
import messages as m
from telebot import types
import utils as u
import emoji
import random as rand
import requests
from time import sleep
import threading
import json
from tinydb import TinyDB, Query

bot = None
unique_code = None


API_TOKEN = '554249450:AAGI9aHl_7MImr-wcyJ6UPsGB8PR_hgApsQ'



WEBHOOK_HOST = '206.189.30.14'
WEBHOOK_PORT = 8443  # 443, 80, 88 or 8443 (port need to be 'open')
WEBHOOK_LISTEN = '206.189.30.14'  # In some VPS you may need to put here the IP addr

WEBHOOK_SSL_CERT = './webhook_cert.pem'  # Path to the ssl certificate
WEBHOOK_SSL_PRIV = './webhook_pkey.pem'  # Path to the ssl private key

# Quick'n'dirty SSL certificate generation:
#
# openssl genrsa -out webhook_pkey.pem 2048
# openssl req -new -x509 -days 3650 -key webhook_pkey.pem -out webhook_cert.pem
#
# When asked for "Common Name (e.g. server FQDN or YOUR name)" you should reply
# with the same value in you put in WEBHOOK_HOST

WEBHOOK_URL_BASE = "https://{}:{}".format(WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/{}/".format(API_TOKEN)


logger = telebot.logger
telebot.logger.setLevel(logging.INFO)
bot = telebot.TeleBot(API_TOKEN)
app = web.Application()

db = TinyDB('db.json')
tableBanned = db.table('bannedUsers')
tableKnown = db.table('knownUsers')
tableSubmitedID = db.table('submittedUsers')

user_dict = {}
knownUsers = [item["Uid"] for item in tableKnown]
bannedUsers= [item["Uid"] for item in tableBanned]
submittedUsers=[item["Uid"] for item in tableSubmitedID]



class User:
    def __init__(self,telegramID):
        self.etherium = None
        self.twitter = None
        self.twitter_repost = None
        self.facebook = None
        self.fb_repost = None
        self.email = None
        self.yes0=False
        self.yes1=False
        self.refferal = None
        self.telegramid = telegramID
        self.submited = False
    def to_json(self):
        return {
            'etherium': self.etherium,
            'twitter': self.twitter,
            'twitter_repost': self.twitter_repost,
            'facebook': self.facebook,
            'fb_repost': self.fb_repost,
            'email': self.email,
            'yes0': self.yes0,
            'yes1': self.yes1,
            'refferal': self.refferal,
            'telegramid': self.telegramid,
        }


def extract_unique_code(text):
    return text.split()[1] if len(text.split()) > 1 else None

# Process webhook calls
async def handle(request):
    if request.match_info.get('token') == bot.token:
        request_body_dict = await request.json()
        update = telebot.types.Update.de_json(request_body_dict)
        bot.process_new_updates([update])
        return web.Response()
    else:
        return web.Response(status=403)

app.router.add_post('/{token}/', handle)



@bot.callback_query_handler(func=lambda c: c.data)
def submit(c):
    print(c.data)
    uid = c.message.from_user.id
    chat_id = c.message.chat.id
    if uid not in submittedUsers:
        if(c.data=='to_Yes'):
            msg = bot.send_message(chat_id, m.yes1)
            user = user_dict[chat_id]
            user.yes0=True
            process_yes_step(msg)
            return
        elif(c.data=="to_No"):
            msg = bot.send_message(chat_id, m.no1)
            user = user_dict[chat_id]
            process_human_step(msg)
            return
        elif(c.data=="to_Yes1"):
            msg = bot.send_message(chat_id, m.yes1_click)
            user = user_dict[chat_id]
            user.yes1=True
            process_human_step(c.message)
            return
        elif(c.data=="to_No1"):
            process_human_step(c.message)
            return

    if uid not in submittedUsers:
        msg = bot.send_message(chat_id, m.eth)
        bot.register_next_step_handler(msg, process_twitter_step)

def process_twitter_step(message):
    try:
        if(message.text=='/cancel'):
            cancel(message)
            return
        chat_id = message.chat.id
        adress = message.text
        if (not u.is_adress(adress)):
            msg = bot.send_message(chat_id, m.eth_error)
            bot.register_next_step_handler(msg, process_twitter_step)
            return
        global unique_code
        user = User(message.from_user.username)
        user.etherium=adress
        user.refferal=unique_code
        user_dict[chat_id] = user
        msg = bot.send_message(chat_id, m.twitter)
        bot.register_next_step_handler(msg, process_twitter_repost_step)
    except Exception as e:
        msg = bot.send_message(chat_id, m.eth_error)
        bot.register_next_step_handler(msg, process_twitter_step)

def process_twitter_repost_step(message):
    try:
        if(message.text=='/cancel'):
            cancel(message)
            return
        chat_id = message.chat.id
        twitter = message.text
        if ((u.is_twitter(twitter)) and (twitter!='nil')):
            msg = bot.send_message(chat_id, m.twitter_error)
            bot.register_next_step_handler(msg, process_twitter_repost_step)
            return
        user = user_dict[chat_id]
        user.twitter=twitter
        msg = bot.send_message(chat_id, m.twitter_repost)
        bot.register_next_step_handler(msg, process_facebook_step)
    except Exception as e:
        msg = bot.send_message(chat_id, m.facebook_error)
        bot.register_next_step_handler(msg, process_twitter_repost_step)



def process_facebook_step(message):
    try:
        if(message.text=='/cancel'):
            cancel(message)
            return
        chat_id = message.chat.id
        twitter_repost = message.text
        if (not (u.is_twitter_repost(twitter_repost)) and (twitter_repost!='nil')):
            msg = bot.send_message(chat_id, m.twitter_repost_error)
            bot.register_next_step_handler(msg, process_facebook_step)
            return
        user = user_dict[chat_id]
        user.twitter_repost=twitter_repost
        msg = bot.send_message(chat_id, m.facebook)
        bot.register_next_step_handler(msg, process_fb_repost_step)
    except Exception as e:
        print(str(e))
        msg = bot.send_message(chat_id, m.twitter_repost_error)
        bot.register_next_step_handler(msg, process_facebook_step)

def process_fb_repost_step(message):
    try:
        if(message.text=='/cancel'):
            cancel(message)
            return
        chat_id = message.chat.id
        facebook = message.text
        if ((not u.is_facebook(facebook)) and (facebook!='nil')):
            msg = bot.send_message(chat_id, m.facebook_error)
            bot.register_next_step_handler(msg, process_fb_repost_step)
            return
        user = user_dict[chat_id]
        user.facebook=facebook
        msg = bot.send_message(chat_id, m.fb_repost)
        bot.register_next_step_handler(msg, process_email_step)
    except Exception as e:
        msg = bot.send_message(chat_id, m.facebook_error)
        bot.register_next_step_handler(msg, process_fb_repost_step)

def process_email_step(message):
    try:
        if(message.text=='/cancel'):
            cancel(message)
            return
        chat_id = message.chat.id
        facebook_repost = message.text
        if ((not u.is_facebook(facebook_repost)) and (facebook_repost!='nil')):
            msg = bot.send_message(chat_id, m.facebook_repost_error)
            bot.register_next_step_handler(msg, process_email_step)
            return
        user = user_dict[chat_id]
        user.fb_repost=facebook_repost
        msg = bot.send_message(chat_id, m.email)
        bot.register_next_step_handler(msg,process_question_step)
    except Exception as e:
        msg = bot.send_message(chat_id, m.facebook_repost_error)
        bot.register_next_step_handler(msg, process_email_step)
def process_question_step(message):
    try:
        email = message.text
        chat_id = message.chat.id
        if ((not u.is_email(email)) and (email!='nil')):
            msg = bot.send_message(chat_id, m.email_error)
            bot.register_next_step_handler(msg, process_human_step)
            return
        user = user_dict[chat_id]
        user.email = email
        keyboard = types.InlineKeyboardMarkup()
        btns=[]
        url_button1 = types.InlineKeyboardButton(text=m.yes, callback_data='to_{}'.format("Yes"))
        url_button2 = types.InlineKeyboardButton(text=m.no, callback_data='to_{}'.format("No"))
        btns.append(url_button1)
        btns.append(url_button2)
        keyboard.add(*btns)
        bot.send_message(chat_id, m.question, reply_markup=keyboard)
    except:
        msg = bot.send_message(chat_id, m.email_error)
        bot.register_next_step_handler(msg, process_question_step)

def process_yes_step(message):
    try:
        chat_id = message.chat.id
        uid = message.from_user.id
        keyboard = types.InlineKeyboardMarkup()
        btns=[]
        url_button1 = types.InlineKeyboardButton(text=m.yes1,callback_data='to_{}'.format("Yes1"))
        url_button2 = types.InlineKeyboardButton(text=m.no1, callback_data='to_{}'.format("No1"))
        btns.append(url_button1)
        btns.append(url_button2)
        keyboard.add(*btns)
        bot.send_message(chat_id, m.bonus, reply_markup=keyboard)
    except Exception as e:
        print(str(e))


def process_human_step(message):
    try:
        chat_id = message.chat.id
        uid = message.from_user.id
        numbers=[':keycap_0:',':keycap_1:',':keycap_2:',':keycap_3:',':keycap_4:',':keycap_5:',':keycap_6:',':keycap_7:',':keycap_8:',':keycap_9:']
        first = rand.randint(0,9)
        second = rand.randint(first,9)
        answer = second - first
        msg = bot.send_message(chat_id, m.human.format(emoji.emojize(numbers[int(second)]),emoji.emojize(numbers[int(first)])).encode(encoding='utf_8'))
        bot.register_next_step_handler(msg, lambda m: process_confirm_step(m, answer,1))
    except Exception as e:
        print(str(e))
        msg = bot.send_message(chat_id, m.email_error)
        bot.register_next_step_handler(msg, process_human_step)

def process_confirm_step(message,answer,count):
	try:
		chat_id = message.chat.id
		uid = message.from_user.id
		ans = message.text
		count+=1
		if (int(ans)!=int(answer)):
			if(count<3):
				msg = bot.send_message(chat_id, m.human_error.format(count))
				bot.register_next_step_handler(msg, lambda m: process_confirm_step(m, answer,count))
				return
			else:
				msg = bot.send_message(chat_id, m.human_error_last)
				bannedUsers.append(uid)
				tableBanned.insert({'Uid': uid})
				return

		process_end_step(message)
	except Exception as e:
		bot.reply_to(message, 'oooops')

def process_end_step(message):
    try:
        chat_id = message.chat.id
        user = user_dict[chat_id]
        uid = message.from_user.id
        bot.send_message(chat_id, m.success.format(str(user.etherium),str(user.twitter),str(user.twitter_repost),str(user.facebook),str(user.fb_repost),str(user.email),str(message.from_user.username),str(message.from_user.username)))
        user.submited = True
        r = requests.post("https://script.google.com/macros/s/AKfycbwR3iI-H-RWBwxtXMKvghPZ20O0lwt8Cus-ibjfPXKBr4T2iO9g/exec",json=user.to_json())
        submittedUsers.append(uid)
        tableSubmitedID.insert({'Uid': uid});
    except Exception as e:
        print(str(e))
        bot.send_message(chat_id, 'Try Again')


def cancel(message):
    cid = message.chat.id
    username = message.from_user.username
    uid = message.from_user.id
    if(uid in knownUsers):
        if(uid in submittedUsers):
            bot.send_message(cid,m.byeKnown.format(username))
        else:
            bot.send_message(cid,m.bye.format(username))
            knownUsers.remove(uid)
    else:
        return


@bot.message_handler(commands=['cancel'])
def cancel(message):
    cid = message.chat.id
    username = message.from_user.username
    uid = message.from_user.id
    if(uid in knownUsers):
        if(uid in submittedUsers):
            bot.send_message(cid,m.byeKnown.format(username))
        else:
            bot.send_message(cid,m.bye.format(username))
            knownUsers.remove(uid)
    else:
        return
@bot.message_handler(commands=['start'])
def id(message):
    global unique_code
    unique_code = extract_unique_code(message.text)
    cid = message.chat.id
    username = message.from_user.username
    uid = message.from_user.id
    if(uid in bannedUsers):
        bot.send_message(cid, m.banned)
        return
    if(uid in knownUsers):
        if(uid in submittedUsers):
            bot.send_message(cid, m.knownUser.format(username,username))
            return


    keyboard = types.InlineKeyboardMarkup()
    btns=[]
    btns1=[]
    url_button1 = types.InlineKeyboardButton(text=m.url_button1, url="https://akaiito.io/home/")
    url_button2 = types.InlineKeyboardButton(text=m.url_button2, url="https://t.me/akaiito_community")
    url_button3 = types.InlineKeyboardButton(text=m.url_button3, url="https://www.facebook.com/officialakaiito")
    url_button4 = types.InlineKeyboardButton(text=m.url_button4, url="https://www.facebook.com/officialakaiito/posts/1992027131125478")
    url_button5 = types.InlineKeyboardButton(text=m.url_button5, url="https://twitter.com/OfficialAkaiito")
    url_button6 = types.InlineKeyboardButton(text=m.url_button6, url="https://twitter.com/OfficialAkaiito/status/983419777132781574")
    sub_button = types.InlineKeyboardButton(text=m.sub_button, callback_data='to_{}')
    btns.append(url_button3)
    btns.append(url_button4)
    btns1.append(url_button5)
    btns1.append(url_button6)
    keyboard.add(url_button1)
    keyboard.add(url_button2)
    keyboard.add(*btns)
    keyboard.add(*btns1)
    keyboard.add(sub_button)
    knownUsers.append(uid)
    tableKnown.insert({'Uid': uid});
    bot.send_message(cid, m.hello.format(username), reply_markup=keyboard)



bot.remove_webhook()


bot.set_webhook(url=WEBHOOK_URL_BASE+WEBHOOK_URL_PATH,
				certificate=open(WEBHOOK_SSL_CERT, 'r'))


context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV)


web.run_app(
    app,
    host=WEBHOOK_LISTEN,
    port=WEBHOOK_PORT,
    ssl_context=context,
)
