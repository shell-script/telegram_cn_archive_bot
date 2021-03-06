#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dbm
import os
import socket

import requests
import socks
from html_telegraph_poster import TelegraphPoster
from telegram import MessageEntity
from telegram.ext import Updater, MessageHandler, Filters
from telegram_util import matchKey, log_on_fail

import webpage2telegraph

socks_none = socket.socket
try:
    os.environ['NO_PROXY'] = 'api.telegram.org,api.telegra.ph'
    socks.set_default_proxy(socks.PROXY_TYPE_SOCKS5, addr='127.0.0.1', port=9050, rdns=True)
    old_getaddrinfo = socket.getaddrinfo


    def new_getaddrinfo(*args, **kwargs):
        responses = old_getaddrinfo(*args, **kwargs)
        return [response for response in responses if response[0] == socket.AF_INET]  # 强制使用ipv4


    socket.getaddrinfo = new_getaddrinfo
    socket.socket = socks.socksocket
    requests.head('http://checkip.amazonaws.com', allow_redirects=False)
except:
    socket.socket = socks_none

with open('token') as f:
    tele = Updater(f.read().strip(), use_context=True)

debug_chat = tele.bot.get_chat(656869271)

source_flags = dbm.open('source_flags.db', 'c')
simplify_flags = dbm.open('simplify_flags.db', 'c')
telegraph_tokens = dbm.open('telegraph_tokens.db', 'c')


# def save_telegraph_tokens():
# 	telegraph_tokens.sync()


def get_from(msg):
    if msg.from_user:
        return msg.from_user.id, msg.from_user.first_name, msg.from_user.username
    return msg.chat_id, msg.chat.title, msg.chat.username  # from channel


def send_auth_url(msg, p):
    r = p.get_account_info(fields=['auth_url'])
    msg.reply_text('如果你需要编辑生成的 Telegraph，或者绑定到你的账户以便日后编辑，请在五分钟内点此链接登录：' + r['auth_url'])


def get_telegraph_token(msg):
    from_id, name, username = get_from(msg)
    fid = str(from_id)
    if fid in telegraph_tokens:
        p = TelegraphPoster(access_token=telegraph_tokens[fid])
    else:
        p = TelegraphPoster()
        r = p.create_api_token(name, username)
        telegraph_tokens[fid] = r['access_token']
    # save_telegraph_tokens()
    send_auth_url(msg, p)


def get_telegraph(msg, url):
    from_id, _, _ = get_from(msg)
    fid = str(from_id)
    if fid not in telegraph_tokens:
        get_telegraph_token(msg)

    webpage2telegraph.token = telegraph_tokens[fid]
    simplify = fid in source_flags
    source = fid in source_flags
    return webpage2telegraph.transfer(url, throw_exception=True, source=source, simplify=simplify)


def transfer(msg):
    for item in msg.entities:
        url = ''
        if item['type'] == 'url':
            url = msg.text[item['offset']:][:item['length']]
        elif item['type'] == 'text_link':
            t = msg.text[item['offset']:][:item['length']]
            if not matchKey(t, ['source', '原文']):
                url = item['url']
        else:
            continue
        if '://' not in url:
            url = 'http://' + url
        elif not url.startswith('http'):
            continue
        result = get_telegraph(msg, url)
        if str(msg.chat_id) in source_flags:
            msg.chat.send_message('%s\n[原文](%s)' % (result, url), parse_mode='Markdown')
        else:
            msg.chat.send_message(result)


@log_on_fail(debug_chat)
def archive(update, context):
    if update.edited_message or update.edited_channel_post:
        return
    msg = update.effective_message
    if msg.forward_from and msg.forward_from.username == 'CNArchiveBot':
        return
    try:
        r = msg.chat.send_message('正在存档…')
    except:
        return
    try:
        transfer(msg)
    except Exception as e:
        msg.chat.send_message(str(e))
        if not matchKey(str(e), ['Content is too big.']):
            raise e
    finally:
        r.delete()


def switch_source_flag(msg):
    from_id, _, _ = get_from(msg)
    fid = str(from_id)
    if fid in source_flags:
        del source_flags[fid]
        msg.reply_text('将隐藏原文链接')
    else:
        source_flags[fid] = b'1'
        msg.reply_text('将展示原文链接')


# source_flags.sync()


def switch_simplify_flag(msg):
    from_id, _, _ = get_from(msg)
    fid = str(from_id)
    if fid in simplify_flags:
        del simplify_flags[fid]
        msg.reply_text('将不再繁简转换')
    else:
        simplify_flags[fid] = b'1'
        msg.reply_text('将进行繁简转换')


# source_flags.sync()


with open('help.md') as f:
    help_message = f.read()


@log_on_fail(debug_chat)
def command(update, context):
    msg = update.message
    if matchKey(msg.text, ['auth', 'token']):
        return get_telegraph_token(msg)
    if matchKey(msg.text, ['source']):
        return switch_source_flag(msg)
    if matchKey(msg.text, ['simplify']):
        return switch_simplify_flag(msg)
    if msg.chat_id > 0:  # from private
        msg.reply_text(help_message)


tele.dispatcher.add_handler(
    MessageHandler(Filters.text & (Filters.entity(MessageEntity.URL) | Filters.entity(MessageEntity.TEXT_LINK)),
                   archive))
tele.dispatcher.add_handler(MessageHandler(Filters.command, command))

tele.start_polling()
tele.idle()
